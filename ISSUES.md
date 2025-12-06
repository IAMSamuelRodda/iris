# IRIS - Issues & Flagged Items

> **Purpose**: Track items needing attention before/during IRIS implementation
> **Generated from**: specs/BLUEPRINT-project-staratlas-20251201.yaml

**Last Updated**: 2025-12-06 (GUI UX improvements)

---

## Critical Priority (Riff Session 2025-12-05)

### ARCH-004: STT Latency Investigation - RESOLVED
**Severity**: ✅ Resolved | **Created**: 2025-12-05 | **Resolved**: 2025-12-05
**Component**: voice-backend (faster-whisper)

**Original Problem**: Getting 181ms STT latency on RTX 4090. Should be sub-50ms.

**Investigation Results** (2025-12-05):
The 181ms was **first-run cold start**, not actual transcription time.

**Actual Benchmarks** (RTX 4090, base model, int8, after warmup):

| Audio Duration | beam_size=5 (old) | beam_size=1 (new) |
|----------------|-------------------|-------------------|
| 2s (typical cmd) | 43ms | 22-28ms |
| 6s (long)      | 87ms | 55-58ms |

**Root Cause**: Default `beam_size=5` was unnecessarily slow for voice commands.

**Fix Applied**: Changed default `beam_size` from 5 to 1 in `src/stt.py:85`.
- ~50% latency reduction with minimal accuracy impact for short voice commands
- Now meeting sub-50ms target (22-28ms for typical 2s commands)

**Streaming Architecture**: Not required for current latency targets. Batch mode with
optimized beam_size is sufficient. RealtimeSTT remains available in `src/stt_streaming.py`
if future requirements demand partial transcripts during speech.

**References**:
- `test_streaming_stt.py` - Benchmark script with results
- `specs/DESIGN-adaptive-verbosity.md` - Streaming architecture design (future use)

**Future Optimization (if sub-20ms needed)**:
Custom streaming wrapper for maximum speed:
- Silero VAD for speech detection (~50ms)
- Custom faster-whisper streaming wrapper with 15-20ms chunks
- Forward pass every 100ms for partials
- Lighter weight than RealtimeSTT (no portaudio dependency)
- Theoretical: <15ms transcription latency possible with aggressive buffering
- ~2-4 hours to implement if batch mode latency becomes a bottleneck

---

### ARCH-005: VAD (Voice Activity Detection)
**Severity**: ✅ Resolved | **Created**: 2025-12-05 | **Resolved**: 2025-12-06
**Component**: voice-backend

**Original Problem**: No real-time voice activity detection. Currently using push-to-talk.

**Solution Implemented**: Silero VAD v5 integrated with full hands-free mode.

**Completed**:
- [x] Integrate Silero VAD into voice-backend (`src/vad.py`)
- [x] Wire VAD to trigger STT finalization (speech offset detection)
- [x] Enable interruption detection (barge-in during TTS)
- [x] Hands-free mode (VAD mode in GUI - speech onset + offset detection)

**How it works**:
1. **PTT mode**: User holds spacebar, VAD detects end-of-speech
2. **VAD mode**: Continuous listening, VAD detects both start and end of speech
3. **Barge-in**: VAD monitors during TTS playback, interrupts on speech detection

**Remaining enhancements** (split to ASP-006):
- Wake word ("Hey IRIS") for reduced false positives
- Background noise robustness improvements

---

### ASP-006: Wake Word Detection ("Hey IRIS")
**Severity**: 🟢 Low | **Created**: 2025-12-06
**Component**: voice-backend
**Type**: Enhancement (not blocking)

**Problem**: In VAD mode, any speech triggers IRIS. A wake word would reduce false positives.

**Options**:
| Approach | Latency | Accuracy | Complexity |
|----------|---------|----------|------------|
| **Porcupine** (Picovoice) | ~50ms | High | Low (pre-built) |
| **OpenWakeWord** | ~100ms | Medium | Medium (custom training) |
| **Whisper-based** | ~200ms | High | Low (reuse STT) |

**Recommended**: Start with Whisper-based (detect "hey iris" in first 2s of audio, discard if not present). Simple, no new dependencies.

**Status**: 🔮 Future (hands-free works without it)

---

## High Priority (Riff Session 2025-12-05)

### ARCH-006: Interruption Context Desync
**Severity**: ✅ Resolved | **Created**: 2025-12-05 | **Resolved**: 2025-12-06
**Component**: voice-backend (iris_local.py)

**Problem**: When user interrupts IRIS mid-response, context doesn't reflect what was actually spoken vs generated.

**Solution Implemented**:

```python
@dataclass
class InterruptionEvent:
    intended_response: str      # Full response IRIS was going to say
    spoken_up_to: str           # What user actually heard
    user_interruption: str      # What they said to interrupt
    timestamp: float
```

**Prompt Injection** (in `process_voice()`):
```
[INTERRUPTION: Your previous response was interrupted.
You intended to say: "Three updates. First, Alpha docked..."
but user only heard up to: "Second, fuel crit—"
Their interruption: "wait, what about my cargo?"]
```

**Implementation Details**:
1. `InterruptionEvent` stored when TTS is interrupted via barge-in
2. On next voice input, STT result populates `user_interruption`
3. Full context injected into conversation history before LLM call
4. GUI shows interruption panel with intended/spoken/user fields

**Benefits**:
- LLM knows what was intended vs heard
- Can offer to continue: "As I was saying, the third update..."
- Understands social context of being cut off

**Files Modified**:
- `iris_local.py`: `process_voice()` restructured to capture user interruption
- `iris_gui.py`: Interruption panel displays all three fields

**References**: `specs/DESIGN-adaptive-verbosity.md`

---

### BUG-001: PTT/VAD Mode Toggle UX Issues
**Severity**: ✅ Resolved | **Created**: 2025-12-06 | **Resolved**: 2025-12-06
**Component**: iris_gui.py, iris_local.py

**Problems Discovered**:
1. **PTT and VAD can both appear active** - checkbox shows VAD ticked while PTT button is active
2. **VAD mode switch during TTS doesn't capture audio** - switching to VAD mid-response fails to detect speech
3. **Barge-in doesn't work after mode switch** - VAD enabled but no speech detection occurs
4. **App becomes unresponsive** - had to use PTT to recover after failed VAD switch

**Root Cause**:
- `threading.Lock()` on VAD model was causing the model inference to hang in daemon threads
- PTT/VAD were independent controls (checkbox + button) instead of mutually exclusive
- No interrupt trigger when PTT pressed during speech

**Fixes Applied**:

| Fix | File | Line | Description |
|-----|------|------|-------------|
| Combo box mode selector | `iris_gui.py` | 263-269 | Replaced checkbox+button with dropdown |
| PTT disabled in VAD mode | `iris_gui.py` | 470-481 | Button disabled when VAD selected |
| PTT triggers interrupt | `iris_gui.py` | 454-459 | Pressing PTT during speech interrupts |
| Context stats in PTT | `iris_local.py` | 1450 | Token counter now updates after PTT |
| Removed VAD thread lock | `iris_local.py` | 315-318 | Lock was causing model() to hang |

