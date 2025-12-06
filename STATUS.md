# IRIS - Project Status

> **Purpose**: Current work, active bugs, and recent changes (2-week rolling window)
> **Lifecycle**: Living (update daily/weekly during active development)

**Last Updated**: 2025-12-06 (9 native tools complete - session todo, utilities, Todoist integration)
**Current Phase**: Implementation (Native client development)
**Version**: 0.1.0 (Pre-MVP)
**Focus**: Native Primary, Web Secondary

---

## Quick Overview

| Aspect | Status | Notes |
|--------|--------|-------|
| Planning | Done | Vision alignment complete, architecture refreshed |
| Architecture Docs | Done | CLAUDE.md, README.md, ARCHITECTURE.md updated for VPS |
| Infrastructure | Done | Using existing DO VPS (640MB+ RAM available) |
| Monorepo Setup | Done | pnpm workspaces, 6 packages (voice-backend added) |
| MCP Server Foundation | Done | Feature 1.1 complete (lifecycle, tools, errors) |
| **Memory Service** | **Done** | Epic 2 complete (knowledge graph, MCP tools, tests) |
| **Agent Core** | **Done** | Epic 3 complete (Claude Agent SDK, IrisAgent class) |
| **Voice Service** | **Done** | Epic 4 complete (faster-whisper STT, Kokoro TTS) |
| **Web App** | **Done** | Epic 5 complete (React + Vite, chat UI, voice PTT) |
| **Tool System** | **Done** | 9 native tools (session todo, utilities, Todoist) |
| CI/CD Pipeline | N/A | Main-only workflow; deploy via docker-compose |
| Test Coverage | Partial | 12 tests for memory service |
| Known Bugs | None | Early implementation |
| **MVP Scope** | **Reduced** | 3 tasks + 1 epic deferred (see below) |

---

## Current Focus

**Completed (2025-12-02):**
- **Web App (Epic 5) complete**:
  - React + Vite frontend with space-themed dark UI
  - Chat interface with streaming SSE responses
  - Voice interface (push-to-talk) with WebSocket
  - Agent HTTP API server (Hono + SSE streaming)
  - Environment-based configuration (VITE_AGENT_API_URL, VITE_VOICE_WS_URL)
- **Voice Service (Epic 4) complete**:
  - Python voice-backend (FastAPI + faster-whisper + Kokoro)
  - Node.js WebSocket bridge for browser audio streaming
  - STT: faster-whisper with int8 quantization (~200MB for base model)
  - TTS: Kokoro-82M (~42ms synthesis, 11 curated voices)
  - Docker Compose orchestration for voice services
  - Modular architecture: browser → WebSocket → Python backend
- **Agent Core (Epic 3) complete**:
  - Claude Agent SDK integration (`@anthropic-ai/claude-agent-sdk`)
  - In-process MCP server via `createSdkMcpServer()` (zero subprocess overhead)
  - `IrisAgent` class with streaming `chat()` and `chatComplete()` methods
  - IRIS system prompt with voice-optimized personality
  - Dynamic user context injection from memory
  - Session management via Agent SDK `resume` option
  - Key decision: Agent-first architecture (not just chat API wrapper)
- **Memory Service (Epic 2) complete**:
  - SQLite knowledge graph (entities, observations, relations)
  - MCP tools: 11 tools aligned with Anthropic memory server
  - Conversation TTL (48h default, cleanup job)
  - User edit tracking ("remember that..." requests)
  - Prose summaries with staleness detection
  - 12 unit tests passing
  - Pattern extracted to agentic-framework: `patterns/sqlite-knowledge-graph.md`
- Monorepo initialized with pnpm workspaces (5 packages)
- MCP Server Foundation (Feature 1.1) complete:
  - TypeScript + MCP SDK setup
  - Server lifecycle handlers (connect, shutdown)
  - Tool registration framework with error handling
  - First tool: `getWalletBalance` (Solana)
- Solana Blockchain Tools (Feature 1.2) complete:
  - `getTransactionHistory` tool with pagination support
  - Transaction type inference (SOL/token transfers, program interactions)
  - MVP scope refined (prepareTransaction deferred)
