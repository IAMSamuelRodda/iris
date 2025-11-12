# Memory Architecture Spike - Star Atlas Agent

**Date**: 2025-11-12
**Status**: Research Complete → Ready for Implementation Planning
**Cost Impact**: +$20-25/month to base architecture (still under $50/month total)

---

## Executive Summary

**Vision**: Build a personalized AI agent that evolves from colleague → partner → friend through persistent memory and contextual learning.

**Solution**: DynamoDB-based vector store for RAG (Retrieval-Augmented Generation) with four-tier memory architecture.

**Cost**: ~$29/month for 200 documents + 6 queries/hour (AWS guidance baseline), optimizable to ~$20-25/month for our use case.

---

## Research Findings

### AWS Vector Database Options Evaluated

| Solution | Cost (Est.) | Free Tier | Serverless | Recommendation |
|----------|-------------|-----------|------------|----------------|
| **DynamoDB + pgvector** | $20-30/mo | Partial (DynamoDB 25GB free) | ✅ Yes | ✅ **RECOMMENDED** |
| Amazon Bedrock KB + OpenSearch | $50-100/mo | ❌ No | ✅ Yes | ❌ Too expensive |
| RDS PostgreSQL + pgvector | $25-40/mo | Partial (12mo RDS free) | ❌ No | ⚠️ Not serverless |
| OpenSearch Serverless | $60+/mo | ❌ No | ✅ Yes | ❌ Too expensive |

### DynamoDB Vector Store Performance