**Verification**:
- Mode switching works cleanly in both directions
- VAD speech detection working (confidence 0.54-0.99)
- Barge-in detection working
- PTT interrupt during TTS working
- Context counter updating

---

### LOW-001: pthread_join Errors on GUI Shutdown
**Severity**: 🟢 Low | **Created**: 2025-12-06
**Component**: iris_local.py (DearPyGui)

**Problem**: On GUI close, spurious pthread_join errors appear in terminal:
```
pthread_join: No such process
```

**Impact**: Cosmetic only - does not affect functionality. Application shuts down correctly.

**Root Cause**: DearPyGui daemon threads may be destroyed before proper join due to Python GC.

**Workaround**: None needed - harmless warning.

---

### LOW-002: Multiple VAD Model Loads During Barge-In
**Severity**: 🟢 Low | **Created**: 2025-12-06
**Component**: iris_local.py (Silero VAD)

**Problem**: During rapid mode switching or barge-in detection, the Silero VAD model may be loaded multiple times:
```
[Barge-in] Loaded new Silero VAD model for detection thread
```

**Impact**:
- ~50-100ms extra latency per load (model is small)
- Slightly higher memory usage during parallel detection

**Root Cause**:
- Lock was removed from VAD model (was causing hangs)
- Barge-in monitor creates separate VAD instance for thread safety
- No model caching/pooling currently

**Potential Fix**: Create a model pool or lazy singleton for VAD instances. Low priority since current behavior is stable.

---

### ARCH-007: Streaming Architecture Overhaul
**Severity**: 🟡 High | **Created**: 2025-12-05
**Component**: Full stack

**Problem**: Current architecture waits for complete inputs before processing. Streaming would reduce perceived latency dramatically.

**Target Architecture**:
```
User speaking → STT streaming partials → LLM pre-thinking on context
User finishes → VAD detects → LLM finalizes immediately → TTS streams first tokens
```

**Key Changes Needed**:
- Streaming STT (ARCH-004)
- VAD integration (ARCH-005)
- LLM receives partials before user finishes ("pre-thinking")
- TTS starts on first token, not complete response

**Two-Tier Response Strategy**:
- **Local models**: Pure streaming, no ack needed (fast enough)
- **Cloud models**: Fast local ack while waiting for first cloud token

**The "Pre-Thinking" Insight**:
```
Partial: "What's the fuel..."
LLM internally: [probably asking about fleet fuel, prep that context]

Partial: "What's the fuel price..."
LLM internally: [oh, market question, pivot to ATLAS/POLIS data]

VAD: [end of speech]
LLM: [already has direction, generates immediately]
```

**Action Items**:
- [ ] Complete ARCH-004 (streaming STT)
- [ ] Complete ARCH-005 (VAD integration)
- [ ] Implement LLM partial context feeding
- [ ] Implement TTS token streaming
- [ ] Benchmark end-to-end latency

---

## Medium Priority (Riff Session 2025-12-05)

### ISSUE-010: Model-Specific System Prompts Needed
**Severity**: 🟠 Medium | **Created**: 2025-12-05 | **Status**: ✅ Implemented (basic)
**Component**: voice-backend (iris_local.py)

**Problem**: Different models respond better to different prompt structures. Currently using one-size-fits-all.

**Solution Implemented** (2025-12-05):
```python
SYSTEM_PROMPT_BASE = "..."  # Core personality (all models)
MODEL_PROMPTS = {
    "qwen": "...",    # English only, no Chinese/emoji
    "mistral": "...", # More concise
    "llama": "...",   # Stay focused
    "phi": "...",     # Extremely brief
}
get_system_prompt(model_name) → combines base + model-specific
```

**Location**: `packages/voice-backend/iris_local.py:76-154`

**Action Items**:
- [x] Create model-specific variants
- [x] Implement dynamic prompt loader (`get_system_prompt()`)
- [x] Logging shows which variant is used
- [ ] A/B test verbosity control per model (future)
- [ ] Extend to narrator module (future)

---

### ISSUE-011: Adaptive Verbosity Control
**Severity**: 🟠 Medium | **Created**: 2025-12-05 | **Status**: Design Phase
**Component**: agent-core

**Problem**: Response length doesn't adapt to user's communication style.

**Designed Solution**: Three-layer verbosity control:

1. **Style Layer** (system prompt) - baseline ceiling
2. **Explicit Commands** - "quick version" / "all details" (highest priority)
3. **Implicit Mirroring** - infer from user message length, cadence

**Signals**:
- Terse user (one-word commands) → short responses
- Verbose user (rambling) → acknowledge first, then detail
- Explicit override always wins

**Key Insight - The Affirmation Pattern**:
When users ramble, they often want to be *heard* first:
1. Brief acknowledgment ("Got it - you're dealing with X, Y, Z")
2. Then detailed response

**Action Items**:
- [ ] Implement word count / message length heuristics
- [ ] Detect explicit verbosity keywords
- [ ] Build rolling window for user style detection (last 3-5 messages)
- [ ] Integrate with narrator verbosity levels

**References**: `specs/DESIGN-adaptive-verbosity.md`

### GUI-001: Voice Style Selector in Native Client
**Severity**: ✅ Resolved | **Created**: 2025-12-06 | **Resolved**: 2025-12-06
**Component**: iris_gui.py, iris_local.py

**Problem**: No way to view or change voice style in the GUI.

**Solution Implemented**:
- Created `src/voice_styles.py` - Python port of TypeScript voice styles
- Added "Style" combo box in GUI config panel
- Five styles: Normal, Formal, Concise, Immersive, Learning
- Style applied to system prompt via `get_system_prompt(model, voice_style)`

**Files**:
- `src/voice_styles.py`: VoiceStyle dataclass, VOICE_STYLES registry, helpers
- `iris_gui.py`: Added combo box, callback `_on_voice_style_change`
- `iris_local.py`: Added `voice_style` to IrisConfig, updated get_system_prompt

**Note**: Persistence not yet implemented (session-only). Would need config file at `~/.config/iris/` for cross-session persistence.

### GUI-002: Show Acknowledgments in Conversation Transcript
**Severity**: ✅ Resolved | **Created**: 2025-12-06 | **Resolved**: 2025-12-06
**Component**: iris_local.py (DearPyGui)

**Problem**: When IRIS says "Checking..." before a tool call, this acknowledgment is spoken but not shown in the conversation transcript panel.

**Solution Implemented**:
- Added `on_acknowledgment` callback to IrisLocal class
- New `add_activity()` method in IrisGUI for activity indicators
- Acknowledgments shown with 💭 icon and distinct formatting

**Implementation**:
- [x] Display acknowledgment text in transcript when `[UX] LLM tool acknowledgment` fires
- [x] Visually distinguish from main responses (💭 prefix)

---

### GUI-003: Streaming Activity Display (Tool Calls, Searches)
**Severity**: ✅ Resolved | **Created**: 2025-12-06 | **Resolved**: 2025-12-06
**Component**: iris_local.py (DearPyGui)

**Problem**: Technical activity (tool calls, searches, memory operations) happens invisibly. User only sees final response.

