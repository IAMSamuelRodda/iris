/**
 * Local Agent - Ollama-based Thinking Layer
 *
 * Provides conversational AI using local Ollama models for fully offline operation.
 * No tool use (Ollama tool support is limited), but fast streaming responses.
 *
 * Use cases:
 * - Offline operation (no internet required)
 * - Cost optimization (free inference)
 * - Privacy (data never leaves local machine)
 * - Development/testing without API costs
 *
 * For tool use capabilities, use the IrisAgent with Claude models.
 */

import { getMemoryManager, addConversationMessage } from "@iris/memory-service";
import { buildSystemPrompt, generateUserContext } from "./system-prompt.js";
import { type VoiceStyleId, type VoiceStyle, getVoiceStyle } from "./voice-styles.js";
import {
  generateQuickAcknowledgment,
  needsAcknowledgment,
  type QuickAcknowledgment,
} from "./fast-layer.js";
import {
  ollamaChatStream,
  type OllamaChatMessage,
} from "./ollama-chat.js";
import { getModel, type ModelConfig } from "./model-config.js";

// ============================================================================
// Types
// ============================================================================

export interface LocalAgentConfig {
  /** User ID for memory and session management */
  userId: string;
  /** Model ID from model-config (default: qwen-2.5-7b) */
  modelId?: string;
  /** Voice style for conversation behavior (default: "normal") */
  voiceStyle?: VoiceStyleId;
  /** Additional instructions to append to system prompt */
  additionalInstructions?: string;
  /** Context window size for Ollama */
  contextSize?: number;
}

export interface LocalAgentResponse {
  /** The text response from the agent */
  text: string;
  /** Whether the response completed successfully */
  success: boolean;
  /** Any errors that occurred */
  errors?: string[];
  /** Model used for this response */
  model: string;
}

export interface LocalStreamChunk {
  type: "text" | "system" | "error" | "done" | "acknowledgment";
  content: string;
  /** For acknowledgment chunks - whether main response follows */
  isInterim?: boolean;
}

// ============================================================================
// Local Agent Class
// ============================================================================

/**
 * Local Agent - Fully offline conversational AI for IRIS.
 *
 * Usage:
 * ```typescript
 * const agent = new LocalAgent({ userId: "user-123" });
 *
 * // Streaming response
 * for await (const chunk of agent.chat("What's happening with my fleet?")) {
 *   process.stdout.write(chunk.content);
 * }
 *
 * // Or collect full response
 * const response = await agent.chatComplete("Tell me about Star Atlas");
 * console.log(response.text);
 * ```
 */
export class LocalAgent {
  private config: LocalAgentConfig;
  private modelConfig: ModelConfig;
  private conversationHistory: OllamaChatMessage[] = [];

  constructor(config: LocalAgentConfig) {
    this.config = {
      modelId: "qwen-2.5-7b",
      contextSize: 8192,
      ...config,
    };

    const model = getModel(this.config.modelId!);
    if (!model) {
      throw new Error(`Unknown model: ${this.config.modelId}`);
    }
    if (model.provider !== "ollama") {
      throw new Error(`LocalAgent only supports Ollama models, got: ${model.provider}`);
    }
    this.modelConfig = model;
  }

