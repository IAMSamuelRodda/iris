/**
 * Fast Layer for Quick Acknowledgments
 *
 * Uses local Qwen 2.5 7B via Ollama for immediate voice feedback while
 * the main model (Claude Sonnet) processes complex requests. Provides
 * natural, contextual acknowledgments with ~130ms latency.
 *
 * Architecture:
 * - User speaks → STT (181ms) → Qwen (130ms) → TTS (42ms) → User hears ack
 * - In parallel: Claude Sonnet processes the main response
 *
 * Benefits over pattern matching:
 * - Contextual responses ("Checking your fleet status" not "Got it")
 * - Natural variation (not robotic repetition)
 * - Understands intent (questions vs commands)
 *
 * Triggered based on voiceStyle.voiceProperties.thinkingFeedback:
 * - "none": No acknowledgments, silent processing
 * - "minimal": Quick contextual acknowledgment
 * - "verbose": Detailed thinking feedback
 */

import { type VoiceStyleId, getVoiceStyle } from "./voice-styles.js";
import { ollamaGenerate, FAST_ACK_MODEL, isOllamaAvailable } from "./ollama-client.js";

// ============================================================================
// Configuration
// ============================================================================

/** System prompt for fast acknowledgment generation */
const FAST_ACK_SYSTEM_PROMPT = `You are IRIS, a voice AI assistant for Star Atlas players.
Generate ONLY a brief acknowledgment (5-8 words) that tells the user you understood
their request and are working on it. Do NOT answer the question - just acknowledge.

Examples:
- "Check my fleet" → "Checking your fleet status now."
- "Why is fuel low?" → "Looking into your fuel situation."
- "What's the price of ATLAS?" → "Pulling up ATLAS prices."
- "Hey IRIS" → "Hey! Ready to help."

Be concise, natural, and contextual.`;

/**
 * Categories of user intent that determine acknowledgment style.
 */
type IntentCategory =
  | "question" // User asking a question
  | "command" // User giving instruction
  | "statement" // User making a statement
  | "greeting" // Social interaction
  | "unclear"; // Ambiguous intent

// ============================================================================
// Types
// ============================================================================

export interface QuickAcknowledgment {
  /** The acknowledgment text to speak immediately */
  text: string;
  /** Detected intent category */
  intent: IntentCategory;
  /** Whether this needs follow-up (main model processing) */
  needsFollowUp: boolean;
  /** Generation latency in ms (for debugging) */
  latencyMs?: number;
}

export interface FastLayerConfig {
  /** Voice style determines acknowledgment behavior */
  voiceStyle: VoiceStyleId;
  /** User ID for context */
  userId: string;
  /** Recent conversation context (last 2-3 exchanges) */
  recentContext?: string;
}

// Track Ollama availability
let ollamaAvailable: boolean | null = null;

// ============================================================================
// Fast Layer Implementation
// ============================================================================

/**
 * Generate a quick acknowledgment using local Qwen 2.5 7B.
 *
 * Uses Ollama for ~130ms response time (vs ~2s for API calls).
 * Falls back to simple acknowledgment if Ollama is unavailable.
 */
