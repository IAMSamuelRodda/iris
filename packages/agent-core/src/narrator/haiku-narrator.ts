/**
 * Haiku Narrator Implementation
 *
 * Uses Claude Haiku 4.5 via Anthropic API for narrator decisions.
 * Benefits: Higher quality, no GPU memory needed.
 * Tradeoffs: API cost, network latency, rate limits.
 */

import Anthropic from "@anthropic-ai/sdk";
import { BaseNarrator, NARRATOR_SYSTEM_PROMPT } from "./base-narrator.js";
import {
  type NarratorConfig,
  type Snippet,
  type VocalizationResult,
} from "./types.js";

// ============================================================================
// Configuration
// ============================================================================

/** Model for Haiku narrator */
export const HAIKU_MODEL = "claude-haiku-4-5-20251001";

// ============================================================================
// Haiku Narrator
// ============================================================================

export class HaikuNarrator extends BaseNarrator {
  private client: Anthropic;
  private model: string;

  constructor(model: string = HAIKU_MODEL, config: Partial<NarratorConfig> = {}) {
    super(config);
    this.client = new Anthropic();
    this.model = model;
  }

  /**
   * Evaluate a snippet using Claude Haiku.
   */
  protected async evaluateWithLLM(snippet: Snippet): Promise<VocalizationResult> {
    try {
      const response = await this.client.messages.create({
        model: this.model,
        max_tokens: 60,
        system: NARRATOR_SYSTEM_PROMPT,
        messages: [
          { role: "user", content: this.buildEvaluationPrompt(snippet) },
        ],
      });

      const text =
        response.content[0].type === "text" ? response.content[0].text : "";

      return this.parseResponse(text);
    } catch (error) {
      console.error("[HaikuNarrator] Evaluation failed:", error);

      // Fallback: vocalize critical, silent otherwise
      if (snippet.priority === "critical") {
        return { action: "vocalize", utterance: "Something important came up." };
      }
      return { action: "silent" };
    }
  }

  /**
   * Summarize current context using Claude Haiku.
   */
  async summarize(): Promise<string> {
    if (this.buffer.length === 0) {
      return "Nothing happening right now.";
    }

    try {
      const response = await this.client.messages.create({
        model: this.model,
        max_tokens: 150,
        system: NARRATOR_SYSTEM_PROMPT,
        messages: [
          { role: "user", content: this.buildSummaryPrompt() },
        ],
      });

      const text =
        response.content[0].type === "text" ? response.content[0].text : "";

      return text.trim() || "Working on a few things.";
    } catch (error) {
      console.error("[HaikuNarrator] Summary failed:", error);
      return this.getFallbackSummary();
    }
  }

  /**
   * Generate a simple fallback summary from buffer.
   */
  private getFallbackSummary(): string {
    if (this.buffer.length === 0) {
      return "Nothing happening right now.";
    }

    const recentFindings = this.buffer
      .filter((s) => s.type === "finding" || s.type === "error")
      .slice(-3);

    if (recentFindings.length === 0) {
      return `Working on ${this.buffer.length} things.`;
    }

    return `Found ${recentFindings.length} things: ${recentFindings.map((s) => s.content).join(", ")}`;
  }
}
