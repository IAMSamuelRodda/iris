# Planning Session: Star Atlas Agent
**Date**: 2025-11-12
**Status**: Vision Alignment Complete → Ready for Blueprint

---

## Vision Statement

**Multi-user SaaS voice-first AI agent** for Star Atlas players focused on:
1. **Fleet monitoring & alerts** (HIGH) - Fuel, repairs, resource tracking
2. **Economic optimization** (HIGH) - Crafting profitability, resource allocation
3. **Voice assistant interface** (HIGH) - Cortana-like conversational experience
4. **Automated trading** (LOW) - Future consideration post-MVP

**Differentiation from EvEye**:
- Voice-first interface (EvEye is GUI/map only)
- AI-driven insights ("your fleet needs fuel in 2h") vs data visualization
- Economic decision support (crafting ROI, resource optimization)
- Price monitoring as context, not primary feature

---

## Timeline & Approach

- **MVP first**: Build minimal viable product with AWS Free Tier
- **AI-assisted development**: Assume 20x speedup vs human estimates
- **Sporadic work pattern**: Plan for interrupted work, clear documentation critical
- **Cost ceiling**: <$10/month until paying users validate product

---

## Archive Mining Results

### galactic-data (Legacy System)

**Core functionality**:
- Fetched CoinGecko token prices (ATLAS, POLIS)
- Fetched Star Atlas Galactic Marketplace order data via Solana blockchain
- Stored in Firestore, exposed via Express API
- Google Sheets integration via Apps Script

**Key patterns to preserve**:
1. **Dual data sources**: CoinGecko API + Solana on-chain data (`@staratlas/galactic-marketplace`)
2. **Anchor Program integration**: Fetch all order accounts from program
3. **Upsert pattern**: Check existence → set or update in Firestore
4. **Scheduled updates**: Time-based refresh checks

**Technologies**:
- `@solana/web3.js` v1.88.0
- `@staratlas/galactic-marketplace` v0.9.7
- Firebase/Firestore
- Docker + Google Cloud Run

**Why we're replacing**:
- Firebase → AWS (per requirements)
- Polling → WebSocket subscriptions for real-time blockchain data
- API-only → Voice-first interface
- Price-focused → Fleet management + economic optimization focused

### EvEye Competitive Analysis

**EvEye strengths** (what they do well):
- Real-time fleet tracking (5-min idle heatmaps)
- Market data (5-10min delayed, 90-365 day charts)
- Custom fleet builder (drag-and-drop)
- Comprehensive inventory tracking (raw materials, consumables)

**Our strategic differentiation**:
- ✅ Voice interface (hands-free, mobile-friendly)
- ✅ AI insights ("fuel alert in 2h" vs manual monitoring)
- ✅ Economic optimization (crafting ROI, not just prices)
- ⚠️ Price monitoring secondary (context for decisions, not charting)

**Decision**: Don't compete on data visualization. Focus on **actionable AI-driven recommendations**.

---

## Architecture Constraints

### AWS Free Tier (MVP Budget: <$10/month)

**Recommended pattern**: Serverless + DynamoDB

```
Components:
├─ Frontend: CloudFront + S3 ($0 Free Tier)
├─ API: API Gateway + Lambda ($0 for 1M req/month)
├─ Database: DynamoDB ($0 for 25GB + 25 WCU/RCU)
├─ Auth: Cognito ($0 for <50k MAUs)
├─ Voice Service: ECS Fargate (1 task) ($3-5/month)*
└─ Monitoring: CloudWatch ($0 Free Tier basics)

Estimated Cost: $3-7/month
Traffic Capacity: 5k requests/day
```

**Why serverless**:
- Event-driven architecture fits Star Atlas blockchain events
- Variable traffic (sporadic fleet checks)
- NoSQL sufficient for fleet/player state
- Lambda cold starts acceptable for non-voice queries

**Voice service exception**:
- WebRTC + STT/TTS requires low latency (<500ms)
- Dedicated ECS Fargate task for persistent WebSocket connections
- Estimate: 1x db.t3.micro equivalent = $3-5/month

### Critical Technical Constraints

1. **Voice latency**: <500ms round-trip (use streaming STT/TTS)
2. **Wallet security**: NEVER auto-sign transactions (explicit user approval)
3. **Real-time data**: WebSocket subscriptions to Solana accounts (not polling)
4. **Offline fallback**: MCP tools MUST handle RPC failures gracefully
5. **Multi-user**: Auth, per-user fleet tracking, subscription tiers
6. **pnpm only**: Package management consistency

---

## Key Architectural Decisions

### Data Sources

**Primary**:
1. **Solana blockchain**: Fleet state, transaction history (WebSocket subscriptions)
2. **Star Atlas SAGE API**: Game state, crafting recipes, resource data
3. **CoinGecko API**: Token prices (ATLAS, POLIS) - secondary context

**Pattern**: Subscribe to Solana account changes via WebSocket, cache in DynamoDB, expose via MCP tools + voice

### Storage Strategy

**DynamoDB tables** (NoSQL, Free Tier 25GB):
- `users`: Auth, preferences, subscription tier
- `fleets`: User fleet configurations, last known state
- `alerts`: Active alerts (fuel low, repairs needed)
- `market-cache`: Recent price data (CoinGecko + marketplace orders)

**S3 buckets** (static assets):
- `frontend`: React app build artifacts
- `voice-recordings`: User voice clips (if needed for debugging)

