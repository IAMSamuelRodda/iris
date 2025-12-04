/**
 * Base Narrator Implementation
 *
 * Provides shared logic for narrator implementations:
 * - Context buffer management (rolling window)
 * - Configuration handling
 * - Vocalization decision framework
 * - Cooldown tracking
 */

import {
  type Narrator,
  type NarratorConfig,
  type Snippet,
  type VocalizationResult,
  type VerbosityLevel,
  type SnippetType,
  DEFAULT_NARRATOR_CONFIG,
} from "./types.js";

// ============================================================================
// System Prompt for Narrator
// ============================================================================

/**
 * Base system prompt for narrator models.
 * Implementations may extend this with provider-specific instructions.
 */
export const NARRATOR_SYSTEM_PROMPT = `You are IRIS's voice during active processing. You translate internal system activity into natural, conversational updates for the user.

ROLE:
- You are the NARRATOR, not the main agent
- You report on what's happening, you don't make decisions
- Keep the user aware without overwhelming them
- Translate technical snippets to casual speech

SNIPPET FORMAT:
[source:type:priority] content

Examples:
[tool:progress:low] Calling getFleetStatus for 3 fleets
[subagent:finding:critical] Fleet Alpha fuel at 15%
[main_agent:decision:medium] Prioritizing fuel alert

OUTPUT FORMAT:
Respond with EXACTLY one of:
SILENT
or
VOCALIZE: <your utterance>

RULES:
1. Utterances must be 1 short sentence (max 15 words)
2. Never repeat what you just said
3. Technical details → casual language
4. Only VOCALIZE if it's genuinely useful to the user
5. SILENT is always valid - when in doubt, stay quiet

EXAMPLES:
[tool:progress:low] Parsing JSON response from API
→ SILENT

[tool:progress:medium] Calling getFleetStatus
→ VOCALIZE: Checking your fleet status now.

[subagent:finding:critical] Fleet Alpha fuel at 15%, below threshold
→ VOCALIZE: Heads up, Fleet Alpha's fuel is critical.

[tool:finding:low] Retrieved 3 fleets from database
→ SILENT

[main_agent:decision:high] Prioritizing fuel alert over market query
→ VOCALIZE: Focusing on your fuel situation first.`;

// ============================================================================
// Base Narrator Abstract Class
// ============================================================================

/**
 * Abstract base class for narrator implementations.
 * Handles buffer management, config, and decision framework.
 * Subclasses implement the actual LLM call.
 */
export abstract class BaseNarrator implements Narrator {
  protected config: NarratorConfig;
  protected buffer: Snippet[] = [];
  protected lastVocalization: Map<SnippetType, number> = new Map();
  protected lastVocalizedContent: string = "";

  constructor(config: Partial<NarratorConfig> = {}) {
    this.config = { ...DEFAULT_NARRATOR_CONFIG, ...config };
  }

  // ============================================================================
  // Configuration
  // ============================================================================

  configure(config: Partial<NarratorConfig>): void {
    this.config = { ...this.config, ...config };
  }

  getConfig(): NarratorConfig {
    return { ...this.config };
  }

  setVerbosity(level: VerbosityLevel): void {
    this.config.verbosity = level;
  }

  // ============================================================================
  // Buffer Management
  // ============================================================================

  clearBuffer(): void {
    this.buffer = [];
  }

  getBufferSize(): number {
    return this.buffer.length;
  }

  protected addToBuffer(snippet: Snippet): void {
    this.buffer.push(snippet);
    this.pruneBuffer();
  }

  protected pruneBuffer(): void {
    const cutoff = Date.now() - this.config.contextWindowMs;
    this.buffer = this.buffer.filter((s) => s.timestamp > cutoff);
  }

  protected formatBuffer(): string {
    return this.buffer
      .map((s) => `[${s.source}:${s.type}:${s.priority}] ${s.content}`)
      .join("\n");
  }

  // ============================================================================
  // Vocalization Logic
  // ============================================================================

  async ingest(snippet: Snippet): Promise<VocalizationResult> {
    const start = Date.now();

    // Add to buffer regardless of vocalization
    this.addToBuffer(snippet);

    // Fast-path: silent mode means never vocalize
    if (this.config.verbosity === "silent") {
      return { action: "silent", latencyMs: Date.now() - start };
    }

    // Check cooldown for this snippet type
    if (this.isOnCooldown(snippet.type)) {
      return { action: "silent", latencyMs: Date.now() - start };
    }

    // Apply verbosity-based filtering
    if (!this.passesVerbosityFilter(snippet)) {
      return { action: "silent", latencyMs: Date.now() - start };
    }

    // Delegate to LLM for decision
    const result = await this.evaluateWithLLM(snippet);

    // Track vocalization for cooldown
    if (result.action === "vocalize" && result.utterance) {
      this.lastVocalization.set(snippet.type, Date.now());
      this.lastVocalizedContent = result.utterance;
    }

    result.latencyMs = Date.now() - start;
    return result;
  }

  /**
   * Check if we're in cooldown for a snippet type.
   */
  protected isOnCooldown(type: SnippetType): boolean {
    const lastTime = this.lastVocalization.get(type);
    if (!lastTime) return false;
    return Date.now() - lastTime < this.config.cooldownMs;
  }