**Solution Implemented**:
- Added `on_tool_call` and `on_tool_result` callbacks to IrisLocal
- Activity displayed inline in transcript with icons:
  - 🔧 Tool calls (e.g., "Using search.web_search...")
  - 📋 Tool results (truncated preview)
  - 💭 Acknowledgments (e.g., "Let me check...")

**Implementation**:
- [x] Add callback mechanism to IrisLocal for activity events
- [x] Display tool calls with 🔧 icon
- [x] Display tool results with 📋 icon (truncated to 100 chars)
- [x] Wire callbacks in run_gui_mode()

---

## Future Architecture (Investigation Items)

### ARCH-008: Subagent Delegation & Multi-Model Infrastructure
**Severity**: 🔮 Future | **Created**: 2025-12-05
**Component**: LLM infrastructure

**Context**: IRIS will need to delegate complex tasks to subagents while preserving main conversation context (similar to Claude Code's task runners).

**Current State (Ollama)**:
- `OLLAMA_MAX_LOADED_MODELS=2` - max 2 models hot
- Model swaps: ~2-3 seconds
- Acceptable for MVP with UX feedback ("Let me look into that...")

**Triggers to Investigate vLLM/SGLang**:
| Trigger | Platform to Evaluate |
|---------|---------------------|
| Need 3+ models simultaneously | vLLM |
| Tool calling unreliable with complex schemas | SGLang |
| Scaling to multiple users | vLLM or TGI |
| Need constrained JSON output | SGLang |

**Subagent Use Cases**:
1. **Task Runners**: Small/fast model for simple tool execution
2. **Deep Thinkers**: Larger model for complex reasoning
3. **Specialists**: Domain-specific fine-tuned models

**MVP Approach**:
- 2 models: conversational (qwen2.5:7b) + thinking (can swap to larger)
- UX communicates delegation: "I need to think about that..."
- User expects delay for complex tasks

**Future Architecture** (when Ollama limits hit):
```
vLLM Server (keeps multiple models warm):
├── Main conversational model (always hot)
├── Task runner model (hot)
├── Deep thinking model (load on demand)
└── Specialist models (pool)
```

**Research Needed**:
- [ ] Benchmark Ollama model swap latency
- [ ] Test vLLM concurrent model loading
- [ ] Evaluate SGLang for tool calling reliability
- [ ] Design delegation protocol (context passing)
- [ ] **Investigate A2A (Agent-to-Agent) protocol** - Google's open standard
- [ ] **Study Claude Code's delegation architecture** - how Anthropic does subagents

**Agent Communication Protocols to Evaluate**:

| Protocol | Origin | Description | Investigate When |
|----------|--------|-------------|------------------|
| **A2A** | Google | Open standard for agent interoperability | Delegation spike |
| **MCP** | Anthropic | Tool/resource protocol (we use this) | Already integrated |
| **Custom** | Internal | Direct function calls, shared context | MVP approach |
| **Claude Code pattern** | Anthropic | Task runners with isolated context | Delegation spike |

**A2A Protocol (Google - April 2025)**:
- Open specification for agent-to-agent communication
- Designed for cross-vendor agent interoperability
- Potential benefits: standardized handoff, capability discovery
- Needs research: overhead vs custom, compatibility with local models

**Claude Code Delegation Pattern**:
- Uses `Task` tool to spawn subagents with specific capabilities
- Subagents have isolated context (stateless, single task)
- Results returned to main agent for integration
- Different agent types for different tasks (Explore, Plan, etc.)
- Study: context isolation benefits, result aggregation patterns

**Pros/Cons Analysis (Future Research)**:

| Approach | Pros | Cons |
|----------|------|------|
| **A2A Protocol** | Interoperability, standardized | Overhead?, new tech, may be overkill for local |
| **Custom Delegation** | Simple, low latency, full control | Not portable, reinventing wheel |
| **Claude Code Style** | Battle-tested, context isolation | Anthropic-specific patterns |

**Status**: 🔮 Future (implement delegation logic with Ollama first, migrate infrastructure when limits hit)

---

### ARCH-009: Context Window Optimization
**Severity**: 🔮 Future | **Created**: 2025-12-05
**Component**: Conversation management

**Context**: More context = more natural conversation + more useful agent. Need strategies to maximize effective context usage.

**Current State**:
- Rolling 10-turn history (~20 messages)
- No summarization
- Tool results stored in full
- Interruption context persisted

**Problem Areas**:
1. Long conversations lose early context
2. Tool results consume tokens (especially large API responses)
3. No distinction between "must remember" vs "nice to have"

**Optimization Strategies to Investigate**:

| Strategy | Description | Complexity |
|----------|-------------|------------|
| **Conversation summarization** | Compress old turns to summaries | Medium |
| **Sliding window + key facts** | Keep recent + extract important facts | Medium |
| **Tool result compression** | Summarize large API responses | Low |
| **Semantic chunking** | Store/retrieve by relevance | High |
| **Memory tier separation** | Hot (recent) vs warm (session) vs cold (persistent) | High |

**Conversation Summarization Pattern**:
```python
# When context exceeds threshold
if token_count > MAX_CONTEXT * 0.8:
    old_turns = conversation[:-5]  # Keep last 5 fresh
    summary = summarize_llm(old_turns)  # Compress to ~200 tokens
    conversation = [{"role": "system", "content": f"Earlier: {summary}"}] + conversation[-5:]
```

**Tool Result Compression Pattern**:
```python
# For large tool responses
if len(tool_result) > 1000:
    compressed = summarize_llm(f"Summarize key data: {tool_result}")
    return f"[Tool returned {len(tool_result)} chars, summary: {compressed}]"
```

**Key Insight**: Context window is precious for voice assistants. Every token spent on old/redundant info is a token not available for nuanced responses.

**Benchmarks Needed**:
- [ ] Measure current token usage per conversation turn
- [ ] Test summarization quality at various compression ratios
- [ ] Measure latency impact of summarization step
- [ ] A/B test user perception of context-aware vs context-limited

**Status**: 🔮 Future (focus after tools are working)

---

### ARCH-010: Native Memory Integration
**Severity**: 🔮 Future | **Created**: 2025-12-05
**Component**: voice-backend (Python), memory-service (TypeScript)

**Context**: IRIS has a fully implemented memory service (`packages/memory-service/`) based on Anthropic's MCP Memory Server pattern, but it's TypeScript for the web backend. The native Python client doesn't use it yet.

**Current State**:
- `packages/memory-service/`: Complete TypeScript implementation
  - Knowledge graph (entities, observations, relations)
  - 11 MCP tools (create/delete/search/summarize)
  - Conversation memory with TTL
  - User edit tracking (`is_user_edit` flag)
- Native client (`iris_local.py`): In-memory conversation only, no persistence

**Integration Options**:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Python port** | Rewrite memory-service in Python | Native, no bridge | Duplicate code |
| **MCP server** | Run memory-service as MCP server | Reuse existing code | Extra process, latency |
| **SQLite direct** | Python client writes to same SQLite | Shared data | Schema coupling |

**Recommended Approach**: Python port with shared SQLite schema
- Port `KnowledgeGraphManager` to Python
- Same SQLite schema as TypeScript version
- Native Ollama tools for memory operations
- Shared database between native and web clients

**Memory Tools for Ollama**:
```python
MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Store a fact about the user or their Star Atlas experience",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string"},
                    "entity_type": {"type": "string"},
                    "observation": {"type": "string"}
                },
                "required": ["entity_name", "observation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search memory for information about a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]
```

**Dependency**: Feature 0.7 (Local Tool Integration) must be complete first - memory tools require tool calling to work.

**Pattern Reference**: `pip-by-arc-forge/ARCHITECTURE.md` (knowledge graph schema), Anthropic MCP Memory Server

**Status**: 🔮 Future (after tools integration)

---

### ARCH-011: Self-Hosted Web Search Infrastructure
**Severity**: ✅ Resolved | **Created**: 2025-12-06 | **Resolved**: 2025-12-06
**Component**: voice-backend

**Problem**: Brave Search API free tier (2000 req/month) insufficient for heavy use.

**Solution Implemented**: Multi-provider search abstraction with SearXNG support.

**Files Created/Modified**:
- `src/search_providers.py`: Abstract provider interface + Brave + SearXNG implementations
- `src/tools.py`: Refactored to use provider abstraction
- `DEVELOPMENT.md`: Added SearXNG setup documentation

**Provider Priority**:
1. **SearXNG** (if `SEARXNG_URL` set) - unlimited, self-hosted
2. **Brave** (if `BRAVE_API_KEY` set) - 2000/month free tier

**Quick Start (SearXNG)**:
```bash
# Start SearXNG
docker run -d -p 8888:8080 searxng/searxng

# Configure IRIS
echo "SEARXNG_URL=http://localhost:8888" >> ~/.config/iris/secrets.env
```

**Implementation Complete**:
- [x] Research SearXNG Docker deployment
- [x] Abstract web search to support multiple providers
- [x] Add SearXNG as alternative search backend
- [x] Document SearXNG setup in DEVELOPMENT.md

**Future Enhancements** (optional):
- Arc Forge hosted service for casual users
- Bundled SearXNG in .deb package

---

### ARCH-012: First-Run Setup Wizard & Tool Management UI
**Severity**: 🔮 Future | **Created**: 2025-12-06
**Component**: voice-backend (DearPyGui)

**Context**: Users need a friendly way to configure API keys and manage tools. Current approach requires manual file editing.

**Proposed Features**:

1. **First-Run Wizard**
   - Detect missing `~/.config/iris/secrets.env`
   - Modal dialog: "IRIS needs some API keys to unlock full functionality"
   - Step-by-step guide with clickable links to signup pages
   - Secure text input (masked) for API keys
   - "Skip for now" option (graceful degradation)

2. **Settings Panel** (in DearPyGui)
   - API key management (add/update/remove, values masked)
   - Tool enable/disable toggles
   - Tool status indicators (configured, rate limited, error)

3. **Tool Library** (Future)
   - Browse community tools
   - One-click install from curated library
   - Custom tool registration (user-defined JSON schemas + Python)
   - Tool versioning and updates

**Security Considerations**:
- Keys stored in `~/.config/iris/secrets.env` (user-only permissions)
- Never log or display full key values
- Consider OS keyring integration (Secret Service on Linux, Keychain on macOS)

**Implementation Order**:
1. ✅ MVP: Manual config file (`secrets.env`)
2. 🔮 Phase 1: Settings panel with key management
3. 🔮 Phase 2: First-run wizard
4. 🔮 Phase 3: Tool library browser

**Status**: 🔮 Future (after core tool integration complete)

---

## Low Priority / Future (Riff Session 2025-12-05)

### ISSUE-015: Remove Temporary System Prompt Limitations
**Severity**: 🟢 Low | **Created**: 2025-12-05 | **Status**: Blocked (waiting for tools)
**Component**: voice-backend (iris_local.py)

**Context**: The local IRIS client has temporary system prompt restrictions to prevent hallucinations while MCP tools are not integrated.

**Current Limitations** (in `IrisConfig.system_prompt`):
```
- NEVER use placeholder text like [Event Name], [Time], [Location], etc.
- NEVER pretend you can access real-time data, calendars, or external systems
- You DON'T have access to: fleet data, wallet balances, real-time prices, or game APIs
- If asked about these, explain you're in local testing mode without those integrations
```

**When to Remove**: After integrating:
1. MCP tools for fleet status, wallet balance, transaction history
2. CITADEL REST API wrappers for real-time game data
3. Price/market data endpoints

**Action Items**:
- [ ] Track MCP tool integration progress (ARCH-001)
- [ ] Update system prompt when tools are available
- [ ] Test that IRIS correctly uses tools instead of hallucinating
- [ ] Consider keeping some anti-hallucination rules even with tools (for edge cases)

**File Location**: `packages/voice-backend/iris_local.py:109-122`

---

### ISSUE-012: Ambient Audio Cues
**Severity**: 🟢 Low | **Created**: 2025-12-05 | **Status**: Idea
**Component**: web-app, voice

**Idea**: Subtle audio cues (chime, typing sound) as alternative to verbal acknowledgment during cloud model latency gaps.

**Rationale**: Less intrusive than "Got it", still fills cognitive gap.

**Action Items**:
- [ ] Design audio cue library
- [ ] Implement optional cue playback
- [ ] User preference toggle

---

### ISSUE-013: Narrator Model Warm-Up Protocol
**Severity**: 🟢 Low | **Created**: 2025-12-05
**Component**: narrator (Ollama)

**Problem**: First inference on cold model takes 3-14s (model loading). Subsequent calls are fast (130-300ms).

**Benchmark Results** (2025-12-05):
| Model | Cold Start | Warm Latency | Notes |
|-------|------------|--------------|-------|
| qwen2.5:7b | 3.0s | 98-215ms | Best balance |
| qwen2.5:14b | 6.6s | 130-360ms | Good quality |
| qwen2.5:32b | 14.1s | 200-860ms | Highest quality |
| mistral:7b | 3.8s | 131-229ms | No filtering (too talkative) |

**Solution**: Warm-up protocol on service start.

**Action Items**:
- [ ] Add narrator warm-up to startup sequence
- [ ] Send dummy inference on load
- [ ] Log warm-up timing

---

### ISSUE-014: Long Response Chunking for Voice
**Severity**: 🟢 Low | **Created**: 2025-12-05 | **Status**: Idea
**Component**: agent-core

**Problem**: Long responses (80+ seconds of audio) are exhausting to listen to. User can't skim.

**Idea**: Chunk responses with natural breakpoints:
```
IRIS: "Three things about your fleet status." [pause]
IRIS: "First, Alpha's docked at MRZ-1."       [pause]
IRIS: "Second, fuel's critical at 15%."       [pause]
```

User can interrupt after any chunk. Front-load critical info.

**Action Items**:
- [ ] Design response chunking logic
- [ ] Implement pause points in TTS
- [ ] Enable per-chunk interruption

---

## High Complexity Items (needs_decomposition)

These tasks have complexity >3.0 and should be broken down further before implementation.

### task_1_2_3: prepareTransaction tool
**Complexity**: 3.2 | **Epic**: MCP Server

**Issue**: High technical complexity (4.0) and risk (4.0) due to transaction construction and security requirements.

**Why flagged**:
- Creating unsigned Solana transactions requires deep blockchain knowledge
- Security-critical: mistakes could cause fund loss
- Must handle various transaction types (SPL transfers, SAGE operations)

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status |
|---------|-------------|------|------------|--------|
| subtask_1_2_3_1 | **Spike**: Research Solana transaction structure | 0.5d | 1.5 | 🔴 |
| subtask_1_2_3_2 | Implement basic SOL transfer builder | 1d | 2.0 | 🔴 |
| subtask_1_2_3_3 | Add SPL token transfer support | 1d | 2.2 | 🔴 |
| subtask_1_2_3_4 | Add SAGE operation templates | 1d | 2.5 | ⏸️ DEFERRED |
| subtask_1_2_3_5 | Transaction validation & security checks | 0.5d | 2.5 | 🔴 |

**MVP Recommendation**: ⏸️ **DEFER ENTIRE TASK** - Voice assistant MVP doesn't need transaction preparation. Users check balances/status via voice, execute transactions via Star Atlas UI. Revisit post-MVP if user demand exists.

**Status**: ⏸️ Deferred (MVP scope cut)

---

### task_1_3_3: subscribeToFleetUpdates WebSocket
**Complexity**: 3.5 | **Epic**: MCP Server

**Issue**: High technical complexity (4.0), dependencies (4.0), and uncertainty (4.0) due to WebSocket state management and Solana account subscriptions.

**Why flagged**:
- Solana account subscriptions are complex (RPC WebSocket)
- State management across reconnections
- Must handle rate limiting and backpressure

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status |
|---------|-------------|------|------------|--------|
| subtask_1_3_3_1 | Basic Solana WebSocket connection handler | 1d | 2.0 | 🔴 |
| subtask_1_3_3_2 | Account subscription management (subscribe/unsubscribe) | 1d | 2.5 | 🔴 |
| subtask_1_3_3_3 | Reconnection and state recovery | 0.5d | 2.8 | 🔴 |
| subtask_1_3_3_4 | Rate limiting and backpressure handling | 0.5d | 2.3 | 🔴 |
| subtask_1_3_3_5 | Fleet update event transformation (Solana → IRIS format) | 0.5d | 2.0 | 🔴 |

**MVP Recommendation**: ⏸️ **DEFER - Use polling instead.** Implement `getFleetStatus` on 30-60s interval for MVP. Provides "near real-time" with far less complexity. WebSocket subscriptions are a post-MVP optimization when users demand faster updates.

**Status**: ⏸️ Deferred (MVP scope cut - use polling)

---

### task_4_3_3: Latency monitoring and optimization
**Complexity**: 3.5 | **Epic**: Voice Service

**Issue**: High technical complexity (4.0) and uncertainty (4.0) due to real-time performance requirements.

**Why flagged**:
- <500ms round-trip is aggressive target
- Multiple components in chain (WebRTC → Chatterbox → Agent → Chatterbox → WebRTC)
- Optimization requires profiling across distributed system

**Decomposition** (updated 2025-12-02):

| Subtask | Description | Est. | Complexity | Status | MVP? |
|---------|-------------|------|------------|--------|------|
| subtask_4_3_3_1 | Add timing instrumentation to voice pipeline | 0.5d | 2.0 | 🔴 | ✅ Yes |
| subtask_4_3_3_2 | Create latency logging/dashboard | 0.5d | 1.8 | 🔴 | ✅ Yes |
| subtask_4_3_3_3 | Profile and identify bottlenecks | 0.5d | 2.5 | 🔴 | Post-MVP |
| subtask_4_3_3_4 | Implement streaming optimizations (overlap STT/Agent/TTS) | 1d | 3.0 | 🔴 | Post-MVP |
| subtask_4_3_3_5 | Add latency alerts and text-only fallback trigger | 0.5d | 2.2 | 🔴 | ✅ Yes |

**MVP Recommendation**: Implement 4_3_3_1, 4_3_3_2, and 4_3_3_5 only. Get baseline measurements first, then optimize post-MVP. Text-only should be the default fallback if voice latency exceeds threshold.

**Status**: 🟡 Partially in scope (3 of 5 subtasks for MVP)

---

## Needs Spike Investigation

These items have high uncertainty (≥4) and need research before implementation.

### SPIKE: SAGE SDK Fleet Enumeration
**Feature**: task_1_3_1 enhancement (getFleetStatus full implementation)
**Uncertainty**: 4.0

**Current State**:
MVP implementation verifies player profile existence. Full fleet data (ship counts, states, resources) requires proper SAGE SDK integration with Anchor IDL parsing.

**Questions to answer**:
1. How to load and use @staratlas/sage IDL with Anchor?
2. What's the correct account structure for Fleet enumeration?
3. How to filter Fleet accounts by player profile efficiently?
4. What's the data size/RPC cost for fetching all fleet data?

**Suggested spike structure**:
```yaml
BLUEPRINT-spike-sage-sdk-integration-20251203.yaml

deliverables:
  - Research report: SAGE SDK account structures
  - POC: Fetch one fleet's full state
  - Decision: IDL loading strategy
  - Documentation: Fleet data parsing guide

duration: 2-3 days
```

**Status**: 🔍 Needs spike before full implementation

---

### SPIKE: Chatterbox Integration
**Feature**: feature_4_1 (Chatterbox Installation & Configuration)
**Uncertainty**: 4.0

**Questions to answer**:
1. What Docker image/setup works best on DO VPS?
2. What are the RAM/CPU requirements?
3. How to configure STT/TTS endpoints?
4. What models are available and their latency characteristics?
5. How to handle concurrent audio streams?

**Suggested spike structure**:
```yaml
BLUEPRINT-spike-chatterbox-integration-20251202.yaml

deliverables:
  - Research report: Chatterbox deployment options
  - POC: Basic STT/TTS working on VPS
  - Decision: Model selection for latency vs quality
  - Documentation: Setup steps for team

duration: 3-5 days
```

**Status**: 🔍 Needs spike before implementation

---

## Risk Register

### High Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Voice latency >500ms | High | Medium | Early Chatterbox spike + fallback to text-only |
| VPS RAM insufficient | High | Low | Load test early, upgrade path ($24/month for 8GB) |
| Solana RPC rate limiting | High | Medium | Aggressive caching (5-min TTL), paid RPC fallback |

### Medium Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| WebSocket stability on mobile | Medium | Medium | Auto-reconnect, polling fallback |
| SQLite concurrent writes | Medium | Low | WAL mode, connection pool, PostgreSQL migration path |
| Star Atlas API changes | Medium | Low | Version lock SAGE SDK, monitor changelog |

---

## Dependencies

### Blocking Dependencies

| Dependency | Blocks | Notes |
|------------|--------|-------|
| Epic 1 (MCP Server) | Epic 3 (Agent Core) | Agent needs MCP tools |
| Epic 2 (Memory Service) | Epic 3 (Agent Core) | Agent needs conversation context |
| Feature 3.4 (Agent API) | Feature 4.4 (Voice API) | Voice needs agent endpoints |

### External Dependencies

| Service | Criticality | Fallback |
|---------|-------------|----------|
| Solana blockchain | High | Cached data, offline mode |
| Star Atlas SAGE API | High | Cached fleet state |
| CoinGecko API | Medium | Stale prices acceptable |
| Chatterbox | High | Text-only fallback |

---

## Assumptions

1. ✅ Digital Ocean VPS has 640MB+ RAM available (verified 2025-12-01)
2. ⚠️ Chatterbox can run alongside other services (needs spike)
3. ⚠️ Star Atlas SAGE API will remain stable (monitor)
4. ✅ SQLite performance adequate for <500 users
5. ✅ WebRTC supported in target browsers

---

## CITADEL Integration (Epic 8)

### task_8_10_2: E2E tests for voice queries
**Complexity**: 3.0 | **Epic**: CITADEL Integration

**Issue**: High technical complexity (4.0) and dependencies (4.0) - requires both IRIS and CITADEL running.

**Why flagged**:
- Playwright tests need to simulate voice input
- Requires CITADEL API running or mocked
- Complex assertion chain: voice → agent → CITADEL API → response

**Suggested breakdown**:
1. Mock CITADEL API responses
2. Test voice input simulation separately
3. Integration test voice → agent flow
4. Full E2E with mock CITADEL

**Status**: 🔴 Not started

---

### CITADEL ↔ IRIS Coordination Notes

**Integration Contract** (defined in blueprint):
```
CITADEL Provides:
├── GET /api/dashboard/prices (30s cache)
├── GET /api/dashboard/fleets/:fleetId (60s cache)
├── GET /api/recommendations/mining (5min cache)
├── GET /api/recommendations/transport/:from/:to (5min cache)
├── WebSocket ws://citadel/ws/prices
└── MCP Tools: citadel_calculate_*, citadel_get_*

IRIS Provides:
├── Voice interface
├── User preferences from knowledge graph
└── Session context
```

**Parallel Development Strategy**:
- IRIS can start immediately with mock APIs (task_8_1_3)
- CITADEL Decision API priority: /api/dashboard/prices first
- Integration testing blocked until both systems have staging

**Risks**:
1. **CITADEL APIs not ready** → Mitigation: Mock responses unblock IRIS
2. **MCP incompatibility** → Mitigation: HTTP API fallback
3. **Voice latency budget** → Mitigation: Aggressive caching (30s-5min TTLs)

---

## Aspirational Features (Distribution & Packaging)

### ASP-004: Linux Distribution via Self-Hosted APT Repository
**Type**: Packaging | **Priority**: Future
**Origin**: Riff session 2025-12-05

**Vision**: Enable `apt install iris-local` for Ubuntu users via self-hosted repository.

**Why APT (not Snap)**:
- No sandbox restrictions (Snap blocks some audio/hardware access)
- Standard Ubuntu UX (`apt install/remove/upgrade`)
- Auto-updates via normal apt mechanisms
- Full system access for GPU, audio devices

**Implementation (Brave browser pattern)**:
```bash
# One-time setup (user runs once)
curl -fsSL https://iris.arcforge.dev/setup-repo.sh | sudo bash

# Then forever after:
sudo apt install iris-local    # Install
sudo apt upgrade iris-local    # Update
sudo apt remove iris-local     # Uninstall
```

**Components Needed**:
1. `.deb` package structure
2. GPG signing key for package authenticity
3. Package hosting (GitHub Releases or S3)
4. Setup script that adds repo + key
5. GitHub Action to auto-build .deb on release

**Package Contents (~2-3GB fully bundled)**:
- Python + all pip dependencies
- Whisper STT model (~150MB)
- Kokoro TTS model (~350MB)
- Silero VAD model (~10MB)
- ffmpeg, PortAudio dependencies
- Desktop launcher + icon

**User Still Needs (external)**:
- Ollama + LLM model (~4GB for qwen2.5:7b)
- NVIDIA drivers (system-specific)

**Alternative: Install Script**:
Simpler approach for initial distribution:
```bash
curl -fsSL https://iris.arcforge.dev/install.sh | bash
```
Downloads ~3GB, installs everything, creates desktop entry.

**Trade-offs**:

| Approach | Pros | Cons |
|----------|------|------|
| **APT repo** | Standard UX, auto-updates | Complex setup, hosting costs |
| **Install script** | Simple, quick to implement | No auto-update, less "official" |
| **Snap** | Bundles everything | Sandbox issues, large size |
| **AppImage** | Single portable file | No auto-update, large |

**Recommendation**: Start with install script for early users, graduate to APT repo when user base grows.

**Status**: 🔮 Aspirational (post-MVP, post initial user validation)

---

### ASP-005: Product Flavors (Star Atlas vs Generic Assistant)
**Type**: Product | **Priority**: Future
**Origin**: Riff session 2025-12-05

**Vision**: Offer IRIS as both a Star Atlas-specific assistant AND a generic voice assistant with tools.

**Rationale**:
- Current implementation is tightly coupled to Star Atlas persona/tools
- Many users might want the voice + tools architecture without game specifics
- Broader market = more users = more feedback

**Proposed Flavors**:

| Flavor | Persona | Tools | Target User |
|--------|---------|-------|-------------|
| **IRIS (Star Atlas)** | "Guy in the chair" | Fleet, wallet, SAGE tools | Star Atlas players |
| **IRIS (Generic)** | Helpful assistant | File, web, shell, calendar | Developers, power users |
| **IRIS (Custom)** | User-defined | Plugin architecture | Builders |

**Implementation Approach**:
```
iris-core/           # Shared: audio, VAD, STT, TTS, LLM integration
iris-staratlas/      # Star Atlas persona + tools
iris-assistant/      # Generic assistant persona + tools
iris-plugins/        # Plugin architecture for custom tools
```

**Configuration**:
```yaml
# ~/.config/iris/config.yaml
flavor: staratlas  # or: generic, custom
persona:
  name: "IRIS"
  style: "guy_in_chair"  # or: professional, casual, custom
tools:
  enabled:
    - fleet_status
    - wallet_balance
  disabled:
    - file_operations
```

**Key Decisions Needed**:
1. How much Star Atlas code is entangled with core?
2. Plugin architecture for tools (MCP-style?)
3. Persona customization depth (just name? or full system prompt?)
4. Packaging: one binary with flags, or separate packages?

**Prerequisites**:
- Stable core architecture (current Python GUI)
- Clear separation of concerns in codebase
- User feedback on desired generic tools

**Status**: 🔮 Aspirational (post-MVP, requires architecture refactor)

---

## Aspirational Features (Native Client)

### ASP-003: Native Compiled Client (Rust/C++)
**Type**: Architecture | **Priority**: Future
**Origin**: Riff session 2025-12-05

**Vision**: Single compiled binary for maximum performance and game engine integration.

**Why Compiled Native**:
- **Unreal Engine integration**: Star Atlas uses Unreal (C++), native client could be an in-game overlay
- **Minimal latency**: No Python interpreter, no web stack overhead
- **Single binary distribution**: Easy install for users with compatible hardware
- **Game modding**: Plugin architecture for various games

**Target Architecture**:
```
Single Rust/C++ Binary:
├── Audio I/O (cpal/portaudio)
├── VAD (Silero ONNX or custom)
├── STT (whisper.cpp)
├── LLM (llama.cpp or Ollama client)
├── TTS (??? - need Rust TTS solution)
└── GUI (egui/imgui)
```

**Key Challenges**:
1. **TTS**: Kokoro is Python-only. Options:
   - whisper.cpp style port of Kokoro
   - Piper TTS (C++ native, ONNX models)
   - espeak-ng (lower quality but native)
   - Keep TTS as separate Python service (hybrid)

2. **Model Loading**: GPU memory management for multiple models

3. **Build Complexity**: CUDA/ROCm support across platforms

**Phased Approach**:
```
Phase 1 (Current): Python native GUI - validate architecture
Phase 2: Rust audio + VAD wrapper around Python backend
Phase 3: Replace STT with whisper.cpp
Phase 4: Replace LLM with llama.cpp (or keep Ollama)
Phase 5: Replace TTS (biggest unknown)
Phase 6: Full native binary
```

**Unreal Engine Integration Path**:
- Phase 1-2: External process, IPC via localhost socket
- Phase 3+: Could become Unreal plugin (C++ compatible)
- Audio routing: Capture game audio context, output to game audio system

**Alternative: Hybrid Architecture**:
```
Rust Frontend (audio + GUI):
├── Audio capture/playback (native)
├── VAD (native ONNX)
├── GUI (egui)
└── IPC to Python backend

Python Backend (unchanged):
├── STT (faster-whisper)
├── LLM (Ollama)
└── TTS (Kokoro)
```

This hybrid gets 80% of the benefit with 20% of the effort.

**Prerequisites**:
- Python native GUI working and validated
- Performance benchmarks establishing baseline
- TTS solution research spike

**Status**: 🔮 Aspirational (post Python GUI validation)

---

## Aspirational Features (from CITADEL)

> **Note**: These ML/RL features were originally scoped for CITADEL but moved to IRIS since IRIS is the "intelligent assistant" layer. CITADEL provides reliable data; IRIS provides intelligence.

### ASP-001: Price Prediction Model
**Type**: Machine Learning | **Priority**: Future
**Origin**: CITADEL Epic 6 (removed from scope)

**Concept**: Time-series forecasting (ARIMA, LSTM, Prophet) for Star Atlas resource prices.

**Why IRIS (not CITADEL)**:
- Predictions are recommendations, not raw data
- IRIS provides intelligent insights; CITADEL provides facts
- Can leverage CITADEL's historical data API

**Prerequisites**:
- CITADEL Milestone 2 (TimescaleDB historical data)
- Sufficient price history (~90 days minimum)
- Spike to assess if market has predictable patterns

**Rough scope**:
1. Feature engineering from CITADEL historical API
2. Model training pipeline (Python/scikit-learn)
3. Prediction endpoint for IRIS agent to consume
4. Confidence scoring and fallback to heuristics

**Status**: 🔮 Aspirational (post-MVP)

---

### ASP-002: Automated Strategy Optimizer (RL Agent)
**Type**: Reinforcement Learning | **Priority**: Future
**Origin**: CITADEL Epic 6 (removed from scope)

**Concept**: RL agent that learns optimal fleet allocation and operation strategies.

**Why IRIS (not CITADEL)**:
- Strategy is intelligence, not automation
- IRIS is the "brain"; CITADEL is the "hands"
- Agent can suggest to user; user decides to execute

**Prerequisites**:
- ASP-001 working (price predictions inform rewards)
- CITADEL profitability calculators stable
- Environment simulator for safe training (no real fleets)

**Rough scope**:
1. Design state/action/reward spaces
2. Build simulator using CITADEL APIs
3. Train with Stable-Baselines3 (DQN or PPO)
4. Shadow mode: suggest but don't execute
5. User approval gate before any real actions

**Status**: 🔮 Aspirational (post-MVP, post ASP-001)

---

## Architectural Issues

### ARCH-003: Voice Pipeline Architecture Overhead (12 Network Hops)
**Severity**: ✅ Resolved | **Created**: 2025-12-03 | **Resolved**: 2025-12-03

**Issue**: The voice pipeline had excessive architecture overhead - 12 network crossings, 11 serialization boundaries, 4 language boundaries, and ~76% encoding overhead from base64.

**Previous Architecture (problematic)**:
```
Browser → WS → Node.js(voice-service) → HTTP → Python(STT) → HTTP →
Node.js → WS → Browser → HTTP → Node.js(agent) → HTTP/2 → Claude →
SSE → Node.js → SSE → Browser → WS → Node.js → HTTP → Python(TTS) →
HTTP → Node.js → WS(base64) → Browser
```

**New Architecture (implemented)**:
```
Browser ←WebSocket(binary)→ Python voice-backend ←HTTP/2→ Claude API
```
- **3 network hops** (vs 12)
- **Binary WebSocket** (2-byte header + raw PCM)
- **Node.js voice-service deprecated**

**Implementation Complete**:

| Phase | Description | Savings | Status |
|-------|-------------|---------|--------|
| **Phase 1**: Kill Node.js voice-service | Direct Browser → Python WebSocket | ~40-80ms | ✅ |
| **Phase 2**: Binary WebSocket frames | Raw PCM instead of base64 | ~30-50ms | ✅ |
| **Phase 3**: Streaming STT | Process during recording | ~50-100ms | ✅ |
| **Phase 4**: GPU STT | faster-whisper on CUDA | ~100-200ms | ✅ |
| **Phase 5**: Plan Rust gateway | Future optimization | TBD | 📝 Documented |

**Results**:
- STT: 181ms (GPU CUDA)
- TTS: 520ms (GPU CUDA)
- Fast-layer acknowledgments: 3-12ms (pattern-based)
- Total time to first audio: ~700ms

**Status**: ✅ Complete - all phases implemented

---

### ARCH-002: Voice Latency Exceeds Natural Conversation Threshold
**Severity**: ✅ Resolved | **Created**: 2025-12-02 | **Resolved**: 2025-12-03

**Issue**: End-to-end voice latency was ~6.2 seconds, far exceeding the <500ms target for natural conversation.

**Empirical Measurements** (2025-12-02, hybrid STT=CPU/TTS=CUDA):
```
Stage                           Mean        Min        Max        Std
-----------------------------------------------------------------
STT (faster-whisper CPU)      266.4ms     258.1ms     270.6ms       5.9ms
Claude API (first token)     1975.2ms    1697.1ms    2450.1ms     337.4ms
Claude API (total)           5030.5ms    4163.6ms    6589.4ms    1104.6ms
TTS (Chatterbox GPU)          896.3ms     888.3ms     905.2ms       6.9ms
-----------------------------------------------------------------
TOTAL E2E                    6193.2ms    5329.3ms    7748.4ms    1101.9ms
```

**Latency Breakdown**:
```
  User stops speaking
       ↓
  STT Processing:      266.4ms (  4.3%)
       ↓
  Claude API:         5030.5ms ( 81.2%)  ← BOTTLENECK
       ↓
  TTS Synthesis:       896.3ms ( 14.5%)
       ↓
  First audio plays

  TOTAL:              6193.2ms
```

**Root Cause Analysis**:
1. **Claude API is the bottleneck** (81.2% of total latency)
2. **Current architecture waits for full response** before starting TTS
   - Location: `packages/web-app/src/components/Chat.tsx:118-125`
   - TTS triggers on `type: "done"` event (full completion)
   - Streaming tokens arrive but aren't used until stream ends

**Optimization Options** (prioritized by impact):

| Option | Effort | Impact | Description |
|--------|--------|--------|-------------|
| **1. Sentence-level TTS streaming** | High | ~50% reduction | Start TTS on first sentence, don't wait for full response |
| **2. Use Claude Haiku for voice** | Low | ~40% reduction | Faster model for voice queries (Sonnet for complex tasks) |
| **3. Speculative first response** | Medium | ~30% reduction | Pre-generate greeting while processing |
| **4. Parallel STT during recording** | Low | ~5% reduction | Start transcription during silence gaps |

**Implementation Plan**:
```
Phase 1 (Quick wins):
- [ ] Switch to Claude Haiku for voice interactions
- [ ] Measure new latency with benchmark

Phase 2 (Streaming optimization):
- [x] Implemented fast-layer acknowledgments (pattern-based, 3-12ms)
- [x] Direct Anthropic SDK for Haiku (bypasses Agent SDK overhead)
- [ ] Sentence boundary TTS (deferred - current latency acceptable)
```

**Benchmark Scripts**:
- `packages/voice-backend/test_e2e_latency.py` (original)
- `packages/voice-backend/test_e2e_latency_v2.py` (with styles)
- `packages/voice-backend/test_e2e_latency_v3.py` (pattern vs Haiku validation)

**Resolution** (2025-12-03):
- Fast-layer pattern matching: 3-12ms acknowledgments
- GPU acceleration: STT 181ms, TTS 520ms
- Total time to first audio: ~700ms (vs 6.2s before)
- Remaining gap to 500ms target is acceptable for MVP

**Status**: ✅ Resolved - latency reduced from 6.2s to ~700ms

---

### ARCH-001: IRIS/CITADEL Separation of Concerns
**Severity**: 🔴 Critical | **Created**: 2025-12-02 | **Updated**: 2025-12-02

**Issue**: IRIS MCP server currently contains blockchain/game data tools that belong in CITADEL.

**Current State**:
The `mcp-staratlas-server` package contains tools that should be CITADEL's responsibility:
- `getWalletBalance` - Solana RPC query
- `getTransactionHistory` - Solana RPC query
- `getFleetStatus` - SAGE SDK integration
- `predictFuelDepletion` - Game calculation with on-chain formulas

**Architecture Decision (2025-12-02)**:

| Layer | CITADEL | IRIS |
|-------|---------|------|
| **REST API** | ✅ Provides | Consumes |
| **WebSocket** | ✅ Provides | Consumes |
| **MCP Tools** | ❌ None | ✅ Wraps REST |
| **Blockchain data** | ✅ | ❌ |
| **Game calculations** | ✅ | ❌ |
| **Voice interface** | ❌ | ✅ |
| **User memory** | ❌ | ✅ |

**Key Decision: MCP tools live in IRIS, not CITADEL**

Rationale:
- Separation of concerns: Citadel = data/execution, IRIS = intelligence
- Tool descriptions should be tailored to IRIS's persona
- IRIS can compose Citadel data with other sources (user memory, etc.)
- REST is the universal contract; MCP is Claude-specific
- Keeps Citadel simpler

**Implementation Pattern**:
```
IRIS MCP Tool → wraps → CITADEL REST API → queries → Solana/SAGE
```

**Example**:
```typescript
// IRIS MCP tool (in iris/packages/mcp-staratlas-server)
const iris_get_fleet_status = async (fleetId: string) => {
  const response = await fetch(`${CITADEL_API}/api/dashboard/fleets/${fleetId}`);
  return response.json();
};
```

**Detailed Design**: See `citadel/docs/IRIS-INTEGRATION.md`

**Action Items**:
1. [x] ~~Create CITADEL repository with MCP server~~ → MCP stays in IRIS
2. [ ] CITADEL: Implement REST API endpoints for blockchain/game data (Epic 2-3)
3. [ ] CITADEL: Implement "Galactic Data Service" pattern for cached game data
4. [ ] IRIS: Update MCP tools to wrap CITADEL REST API (Epic 8) - **BLOCKED on Citadel API**
5. [ ] IRIS: Remove direct Solana RPC calls from MCP tools

**Dependency Chain**:
```
Citadel REST API (Epic 2-3) → IRIS MCP wrappers (Epic 8) → Voice agent queries
```

**Why This Matters**:
- Game formulas are on-chain (SAGE program) - hardcoding them in IRIS will break when Star Atlas updates
- CITADEL should own the "source of truth" for all blockchain/game data
- IRIS should be a thin voice layer + user context, not a data service
- Prevents duplicate RPC costs and inconsistent caching strategies

**Status**: 🟡 In Progress - Citadel REST API under development, IRIS MCP blocked until complete

---

## Action Items

1. [x] **ARCH-001**: Architecture decision made - MCP tools stay in IRIS, wrap Citadel REST (2025-12-02)
2. [ ] **ARCH-001**: Wait for Citadel REST API (Epic 2-3) before updating IRIS MCP tools (BLOCKED)
3. [ ] **Create spike blueprint** for Chatterbox integration
4. [x] **Decompose task_1_2_3** (prepareTransaction) - DONE, DEFERRED from MVP (2025-12-02)
5. [x] **Decompose task_1_3_3** (subscribeToFleetUpdates) - DONE, DEFERRED from MVP (2025-12-02)
6. [x] **Decompose task_4_3_3** (latency monitoring) - DONE, partial MVP scope (2025-12-02)
7. [ ] **Set up monitoring** for external API availability
8. [ ] **Coordinate with CITADEL** on API timeline and contract validation
9. [ ] **Create mock API** responses for CITADEL endpoints (task_8_1_3)
10. [ ] **Spike ASP-001** after CITADEL historical data available (assess prediction feasibility)

## MVP Scope Decisions (2025-12-02)

| Decision | Rationale |
|----------|-----------|
| **DEFER prepareTransaction** | Voice assistant checks status; users execute via Star Atlas UI |
| **DEFER WebSocket subscriptions** | Use polling (30-60s) for MVP; near real-time is sufficient |
| **SKIP traditional CI/CD** | Main-only workflow; deploy via `docker-compose` on VPS |
| **Text-only fallback default** | Voice is aspirational for MVP; must work without it |
| **MCP tools stay in IRIS** | IRIS wraps Citadel REST API; keeps separation clean (ARCH-001) |
| **BLOCKED: MCP wrapper updates** | Wait for Citadel REST API (Epic 2-3) before refactoring MCP tools |

---

**Note**: Update this file as issues are resolved or new ones discovered.
