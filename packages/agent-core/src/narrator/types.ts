/**
 * Narrator Types
 *
 * Defines the interface for the streaming narrator system.
 * The narrator ingests context snippets from the main agent pipeline
 * and decides what to vocalize to the user in real-time.
 */

// ============================================================================
// Snippet Types (Input to Narrator)
// ============================================================================

/** Where the snippet originated from */
export type SnippetSource =
  | "main_agent"    // Primary Claude agent
  | "subagent"      // Task delegated to sub-agent
  | "tool"          // MCP tool execution
  | "external";     // External system (Citadel, etc.)

/** What kind of event this represents */
export type SnippetType =
  | "progress"      // Work in progress ("calling getFleetStatus...")
  | "finding"       // Discovered information ("fleet fuel at 15%")
  | "decision"      // Agent decided something ("prioritizing fuel alert")
  | "error"         // Something went wrong
  | "completion";   // Task/subtask finished

/** Priority level for vocalization decisions */
export type SnippetPriority = "low" | "medium" | "high" | "critical";

/** A context snippet from the agent pipeline */
export interface Snippet {
  id: string;
  source: SnippetSource;
  type: SnippetType;
  content: string;
  priority: SnippetPriority;
  timestamp: number;
  /** Optional metadata (tool name, subagent ID, etc.) */
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Vocalization Types (Output from Narrator)
// ============================================================================

/** Result of narrator evaluating a snippet */
export interface VocalizationResult {
  /** Should this be spoken to the user? */
  action: "vocalize" | "silent";
  /** The utterance to speak (only if action === "vocalize") */
  utterance?: string;
  /** Confidence in this decision (0-1) */
  confidence?: number;
  /** Latency of this evaluation in ms */
  latencyMs?: number;
}

// ============================================================================
// Narrator Configuration
// ============================================================================

/** User-controllable verbosity level */
export type VerbosityLevel = "silent" | "minimal" | "normal" | "verbose";

/** Configuration for narrator behavior */
export interface NarratorConfig {
  /** How chatty should the narrator be? */
  verbosity: VerbosityLevel;
  /** Maximum length of utterances (chars, for TTS budget) */
  maxUtteranceLength: number;
  /** Rolling buffer duration in ms (for context summarization) */
  contextWindowMs: number;
  /** Minimum silence before proactive update (ms) */
  silenceThresholdMs: number;
  /** Cooldown between vocalizations of same type (ms) */
  cooldownMs: number;
}

/** Default narrator configuration */
export const DEFAULT_NARRATOR_CONFIG: NarratorConfig = {
  verbosity: "normal",
  maxUtteranceLength: 100,
  contextWindowMs: 30_000,      // 30 seconds of context
  silenceThresholdMs: 5_000,    // Speak after 5s of silence
  cooldownMs: 3_000,            // 3s between same-type updates
};

// ============================================================================
// Narrator Interface
// ============================================================================

/** The narrator interface - implemented by Ollama and Haiku versions */
export interface Narrator {
  /** Configure narrator behavior */
  configure(config: Partial<NarratorConfig>): void;

  /** Get current configuration */
  getConfig(): NarratorConfig;

  /** Ingest a snippet and decide whether to vocalize */
  ingest(snippet: Snippet): Promise<VocalizationResult>;

  /** Summarize current context buffer (for "what's happening?" queries) */
  summarize(): Promise<string>;

  /** Set verbosity level (convenience method for user commands) */
  setVerbosity(level: VerbosityLevel): void;

  /** Clear the context buffer */
  clearBuffer(): void;

  /** Get number of snippets in buffer */
  getBufferSize(): number;
}

// ============================================================================
// Comparison/Benchmarking Types
// ============================================================================

/** Metrics from a single narrator evaluation */
export interface NarratorMetrics {
  provider: "ollama" | "haiku";
  snippet: Snippet;
  result: VocalizationResult;
  latencyMs: number;
  timestamp: number;
}

/** Comparison result from running both narrators */
export interface ComparisonMetrics {
  snippet: Snippet;
  ollama: NarratorMetrics;
  haiku: NarratorMetrics;
  agreement: boolean;  // Did they agree on vocalize/silent?
  timestamp: number;
}