  /**
   * Apply verbosity-based pre-filtering.
   * Returns true if snippet should be evaluated by LLM.
   */
  protected passesVerbosityFilter(snippet: Snippet): boolean {
    switch (this.config.verbosity) {
      case "silent":
        return false;

      case "minimal":
        // Only critical and high priority findings/errors
        return (
          snippet.priority === "critical" ||
          (snippet.priority === "high" &&
            (snippet.type === "finding" || snippet.type === "error"))
        );

      case "normal":
        // Medium+ priority, or any critical
        return snippet.priority !== "low";

      case "verbose":
        // Everything gets evaluated
        return true;

      default:
        return false;
    }
  }

  // ============================================================================
  // Abstract Methods (Implemented by Subclasses)
  // ============================================================================

  /**
   * Evaluate a snippet using the LLM.
   * Subclasses implement the actual API call.
   */
  protected abstract evaluateWithLLM(
    snippet: Snippet
  ): Promise<VocalizationResult>;

  /**
   * Summarize the current context buffer.
   * Called when user asks "what's happening?"
   */
  abstract summarize(): Promise<string>;

  // ============================================================================
  // Helpers
  // ============================================================================

  /**
   * Format a snippet for the LLM prompt.
   */
  protected formatSnippet(snippet: Snippet): string {
    return `[${snippet.source}:${snippet.type}:${snippet.priority}] ${snippet.content}`;
  }

  /**
   * Parse LLM response into VocalizationResult.
   * Handles multi-line responses where reasoning follows the decision.
   */
  protected parseResponse(response: string): VocalizationResult {
    const trimmed = response.trim();

    // Get first line (Haiku sometimes adds reasoning on subsequent lines)
    const firstLine = trimmed.split("\n")[0].trim();

    // Check for SILENT (with or without trailing explanation)
    if (firstLine.toUpperCase() === "SILENT" || firstLine.toUpperCase().startsWith("SILENT")) {
      return { action: "silent" };
    }

    // Check for VOCALIZE on first line
    const match = firstLine.match(/^VOCALIZE:\s*(.+)$/i);
    if (match) {
      let utterance = match[1].trim();

      // Remove trailing quotes if present
      if (utterance.endsWith('"') && !utterance.startsWith('"')) {
        utterance = utterance.slice(0, -1);
      }
      if (utterance.startsWith('"') && utterance.endsWith('"')) {
        utterance = utterance.slice(1, -1);
      }

      // Enforce max length
      if (utterance.length > this.config.maxUtteranceLength) {
        utterance = utterance.slice(0, this.config.maxUtteranceLength - 3) + "...";
      }

      return {
        action: "vocalize",
        utterance,
      };
    }

    // Also check full response for VOCALIZE pattern (in case it's on a later line)
    const fullMatch = trimmed.match(/^VOCALIZE:\s*(.+?)(?:\n|$)/im);
    if (fullMatch) {
      let utterance = fullMatch[1].trim();
      if (utterance.length > this.config.maxUtteranceLength) {
        utterance = utterance.slice(0, this.config.maxUtteranceLength - 3) + "...";
      }
      return { action: "vocalize", utterance };
    }

    // Default to silent if we can't parse
    console.warn("[Narrator] Failed to parse response:", response.slice(0, 100));
    return { action: "silent" };
  }

  /**
   * Build the evaluation prompt for a snippet.
   */
  protected buildEvaluationPrompt(snippet: Snippet): string {
    let prompt = `VERBOSITY: ${this.config.verbosity}\n\n`;

    // Include recent context if available
    if (this.buffer.length > 1) {
      const recentSnippets = this.buffer.slice(-5, -1); // Last 4 before current
      if (recentSnippets.length > 0) {
        prompt += `RECENT CONTEXT:\n${recentSnippets.map((s) => this.formatSnippet(s)).join("\n")}\n\n`;
      }
    }

    // Include what we last said (to avoid repetition)
    if (this.lastVocalizedContent) {
      prompt += `LAST SAID: "${this.lastVocalizedContent}"\n\n`;
    }

    prompt += `CURRENT SNIPPET:\n${this.formatSnippet(snippet)}\n\nDecide: SILENT or VOCALIZE?`;

    return prompt;
  }

  /**
   * Build the summary prompt.
   */
  protected buildSummaryPrompt(): string {
    if (this.buffer.length === 0) {
      return "No recent activity to summarize.";
    }

    return `The user asked "what's happening?" - summarize the current activity in 1-2 natural sentences.

RECENT ACTIVITY:
${this.formatBuffer()}

IMPORTANT: Respond with ONLY a brief, casual summary. Do NOT use "VOCALIZE:" or "SILENT" format.
Just give a natural response like you're talking to a friend:`;
  }

  /**
   * Clean up summary response (strip any accidental formatting).
   */
  protected cleanSummaryResponse(response: string): string {
    let cleaned = response.trim();

    // Strip "VOCALIZE:" prefix if model accidentally used it
    const match = cleaned.match(/^VOCALIZE:\s*(.+)$/is);
    if (match) {
      cleaned = match[1].trim();
    }

    // Remove quotes if wrapped
    if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
      cleaned = cleaned.slice(1, -1);
    }

    return cleaned;
  }
}