  /**
   * Send a message and stream the response.
   * Yields chunks as they arrive for real-time display.
   */
  async *chat(message: string): AsyncGenerator<LocalStreamChunk> {
    const voiceStyleId = this.config.voiceStyle || "normal";
    const wantsAck = needsAcknowledgment(message, voiceStyleId);

    const timings = {
      start: Date.now(),
      ackEnd: 0,
      firstToken: 0,
    };

    // === Acknowledgment Phase ===
    let spokenAck: string | null = null;
    if (wantsAck) {
      const acknowledgment = await this.getAcknowledgment(message);
      timings.ackEnd = Date.now();
      if (acknowledgment) {
        spokenAck = acknowledgment.text;
        console.log(`[LocalAgent] Ack (${timings.ackEnd - timings.start}ms): "${spokenAck}"`);
        yield {
          type: "acknowledgment",
          content: acknowledgment.text,
          isInterim: acknowledgment.needsFollowUp,
        };
      }
    }

    // === Build System Prompt ===
    const systemPrompt = await this.buildPromptWithContext();

    // === Add User Message to History ===
    // Include ack context so model continues naturally
    let userContent = message;
    if (spokenAck) {
      userContent = `[You already responded with: "${spokenAck}" - now continue naturally from that acknowledgment]\n\nUser: ${message}`;
    }

    this.conversationHistory.push({
      role: "user",
      content: userContent,
    });

    // Record in memory service
    addConversationMessage(this.config.userId, "user", message);

    // === Build Full Message List ===
    const messages: OllamaChatMessage[] = [
      { role: "system", content: systemPrompt },
      ...this.conversationHistory,
    ];

    // === Stream Response ===
    let responseText = "";
    let firstTokenLogged = false;

    try {
      console.log(`[LocalAgent] Starting ${this.modelConfig.modelId} stream...`);

      const stream = ollamaChatStream({
        model: this.modelConfig.modelId,
        messages,
        options: {
          num_ctx: this.config.contextSize,
          temperature: 0.7,
        },
      });

      for await (const chunk of stream) {
        if (!firstTokenLogged) {
          timings.firstToken = Date.now();
          console.log(
            `[LocalAgent] First token: ${timings.firstToken - timings.start}ms from start`
          );
          firstTokenLogged = true;
        }

        const content = chunk.message.content;
        if (content) {
          responseText += content;
          yield {
            type: "text",
            content,
          };
        }
      }

      // Add assistant response to history
      if (responseText) {
        this.conversationHistory.push({
          role: "assistant",
          content: responseText,
        });

        // Record in memory service
        addConversationMessage(this.config.userId, "assistant", responseText);
      }

      yield {
        type: "done",
        content: "",
      };
    } catch (error) {
      console.error("[LocalAgent] Stream error:", error);
      yield {
        type: "error",
        content: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  /**
   * Send a message and wait for the complete response.
   * Convenience method when streaming isn't needed.
   */
  async chatComplete(message: string): Promise<LocalAgentResponse> {
    let text = "";
    let success = true;
    const errors: string[] = [];

    for await (const chunk of this.chat(message)) {
      switch (chunk.type) {
        case "text":
          text += chunk.content;
          break;
        case "error":
          success = false;
          errors.push(chunk.content);
          break;
      }
    }

    return {
      text,
      success,
      errors: errors.length > 0 ? errors : undefined,
      model: this.modelConfig.modelId,
    };
  }

  /**
   * Clear conversation history (start fresh).
   */
  clearHistory(): void {
    this.conversationHistory = [];
  }

  /**
   * Get the current conversation history.
   */
  getHistory(): OllamaChatMessage[] {
    return [...this.conversationHistory];
  }

  /**
   * Build the system prompt with user context from memory.
   */
  private async buildPromptWithContext(): Promise<string> {
    const manager = getMemoryManager(this.config.userId);
    const graph = manager.readGraph();
    const summary = manager.getSummary();

    const userContext = generateUserContext({
      entities: graph.entities,
      summary: summary?.summary,
    });

    // Add local model note to prompt
    const localNote = `
Note: You are running on a local model (${this.modelConfig.name}) for fast, offline responses.
You do NOT have access to real-time data, tools, or external APIs.
Answer based on your knowledge and the conversation context.
If asked about real-time data (prices, fleet status, etc.), explain you're in offline mode.`;

    return buildSystemPrompt({
      userContext,
      additionalInstructions: (this.config.additionalInstructions || "") + localNote,
      voiceStyle: this.config.voiceStyle,
    });
  }

  /**
   * Get the voice style configuration (for TTS parameters).
   */
  getVoiceStyle(): VoiceStyle {
    return getVoiceStyle(this.config.voiceStyle || "normal");
  }

  /**
   * Get a quick acknowledgment for the user message.
   */
  private async getAcknowledgment(message: string): Promise<QuickAcknowledgment | null> {
    const voiceStyleId = this.config.voiceStyle || "normal";
    return generateQuickAcknowledgment(message, {
      voiceStyle: voiceStyleId,
      userId: this.config.userId,
    });
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a new Local agent for a user.
 */
export function createLocalAgent(config: LocalAgentConfig): LocalAgent {
  return new LocalAgent(config);
}

/**
 * Send a one-shot message using local model.
 */
export async function quickLocalChat(userId: string, message: string): Promise<string> {
  const agent = createLocalAgent({ userId });
  const response = await agent.chatComplete(message);
  return response.text;
}
