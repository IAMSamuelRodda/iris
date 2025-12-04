/**
 * Ollama Narrator Implementation
 *
 * Uses local Qwen 2.5 7B via Ollama for narrator decisions.
 * Benefits: Zero cost, no rate limits, fully local.
 * Tradeoffs: Requires GPU memory, may have lower quality than Haiku.
 */

import { ollamaChatComplete, type OllamaChatMessage } from "../ollama-chat.js";
import { isOllamaAvailable } from "../ollama-client.js";
import { BaseNarrator, NARRATOR_SYSTEM_PROMPT } from "./base-narrator.js";
import {
  type NarratorConfig,
  type Snippet,
  type VocalizationResult,
} from "./types.js";

// ============================================================================
// Configuration
// ============================================================================

/** Default model for narrator */
export const NARRATOR_MODEL = process.env.NARRATOR_MODEL || "qwen2.5:7b";

/** Fallback responses when Ollama is unavailable */
const FALLBACK_RESPONSES: Record<string, VocalizationResult> = {
  critical: { action: "vocalize", utterance: "Something important came up." },
  high: { action: "vocalize", utterance: "Found something." },
  medium: { action: "silent" },
  low: { action: "silent" },
};

// ============================================================================
// Ollama Narrator
// ============================================================================

export class OllamaNarrator extends BaseNarrator {
  private model: string;
  private available: boolean | null = null;

  constructor(model: string = NARRATOR_MODEL, config: Partial<NarratorConfig> = {}) {
    super(config);
    this.model = model;
  }

  /**
   * Check if Ollama is available (cached).
   */
  private async ensureAvailable(): Promise<boolean> {
    if (this.available === null) {
      this.available = await isOllamaAvailable();
      if (!this.available) {
        console.warn("[OllamaNarrator] Ollama not available, using fallbacks");
      }
    }
    return this.available;
  }

  /**
   * Evaluate a snippet using Qwen 7B.
   */
  protected async evaluateWithLLM(snippet: Snippet): Promise<VocalizationResult> {
    const available = await this.ensureAvailable();

    if (!available) {
      // Fallback: simple priority-based decision
      return FALLBACK_RESPONSES[snippet.priority] || { action: "silent" };
    }

    try {
      const messages: OllamaChatMessage[] = [
        { role: "system", content: NARRATOR_SYSTEM_PROMPT },
        { role: "user", content: this.buildEvaluationPrompt(snippet) },
      ];

      const response = await ollamaChatComplete({
        model: this.model,
        messages,
        options: {
          temperature: 0.3,    // Low creativity for consistent decisions
          num_predict: 50,     // Short responses only
          num_ctx: 2048,       // Small context window (narrator doesn't need much)
        },
      });

      return this.parseResponse(response.message.content);
    } catch (error) {
      console.error("[OllamaNarrator] Evaluation failed:", error);
      // Mark as unavailable and return fallback
      this.available = false;
      return FALLBACK_RESPONSES[snippet.priority] || { action: "silent" };
    }
  }

  /**
   * Summarize current context.
   */
  async summarize(): Promise<string> {
    const available = await this.ensureAvailable();

    if (!available) {
      return this.getFallbackSummary();
    }

    if (this.buffer.length === 0) {
      return "Nothing happening right now.";
    }

    try {
      const messages: OllamaChatMessage[] = [
        { role: "system", content: NARRATOR_SYSTEM_PROMPT },
        { role: "user", content: this.buildSummaryPrompt() },
      ];

      const response = await ollamaChatComplete({
        model: this.model,
        messages,
        options: {
          temperature: 0.5,
          num_predict: 100,
          num_ctx: 2048,
        },
      });

      return response.message.content.trim();
    } catch (error) {
      console.error("[OllamaNarrator] Summary failed:", error);
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

  /**
   * Reset availability check (call if Ollama starts up later).
   */
  resetAvailability(): void {
    this.available = null;
  }
}