- Star Atlas Fleet Tools (Feature 1.3) complete:
  - `getFleetStatus` MVP: player profile verification
  - `predictFuelDepletion`: fuel status and recommendations
  - SAGE SDK spike needed for auto-fetch fleet data

**Completed (2025-12-01):**
- Vision alignment session (docs/planning-session-2025-11-12.md)
- Architecture pivot: AWS -> Digital Ocean VPS
- Memory architecture simplified to SQLite (pip-by-arc-forge pattern)
- Voice service updated to use Chatterbox (self-hosted STT/TTS)

**Completed (2025-12-04):**
- **Streaming Narrator Module** (Experimental):
  - Ingests context snippets from agent pipeline, decides what to vocalize
  - Dual implementation: local Qwen 7B (production) and cloud Haiku (reference)
  - Verbosity levels: silent, minimal, normal, verbose
  - Context buffer with rolling window for "what's happening?" queries
  - Cooldown mechanism to prevent vocalization spam
  - Benchmarks: Qwen 7B = 180-200ms, Haiku = 1500-3200ms (100% API time)
  - Decision: Local Qwen for production, Haiku for reference/future OAuth
  - Files: `packages/agent-core/src/narrator/`
  - Status: Merged to main, not yet integrated with agent.ts producer loop

**Completed (2025-12-03):**
- **Voice Styles System** (UX Enhancement):
  - 5 voice styles: Normal, Formal, Concise, Immersive, Learning
  - Voice style selector in web-app UI (persists to localStorage)
  - Style-specific system prompt injection via `buildVoiceStylePrompt()`
  - TTS parameters: `speechRate`, `exaggeration` per style
  - Thinking feedback control: "none", "minimal", "verbose"
- **Fast Layer (Haiku 4.5)** - Quick acknowledgments:
  - **OPTIMIZED**: Direct Anthropic SDK (not Agent SDK) for minimal latency
  - Model: `claude-haiku-4-5-20251001` for <200ms acknowledgments
  - **Expanded pattern-based fallbacks**: Now covers ~90% of voice queries
    - Domain patterns: fleet, wallet, market, mission, account
    - Question patterns: what/where/when/why/who/how/can you/etc.
    - Request patterns: tell me/show me/find/search/explain/etc.
    - Action patterns: do/make/create/start/stop/enable/etc.
    - Fallback: Any message >10 chars gets generic acknowledgment
  - **Results**: Pattern fallbacks = 3-12ms, Haiku dynamic = 1.7-2.7s
  - Acknowledgment streaming via SSE `acknowledgment` chunk type
  - Respects voice style `thinkingFeedback` setting
- **Fast Layer Testing** (End-to-end verified):
  - Fixed `needsAcknowledgment()` threshold: 20 chars → 5 chars
  - Acknowledgments now trigger for typical voice input
  - Voice-only feedback (no text shown) - intentional for speed
  - Measured warm TTS: 2-3s for acknowledgment synthesis
  - Known issue: TTS cold start ~2s (Kokoro model load)
  - ✅ Fixed: Audio overlap (ack + response now play sequentially)

