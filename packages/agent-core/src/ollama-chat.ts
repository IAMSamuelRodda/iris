/**
 * Ollama Chat Client for Thinking Layer
 *
 * Provides conversational inference using Ollama's chat API.
 * Supports streaming responses for real-time voice feedback.
 *
 * This enables running the full IRIS stack locally without internet.
 *
 * Usage:
 * ```typescript
 * const stream = ollamaChat({
 *   model: "qwen2.5:7b",
 *   messages: [
 *     { role: "system", content: "You are IRIS..." },
 *     { role: "user", content: "Check my fleet" }
 *   ],
 *   stream: true
 * });
 *
 * for await (const chunk of stream) {
 *   process.stdout.write(chunk.message.content);
 * }
 * ```
 */

// ============================================================================
// Types
// ============================================================================

export interface OllamaChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface OllamaChatRequest {
  model: string;
  messages: OllamaChatMessage[];
  stream?: boolean;
  options?: {
    num_predict?: number;
    temperature?: number;
    top_p?: number;
    num_ctx?: number; // Context window size
  };
}

export interface OllamaChatResponse {
  model: string;
  created_at: string;
  message: OllamaChatMessage;
  done: boolean;
  total_duration?: number; // nanoseconds (only on final response)
  load_duration?: number;
  prompt_eval_count?: number;
  eval_count?: number;
  eval_duration?: number;
}

export interface OllamaChatStreamChunk {
  model: string;
  created_at: string;
  message: {
    role: "assistant";
    content: string;
  };
  done: boolean;
}

// ============================================================================
// Configuration
// ============================================================================

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";

// ============================================================================
// Ollama Chat API
// ============================================================================

/**
 * Send a chat request to Ollama (non-streaming).
 *
 * @param request - Chat request with messages
 * @returns Complete response
 */
export async function ollamaChatComplete(
  request: OllamaChatRequest
): Promise<OllamaChatResponse> {
  const response = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...request,
      stream: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`Ollama chat failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<OllamaChatResponse>;
}

/**
 * Stream a chat response from Ollama.
 *
 * @param request - Chat request with messages
 * @yields Streaming chunks as they arrive
 */
export async function* ollamaChatStream(
  request: OllamaChatRequest
): AsyncGenerator<OllamaChatStreamChunk> {
  const response = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...request,
      stream: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Ollama chat failed: ${response.status} ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error("No response body from Ollama");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse newline-delimited JSON
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.trim()) {
          try {
            const chunk = JSON.parse(line) as OllamaChatStreamChunk;
            yield chunk;
          } catch {
            console.warn("[OllamaChat] Failed to parse chunk:", line);
          }
        }
      }
    }

    // Process any remaining data in buffer
    if (buffer.trim()) {
      try {
        const chunk = JSON.parse(buffer) as OllamaChatStreamChunk;
        yield chunk;
      } catch {
        console.warn("[OllamaChat] Failed to parse final chunk:", buffer);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert conversation history to Ollama message format.
 */
export function toOllamaMessages(
  systemPrompt: string,
  conversationHistory: Array<{ role: "user" | "assistant"; content: string }>
): OllamaChatMessage[] {
  const messages: OllamaChatMessage[] = [
    { role: "system", content: systemPrompt },
  ];

  for (const msg of conversationHistory) {
    messages.push({
      role: msg.role,
      content: msg.content,
    });
  }

  return messages;
}

/**
 * Collect streaming response into a single string.
 */
export async function collectStreamResponse(
  stream: AsyncGenerator<OllamaChatStreamChunk>
): Promise<string> {
  let response = "";
  for await (const chunk of stream) {
    response += chunk.message.content;
  }
  return response;
}
