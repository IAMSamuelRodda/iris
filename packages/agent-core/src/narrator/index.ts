/**
 * Narrator Module
 *
 * Streaming context narrator for voice-first feedback.
 * Evaluates snippets from the agent pipeline and decides
 * what to vocalize to the user in real-time.
 *
 * Usage:
 * ```typescript
 * import { createNarrator } from "./narrator";
 *
 * const narrator = createNarrator("ollama");
 * narrator.configure({ verbosity: "normal" });
 *
 * // As agent works, feed it snippets
 * const result = await narrator.ingest({
 *   id: "1",
 *   source: "tool",
 *   type: "progress",
 *   content: "Calling getFleetStatus",
 *   priority: "medium",
 *   timestamp: Date.now(),
 * });
 *
 * if (result.action === "vocalize") {
 *   await tts.synthesize(result.utterance);
 * }
 *
 * // User asks "what's happening?"
 * const summary = await narrator.summarize();
 * ```
 */

// Types
export type {
  Narrator,
  NarratorConfig,
  Snippet,
  SnippetSource,
  SnippetType,
  SnippetPriority,
  VocalizationResult,
  VerbosityLevel,
  NarratorMetrics,
  ComparisonMetrics,
} from "./types.js";

export { DEFAULT_NARRATOR_CONFIG } from "./types.js";

// Base class (for extension)
export { BaseNarrator, NARRATOR_SYSTEM_PROMPT } from "./base-narrator.js";

// Implementations
export { OllamaNarrator, NARRATOR_MODEL } from "./ollama-narrator.js";
export { HaikuNarrator, HAIKU_MODEL } from "./haiku-narrator.js";
export { ComparisonNarrator } from "./comparison-narrator.js";

// ============================================================================
// Factory
// ============================================================================

import type { Narrator, NarratorConfig } from "./types.js";
import { OllamaNarrator } from "./ollama-narrator.js";
import { HaikuNarrator } from "./haiku-narrator.js";
import { ComparisonNarrator } from "./comparison-narrator.js";

export type NarratorProvider = "ollama" | "haiku" | "comparison";

/**
 * Create a narrator instance.
 *
 * @param provider - Which narrator implementation to use
 * @param config - Optional configuration overrides
 */
export function createNarrator(
  provider: NarratorProvider = "ollama",
  config: Partial<NarratorConfig> = {}
): Narrator {
  switch (provider) {
    case "ollama":
      return new OllamaNarrator(undefined, config);

    case "haiku":
      return new HaikuNarrator(undefined, config);

    case "comparison":
      return new ComparisonNarrator("ollama", config);

    default:
      throw new Error(`Unknown narrator provider: ${provider}`);
  }
}

// ============================================================================
// Snippet Factory (convenience)
// ============================================================================

import type { Snippet, SnippetSource, SnippetType, SnippetPriority } from "./types.js";

let snippetCounter = 0;

/**
 * Create a snippet with auto-generated ID and timestamp.
 */
export function createSnippet(
  source: SnippetSource,
  type: SnippetType,
  content: string,
  priority: SnippetPriority = "medium",
  metadata?: Record<string, unknown>
): Snippet {
  return {
    id: `snippet_${++snippetCounter}`,
    source,
    type,
    content,
    priority,
    timestamp: Date.now(),
    metadata,
  };
}
