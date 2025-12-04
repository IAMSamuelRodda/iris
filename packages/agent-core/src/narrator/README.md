# Narrator Module

> Streaming context narrator for voice-first feedback

## Overview

The narrator ingests context snippets from the agent pipeline and decides what to vocalize to the user in real-time. It translates technical agent activity into natural speech.

## Architecture

```
Agent Pipeline                     Narrator                        TTS
     │                                │                             │
     ├─► tool_progress ─────────────► │                             │
     │   "Calling getFleetStatus"     │ ──► evaluate() ─────────►   │
     │                                │     Should vocalize?        │
     ├─► finding ───────────────────► │                             │
     │   "Fleet Alpha fuel at 15%"    │ ──► "Heads up, fuel is      │
     │                                │      critically low."  ────►│
     │                                │                             │
     └─► completion ────────────────► │ ──► SILENT (not useful)     │
                                      │                             │
                                      │                             │
User: "What's happening?"  ─────────► │ ──► summarize() ──────────► │
                                      │     "I'm checking your      │
                                      │      fleet status..."       │
```

## Dual Implementation Strategy

We maintain **two narrator implementations**:

### OllamaNarrator (Local - Qwen 7B)

**Production default.** Fast, free, always available.

| Metric | Value |
|--------|-------|
| Latency | 180-200ms |
| Cost | $0 |
| Availability | 100% (local) |
| Quality | Good |

### HaikuNarrator (Cloud - Claude Haiku 4.5)

**Reference implementation.** Higher quality, but latency/cost prohibitive for real-time narration.

| Metric | Value |
|--------|-------|
| Latency | 1500-3200ms |
| Cost | ~$0.01/snippet |
| Availability | Requires internet |
| Quality | Excellent |

## Why Keep Both?

1. **Future OAuth Integration**
   When Anthropic enables OAuth, users can bring their own API keys. The Haiku path will be ready.

2. **Learning from Haiku**
   Haiku's responses inform system prompt improvements for local models. We observe patterns in Haiku's better decisions and encode them into Qwen's prompts.

3. **Latency Diagnosis**
   Haiku includes timing instrumentation. The 1.5-3.2s latency is **100% API call time** (network + Anthropic processing), not our code. This validates our local-first approach.

4. **A/B Testing**
   `ComparisonNarrator` runs both in parallel for quality comparison during development.

## Latency Breakdown (Haiku)

```
prompt=0ms, api=1700ms, parse=0ms
```

The API call dominates. For short narrator responses (~20 tokens), network overhead matters more than generation speed.

## Usage

```typescript
import { createNarrator, createSnippet } from "@iris/agent-core";

// Use local Qwen (default, fast)
const narrator = createNarrator("ollama");

// Or use Haiku (slower but smarter)
const narrator = createNarrator("haiku");

// Configure verbosity
narrator.configure({ verbosity: "normal" });

// Ingest snippets as agent works
const result = await narrator.ingest(
  createSnippet("tool", "progress", "Calling getFleetStatus", "medium")
);

if (result.action === "vocalize") {
  await tts.synthesize(result.utterance);
}

// User asks "what's happening?"
const summary = await narrator.summarize();
```

## Verbosity Levels

| Level | Behavior |
|-------|----------|
| `silent` | Never vocalize, but still buffer context |
| `minimal` | Only critical findings and errors |
| `normal` | Key progress points, important findings |
| `verbose` | Narrate most activity |

## Files

- `types.ts` - Snippet, VocalizationResult, NarratorConfig
- `base-narrator.ts` - Shared logic: buffer, cooldowns, parsing
- `ollama-narrator.ts` - Local Qwen 7B implementation
- `haiku-narrator.ts` - Cloud Haiku 4.5 implementation
- `comparison-narrator.ts` - A/B testing harness
- `index.ts` - Factory and exports

## Future Work

- [ ] Integrate with agent.ts producer loop
- [ ] WebSocket streaming of narrator decisions
- [ ] Hybrid mode: Qwen for routine, Haiku for summaries
- [ ] Fine-tune local model on Haiku's output patterns