**AWS Guidance Project**: [guidance-for-low-cost-semantic-search-on-aws](https://github.com/aws-solutions-library-samples/guidance-for-low-cost-semantic-search-on-aws)

**Benchmarks**:
- 25K-30K embeddings: 100-200ms query latency ✅
- 50K-100K embeddings: 500-800ms query latency ⚠️
- >100K embeddings: Consider migration to OpenSearch Serverless

**Cost Baseline** (AWS guidance, 200 PDFs + 6 queries/hour):
- Total: $29.16/month
- Breakdown:
  - Lambda invocations: ~$5/month
  - DynamoDB storage + queries: ~$15/month
  - Bedrock embedding model (Titan v2): ~$8/month
  - S3 document storage: ~$1/month

**Our Optimization** (Star Atlas use case):
- Fewer documents (user conversations + preferences, not 200 PDFs)
- More frequent queries (voice interactions)
- Estimated: $20-25/month

---

## Four-Tier Memory Architecture

### 1. Session Memory (In-Memory)
**Purpose**: Current conversation context
**Storage**: Lambda execution environment (ephemeral)
**Lifetime**: Duration of voice/chat session
**Size**: Last 10-20 messages (~5-10KB)
**Cost**: $0 (included in Lambda execution)

**Example**:
```
User: "Check my fleet status"
Agent: "You have 3 fleets..."
User: "Focus on Fleet Alpha"  ← Agent remembers "Fleet Alpha" from context
```

### 2. Short-Term Memory (Hot Cache)
**Purpose**: Recent interactions for context continuity
**Storage**: DynamoDB with 7-day TTL
**Lifetime**: 7 days
**Size**: ~100 recent conversations per user (~50KB per user)
**Cost**: ~$0.50/month per 100 active users

**Example**:
```
Monday: "I'm low on fuel at Starbase X"
Tuesday: Agent proactively: "You mentioned fuel issues yesterday - want me to check Starbase X again?"
```

### 3. Long-Term Memory (User Profile + Preferences)
**Purpose**: Persistent user preferences, play style, decision patterns
**Storage**: DynamoDB (no TTL) + vector embeddings
**Lifetime**: Indefinite
**Size**: ~200KB per user (preferences + embeddings)
**Cost**: ~$2/month per 100 users

**Data Stored**:
- Fleet names and configurations
- Preferred communication style (technical vs casual)
- Risk tolerance (aggressive vs conservative trading)
- Favorite starbases, routes, resources
- Historical decisions (crafting choices, trade patterns)

**Example**:
```
Agent learns: User always prioritizes fuel efficiency over speed
Future recommendations: "Route A uses 20% less fuel but takes 1 hour longer - based on your preferences, I recommend Route A"
```

### 4. Semantic Memory (Pre-Loaded Game Knowledge)
**Purpose**: Star Atlas game mechanics, strategies, market patterns
**Storage**: DynamoDB vector embeddings (shared across all users)
**Lifetime**: Updated with game patches
**Size**: ~500KB-1MB (game knowledge base)
**Cost**: ~$5/month (one-time storage, shared)

**Data Stored**:
- Crafting recipes and optimization strategies
- Starbase locations and capabilities
- Resource market patterns
- Common player strategies

**Example**:
```
User: "What's the best way to make a Medium Fighter?"
Agent retrieves: Crafting recipe + cost analysis + user's resource inventory → personalized recommendation
```

---

## Trust-Building Visualization Strategy

### Core Principle
**Voice-first, visualizations secondary** - BUT available when user asks "why?"

### Visualization Types

#### 1. Reasoning Transparency (High Priority)
**When**: User asks "why did you recommend X?"

**Show**:
- Decision tree visualization
- Weighted factors (cost, time, risk, user preferences)
- Data sources used (market prices, user history, game mechanics)

**Example**:
```
User: "Why Route A?"
Agent (voice): "Route A saves 20% fuel, which matches your efficiency preference"
Agent (visual): [Bar chart showing fuel cost comparison + user preference weight]
```

#### 2. Fleet Status Dashboard (Medium Priority)
**When**: User asks for fleet status or detailed view

**Show**:
- EvEye-level detail (fuel %, cargo, location, health)
- Historical trends (fuel consumption over time)
- Predictive alerts ("Fuel depletes in 2 hours")

**Not primary UI** - available on request, not pushed

#### 3. Market Context (Low Priority)
**When**: User asks about prices or market conditions

**Show**:
- Price charts (simple, not EvEye-level complexity)
- "Agent's view": What data influenced the recommendation

**Example**:
```
User: "Should I sell titanium now?"
Agent (voice): "Wait 2 days - price trend suggests 15% increase"
Agent (visual): [Simple price trend line + agent's prediction overlay]
```

---

## RAG Implementation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interaction                        │
│                  (Voice/Text via Web App)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Core (Lambda)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Classify query intent                            │  │
│  │  2. Retrieve relevant context (vector search)        │  │
│  │  3. Augment prompt with personalized context         │  │
│  │  4. Generate response (Claude Agent SDK)             │  │
│  │  5. Store interaction embedding                      │  │
│  └──────────────────────────────────────────────────────┘  │
└───────┬─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              DynamoDB Vector Store (Memory)                  │
│  ┌─────────────────────┬─────────────────────┬────────────┐ │
│  │  Short-Term         │  Long-Term          │  Semantic  │ │
│  │  (7-day TTL)        │  (User Profile)     │  (Shared)  │ │
│  ├─────────────────────┼─────────────────────┼────────────┤ │
│  │ Recent convos       │ Preferences         │ Game rules │ │
│  │ Context threads     │ Decision patterns   │ Strategies │ │
│  │ Temp fleet states   │ Fleet configs       │ Recipes    │ │
│  └─────────────────────┴─────────────────────┴────────────┘ │
└───────┬─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│           Embedding Service (Bedrock Titan v2)               │
│  - Convert text to 1024-dim vectors                          │
│  - Cost: $0.0001 per 1K tokens                               │
│  - Binary embeddings for cost optimization (50% savings)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Personality Progression Implementation

### Colleague Phase (First 2 weeks)
**Characteristics**:
- Formal, professional tone
- Explicit confirmations ("Shall I proceed?")
- Educational responses ("Here's how this works...")
- Risk-averse recommendations

**Memory Focus**:
- Learn user's fleet names and basic preferences
- Identify communication style preference
- Build confidence through successful interactions

**Trust Building**:
- Show reasoning frequently (build transparency)
- Offer choices, explain trade-offs
- Admit uncertainty when data is incomplete

### Partner Phase (Weeks 3-8)
**Characteristics**:
- Conversational tone, less formal
- Anticipatory suggestions ("You might want to...")
- Balanced risk/reward recommendations
- Contextual awareness ("Last time you chose X because...")

**Memory Focus**:
- Pattern recognition (user's decision-making style)
- Proactive monitoring (alerts before user asks)
- Strategy alignment (understand user's goals)

**Trust Building**:
- Show reasoning on request (not always)
- Make recommendations with confidence
- Acknowledge user's expertise

### Friend Phase (2+ months)
**Characteristics**:
- Casual, personalized tone
- Proactive optimization ("I handled X for you")
- High-confidence recommendations
- Personality quirks (user-specific)

**Memory Focus**:
- Deep preference model (implicit preferences)
- Long-term goal tracking ("Your goal to build 10 fighters is 60% complete")
- Social context ("You mentioned vacation next week - want me to auto-monitor?")

**Trust Building**:
- Reasoning shown only when asked or when uncertain
- High autonomy (with safeguards)
- Shared history references ("Remember when...")

---

## Cost Analysis (Updated with Memory)

### Base Architecture (from planning session)
- Lambda + API Gateway: $0 (Free Tier, 1M requests/month)
- DynamoDB (fleet data): $0 (Free Tier, 25GB)
- S3 + CloudFront: $0 (Free Tier, 50GB + 1TB transfer)
- ECS Fargate (voice service): $3-5/month
- **Subtotal**: $3-7/month

### Memory Architecture Addition
- DynamoDB storage (embeddings): ~$10/month (beyond Free Tier)
- DynamoDB queries (vector search): ~$5/month
- Bedrock Titan v2 (embeddings): ~$8/month
- Lambda (RAG processing): ~$2/month
- **Subtotal**: ~$25/month

### Total MVP Cost
**$28-32/month** for fully personalized agent with memory

**Cost per user** (100 users):
- **$0.28-0.32 per user/month**
- Subscription pricing: $5/month = sustainable at <20 users

### Optimization Opportunities
1. **Binary embeddings**: 50% cost reduction on Bedrock → $4/month savings
2. **Aggressive TTL**: 3-day vs 7-day short-term memory → $2/month savings
3. **Batch processing**: Group embedding requests → $3/month savings
4. **User tiers**: Free = no long-term memory, Pro = full memory → variable cost

**Optimized MVP Cost**: **$20-25/month** total

---

## Scalability & Migration Path

### MVP (0-100 users)
- DynamoDB vector store
- Up to 30K embeddings per user
- 100-200ms query latency
- Cost: $20-30/month

### Growth (100-1K users)
- DynamoDB vector store (still cost-effective)
- Sharding by user ID
- Caching layer (ElastiCache)
- Cost: $50-100/month

### Scale (1K-10K users)
- Migrate to OpenSearch Serverless
- Dedicated vector search infrastructure
- Multi-region replication
- Cost: $200-500/month

### Enterprise (10K+ users)
- Amazon Bedrock Knowledge Bases
- Multi-AZ, auto-scaling
- Advanced monitoring
- Cost: $1K-5K/month

**Migration trigger**: When DynamoDB query latency >500ms consistently

---

## Implementation Phases

### Phase 1: Basic Memory (Week 1-2)
- [ ] DynamoDB table design (users, conversations, embeddings)
- [ ] Bedrock Titan v2 integration (embedding generation)
- [ ] Vector search Lambda (cosine similarity)
- [ ] Session memory (in-Lambda context)

### Phase 2: RAG Integration (Week 3-4)
- [ ] Claude Agent SDK + memory augmentation
- [ ] Short-term memory (7-day TTL)
- [ ] Conversation threading
- [ ] Basic personalization (name, preferences)

### Phase 3: Long-Term Learning (Week 5-8)
- [ ] Decision pattern analysis
- [ ] Preference inference (implicit learning)
- [ ] Personality progression triggers
- [ ] Trust score metrics

### Phase 4: Trust Visualizations (Week 9-12)
- [ ] Reasoning transparency UI
- [ ] Fleet status dashboard
- [ ] Market context visualizations
- [ ] "Show your work" feature

---

## Open Technical Questions

1. **Embedding dimension**: 1024 (Titan v2) vs 768 (Titan v1)? (Recommend v2 for quality)
2. **Similarity threshold**: What cosine similarity = "relevant context"? (Recommend 0.7-0.8, A/B test)
3. **Context window**: How many retrieved memories to include in prompt? (Recommend 5-10 top results)
4. **Update frequency**: Real-time embedding vs batch? (Recommend async batch every 5 minutes)
5. **Privacy**: Memory retention policy for inactive users? (Recommend 90-day deletion)

---

## Next Steps

1. **Spike task**: Prototype DynamoDB vector search with sample Star Atlas data
   - Validate 100-200ms latency assumption
   - Measure actual embedding costs
   - Test cosine similarity accuracy

2. **Update ARCHITECTURE.md**: Add four-tier memory architecture diagram

3. **Update BLUEPRINT.yaml**: Add memory implementation phases

4. **Cost validation**: Deploy pilot with 10 test users, measure actual AWS costs

---

**Status**: Research complete. Ready to integrate into blueprint and implementation plan.

**Recommendation**: Proceed with DynamoDB vector store for MVP. Plan migration path to OpenSearch Serverless if we hit 1K+ users.
