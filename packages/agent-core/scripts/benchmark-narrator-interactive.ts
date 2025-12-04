#!/usr/bin/env npx tsx
/**
 * Interactive Narrator Benchmark with TTS Playback
 *
 * Tests the narrator and SPEAKS the vocalizations so you can hear them.
 * Human in the loop evaluation.
 *
 * Usage:
 *   npx tsx scripts/benchmark-narrator-interactive.ts
 *   npx tsx scripts/benchmark-narrator-interactive.ts --provider haiku
 *   npx tsx scripts/benchmark-narrator-interactive.ts --model deepseek-r1:14b
 *   npx tsx scripts/benchmark-narrator-interactive.ts --model qwq:32b
 */

import { spawn } from "child_process";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

import { OllamaNarrator } from "../src/narrator/ollama-narrator.js";
import { HaikuNarrator } from "../src/narrator/haiku-narrator.js";
import type { Snippet, VerbosityLevel, Narrator } from "../src/narrator/types.js";

// ============================================================================
// TTS Integration
// ============================================================================

const TTS_URL = process.env.TTS_URL || "http://localhost:8001/synthesize";

async function synthesizeAndPlay(text: string): Promise<void> {
  // Call TTS endpoint
  const response = await fetch(TTS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      speech_rate: 1.1,  // Slightly faster for narrator
    }),
  });

  if (!response.ok) {
    console.error(`TTS failed: ${response.status}`);
    return;
  }

  // Get WAV bytes
  const wavBuffer = Buffer.from(await response.arrayBuffer());

  // Write to temp file
  const tempFile = join(tmpdir(), `narrator-${Date.now()}.wav`);
  writeFileSync(tempFile, wavBuffer);

  // Play with aplay (Linux) or afplay (macOS)
  const player = process.platform === "darwin" ? "afplay" : "aplay";

  return new Promise((resolve) => {
    const proc = spawn(player, [tempFile], { stdio: "ignore" });
    proc.on("close", () => {
      try { unlinkSync(tempFile); } catch {}
      resolve();
    });
    proc.on("error", () => {
      console.error(`Could not play audio with ${player}`);
      resolve();
    });
  });
}

// ============================================================================
// Test Snippets (Simulating agent activity)
// ============================================================================

const TEST_SNIPPETS: Snippet[] = [
  {
    id: "1",
    source: "tool",
    type: "progress",
    content: "Calling getFleetStatus for your 3 fleets",
    priority: "medium",
    timestamp: Date.now(),
  },
  {
    id: "2",
    source: "subagent",
    type: "finding",
    content: "Fleet Alpha is currently docked at Starbase MRZ-1",
    priority: "high",
    timestamp: Date.now(),
  },
  {
    id: "3",
    source: "subagent",
    type: "finding",
    content: "Fleet Alpha fuel level is at 15 percent, below critical threshold",
    priority: "critical",
    timestamp: Date.now(),
  },
  {
    id: "4",
    source: "tool",
    type: "progress",
    content: "Checking current ATLAS token price",
    priority: "medium",
    timestamp: Date.now(),
  },
  {
    id: "5",
    source: "main_agent",
    type: "decision",
    content: "Prioritizing fuel alert - will recommend immediate refueling",
    priority: "high",
    timestamp: Date.now(),
  },
  {
    id: "6",
    source: "tool",
    type: "error",
    content: "Failed to connect to Solana RPC endpoint",
    priority: "critical",
    timestamp: Date.now(),
  },
  {
    id: "7",
    source: "tool",
    type: "completion",
    content: "Fleet status analysis complete",
    priority: "medium",
    timestamp: Date.now(),
  },
];

// ============================================================================
// Interactive Benchmark
// ============================================================================

async function runInteractiveBenchmark(
  provider: "ollama" | "haiku",
  verbosity: VerbosityLevel,
  model?: string
): Promise<void> {
  console.log("\n🎙️  INTERACTIVE NARRATOR BENCHMARK");
  console.log(`Provider: ${provider.toUpperCase()}${model ? ` (${model})` : ""}`);
  console.log(`Verbosity: ${verbosity}`);
  console.log("=".repeat(60));

  // Intro speech
  console.log("\n🔊 Speaking intro...");
  await synthesizeAndPlay("Starting narrator test. Listen for vocalizations.");

  const narrator: Narrator = provider === "ollama"
    ? new OllamaNarrator(model)  // Pass custom model
    : new HaikuNarrator();

  narrator.configure({ verbosity });

  let vocalizeCount = 0;
  let silentCount = 0;

  for (const snippet of TEST_SNIPPETS) {
    // Update timestamp to NOW (test data timestamps are stale)
    snippet.timestamp = Date.now();

    console.log(`\n📋 Snippet [${snippet.priority}]: "${snippet.content}"`);

    const start = Date.now();
    const result = await narrator.ingest(snippet);
    const latency = Date.now() - start;

    if (result.action === "vocalize" && result.utterance) {
      vocalizeCount++;
      console.log(`🗣️  VOCALIZE (${latency}ms): "${result.utterance}"`);
      console.log("   🔊 Speaking...");
      await synthesizeAndPlay(result.utterance);
    } else {
      silentCount++;
      console.log(`🤫 SILENT (${latency}ms)`);
    }

    // Small pause between snippets
    await new Promise((r) => setTimeout(r, 300));
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("SUMMARY");
  console.log("=".repeat(60));
  console.log(`Vocalized: ${vocalizeCount}/${TEST_SNIPPETS.length}`);
  console.log(`Silent: ${silentCount}/${TEST_SNIPPETS.length}`);

  // Test summarization
  console.log(`\n📝 Testing summarization (buffer has ${narrator.getBufferSize()} snippets)...`);
  const summary = await narrator.summarize();
  console.log(`Summary: "${summary}"`);
  console.log("🔊 Speaking summary...");
  await synthesizeAndPlay(summary);

  console.log("\n✅ Interactive benchmark complete!");
}

// ============================================================================
// CLI
// ============================================================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  let provider: "ollama" | "haiku" = "ollama";
  let verbosity: VerbosityLevel = "normal";
  let model: string | undefined;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--provider" && args[i + 1]) {
      provider = args[++i] as typeof provider;
    }
    if (args[i] === "--verbosity" && args[i + 1]) {
      verbosity = args[++i] as VerbosityLevel;
    }
    if (args[i] === "--model" && args[i + 1]) {
      model = args[++i];
    }
  }

  // Check TTS is available
  try {
    const health = await fetch("http://localhost:8001/health");
    if (!health.ok) throw new Error("TTS not healthy");
  } catch {
    console.error("❌ Voice backend not running at localhost:8001");
    console.error("   Start it with: cd packages/voice-backend && python -m src.main");
    process.exit(1);
  }

  await runInteractiveBenchmark(provider, verbosity, model);
}

main().catch((error) => {
  console.error("Benchmark failed:", error);
  process.exit(1);
});