**In Progress:**
- ✅ **Local Tool Integration** (2025-12-06) **COMPLETE**:
  - **Native Ollama Tools** (9 tools, 0ms overhead):
    - Session: `todo_add`, `todo_complete`, `todo_list` (like Claude Code's TodoWrite)
    - Utility: `get_current_time`, `calculate`, `web_search` (Brave API)
    - Todoist: `todoist_create_task`, `todoist_list_tasks`, `todoist_complete_task`
  - **Todoist Integration**: Direct REST API (simpler than MCP)
    - Natural language due dates ("tomorrow", "in 4 hours")
    - Fuzzy task completion (search by content)
    - Config: `TODOIST_API_KEY` in `~/.config/iris/secrets.env`
  - **Files**: `src/tools.py` (all tools in one place)
  - **MCP Bridge**: `src/mcp_bridge.py` available for future MCP tools

- ✅ **Voice Latency Architecture Overhaul** (2025-12-03 - ARCH-003) **COMPLETE**:
  - ✅ Phase 1.1: WebSocket endpoint added to Python FastAPI (`/ws/voice`)
  - ✅ Phase 1.3: Browser VoiceClient updated for direct Python connection
  - ✅ Phase 1.4: Node.js voice-service marked as DEPRECATED
  - ✅ Phase 2: Binary WebSocket protocol (eliminates base64 overhead)
    - Binary protocol: 2-byte header + raw PCM payload
    - Browser sends raw PCM audio (no base64 encode)
    - Server sends raw PCM TTS (no base64 encode)
    - ~33% less data transfer, eliminates btoa/atob overhead
  - ✅ Phase 3.1: Streaming audio capture (real-time PCM via ScriptProcessorNode)
  - ✅ Phase 3.3: GPU STT working (cuDNN fix: auto-load nvidia-cudnn libs at startup)
  - ✅ Phase 4: Rust gateway design document (`specs/DESIGN-rust-voice-gateway.md`)
  - **Architecture change**: 12 hops → 3 hops, ~76% encoding overhead → ~10%
  - **Full GPU config**: STT=CUDA (181ms), TTS=CUDA (520ms) - both now work together
  - **Plan**: `specs/PLAN-voice-latency-optimization.md`

- 🟢 **Voice Latency Optimization** (2025-12-03 - ARCH-002):
  - ✅ Empirical benchmark created: `test_e2e_latency.py`
  - ✅ Measured: E2E latency = 6.2s (target: <500ms)
  - ✅ GPU TTS acceleration: Kokoro on RTX 4090 (42ms, 12x faster than Chatterbox)
  - ✅ Full GPU config: STT=CUDA (181ms), TTS=CUDA (42ms)
  - ✅ Fast Layer: Haiku 4.5 for quick acknowledgments while Sonnet processes
  - ✅ Fast Layer tested: acknowledgments working via voice
  - ✅ Audio queue: Fixed overlap with producer-consumer pattern
  - ❌ Bottleneck: Claude API (Sonnet) = 5030ms (81% of total)
  - **Target**: ~225ms audio latency (STT + pattern match + TTS)

- 🟢 **Voice Integration** (Complete 2025-12-03):
  - ✅ STT (faster-whisper) - **GPU WORKING** - 181ms latency (32% faster than CPU)
  - ✅ WebSocket bridge - audio streaming from browser functional
  - ✅ Push-to-talk UI - recording and sending audio
  - ✅ TTS (Kokoro) - **WORKING** - 42ms on GPU (12x faster than Chatterbox)
  - ✅ Response conciseness - max 2 sentences for TTS
  - ✅ Duplicate response bug - fixed
  - ✅ cuDNN conflict resolved - auto-load nvidia-cudnn libs at startup
  - Note: Full GPU mode (STT_DEVICE=cuda, TTS_DEVICE=cuda)
  - Note: Kokoro-82M model cached in ~/.cache/huggingface/

- 🟡 **Integration Testing** (2025-12-02):
  - ✅ Agent API (port 3001) - working, tested chat endpoint
  - ✅ Web App (port 3002) - serving, chat interface functional
  - ✅ Voice backend (port 8001) - STT working on CPU
  - ✅ Voice WebSocket (port 8002) - audio streaming works
  - ✅ Dockerfiles fixed (UID 1000 conflict resolved)
  - Branding: "guy in the chair" personality

- 🟡 **ARCH-001**: IRIS/CITADEL separation - decision made (2025-12-02)
  - MCP tools **stay in IRIS** (wrap Citadel REST API)
  - Citadel provides REST + WebSocket only
  - BLOCKED: Waiting for Citadel REST API (Epic 2-3)

**Next Up (MVP scope):**
- [x] **Voice conciseness**: IRIS responses max 2 sentences for TTS
- [x] **TTS testing**: Chatterbox voice synthesis working
- [x] **End-to-end voice testing**: Full voice loop tested (ack + response)
- [ ] **Audio queue**: Fix playback overlap (ack plays over response)
- [ ] **TTS pre-warming**: Load model on startup to avoid cold start
- [ ] CITADEL: REST API for blockchain/game data (separate repo)

**Deferred from MVP (2025-12-02):**
- ⏸️ `prepareTransaction` tool - users execute via Star Atlas UI
- ⏸️ `subscribeToFleetUpdates` WebSocket - use polling instead
- ⏸️ Latency optimization - measure first, optimize post-MVP
- ⏸️ CITADEL Integration (Epic 8) - entire epic is post-MVP
- ⏸️ CI/CD pipelines - main-only workflow, deploy via docker-compose

---

## Deployment Status

### Production (Planned)
- **Target**: Digital Ocean VPS (production-syd1)
- **URL**: TBD (staratlas.rodda.xyz or similar)
- **Status**: Not deployed

---

## Known Issues

### Critical

**ARCH-002: Voice Latency Optimization** ✅ RESOLVED
- **Fast-Layer Benchmark** (v2): `packages/voice-backend/test_e2e_latency_v2.py`
- **Measured Fast Path** (Full GPU, warm, beam_size=1):
  - STT: 22-28ms + Pattern match: 3-12ms + TTS: 42ms = **~70-80ms to first audio** ✅
- **Pattern-based acknowledgments**: 3-12ms (covers ~90% of voice queries)
- **Haiku dynamic acknowledgments**: 1.7-2.7s (for unmatched patterns)
- **GPU STT**: 22-28ms for 2s audio (optimized beam_size=1) - cuDNN conflict RESOLVED
- **GPU TTS (Kokoro)**: 42ms (vs 500ms with Chatterbox - 12x improvement)
- **Claude main model**: Currently Haiku for testing (switch to Sonnet for production)
- **Run services**: `STT_DEVICE=cuda TTS_DEVICE=cuda` (default, both GPU)
- **Run benchmark**: `python test_e2e_latency_v2.py --compare-styles`

### High Priority
None

### Medium Priority

**Audio Playback Overlap** ✅ RESOLVED (2025-12-03)
- Fixed: Audio now queued sequentially (nextPlayTime scheduling)
- File: `packages/web-app/src/api/voice.ts`

**TTS Cold Start** ✅ RESOLVED (2025-12-03)
- Switched to Kokoro-82M: cold start ~2s, warm synthesis ~42ms
- Model pre-warmed on server startup (see warmup_tts() in main.py)
- 11 curated voices available (default: af_heart)

---

## Recent Achievements (Last 2 Weeks)

**Tool System Complete (2025-12-06)**
- **Session Todo Tools** (like Claude Code's TodoWrite):
  - IRIS can track multi-step tasks during conversation
  - `todo_add`, `todo_complete`, `todo_list` native tools
  - Session-scoped: cleared on restart, used for complex requests
  - Example: "Check fleet, find route, remind me to refuel" → 3 tracked tasks
- **MCP Bridge for External Tools**:
  - `src/mcp_bridge.py`: Connects to lazy-mcp proxy
  - Todoist integration: `mcp_create_reminder`, `mcp_list_reminders`, `mcp_complete_reminder`
  - Graceful degradation: MCP tools only appear when lazy-mcp is running
  - ~800 token overhead (95% less than direct MCP)
- **Unified Tool Access**:
  - `get_all_tools()`: Returns native + MCP tools for Ollama
  - `execute_tool()`: Routes to native or MCP based on `mcp_*` prefix
  - Rate limiter and quota tracking for web search (Brave API)

**Future Architecture Planning (2025-12-05)**
- **Subagent Delegation** (ARCH-008, Epic 9):
  - Documented Ollama 2-model limit and vLLM/SGLang migration triggers
  - Added A2A protocol (Google) and Claude Code pattern research items
  - UX patterns for delegation feedback ("Let me look into that...")
- **Context Window Optimization** (ARCH-009, Epic 10):
  - Strategies: summarization, sliding window, tool compression
  - Context budget monitoring patterns
- **Native Memory Integration** (ARCH-010, Epic 11):
  - Documented gap: memory-service is TypeScript, native client is Python
  - Plan: Python port with shared SQLite schema
  - Dependency chain: Tools → Memory → Delegation → Context

**PROGRESS.md Realignment & Tool Research (2025-12-05)**
- **Focus pivot**: Native Primary, Web Secondary
  - Epic 0 (Native Client) now primary development track
  - Epics 1, 3, 5-8 marked as SECONDARY (Web)
  - Epics 2, 4 marked as SHARED (used by both)
- **Tool integration research**: `specs/RESEARCH-tool-integration-architecture.md`
  - Ollama native tools: 0ms overhead, ~50-80 tokens/tool
  - MCP tools via lazy-mcp: ~800 tokens total (95% reduction from 15k)
  - Hybrid approach: local tools bundled in .deb, remote via MCP
  - lazy-mcp-preload eliminates cold-start latency
- **Implementation strategy**:
  - Phase 1: Native Ollama tools (time, calculator, timer)
  - Phase 2: MCP for CITADEL when API ready

**GUI Improvements & Bug Fixes (2025-12-05)**
- **Audio overlap race condition**: Fixed with threading mutex lock
  - `_processing_lock` prevents multiple VAD responses playing simultaneously
  - Lock acquired before processing, released in `finally` block
- **VAD toggle buffer flush**: Audio captured mid-recording now processed when VAD disabled
  - Instance-level `_vad_audio_buffer` and `_vad_is_speaking` for state tracking
  - `_stop_vad_listening()` flushes buffered audio ≥1s before stopping
- **Interruption context GUI panel**: Visual display of interruption state
  - Shows: intended response, spoken text, user interruption
  - Color-coded labels, auto-truncation, time display ("Interrupted Xs ago")
  - Updates on interruption record, user STT, and periodic refresh (1s)
- **Interruption context persistence**: Added to conversation history for LLM recall
  - Interruption note stored as assistant message in `_conversation_history`
  - IRIS can now answer "what did I miss?" after interruptions
  - Log: `[LLM] Added interruption context to history`

**Model-Specific System Prompts (2025-12-05)**
- **Layered prompt architecture**: Base prompt + model-specific additions
  - `SYSTEM_PROMPT_BASE`: Core personality and rules (all models)
  - `MODEL_PROMPTS`: Dict of model family → specific instructions
  - `get_system_prompt(model_name)`: Combines them at runtime
- **Current model-specific rules**:
  - Qwen: English only, no Chinese characters or emoji
  - Mistral: More concise, avoid verbosity
  - Llama: Stay focused, skip caveats
  - Phi: Extremely brief responses
- **Logging**: Shows which prompt variant is used (`[LLM] Using QWEN-specific system prompt`)
- **Tracked**: ISSUE-015 for removing limitations when tools are integrated

**Conversation Memory & Context Tracking (2025-12-05)**
- **Conversation history**: IRIS now remembers previous exchanges using Ollama `/api/chat`
  - Maintains last 10 turns (20 messages) in rolling history
  - Includes interruption context in prompts (what was intended vs spoken)
- **Context window tracking**: Token usage displayed in GUI and logged
  - GUI shows: `Context: X tokens (Y/10 turns)` in config section
  - Logs: `[LLM] Tokens: X prompt + Y completion = Z total (session: N)`
- **Minimum audio filter**: Increased from 0.3s to 1.0s to reduce false VAD triggers
- **System prompt improvements**: Explicit rules to prevent hallucinations
  - No placeholder text like `[Event Name]`, `[Time]`, `[Location]`
  - Clear statement of limitations (no fleet data, wallet, APIs in local mode)
- **Smooth interruptible playback**: Fixed choppy audio during barge-in
  - Continuous `sd.play()` with 50ms interrupt polling (was 100ms chunked)
- **Thread-safe VAD**: Separate VAD instance for barge-in monitor (prevents state corruption)

**Desktop Launcher & Interruption Architecture (2025-12-05)**
- **Desktop launcher**: `iris-local.desktop` + `iris-local-launcher.sh` for dock integration
  - Icon: `assets/iris-icon.png` (blue circle with IRIS text)
  - Launches GUI with ffmpeg audio mode automatically
  - Installs to `~/.local/share/applications/`
- **Interruption infrastructure** (barge-in support):
  - Added `InterruptionEvent` dataclass to track context during interruptions
  - State tracking: `_is_speaking`, `_interrupt_requested`, `_last_interruption`
  - Interruptible playback: Audio plays in 100ms chunks with interrupt checking
  - VAD monitoring during TTS: Detects when user starts speaking mid-response
  - Context annotation: Next LLM prompt includes what was intended vs what was spoken
  - Based on design in `specs/DESIGN-adaptive-verbosity.md`
- **Graceful shutdown**: Ctrl+C handler via SIGINT/SIGTERM signals in GUI
- **Distribution planning** (documented in ISSUES.md):
  - ASP-004: Self-hosted APT repository (Brave pattern) for Ubuntu
  - ASP-005: Product flavors (Star Atlas vs generic assistant)

**Python Native Client - iris-local (2025-12-05)**
- **New client**: `packages/voice-backend/iris_local.py` - native Python voice client
- **Zero web stack**: Direct sounddevice audio I/O (no WebSocket, no base64)
- **Silero VAD integration**: Always-listening mode with speech detection
- **Three modes**:
  - PTT (Push-to-Talk): Press Enter to record (CLI)
  - VAD (Voice Activity Detection): Auto-detects speech start/end (CLI)
  - GUI (DearPyGui): Visual interface with waveform, transcript, config
- **GUI features** (`python iris_local.py --gui`):
  - Real-time waveform visualizer
  - PTT button and VAD toggle (both now functional)
  - Conversation transcript display
  - Pipeline status indicators (STT/LLM/TTS)
  - Config panel (model, voice, max tokens)
- **ffmpeg audio fallback** (PipeWire compatibility):
  - Auto-detects when sounddevice can't capture from PipeWire
  - Falls back to `ffmpeg -f pulse -i default` for audio capture
  - `--ffmpeg` CLI flag to force ffmpeg mode
  - Enables USB wireless headsets (e.g., RIG 800HX) that only work via PipeWire
- **Benchmark results** (warm components):
  - First audio: **96-123ms** (vs 300-500ms with web stack)
  - LLM first token: 73-78ms
  - TTS first chunk: 23-45ms
- **Architecture**: Bypasses all network infrastructure
  ```
  Microphone → ffmpeg/sounddevice → VAD → STT → LLM → TTS → sounddevice → Speaker
  ```
- **Dependencies added**: `sounddevice` (local), `dearpygui` (gui) optional extras
- **Usage**: `python iris_local.py --gui --ffmpeg` for graphical interface with PipeWire
- **Known limitation**: Cannot interrupt IRIS mid-response (see DESIGN-adaptive-verbosity.md)
- **Future**: IPC for game integration (see ASP-003 in ISSUES.md)

**Streaming Stress Test & Benchmarks (2025-12-05)**
- **New test harness**: `packages/voice-backend/test_streaming_stress.py`
  - Extended LLM streaming (300-500 tokens)
  - Sentence-based chunking for progressive TTS
  - Audio playback with metrics collection
- **New benchmark doc**: `packages/voice-backend/BENCHMARKS.md`
  - Historical performance tracking across architectures
  - Model comparison (qwen2.5:7b, llama3.1:8b, mistral:7b)
  - Component warmup timings
- **Dynamic warmup system**: `packages/voice-backend/src/warmup.py`
  - Environment-based configuration (OLLAMA_MODEL, STT_DEVICE, etc.)
  - Runtime model switching: `warmup.warmup_llm("mistral:7b")`
  - Public methods: `warmup_all()`, `warmup_llm()`, `set_llm_model()`
- **Model comparison results** (300 tokens, warm):
  - qwen2.5:7b: 70-88ms first token, 122 tok/s, 180-434ms first audio
  - llama3.1:8b: 80-96ms first token, 116 tok/s, 288-480ms first audio
  - mistral:7b: 23ms first token, 127 tok/s, 138ms first audio (fastest)
- **Architecture validated**: Streaming LLM → sentence buffer → chunked TTS → progressive playback
- **Extended test**: 500 tokens = 29 TTS chunks, 156s audio, 4.3s total processing

**TTS Text Preprocessing (2025-12-05)**
- **New module**: `packages/voice-backend/src/text_processing.py`
- **Roman numerals → English words**: "Calico I" → "Calico one", "LVIII" → "fifty eight"
- **Smart pronoun detection**: Preserves "I" in "I am", "Can I help", "Hungry I am" (Yoda-speak)
- **Rules-based approach**:
  - Proper noun + I = Roman numeral ("Calico I" → "Calico one")
  - Common word + I = pronoun ("Can I" → preserved)
  - Action verb after I = pronoun ("Emily I know" → preserved)
- **Performance**: 0.01-0.02ms overhead (O(1) hash lookups, no NLP)
- **26 test cases** covering edge cases: Yoda-speak, inverted sentences, proper nouns
- **Bug discovered**: Kokoro TTS says "Chinese letter" for each CJK character
  - Root cause: LLM (Qwen) occasionally outputs Chinese characters
  - Fix: Preprocessing strips/handles non-ASCII before TTS

**Streaming LLM Testing (2025-12-05)**
- **Voice flow test harness**: `packages/voice-backend/test_voice_flow.py`
- **Performance benchmark**: `packages/voice-backend/test_preprocessing_perf.py`
- **GPU TTS with preprocessing**: 40-42ms total (preprocessing adds 0.01ms)
- **Full pipeline verified**: STT → LLM → preprocessing → TTS

**STT Latency Optimization (2025-12-05)**
- **Investigated ARCH-004**: 181ms STT latency was actually first-run cold start, not production latency
- **Actual warm latency**: 22-28ms for 2s voice commands (well under 50ms target)
- **Optimization applied**: `beam_size` changed from 5 to 1 (~50% latency reduction)
- **Benchmarks documented**: `packages/voice-backend/test_streaming_stt.py`
- **RealtimeSTT prototype**: `src/stt_streaming.py` available for future streaming needs
- **Conclusion**: Batch mode with optimized beam_size is sufficient; streaming architecture not required

**Ollama num_predict Discovery (2025-12-05)**
- **Root cause found**: Ollama has ~3s overhead when `num_predict` is not specified
- **Fix**: Add `options: { num_predict: 100 }` to all Ollama calls
- **Before fix**: 3487ms for 7 tokens (!!!)
- **After fix**: 106-118ms for same response
- **Impact**: 30x latency improvement for voice responses
- **Applied to**: `test_voice_flow.py`, narrator module already had it

**Voice Flow Test (2025-12-05)**
- **Test harness**: `packages/voice-backend/test_voice_flow.py` - automated test with audio playback
- **Film-style slates**: Audio announcements ("Model: qwen2.5 7b, Take 1") identify each test
- **Architecture validated**: STT → Ollama LLM → Kokoro TTS (pattern matching removed)
- **LLM latency (direct Ollama with num_predict=100)**: qwen2.5:7b ~174ms, mistral:7b ~234ms
- **TTS latency (warm)**: ~50ms for typical voice responses
- **Total latency**: 224-289ms for local 7B models (meets <500ms target)
- **Usage**: `python test_voice_flow.py --models qwen2.5:7b --no-slate`
- **Note**: Agent API uses Claude Cloud (~4-5s), direct Ollama for fast local inference

**Streaming Narrator Module (2025-12-04)**
- **Local-first approach**: Qwen 2.5 7B at 180-200ms latency (production ready)
- **Cloud reference**: Haiku 4.5 at 1500-3200ms (100% API time, validates local-first)
- **Architecture**: Base narrator + provider implementations (Ollama, Haiku)
- **Features**: Verbosity control, context buffer, cooldown, A/B comparison harness
- **Benchmarking**: Interactive TTS playback for human evaluation
- **Future**: Integrate with agent.ts, WebSocket streaming, hybrid mode

**Voice Latency Optimization (2025-12-03)**
- **GPU STT**: 22-28ms for 2s audio (optimized beam_size=1, was 181ms with beam_size=5)
- **GPU TTS (Kokoro)**: 42ms (12x faster than Chatterbox's 500ms)
- cuDNN fix: Auto-load nvidia-cudnn libs at startup via ctypes.CDLL
- Full GPU pipeline: STT=CUDA + TTS=CUDA both working together
- Streaming audio capture: Real-time PCM via ScriptProcessorNode (~93ms chunks)
- Binary WebSocket protocol: 2-byte header + raw PCM (~33% less overhead)

**Fast Layer Optimization (2025-12-03)**
- **BLAZING FAST**: Pattern-based acknowledgments now 3-12ms (was 5+ seconds)
- Root cause: Agent SDK `query()` had ~5s overhead for Haiku calls
- Fix 1: Replaced Agent SDK with direct `@anthropic-ai/sdk` for fast-layer
- Fix 2: Expanded pattern matching to cover ~90% of voice queries
- Fix 3: VoiceClient race condition fixed (connect() promise resolution)
- Fix 4: Acknowledgment yielded BEFORE prompt building (parallel execution)
- **Results**: User gets audio feedback in <500ms after speaking

**Voice UX Enhancement (2025-12-03)**
- Voice Styles: 5 distinct conversation modes (Normal, Formal, Concise, Immersive, Learning)
- GPU TTS: 42ms synthesis with Kokoro (12x faster than Chatterbox's 500ms)
- **Time to first audio: ~70-80ms** (STT ~25ms + pattern match 3ms + TTS ~42ms)
- UI: Voice style selector with persistent preferences

**Architecture Refresh (2025-12-01)**
- Migrated from AWS to Digital Ocean VPS (cost-predictable)
- Deferred personality progression (colleague -> partner -> friend)
- Adopted pip-by-arc-forge pattern (SQLite + Node.js)
- Self-hosted voice with Kokoro-82M ($0/month, Apache 2.0 license)

**Vision & Planning Session (2025-11-12)**
- Established multi-user SaaS scope with voice-first interface
- Documented strategic differentiation from EvEye (AI insights vs data viz)
- Extracted wisdom from galactic-data archives (Solana integration patterns)

---

## Next Steps (Priority Order)

1. ✅ **Simple Git Workflow** (Complete 2025-12-02)
   - `main` only, no branch protection
   - Worktrees for parallel agent work
   - See `CONTRIBUTING.md` for workflow

2. ✅ **Memory Service** (Complete 2025-12-02)
   - SQLite knowledge graph with MCP tools
   - Pattern extracted to agentic-framework

3. ✅ **Agent Core** (Complete 2025-12-02)
   - Claude Agent SDK integration
   - In-process MCP server with memory + Star Atlas tools
   - IrisAgent class with streaming support

4. ✅ **Voice Service** (Complete 2025-12-02)
   - Python voice-backend: faster-whisper (STT) + Chatterbox (TTS)
   - Node.js WebSocket bridge for browser audio streaming
   - Docker Compose orchestration

5. ✅ **Web App** (Complete 2025-12-02)
   - React + Vite frontend with dark theme
   - Chat UI with streaming responses
   - Voice interface (push-to-talk)
   - Agent HTTP API with Hono

6. **Integration & Deployment** - Next
   - Docker Compose for all services
   - End-to-end testing
   - VPS deployment

---

## Open Questions

**Resolved:**
1. ~~Architecture?~~ -> VPS + SQLite (Digital Ocean, pip-by-arc-forge pattern)
2. ~~Price monitoring?~~ -> Secondary feature (context for AI, not charting)
3. ~~Target users?~~ -> Multi-user SaaS
4. ~~Personality progression?~~ -> DEFERRED (focus on robust memory first)
5. ~~Infrastructure?~~ -> Existing DO VPS (640MB+ RAM available)
6. ~~Voice processing?~~ -> Chatterbox (self-hosted, $0/month)
7. ~~Voice UX?~~ -> Push-to-talk for MVP

**Still pending:**
1. **Authentication flow**: Magic link vs wallet-first? (Lean: email-first)
2. **Subscription tiers**: Decide after MVP validation

---

**Note**: Archive items older than 2 weeks to keep document focused.
