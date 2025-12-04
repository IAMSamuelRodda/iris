#!/usr/bin/env npx tsx
/**
 * Narrator Benchmark Script
 *
 * Compares Ollama (Qwen 7B) and Haiku narrator implementations.
 * Measures latency, agreement rate, and quality of vocalizations.
 *
 * Usage:
 *   pnpm exec tsx scripts/benchmark-narrator.ts
 *   pnpm exec tsx scripts/benchmark-narrator.ts --verbosity verbose
 *   pnpm exec tsx scripts/benchmark-narrator.ts --provider ollama
 */

import { ComparisonNarrator } from "../src/narrator/comparison-narrator.js";
import { OllamaNarrator } from "../src/narrator/ollama-narrator.js";
import { HaikuNarrator } from "../src/narrator/haiku-narrator.js";
import type { Snippet, VerbosityLevel } from "../src/narrator/types.js";

// ============================================================================
// Test Data
// ============================================================================

const TEST_SNIPPETS: Snippet[] = [
  // Low priority - should mostly be silent
  {
    id: "1",
    source: "tool",
    type: "progress",
    content: "Parsing JSON response from API",
    priority: "low",
    timestamp: Date.now(),
  },
  {
    id: "2",
    source: "tool",
    type: "progress",
    content: "Formatting output string",
    priority: "low",
    timestamp: Date.now(),
  },

  // Medium priority - depends on verbosity
  {
    id: "3",
    source: "tool",
    type: "progress",
    content: "Calling getFleetStatus for 3 fleets",
    priority: "medium",
    timestamp: Date.now(),
  },
  {
    id: "4",
    source: "main_agent",
    type: "decision",
    content: "Will check fleet status before market prices",
    priority: "medium",
    timestamp: Date.now(),
  },

  // High priority - should often vocalize
  {
    id: "5",
    source: "subagent",
    type: "finding",
    content: "Fleet Alpha located at Starbase X-5",
    priority: "high",
    timestamp: Date.now(),
  },
  {
    id: "6",
    source: "tool",
    type: "finding",
    content: "Retrieved 5 fleets from user account",
    priority: "high",
    timestamp: Date.now(),
  },

  // Critical priority - should almost always vocalize
  {
    id: "7",
    source: "subagent",
    type: "finding",
    content: "Fleet Alpha fuel at 15%, below critical threshold",
    priority: "critical",
    timestamp: Date.now(),
  },
  {
    id: "8",
    source: "tool",
    type: "error",
    content: "Failed to connect to blockchain RPC",
    priority: "critical",
    timestamp: Date.now(),
  },
  {
    id: "9",
    source: "main_agent",
    type: "decision",
    content: "Prioritizing fuel alert over market query due to critical status",
    priority: "critical",
    timestamp: Date.now(),
  },

  // Completion events
  {
    id: "10",
    source: "tool",
    type: "completion",
    content: "Fleet status check complete",
    priority: "medium",
    timestamp: Date.now(),
  },
];

// ============================================================================
// Benchmark Functions
// ============================================================================

async function benchmarkSingle(
  provider: "ollama" | "haiku",
  verbosity: VerbosityLevel
): Promise<void> {
  console.log(`\n${"=".repeat(60)}`);
  console.log(`Benchmarking ${provider.toUpperCase()} with verbosity: ${verbosity}`);
  console.log("=".repeat(60));

  const narrator =
    provider === "ollama"
      ? new OllamaNarrator()
      : new HaikuNarrator();

  narrator.configure({ verbosity });

  const results: Array<{
    snippet: Snippet;
    action: string;
    utterance?: string;
    latencyMs: number;
  }> = [];

  for (const snippet of TEST_SNIPPETS) {
    const result = await narrator.ingest(snippet);
    results.push({
      snippet,
      action: result.action,
      utterance: result.utterance,
      latencyMs: result.latencyMs || 0,
    });

    const icon = result.action === "vocalize" ? "🗣️" : "🤫";
    console.log(
      `${icon} [${snippet.priority}] "${snippet.content.slice(0, 40)}..."` +
        (result.utterance ? ` → "${result.utterance}"` : "") +
        ` (${result.latencyMs}ms)`
    );
  }

  // Summary
  const vocalizations = results.filter((r) => r.action === "vocalize");
  const avgLatency =
    results.reduce((sum, r) => sum + r.latencyMs, 0) / results.length;

  console.log(`\nSummary:`);
  console.log(`  Vocalized: ${vocalizations.length}/${results.length}`);
  console.log(`  Avg latency: ${avgLatency.toFixed(0)}ms`);
}

async function benchmarkComparison(verbosity: VerbosityLevel): Promise<void> {
  console.log(`\n${"=".repeat(60)}`);
  console.log(`COMPARISON MODE with verbosity: ${verbosity}`);
  console.log("=".repeat(60));

  const narrator = new ComparisonNarrator("ollama", { verbosity });

  for (const snippet of TEST_SNIPPETS) {
    await narrator.ingest(snippet);
  }

  // Get and display stats
  const stats = narrator.getStats();

  console.log(`\n${"=".repeat(60)}`);
  console.log("FINAL STATISTICS");
  console.log("=".repeat(60));

  console.log(`\nSnippets processed: ${stats.count}`);
  console.log(`Agreement rate: ${(stats.agreementRate * 100).toFixed(1)}%`);
  console.log(`\nLatency:`);
  console.log(`  Ollama avg: ${stats.avgOllamaLatency.toFixed(0)}ms`);
  console.log(`  Haiku avg:  ${stats.avgHaikuLatency.toFixed(0)}ms`);
  console.log(`\nVocalization rate:`);
  console.log(`  Ollama: ${(stats.ollamaVocalizeRate * 100).toFixed(1)}%`);
  console.log(`  Haiku:  ${(stats.haikuVocalizeRate * 100).toFixed(1)}%`);

  // Test summarization
  console.log(`\n${"=".repeat(60)}`);
  console.log("SUMMARIZATION TEST");
  console.log("=".repeat(60));
  await narrator.summarize();
}

// ============================================================================
// CLI
// ============================================================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  let provider: "ollama" | "haiku" | "comparison" = "comparison";
  let verbosity: VerbosityLevel = "normal";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--provider" && args[i + 1]) {
      provider = args[++i] as typeof provider;
    }
    if (args[i] === "--verbosity" && args[i + 1]) {
      verbosity = args[++i] as VerbosityLevel;
    }
  }

  console.log("\n🎙️  NARRATOR BENCHMARK");
  console.log(`Provider: ${provider}`);
  console.log(`Verbosity: ${verbosity}`);

  if (provider === "comparison") {
    await benchmarkComparison(verbosity);
  } else {
    await benchmarkSingle(provider, verbosity);
  }

  console.log("\n✅ Benchmark complete!\n");
}

main().catch((error) => {
  console.error("Benchmark failed:", error);
  process.exit(1);
});
