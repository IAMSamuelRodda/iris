/**
 * Agent API Client
 *
 * Handles communication with the IRIS Agent API.
 * Supports streaming responses via Server-Sent Events.
 */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  toolName?: string;
}

export interface StreamChunk {
  type: "text" | "tool_start" | "tool_end" | "system" | "error" | "done";
  content: string;
  toolName?: string;
  sessionId?: string;
}

export interface ChatResponse {
  text: string;
  sessionId: string;
  success: boolean;
  errors?: string[];
}

const API_BASE = import.meta.env.VITE_AGENT_API_URL || "http://localhost:3001";

/**
 * Send a chat message and stream the response.
 */
export async function* streamChat(
  userId: string,
  message: string,
  sessionId?: string
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ userId, message, sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data as StreamChunk;
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Send a chat message and wait for complete response.
 */
export async function sendChat(
  userId: string,
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ userId, message, sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<{
  status: string;
  version: string;
  uptime: number;
}> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}
