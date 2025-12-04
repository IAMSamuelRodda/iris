# IRIS - Vision Document

> **Purpose**: Strategic vision and long-term direction
> **Lifecycle**: Living (update as vision evolves)

**Last Updated**: 2025-12-04

---

## Core Vision

**IRIS is a voice-first agentic layer** - a reusable module designed to provide natural voice interaction for any agentic system. While Star Atlas integration (via Citadel) is the first implementation, IRIS is architected to plug into multiple domains and applications.

### What IRIS Is

- **A voice-first interface layer** - optimized for <500ms round-trip voice interactions
- **A reusable module** - plugs into any agentic system via MCP tools and REST APIs
- **Domain-agnostic core** - voice processing, memory, and agent orchestration are universal
- **Integration-specific adapters** - Star Atlas/Citadel is one of many possible integrations

### What IRIS Is Not

- Not a Star Atlas-only product (though that's the first integration)
- Not a monolithic application (modular by design)
- Not a simple chat wrapper (full agentic capabilities via Claude Agent SDK)

---

## Strategic Positioning

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Arc Forge Ecosystem                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │                    IRIS (Voice Layer)                     │    │
│    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │    │
│    │  │ Voice Core  │  │   Memory    │  │ Agent Core  │       │    │
│    │  │ (STT/TTS)   │  │ (Knowledge) │  │ (Claude SDK)│       │    │
│    │  └─────────────┘  └─────────────┘  └─────────────┘       │    │
│    │                        ▼                                  │    │
│    │              ┌─────────────────┐                          │    │
│    │              │   MCP Adapters  │                          │    │
│    │              └─────────────────┘                          │    │
│    └───────────────────────┬──────────────────────────────────┘    │
│                            │                                        │
│    ┌───────────────────────┼──────────────────────────────────┐    │
│    │              Integration Points                           │    │
│    │                       │                                   │    │
│    │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │    │
│    │  │  Citadel   │  │  Future    │  │  Future    │          │    │
│    │  │(Star Atlas)│  │ Domain B   │  │ Domain C   │          │    │
│    │  └────────────┘  └────────────┘  └────────────┘          │    │
│    └──────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Principles

### 1. Voice-First Optimization
- Sub-500ms latency is non-negotiable
- Streaming STT/TTS (faster-whisper + Kokoro)
- Fast-layer acknowledgments (pattern matching + Haiku)
- Binary WebSocket protocol for minimal overhead

### 2. Modular Integration
- Core services are domain-agnostic (voice, memory, agent)
- Domain-specific tools via MCP adapters
- Each integration is a separate adapter, not core modification

### 3. Multi-System Reuse
- IRIS core can plug into:
  - Star Atlas (via Citadel) - current
  - Other blockchain games
  - Personal productivity systems
  - Smart home automation
  - Any system with an API

---

## Current Integration: Star Atlas via Citadel

The first implementation connects IRIS to Star Atlas through the Citadel app:

- **Citadel** provides REST API for blockchain/game data
- **IRIS** wraps Citadel API with MCP tools
- **Users** interact via voice to manage fleets, check markets, get recommendations

See `ARCHITECTURE.md` → ARCH-001 for the IRIS/Citadel separation decision.

---

## Future Integrations (Conceptual)

These represent the extensibility of the IRIS architecture, not committed roadmap:

| Domain | Integration Point | Use Case |
|--------|-------------------|----------|
| Productivity | Todoist, Calendar APIs | Voice task management |
| Smart Home | Home Assistant | Voice automation control |
| Development | Claude Code, GitHub | Voice-assisted coding |
| Knowledge | Joplin, Obsidian | Voice note management |

---

## Success Metrics

### Voice Performance
- Time to first audio: <500ms
- STT latency: <200ms
- TTS synthesis: <100ms
- Pattern acknowledgments: <20ms

### Reusability
- Core components work without Star Atlas
- New integrations require only MCP adapter
- No domain-specific code in voice/memory/agent core

---

## Relationship to Arc Forge

IRIS is part of the broader Arc Forge ecosystem:

- **Arc Forge**: Parent organization/brand
- **IRIS**: Voice-first agentic layer (this repo)
- **Citadel**: Star Atlas integration app (separate repo)
- **Other projects**: Future agentic systems

---

**See Also**:
- `ARCHITECTURE.md` - Technical implementation
- `STATUS.md` - Current development state
- `docs/planning-session-2025-11-12.md` - Original vision alignment
