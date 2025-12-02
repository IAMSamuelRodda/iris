/**
 * Fast Layer for Quick Acknowledgments
 *
 * Uses Claude Haiku via the Agent SDK for immediate voice feedback while
 * the main model (Sonnet) processes complex requests. Provides natural
 * conversation flow with minimal latency.
 *
 * Uses Agent SDK's query() for consistency with main architecture,
 * enabling future delegation patterns (Haiku -> Sonnet for complex analysis).
 *
 * Triggered based on voiceStyle.voiceProperties.thinkingFeedback:
 * - "none": No acknowledgments, silent processing
 * - "minimal": Quick acknowledgment, then result
 * - "verbose": Detailed thinking feedback throughout
 */

import { query } from "@anthropic-ai/claude-agent-sdk";
import { type VoiceStyleId, getVoiceStyle } from "./voice-styles.js";

// ============================================================================
// Configuration
// ============================================================================

/** Claude Haiku 4.5 for fast acknowledgments */
const HAIKU_MODEL = "claude-haiku-4-5-20251001";

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
  /** Suggested delegation announcement (if applicable) */
  delegationText?: string;
}

export interface FastLayerConfig {
  /** Voice style determines acknowledgment behavior */
  voiceStyle: VoiceStyleId;
  /** User ID for context */
  userId: string;
  /** Recent conversation context (last 2-3 exchanges) */
  recentContext?: string;
}

// ============================================================================
// Fast Layer Implementation
// ============================================================================

/**
 * Generate a quick acknowledgment using Haiku via Agent SDK.
 *
 * Uses the same query() function as the main agent for consistency,
 * but with Haiku 4.5 for speed. This enables future delegation patterns
 * where Haiku could escalate to Sonnet for complex analysis.
 *
 * Designed for <200ms response time.
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

  const systemPrompt = buildAcknowledgmentPrompt(style.voiceProperties.thinkingFeedback === "verbose");
  const prompt = buildUserPrompt(userMessage, config.recentContext);

  try {
    // Use Agent SDK query() - same pattern as main agent, different model
    const stream = query({
      prompt,
      options: {
        model: HAIKU_MODEL,
        systemPrompt,
        permissionMode: "bypassPermissions",
        // No MCP servers, no tools - pure speed for acknowledgments
      },
    });

    // Collect the response (non-streaming for speed)
    let responseText = "";
    for await (const msg of stream) {
      if (msg.type === "assistant") {
        // Extract text from assistant message
        const content = (msg as { message?: { content?: Array<{ type: string; text?: string }> } }).message?.content;
        if (content) {
          for (const block of content) {
            if (block.type === "text" && block.text) {
              responseText += block.text;
            }
          }
        }
      }
    }

    return parseAcknowledgmentResponse(responseText);
  } catch (error) {
    console.error("[FastLayer] Acknowledgment generation failed:", error);
    // Fail silently - fast layer is optional
    return null;
  }
}

/**
 * Check if a message needs acknowledgment based on voice style and content.
 *
 * For voice input, we want quick feedback to reduce perceived latency.
 * The threshold is intentionally low - most messages benefit from acknowledgment.
 */
export function needsAcknowledgment(userMessage: string, voiceStyle: VoiceStyleId): boolean {
  const style = getVoiceStyle(voiceStyle);

  // No acknowledgments in "none" mode
  if (style.voiceProperties.thinkingFeedback === "none") {
    return false;
  }

  // Very short messages (< 5 chars) are likely noise or single words like "yes"/"no"
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

  // All other messages get acknowledgment for voice latency improvement
  return true;
}

/**
 * Get a pre-canned acknowledgment for common patterns.
 * Faster than calling Haiku when pattern is clear.
 */
export function getQuickFallback(userMessage: string, voiceStyle: VoiceStyleId): QuickAcknowledgment | null {
  const style = getVoiceStyle(voiceStyle);

  if (style.voiceProperties.thinkingFeedback === "none") {
    return null;
  }

  // Pattern-based fallbacks for common requests
  const lowerMessage = userMessage.toLowerCase();

  if (lowerMessage.includes("fleet") || lowerMessage.includes("ship")) {
    return {
      text: "Checking your fleet status.",
      intent: "command",
      needsFollowUp: true,
      delegationText: "Pulling up the fleet data now.",
    };
  }

  if (lowerMessage.includes("wallet") || lowerMessage.includes("balance")) {
    return {
      text: "Let me check that for you.",
      intent: "command",
      needsFollowUp: true,
      delegationText: "Accessing wallet information.",
    };
  }

  if (lowerMessage.includes("help") || lowerMessage.includes("how do")) {
    return {
      text: "Sure, I can help with that.",
      intent: "question",
      needsFollowUp: true,
    };
  }

  // No clear pattern - let Haiku handle it
  return null;
}

// ============================================================================
// Prompt Building
// ============================================================================

function buildAcknowledgmentPrompt(verbose: boolean): string {
  const basePrompt = `You are IRIS, a voice AI assistant. Generate a brief spoken acknowledgment for the user's request.

Rules:
- Maximum 10 words
- Natural, conversational tone
- No questions back
- Show you understood the intent

Output format (JSON):
{"text": "acknowledgment", "intent": "question|command|statement|greeting|unclear", "needsFollowUp": true|false}`;

  if (verbose) {
    return (
      basePrompt +
      `

For verbose mode, also include what you're about to do:
{"text": "acknowledgment", "intent": "...", "needsFollowUp": true, "delegationText": "what you're checking"}`
    );
  }

  return basePrompt;
}

function buildUserPrompt(userMessage: string, recentContext?: string): string {
  let prompt = `User message: "${userMessage}"`;

  if (recentContext) {
    prompt = `Recent context:\n${recentContext}\n\n${prompt}`;
  }

  return prompt;
}

// ============================================================================
// Response Parsing
// ============================================================================

function parseAcknowledgmentResponse(response: string): QuickAcknowledgment {
  try {
    // Try to parse as JSON
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        text: parsed.text || "Got it.",
        intent: validateIntent(parsed.intent),
        needsFollowUp: parsed.needsFollowUp !== false,
        delegationText: parsed.delegationText,
      };
    }
  } catch {
    // Fall through to default
  }

  // Default fallback
  return {
    text: response.slice(0, 50) || "Got it.",
    intent: "unclear",
    needsFollowUp: true,
  };
}

function validateIntent(intent: string): IntentCategory {
  const valid: IntentCategory[] = ["question", "command", "statement", "greeting", "unclear"];
  return valid.includes(intent as IntentCategory) ? (intent as IntentCategory) : "unclear";
}
