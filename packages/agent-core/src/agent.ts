/**
 * IRIS Agent
 *
 * Main agent class that wraps the Claude Agent SDK.
 * Manages conversation flow, tool execution, and streaming responses.
 */

import {
  query,
  type Query,
  type SDKMessage,
  type SDKResultMessage,
  type SDKSystemMessage,
  type Options,
} from "@anthropic-ai/claude-agent-sdk";
import { getMemoryManager, addConversationMessage } from "@iris/memory-service";
import { buildSystemPrompt, generateUserContext } from "./system-prompt.js";
import { createIrisMcpServer } from "./mcp-server.js";
import { type VoiceStyleId, type VoiceStyle, getVoiceStyle } from "./voice-styles.js";
import {
  generateQuickAcknowledgment,
  needsAcknowledgment,
  getQuickFallback,
  type QuickAcknowledgment,
} from "./fast-layer.js";

// ============================================================================
// Types
// ============================================================================

export interface IrisAgentConfig {
  /** User ID for memory and session management */
  userId: string;
  /** Optional session ID to resume */
  sessionId?: string;
  /** Model to use (default: claude-sonnet-4-5-20250929) */
  model?: string;
  /** Voice style for conversation behavior (default: "normal") */
  voiceStyle?: VoiceStyleId;
  /** Additional instructions to append to system prompt */
  additionalInstructions?: string;
  /** Abort controller for cancellation */
  abortController?: AbortController;
}

export interface AgentResponse {
  /** The text response from the agent */
  text: string;
  /** Session ID for resuming this conversation */
  sessionId: string;
  /** Whether the response completed successfully */
  success: boolean;
  /** Usage statistics */
  usage?: {
    inputTokens: number;
    outputTokens: number;
    totalCostUsd: number;
  };
  /** Any errors that occurred */
  errors?: string[];
}

export interface StreamChunk {
  type: "text" | "tool_start" | "tool_end" | "system" | "error" | "done" | "acknowledgment";
  content: string;
  toolName?: string;
  sessionId?: string;
  /** For acknowledgment chunks - whether main response follows */
  isInterim?: boolean;
}

// ============================================================================
// IRIS Agent Class
// ============================================================================

/**
 * IRIS Agent - Voice-first AI companion for Star Atlas.
 *
 * Usage:
 * ```typescript
 * const agent = new IrisAgent({ userId: "user-123" });
 *
 * // Streaming response
 * for await (const chunk of agent.chat("How's my fleet doing?")) {
 *   process.stdout.write(chunk.content);
 * }
 *
 * // Or collect full response
 * const response = await agent.chatComplete("Check my wallet balance");
 * console.log(response.text);
 * ```
 */
export class IrisAgent {
  private config: IrisAgentConfig;
  private mcpServer = createIrisMcpServer();
  private currentSessionId?: string;

  constructor(config: IrisAgentConfig) {
    this.config = {
      model: "claude-sonnet-4-5-20250929",
      ...config,
    };
    this.currentSessionId = config.sessionId;
  }

