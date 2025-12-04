/**
 * Comparison Narrator
 *
 * Runs both Ollama and Haiku narrators in parallel for benchmarking.
 * Collects metrics on latency, agreement, and quality.
 */

import { OllamaNarrator } from "./ollama-narrator.js";
import { HaikuNarrator } from "./haiku-narrator.js";
import {
  type Narrator,
  type NarratorConfig,
  type Snippet,
  type VocalizationResult,
  type VerbosityLevel,
  type ComparisonMetrics,
  type NarratorMetrics,
  DEFAULT_NARRATOR_CONFIG,
} from "./types.js";

// ============================================================================
// Comparison Narrator
// ============================================================================

export class ComparisonNarrator implements Narrator {
  private ollama: OllamaNarrator;
  private haiku: HaikuNarrator;
  private config: NarratorConfig;
  private metrics: ComparisonMetrics[] = [];

  /** Which narrator to use for actual output */
  private primary: "ollama" | "haiku";

  constructor(
    primary: "ollama" | "haiku" = "ollama",
    config: Partial<NarratorConfig> = {}
  ) {
    this.config = { ...DEFAULT_NARRATOR_CONFIG, ...config };
    this.ollama = new OllamaNarrator(undefined, this.config);
    this.haiku = new HaikuNarrator(undefined, this.config);
    this.primary = primary;
  }

  // ============================================================================
  // Configuration
  // ============================================================================

  configure(config: Partial<NarratorConfig>): void {
    this.config = { ...this.config, ...config };
    this.ollama.configure(config);
    this.haiku.configure(config);
  }

  getConfig(): NarratorConfig {
    return { ...this.config };
  }

  setVerbosity(level: VerbosityLevel): void {
    this.config.verbosity = level;
    this.ollama.setVerbosity(level);
    this.haiku.setVerbosity(level);
  }

  // ============================================================================
  // Buffer Management (delegate to primary)
  // ============================================================================

  clearBuffer(): void {
    this.ollama.clearBuffer();
    this.haiku.clearBuffer();
  }

  getBufferSize(): number {
    return this.ollama.getBufferSize();
  }

  // ============================================================================
  // Comparison Logic
  // ============================================================================

  /**
   * Ingest snippet through both narrators and compare.
   */
  async ingest(snippet: Snippet): Promise<VocalizationResult> {
    const timestamp = Date.now();

    // Run both in parallel
    const [ollamaResult, haikuResult] = await Promise.all([
      this.timeExecution("ollama", () => this.ollama.ingest(snippet)),
      this.timeExecution("haiku", () => this.haiku.ingest(snippet)),
    ]);

    // Record comparison metrics
    const comparison: ComparisonMetrics = {
      snippet,
      ollama: ollamaResult,
      haiku: haikuResult,
      agreement: ollamaResult.result.action === haikuResult.result.action,
      timestamp,
    };
    this.metrics.push(comparison);

    // Log comparison
    this.logComparison(comparison);

    // Return result from primary narrator
    return this.primary === "ollama" ? ollamaResult.result : haikuResult.result;
  }

  /**
   * Summarize using both narrators (return primary).
   */
  async summarize(): Promise<string> {
    const [ollamaSummary, haikuSummary] = await Promise.all([
      this.ollama.summarize(),
      this.haiku.summarize(),
    ]);

    console.log("\n[Comparison] Summaries:");
    console.log(`  Ollama: "${ollamaSummary}"`);
    console.log(`  Haiku:  "${haikuSummary}"`);

    return this.primary === "ollama" ? ollamaSummary : haikuSummary;
  }

  // ============================================================================
  // Metrics
  // ============================================================================

  /**
   * Get collected comparison metrics.
   */
  getMetrics(): ComparisonMetrics[] {
    return [...this.metrics];
  }

  /**
   * Clear metrics.
   */
  clearMetrics(): void {
    this.metrics = [];
  }

  /**
   * Get summary statistics.
   */
  getStats(): {
    count: number;
    agreementRate: number;
    avgOllamaLatency: number;
    avgHaikuLatency: number;
    ollamaVocalizeRate: number;
    haikuVocalizeRate: number;
  } {
    if (this.metrics.length === 0) {
      return {
        count: 0,
        agreementRate: 0,
        avgOllamaLatency: 0,
        avgHaikuLatency: 0,
        ollamaVocalizeRate: 0,
        haikuVocalizeRate: 0,
      };
    }

    const count = this.metrics.length;
    const agreements = this.metrics.filter((m) => m.agreement).length;
    const ollamaVocalizes = this.metrics.filter(
      (m) => m.ollama.result.action === "vocalize"
    ).length;
    const haikuVocalizes = this.metrics.filter(
      (m) => m.haiku.result.action === "vocalize"
    ).length;

    return {
      count,
      agreementRate: agreements / count,
      avgOllamaLatency:
        this.metrics.reduce((sum, m) => sum + m.ollama.latencyMs, 0) / count,
      avgHaikuLatency:
        this.metrics.reduce((sum, m) => sum + m.haiku.latencyMs, 0) / count,
      ollamaVocalizeRate: ollamaVocalizes / count,
      haikuVocalizeRate: haikuVocalizes / count,
    };
  }

  /**
   * Export metrics as JSON.
   */
  exportMetrics(): string {
    return JSON.stringify(
      {
        stats: this.getStats(),
        metrics: this.metrics,
      },
      null,
      2
    );
  }

  // ============================================================================
  // Helpers
  // ============================================================================

  private async timeExecution(
    provider: "ollama" | "haiku",
    fn: () => Promise<VocalizationResult>
  ): Promise<NarratorMetrics> {
    const start = Date.now();
    const result = await fn();
    const latencyMs = Date.now() - start;

    return {
      provider,
      snippet: {} as Snippet, // Will be filled by caller
      result,
      latencyMs,
      timestamp: start,
    };
  }

  private logComparison(comparison: ComparisonMetrics): void {
    const { snippet, ollama, haiku, agreement } = comparison;
    const agreementIcon = agreement ? "✓" : "✗";

    console.log(`\n[Comparison] ${agreementIcon} Snippet: "${snippet.content.slice(0, 50)}..."`);
    console.log(`  Ollama (${ollama.latencyMs}ms): ${ollama.result.action}${ollama.result.utterance ? ` → "${ollama.result.utterance}"` : ""}`);
    console.log(`  Haiku  (${haiku.latencyMs}ms): ${haiku.result.action}${haiku.result.utterance ? ` → "${haiku.result.utterance}"` : ""}`);
  }
}
