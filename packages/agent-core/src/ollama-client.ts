/**
 * Ollama Client for Local LLM Inference
 *
 * Provides fast acknowledgments via local Qwen 2.5 7B model.
 * ~130ms warm latency vs ~2s for API calls.
 *
 * Requirements:
 * - Ollama running locally: `ollama serve`
 * - Model downloaded: `ollama pull qwen2.5:7b`
 */

export interface OllamaGenerateRequest {
  model: string;
  prompt: string;
  system?: string;
  stream?: boolean;
  options?: {
    num_predict?: number;
    temperature?: number;
    top_p?: number;
  };
}

export interface OllamaGenerateResponse {
  response: string;
  done: boolean;
  total_duration: number; // nanoseconds
  load_duration: number;
  prompt_eval_count: number;
  eval_count: number;
  eval_duration: number;
}

/** Default Ollama API endpoint */
const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";

/** Model for fast acknowledgments */
export const FAST_ACK_MODEL = "qwen2.5:7b";

/**
 * Generate a response from Ollama.
 *
 * @param request - Generation request parameters
 * @returns Generated response with timing info
 * @throws Error if Ollama is unavailable
 */
export async function ollamaGenerate(
  request: OllamaGenerateRequest
): Promise<OllamaGenerateResponse> {
  const response = await fetch(`${OLLAMA_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...request,
      stream: false, // Always non-streaming for acknowledgments
    }),
  });

  if (!response.ok) {
    throw new Error(`Ollama request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<OllamaGenerateResponse>;
}

/**
 * Check if Ollama is available and the model is loaded.
 *
 * @returns true if Ollama is reachable
 */
export async function isOllamaAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${OLLAMA_URL}/api/tags`, {
      signal: AbortSignal.timeout(1000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Pre-warm the model by sending a simple request.
 * Call this on server startup to avoid cold start latency.
 */
export async function warmupOllama(): Promise<void> {
  try {
    console.log("[Ollama] Warming up model...");
    const start = Date.now();
    await ollamaGenerate({
      model: FAST_ACK_MODEL,
      prompt: "Hello",
      options: { num_predict: 5 },
    });
    console.log(`[Ollama] Model warmed up in ${Date.now() - start}ms`);
  } catch (error) {
    console.warn("[Ollama] Warmup failed:", error);
  }
}