  /**
   * Send a message and stream the response.
   * Yields chunks as they arrive for real-time display.
   */
  async *chat(message: string): AsyncGenerator<StreamChunk> {
    const voiceStyleId = this.config.voiceStyle || "normal";

    // Fast layer: Generate quick acknowledgment if needed
    if (needsAcknowledgment(message, voiceStyleId)) {
      const acknowledgment = await this.getAcknowledgment(message);
      if (acknowledgment) {
        yield {
          type: "acknowledgment",
          content: acknowledgment.text,
          isInterim: acknowledgment.needsFollowUp,
        };
      }
    }

    const systemPrompt = await this.buildPromptWithContext();

    // Record user message in conversation history
    addConversationMessage(this.config.userId, "user", message);

    const options: Options = {
      model: this.config.model,
      systemPrompt,
      permissionMode: "bypassPermissions", // Server-side, no user prompts
      mcpServers: {
        iris: this.mcpServer,
      },
      abortController: this.config.abortController,
      includePartialMessages: true,
    };

    // Resume session if we have one
    if (this.currentSessionId) {
      options.resume = this.currentSessionId;
    }

    const stream: Query = query({ prompt: message, options });

    let responseText = "";
    let sessionId = this.currentSessionId;

    try {
      for await (const msg of stream) {
        const chunk = this.processMessage(msg);
        if (chunk) {
          // Track session ID
          if (chunk.sessionId) {
            sessionId = chunk.sessionId;
            this.currentSessionId = sessionId;
          }

          // Accumulate text
          if (chunk.type === "text") {
            responseText += chunk.content;
          }

          yield chunk;
        }
      }

      // Record assistant response in conversation history
      if (responseText) {
        addConversationMessage(this.config.userId, "assistant", responseText);
      }

      yield {
        type: "done",
        content: "",
        sessionId,
      };
    } catch (error) {
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
  async chatComplete(message: string): Promise<AgentResponse> {
    let text = "";
    let sessionId = this.currentSessionId || "";
    let success = true;
    const errors: string[] = [];
    let usage: AgentResponse["usage"];

    for await (const chunk of this.chat(message)) {
      switch (chunk.type) {
        case "text":
          text += chunk.content;
          break;
        case "done":
          sessionId = chunk.sessionId || sessionId;
          break;
        case "error":
          success = false;
          errors.push(chunk.content);
          break;
      }
    }

    return {
      text,
      sessionId,
      success,
      errors: errors.length > 0 ? errors : undefined,
      usage,
    };
  }

  /**
   * Get the current session ID.
   */
  getSessionId(): string | undefined {
    return this.currentSessionId;
  }

  /**
   * Set/change the session ID (for resuming).
   */
  setSessionId(sessionId: string): void {
    this.currentSessionId = sessionId;
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

    return buildSystemPrompt({
      userContext,
      additionalInstructions: this.config.additionalInstructions,
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
   * Tries pattern-based fallback first, then Haiku for dynamic responses.
   */
  private async getAcknowledgment(message: string): Promise<QuickAcknowledgment | null> {
    const voiceStyleId = this.config.voiceStyle || "normal";

    // Try quick fallback first (instant, no API call)
    const fallback = getQuickFallback(message, voiceStyleId);
    if (fallback) {
      return fallback;
    }

    // Use Haiku for dynamic acknowledgment
    return generateQuickAcknowledgment(message, {
      voiceStyle: voiceStyleId,
      userId: this.config.userId,
    });
  }

  /**
   * Process an SDK message into a stream chunk.
   */
  private processMessage(msg: SDKMessage): StreamChunk | null {
    switch (msg.type) {
      case "system":
        if ((msg as SDKSystemMessage).subtype === "init") {
          return {
            type: "system",
            content: "Session initialized",
            sessionId: msg.session_id,
          };
        }
        return null;

      case "assistant":
        // Skip text extraction - we get text from stream_event deltas
        // Only assistant messages for tool_use blocks would be processed here
        // but we handle tools via tool_progress messages instead
        return null;

      case "stream_event":
        // Handle streaming text deltas
        const event = (msg as { event: { type: string; delta?: { text?: string } } }).event;
        if (event.type === "content_block_delta" && event.delta?.text) {
          return {
            type: "text",
            content: event.delta.text,
          };
        }
        return null;

      case "tool_progress":
        // Tool is being executed
        const toolProgress = msg as { tool_name: string };
        return {
          type: "tool_start",
          content: `Using ${toolProgress.tool_name}...`,
          toolName: toolProgress.tool_name,
        };

      case "result":
        // Conversation complete
        const result = msg as SDKResultMessage;
        if (result.subtype === "success") {
          return null; // Handled by done chunk
        }
        // Error result
        return {
          type: "error",
          content: "errors" in result ? result.errors.join(", ") : "Unknown error",
        };

      default:
        return null;
    }
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a new IRIS agent for a user.
 */
export function createAgent(config: IrisAgentConfig): IrisAgent {
  return new IrisAgent(config);
}

/**
 * Send a one-shot message without session management.
 * Useful for simple queries that don't need context.
 */
export async function quickChat(userId: string, message: string): Promise<string> {
  const agent = createAgent({ userId });
  const response = await agent.chatComplete(message);
  return response.text;
}