export async function generateQuickAcknowledgment(
  userMessage: string,
  config: FastLayerConfig
): Promise<QuickAcknowledgment | null> {
  const style = getVoiceStyle(config.voiceStyle);

  // Skip if style doesn't want acknowledgments
  if (style.voiceProperties.thinkingFeedback === "none") {
    return null;
  }

  // Check Ollama availability (cached)
  if (ollamaAvailable === null) {
    ollamaAvailable = await isOllamaAvailable();
    if (!ollamaAvailable) {
      console.warn("[FastLayer] Ollama not available, using fallback acknowledgments");
    }
  }

  // Build the prompt
  const prompt = buildPrompt(userMessage, config.recentContext, style.voiceProperties.thinkingFeedback === "verbose");

  try {
    const start = Date.now();

    if (ollamaAvailable) {
      // Use local Qwen for contextual acknowledgment
      const response = await ollamaGenerate({
        model: FAST_ACK_MODEL,
        system: FAST_ACK_SYSTEM_PROMPT,
        prompt: prompt,
        options: {
          num_predict: 25, // Short acknowledgments only
          temperature: 0.7,
        },
      });

      const latencyMs = Date.now() - start;
      const text = response.response.trim();

      console.log(`[FastLayer] Qwen ack (${latencyMs}ms): "${text}"`);

      return {
        text: text || "Got it, working on that.",
        intent: detectIntent(userMessage),
        needsFollowUp: true,
        latencyMs,
      };
    } else {
      // Fallback: simple acknowledgment
      return getSimpleFallback(userMessage);
    }
  } catch (error) {
    console.error("[FastLayer] Acknowledgment generation failed:", error);
    // Mark Ollama as unavailable and return fallback
    ollamaAvailable = false;
    return getSimpleFallback(userMessage);
  }
}

/**
 * Check if a message needs acknowledgment based on voice style and content.
 */
export function needsAcknowledgment(userMessage: string, voiceStyle: VoiceStyleId): boolean {
  const style = getVoiceStyle(voiceStyle);

  // No acknowledgments in "none" mode
  if (style.voiceProperties.thinkingFeedback === "none") {
    return false;
  }

  // Very short messages (< 5 chars) are likely noise
  if (userMessage.length < 5) {
    return false;
  }

  // In verbose mode, always acknowledge
  if (style.voiceProperties.thinkingFeedback === "verbose") {
    return true;
  }

  // For minimal mode: acknowledge most messages except very simple greetings
  const simpleGreetings = /^(hi|hey|hello|yo|sup|bye|ok|okay|yes|no|yep|nope|sure|thanks|thank you)[\s!?.]*$/i;
  if (simpleGreetings.test(userMessage.trim())) {
    return false;
  }

  return true;
}

/**
 * Reset Ollama availability check (call if Ollama starts up later).
 */
export function resetOllamaAvailability(): void {
  ollamaAvailable = null;
}

// ============================================================================
// Helpers
// ============================================================================

function buildPrompt(userMessage: string, recentContext?: string, verbose?: boolean): string {
  let prompt = `User: "${userMessage}"`;

  if (recentContext) {
    prompt = `Context:\n${recentContext}\n\n${prompt}`;
  }

  if (verbose) {
    prompt += "\n\nInclude what you're about to check/do.";
  }

  return prompt;
}

function detectIntent(message: string): IntentCategory {
  const lower = message.toLowerCase().trim();

  if (/^(hi|hey|hello|yo|sup)[\s!?,]*/.test(lower)) {
    return "greeting";
  }

  if (/^(what|where|when|why|who|how|can|could|would|is|are|do|does|did)/i.test(lower)) {
    return "question";
  }

  if (/^(check|show|get|find|tell|list|create|start|stop|enable|disable)/i.test(lower)) {
    return "command";
  }

  return "unclear";
}

/**
 * Simple fallback when Ollama is unavailable.
 * Much simpler than pattern matching - just a few generic responses.
 */
function getSimpleFallback(userMessage: string): QuickAcknowledgment {
  const intent = detectIntent(userMessage);

  const fallbacks: Record<IntentCategory, string> = {
    greeting: "Hey there!",
    question: "Let me look into that.",
    command: "On it.",
    statement: "Got it.",
    unclear: "Working on that.",
  };

  return {
    text: fallbacks[intent],
    intent,
    needsFollowUp: true,
  };
}

// Legacy export for backwards compatibility (now unused)
export function getQuickFallback(userMessage: string, voiceStyle: VoiceStyleId): QuickAcknowledgment | null {
  const style = getVoiceStyle(voiceStyle);
  if (style.voiceProperties.thinkingFeedback === "none") {
    return null;
  }
  return getSimpleFallback(userMessage);
}