### Real-Time Architecture

**Blockchain monitoring**:
```
Solana WebSocket → Lambda (event processor) → DynamoDB (state update) → EventBridge → Notification Lambda
                                                                        ↓
                                                                   User alert (voice/web)
```

**Voice flow**:
```
User → WebRTC (browser) → ECS (voice service) → Whisper (STT) → Claude Agent SDK → MCP tools → DynamoDB/Solana
                                                                                               ↓
                                                                        ElevenLabs (TTS) ← Response
```

### MCP Tools Design

**Package**: `mcp-staratlas-server`

**Tool categories**:
1. **Fleet tools**: `get_fleet_status`, `get_fuel_remaining`, `get_repair_status`
2. **Market tools**: `get_token_price`, `get_marketplace_orders`, `calculate_crafting_roi`
3. **Transaction tools**: `prepare_transaction`, `get_wallet_balance`
4. **Game data tools**: `get_crafting_recipes`, `get_resource_info`

**Offline handling**: All tools have fallback modes (cached data, error messages, degraded functionality)

---

## Technology Stack

### Frontend
- **Framework**: React + TypeScript
- **Build**: Vite
- **UI**: TBD (shadcn/ui vs custom)
- **Voice**: WebRTC for browser-based push-to-talk
- **Hosting**: S3 + CloudFront

### Backend Services

**Voice Service** (ECS Fargate):
- Runtime: Node.js 20
- STT: OpenAI Whisper API
- TTS: ElevenLabs API
- WebSocket: ws library for persistent connections

**Agent Core** (Lambda):
- Runtime: Node.js 20
- Framework: Claude Agent SDK
- MCP Server: `mcp-staratlas-server` package
- Orchestration: EventBridge for event routing

**MCP Server** (Lambda):
- Runtime: Node.js 20
- Solana: `@solana/web3.js` v1.88+
- Star Atlas: `@staratlas/sage` (latest)
- Market: `@staratlas/galactic-marketplace` v0.9.7+

### Infrastructure
- **IaC**: Terraform (preferred for AWS)
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch (Free Tier)
- **Secrets**: AWS Secrets Manager (Free Tier 30 days, then $0.40/secret/month)

### Database
- **Primary**: DynamoDB (NoSQL, Free Tier 25GB)
- **Caching**: Lambda-local caching (no ElastiCache to save cost)

---

## Next Steps

1. ✅ Vision alignment complete
2. ⏭️ Initialize base documentation structure (`project-documentation-template` skill)
3. ⏭️ Generate BLUEPRINT.yaml (`blueprint-planner` subagent)
4. ⏭️ Validate complexity (`improving-plans` skill)
5. ⏭️ Create GitHub issues (`github-project-infrastructure` skill)
6. ⏭️ Begin implementation

---

## Critical New Requirements (Added 2025-11-12)

### Persistent Memory & Personalization

**Vision**: Agent as colleague → partner → friend (relationship progression)

**Requirements**:
1. **Conversation Memory**: Remember past interactions, user preferences, play style
2. **Learning System**: Adapt to user's decision-making patterns over time
3. **Trust Building**: Show reasoning via data visualizations (not primary feature)
4. **Personalized Experience**: Tailor recommendations based on user history

**Implementation Strategy**:
- **DynamoDB as Vector Store**: AWS guidance project for low-cost RAG (<50K embeddings)
- **Cost**: ~$29/month for 200 documents + 6 queries/hour (under budget with optimization)
- **Performance**: 25K-30K embeddings = 100-200ms query latency (acceptable)
- **Fallback**: Upgrade to OpenSearch Serverless if >50K embeddings needed

**Data Visualization for Trust**:
- "Why I'm recommending this": Show agent's logic visually
- EvEye-level data detail available, but presented as reasoning transparency
- NOT primary UI (voice is primary), but available when user asks "why?"

**Architecture Addition**:
```
User Voice/Text → Agent Core → Vector Search (DynamoDB) → Personalized Context
                      ↓                                              ↓
                  Claude Agent SDK ← Memory-augmented prompts ← User history embeddings
```

**Memory Types**:
1. **Session memory**: Current conversation (in-memory)
2. **Short-term memory**: Recent interactions (DynamoDB, 7-day TTL)
3. **Long-term memory**: User preferences, patterns (DynamoDB + vector embeddings)
4. **Semantic memory**: Game knowledge, strategies (pre-loaded embeddings)

---

## Open Questions

1. **Voice UX**: Push-to-talk vs always-listening? (Recommend PTT for MVP - simpler, lower cost)
2. **Authentication**: Wallet-based (Solana) vs traditional (email)? (Recommend both - wallet for on-chain, email for notifications)
3. **Subscription tiers**: Free tier limits? (Recommend: Free = 5 fleets, Pro = unlimited)
4. **Market data frequency**: How often refresh prices? (Recommend: 5-min like EvEye for MVP)
5. **Alert delivery**: Voice-only vs also push notifications/email? (Recommend: Multi-channel for MVP)
6. **Memory retention**: How long to keep conversation history? (Recommend: 7 days short-term, indefinite long-term preferences)
7. **Visualization depth**: What level of EvEye data detail to show? (Recommend: Start with fleet status, expand based on user feedback)

**Decision needed**: Should we resolve these now or during blueprint creation?

---

**Status**: Ready for base documentation initialization and blueprint planning (with memory architecture addition).
