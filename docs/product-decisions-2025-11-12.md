# Product Decisions - Star Atlas Agent

**Date**: 2025-11-12
**Status**: Core decisions finalized, spikes identified
**Next**: Integrate into BLUEPRINT.yaml

---

## Decision Summary Table

| Decision Area | MVP Approach | Post-MVP / Future | Spike Required? |
|---------------|--------------|-------------------|-----------------|
| Voice UX | Push-to-talk | Always-listening (toggle) | ❌ No |
| Authentication | Email + Wallet + zProfile | Same, with smoother onboarding | ✅ Yes (z.ink integration) |
| Subscription Tiers | TBD | Free / Pro / Ultimate | ✅ Yes (feature distribution) |
| Memory Retention | Human-like (key memories) | Same | ✅ Yes (cost optimization) |
| Visualizations | Data-rich backend, light UI | Expand based on feedback | ❌ No (clear strategy) |

---

## 1. Voice UX Decision

### MVP: Push-to-Talk (PTT)
**Rationale**:
- Simpler implementation (no wake word detection)
- Lower cost (no always-on audio stream processing)
- Better privacy (explicit user control)
- Faster to market

**Implementation**:
- Web: Hold spacebar or on-screen button
- Mobile: Tap-and-hold button
- Visual indicator: Recording state clear

**Cost Impact**: $0 (baseline voice service already budgeted)

### Post-MVP: Always-Listening (Optional)
**Trigger for implementation**: User requests or competitive pressure

**Implementation**:
- Wake word: "Hey Cortana" (customizable)
- User setting: Toggle always-listening on/off
- Privacy indicator: LED/icon when listening
- Local wake word detection (Picovoice Porcupine ~$1/month)

**Cost Impact**: +$1-2/month per active always-listening user

**Timeline**: 3-6 months post-MVP

---

## 2. Authentication Decision

### MVP: Triple Authentication (Email + Wallet + zProfile)

**Flow Options**:

#### Option A: Email-First (Recommended for "handshake UX")
```
1. User visits app
2. "Enter email to get started" (no password yet)
3. → Send magic link
4. User clicks link → Basic profile created
5. → Voice assistant greets: "Welcome! Let's connect your Star Atlas account"
6. → Guided wallet connection (Phantom/Solflare)
7. → Optional: zProfile linking
8. → Done (user can use basic features immediately)
```

**Rationale**:
- Lowest friction (email = familiar)
- Progressive authentication (wallet optional initially)
- Can use agent before owning Star Atlas assets
- Magic links = no password friction

#### Option B: Wallet-First (Traditional Web3)
```
1. User visits app
2. "Connect wallet to begin"
3. → Phantom/Solflare connection
4. → Email prompt for notifications (optional)
5. → zProfile linking (optional)
6. → Done
```

**Rationale**:
- Web3-native experience
- Immediate wallet integration
- No email required (privacy)

**Decision**: **Option A (Email-First)** for "handshake UX" - frictionless onboarding

### zProfile Integration (Spike Required)

**Benefits**:
- Single Sign-On across Star Atlas ecosystem
- dApp permissioning (auto-sign within limits)
- KYC-once (if we need compliance)
- XP/leveling integration (gamification)
- Airdrop eligibility tracking

**Spike Questions**:
1. Is there a zProfile developer API? (December 2025 launch)
2. Can third-party apps create zProfiles on behalf of users?
3. What's the minimum friction path to link existing wallet → zProfile?
4. Does zProfile support email-based identity, or wallet-only?
5. Cost per zProfile creation/linking operation?

**Implementation Timeline**:
- **MVP (Nov-Dec 2025)**: Email + Wallet (zProfile optional manual link)
- **Post-Launch (Jan 2025+)**: Full zProfile integration after December launch
- **Future**: "Create Star Atlas account for you" feature (if API supports)

### "Handshake UX" Design

**Goal**: As easy as shaking hands when you meet someone for the first time

**Key Principles**:
1. **No barriers**: Email-only to start, everything else optional
2. **Progressive disclosure**: Add wallet/zProfile when user needs features
3. **Voice-guided**: Agent walks user through setup conversationally
4. **Instant value**: User can ask questions immediately, even without wallet

**Example Flow**:
```
User arrives → Email input → Magic link → Greeted by voice agent

Agent (voice): "Hi! I'm your Star Atlas assistant. What should I call you?"
User: "Sam"
Agent: "Great to meet you, Sam! I can help you with Star Atlas gameplay,
       fleet management, and economic optimization. To get started,
       would you like to connect your wallet, or should I give you a tour first?"

User: "Give me a tour"
Agent: "Perfect! Let me show you what I can do..."
[Voice-guided onboarding, no wallet required yet]

Later...
User: "Check my fleet status"
Agent: "I'll need to connect to your wallet to see your fleets.
       This takes about 10 seconds. Ready?"
User: "Yes"
Agent: "Great! I'm opening your wallet connection now..."
[Phantom popup, user approves, instant fleet access]
```

**Friction Metrics**:
- Time to first agent interaction: **<30 seconds** (email → magic link)
- Time to wallet connection: **<60 seconds** (when user needs it)
- Time to full feature access: **<2 minutes** (email → wallet → zProfile)

---

## 3. Subscription Tier Decision (Spike Required)

### Core Philosophy: "Audible Model"

**Principle**: Users should never feel like they lose their "friend" or "progress" if they stop paying

**Key Insight from Audible**:
- You keep your books even if you cancel subscription
- You just can't get *new* books without paying
- Your library and progress are permanent

**Applied to Star Atlas Agent**:
- You keep your *relationship* (memory, personality) even if you cancel
- You just can't access *premium features* without paying
- Your fleet data, conversation history, and preferences are permanent

### Proposed Tier Structure (Requires Spike)

**Free Tier** (Always available):
- ✅ Basic fleet monitoring (5 fleets max)
- ✅ Voice interactions (100 queries/month limit)
- ✅ Price checking (5-min delayed data)
- ✅ Basic memory (7-day short-term only)
- ✅ Profile access (can view but not edit)
- ❌ No economic optimization
- ❌ No proactive alerts
- ❌ No always-listening

**Pro Tier** ($9.99/month):
- ✅ Unlimited fleets
- ✅ Unlimited voice queries
- ✅ Real-time market data
- ✅ Full memory (long-term + semantic)
- ✅ Economic optimization (crafting ROI)
- ✅ Proactive alerts (fuel, repairs)
- ✅ Personality progression (colleague → partner → friend)
- ✅ Custom visualizations
- ❌ No transaction automation
- ❌ No multi-user coordination

**Ultimate Tier** ($29.99/month):
- ✅ Everything in Pro
- ✅ Always-listening mode
- ✅ Transaction automation (within user-set limits)
- ✅ Multi-user coordination (guild features)
- ✅ Advanced analytics (custom dashboards)
- ✅ Priority support
- ✅ Early access to new features

### Retention Policy (Critical)

**When user cancels subscription**:
- ✅ **Keep**: All conversation history (read-only)
- ✅ **Keep**: Personality/relationship data (frozen)
- ✅ **Keep**: Fleet configurations (read-only)
- ✅ **Keep**: Profile and preferences
- ⏸️ **Pause**: Proactive monitoring (no new alerts)
- ⏸️ **Pause**: Long-term memory updates (no new learning)
- 🔒 **Lock**: Premium features (economic optimization, automation)

**When user re-subscribes**:
- ✅ **Restore**: Full feature access immediately
- ✅ **Resume**: Memory and learning
- ✅ **Continuity**: "Welcome back, Sam! It's been 3 weeks. Let me catch up on your fleets..."

**Goal**: User feels like they're **pausing a friendship**, not **losing a friend**

### Spike Questions

1. **Feature Distribution**:
   - Which features drive most value? (MVP data will reveal)
   - What's the minimum viable Free tier to hook users?
   - Where's the Pro/Ultimate boundary? (usage-based vs capability-based)

2. **Pricing Psychology**:
   - Is $9.99 the right Pro price? (A/B test $7.99 vs $9.99 vs $14.99)
   - Should Ultimate be $19.99 or $29.99? (guild features justify higher?)
   - Annual discount? (20% off = better retention)

3. **Retention Metrics**:
   - How long do canceled users typically wait before re-subscribing?
   - Does "keep your data" policy improve retention vs competitors?
   - What % of Free users convert to Pro? (industry: 2-5%)

4. **Cost-to-Serve**:
   - What's the actual cost per Free user? (target: <$0.25/month)
   - What's the margin on Pro? (target: >70%)
   - Can we sustain Free tier at scale? (cross-subsidy model)

**Timeline**:
- **MVP (Month 1-3)**: Free tier only (validate product-market fit)
- **Month 4-6**: Introduce Pro tier (early adopter pricing)
- **Month 7-12**: Add Ultimate tier (after guild features built)

---

## 4. Memory Retention Decision (Spike Required)

### Core Philosophy: "Simulate Humans"

**How humans remember**:
- 🔥 **Vivid details** from recent events (hours-days ago)
- 💡 **Key moments** from important conversations (weeks-months ago)
- 🎭 **General impressions** of relationships (years ago)
- ❌ **Not verbatim** everything (we forget details, keep essence)

**Applied to Agent Memory**:
- 🔥 **Session memory**: Exact conversation (current session only)
- 💡 **Key memories**: Important decisions, preferences, events (permanent)
- 🎭 **Relationship impression**: User's style, risk tolerance, goals (permanent)
- ❌ **Not verbatim**: Old conversations compressed to embeddings, details fade

### Proposed Memory Architecture

#### Tier 1: Session Memory (In-Memory)
**Retention**: Duration of session (30 min typical voice session)
**Fidelity**: Verbatim transcript
**Cost**: $0 (Lambda execution memory)

**Example**:
```
User: "Check my fleet Alpha"
Agent: "Fleet Alpha is at Starbase 7, fuel 78%"
User: "What about fuel?" ← Agent remembers "Fleet Alpha" from 10 seconds ago
```

#### Tier 2: Recent Memory (Hot Cache, 48 Hours)
**Retention**: 48 hours (2 days)
**Fidelity**: Full conversation threads
**Storage**: DynamoDB with 48-hour TTL
**Cost**: ~$0.10/month per 100 users

**Example**:
```
Monday 10am: "My fleet needs repairs at Starbase X"
Monday 8pm: "Did you get those repairs done?" ← Agent remembers context from 10 hours ago
```

**Rationale**: Humans remember conversations vividly for ~2 days, then details fade

#### Tier 3: Key Memories (Permanent, Sparse)
**Retention**: Permanent
**Fidelity**: Summarized + tagged (not verbatim)
**Storage**: DynamoDB + vector embeddings
**Trigger**: Agent identifies "important moment" via Claude

**Important Moments**:
- User sets a goal ("I want to build 10 fighters")
- User makes a significant decision ("Sold all titanium, going all-in on iron")
- User shares personal context ("Going on vacation next week")
- User expresses preference ("I always prioritize fuel efficiency")
- User corrects agent ("No, I prefer Route B because...")

**Example Storage**:
```json
{
  "memory_id": "mem_abc123",
  "user_id": "user_xyz",
  "timestamp": "2025-11-10T14:30:00Z",
  "type": "preference",
  "summary": "User prioritizes fuel efficiency over speed",
  "embedding": [0.234, -0.567, ...],  // Vector for similarity search
  "metadata": {
    "confidence": 0.95,
    "context": "route_planning",
    "reinforced_count": 3  // User has confirmed this 3 times
  }
}
```

**Cost**: ~$5/month per 100 users (assuming 50 key memories per user)

#### Tier 4: Relationship Impression (Permanent, High-Level)
**Retention**: Permanent
**Fidelity**: Structured profile (not conversation-based)
**Storage**: DynamoDB user profile table
**Update Frequency**: After each session (async batch)

**Profile Structure**:
```json
{
  "user_id": "user_xyz",
  "personality_phase": "partner",  // colleague → partner → friend
  "communication_style": "casual",  // formal, technical, casual
  "risk_tolerance": "moderate",    // conservative, moderate, aggressive
  "decision_speed": "deliberate",   // quick, deliberate, analytical
  "primary_goals": [
    "Build 10 fighters by end of year",
    "Maximize crafting profit margins"
  ],
  "fleet_preferences": {
    "fuel_priority": "high",
    "speed_priority": "medium",
    "cost_priority": "medium"
  },
  "relationship_metrics": {
    "sessions_count": 47,
    "total_voice_minutes": 320,
    "trust_score": 0.82,  // 0-1 scale
    "last_interaction": "2025-11-12T10:00:00Z"
  }
}
```

**Cost**: ~$0.05/month per 100 users (lightweight structured data)

### Memory Compression Strategy (Cost Optimization)

**Problem**: Storing full conversation transcripts expensive at scale
**Solution**: Progressive compression

**Timeline**:
- **0-48 hours**: Full conversation (verbatim)
- **2-7 days**: Summarized conversation (Claude-generated summary)
- **7-30 days**: Key memories only (extracted moments + embeddings)
- **30+ days**: Relationship impression only (structured profile updates)

**Example Compression**:

**Day 1** (Full):
```
User: "I need to move Fleet Alpha from Starbase 7 to Starbase 12"
Agent: "Fleet Alpha is currently at Starbase 7 with 78% fuel. The journey to Starbase 12 takes 2 hours and consumes 35% fuel. You'll arrive with 43% fuel remaining. Shall I proceed?"
User: "Yes, but take the scenic route through Sector 9"
Agent: "Understood. Taking the route through Sector 9 adds 30 minutes but you mentioned you enjoy the view there. Initiating warp now."
```

**Day 3** (Summarized):
```
"User moved Fleet Alpha from Starbase 7 to Starbase 12 via Sector 9 (scenic route preference confirmed)"
```

**Day 8** (Key Memory Extracted):
```
{
  "type": "preference",
  "summary": "User prefers scenic routes even if slower (Sector 9 example)",
  "embedding": [...]
}
```

**Day 31** (Profile Update Only):
```
{
  "route_preferences": {
    "scenic_routes": "preferred",
    "time_sensitivity": "low"
  }
}
```

**Cost Savings**: 95% reduction in storage costs after 30 days

### Spike Questions

1. **Compression Timing**:
   - Is 48-hour verbatim retention enough? (vs 7 days)
   - When to trigger summarization? (batch daily vs real-time)
   - What's the Claude API cost for summarization? (estimate ~$0.01 per 100 conversations)

2. **Key Memory Identification**:
   - Can Claude reliably identify "important moments"? (needs testing)
   - What's the false positive rate? (storing unimportant memories)
   - How many key memories per user per month? (estimate 10-20)

3. **Relationship Metrics**:
   - What trust score algorithm? (simple: interactions/corrections ratio)
   - How to measure personality phase progression? (rule-based vs ML)
   - Should users see these metrics? (transparency vs magic)

4. **Cost Validation**:
   - Actual DynamoDB costs with realistic data? (need pilot)
   - Embedding generation cost? (Bedrock Titan v2: $0.0001/1K tokens)
   - Total memory cost per user per month? (target: <$0.25)

**Timeline**:
- **Month 1-2**: Build basic architecture (all tiers)
- **Month 3-4**: Add compression pipeline (test with 50 users)
- **Month 5-6**: Optimize based on real usage data

---

## 5. Visualization Strategy Decision

### Core Principle: "Data-Rich Backend, Light Frontend"

**Goal**: Agent generates visualizations programmatically (saves tokens) but only shows when needed (saves user attention)

### Three-Layer Visualization Architecture

#### Layer 1: Programmatic Generation (Always On, Hidden)
**Purpose**: Token efficiency - compute, don't describe

**What gets generated** (every query):
- Fleet status tables (fuel %, cargo %, location)
- Market price charts (time series data)
- Route maps (coordinates, travel times)
- Decision trees (weighted factors)
- Comparison matrices (option A vs B vs C)

**Where it lives**:
- Backend Lambda functions (not in LLM tokens)
- Structured data in DynamoDB
- Pre-computed charts in S3 (cached)

**Example**:
```
User: "Should I sell titanium now?"

Backend generates (before LLM call):
- Price chart: Last 7 days titanium prices
- Trend analysis: Linear regression, volatility
- Comparison table: Sell now vs wait 1 day vs wait 3 days

LLM receives:
- Chart URL: "s3://bucket/charts/titanium-7day-abc123.png"
- Structured data: { current_price: 0.045, trend: "rising", recommendation: "wait" }

Agent responds (voice):
"Wait 2 days - titanium is trending up 15%"

Agent responds (visual, if user asks "why?"):
[Shows chart with trend line + decision factors]
```

**Token savings**: 500-1000 tokens per complex query (chart description avoided)

**Cost impact**: +$2-3/month for chart generation (Chart.js Lambda function + S3 storage)

#### Layer 2: On-Demand Display (User Requested)
**Purpose**: Trust building - show reasoning when asked

**Triggers**:
- User asks "why?" or "show me"
- User requests specific visualization ("show chart")
- Complex recommendation (agent offers to show logic)

**What gets shown**:
- Decision tree: "Here's how I weighted your options..."
- Data sources: "I used these 3 data points..."
- Reasoning transparency: "You told me you prefer X, so..."

**Example**:
```
Agent (voice): "I recommend Route A - it saves 20% fuel"
User: "Why?"
Agent (voice): "Let me show you the breakdown"
Agent (visual):
  [Side-by-side comparison]
  Route A: Fuel: 35%, Time: 2h, Cost: 12 ATLAS
  Route B: Fuel: 45%, Time: 1.5h, Cost: 18 ATLAS
  [Highlighted] Your preference: Fuel efficiency (weight: 0.8)
```

**Frequency**: ~20% of queries (user asks for details)

#### Layer 3: Proactive Display (Agent Initiated)
**Purpose**: Prevent misunderstandings on critical decisions

**Triggers**:
- High-stakes decisions (>100 ATLAS transaction)
- User safety (low fuel warning)
- Conflicting data (agent uncertain)
- New feature introduction

**Example**:
```
Agent (voice): "ALERT: Fleet Alpha fuel critical - 8% remaining"
Agent (visual, automatically shown):
  [Fleet status dashboard with red warning]
  Fleet Alpha - CRITICAL
  Fuel: 8% (1.2 hours remaining)
  Nearest refuel: Starbase 12 (45 min away)
  [Action buttons: "Refuel now" | "Dock fleet" | "Ignore"]
```

**Frequency**: ~5% of interactions (critical alerts only)

### Visualization Types (Priority Order)

**MVP (Month 1-3)**:
1. ✅ Fleet status table (HTML table, simple)
2. ✅ Price comparison (bar chart, Chart.js)
3. ✅ Route comparison (side-by-side table)
4. ✅ Decision breakdown (weighted factors)

**Post-MVP (Month 4-6)**:
5. 📊 Historical price charts (time series)
6. 🗺️ Route maps (2D starbase locations)
7. 📈 Portfolio tracker (fleet value over time)
8. 🎯 Goal progress (visual progress bars)

**Future (Month 7+)**:
9. 🌐 3D fleet visualization (EvEye-style map)
10. 📊 Custom dashboards (user-configurable)
11. 🤖 Agent reasoning graph (show thought process)

### Token Efficiency Measurement

**Baseline** (no visualizations):
```
User: "Should I sell titanium?"
Agent prompt: "Current titanium price is 0.045 ATLAS, down 2.3% from yesterday.
24-hour volume is 1.2M units. Historical prices: 7 days ago: 0.047, 14 days ago: 0.043..."
[500 tokens of data description]

Agent response: "Wait 2 days - trending up" [10 tokens]
Total: 510 tokens
```

**With programmatic visualization**:
```
User: "Should I sell titanium?"
Agent prompt: "Current titanium analysis: [chart URL], trend: rising, recommendation: wait"
[50 tokens of structured data]

Agent response: "Wait 2 days - trending up" [10 tokens]
Total: 60 tokens
```

**Savings**: 88% token reduction on data-heavy queries

**Cost impact**:
- Token savings: ~$0.10/month per user (at 100 queries/month)
- Chart generation cost: ~$0.05/month per user
- **Net savings**: $0.05/month per user (scales with usage)

### Implementation Notes

- All charts generated server-side (no client-side Chart.js for token efficiency)
- Charts cached in S3 with 5-min TTL (balance freshness vs cost)
- Visual URLs passed to agent in prompt (not chart data)
- Agent decides whether to show visualization (based on user query + context)

**No spike required** - strategy is clear, implement incrementally

---

## Summary: Spikes Required

### 1. z.ink / zProfile Integration (High Priority)
**Timeline**: December 2025 (after z.ink mainnet launch)
**Questions**:
- Developer API availability
- User creation/linking flow
- Cost per operation
- Email integration support

**Deliverable**: Technical feasibility doc + integration plan

### 2. Subscription Tier Feature Distribution (Medium Priority)
**Timeline**: Month 3-4 (after MVP user data)
**Questions**:
- Which features drive most value?
- Optimal Free tier to hook users?
- Pro/Ultimate pricing sweet spot?
- Retention metrics vs competitors?

**Deliverable**: Pricing strategy with A/B test plan

### 3. Memory Retention Cost Optimization (Medium Priority)
**Timeline**: Month 2-3 (during MVP with pilot users)
**Questions**:
- Actual DynamoDB costs with real data?
- Compression effectiveness?
- Key memory identification accuracy?
- Cost per user at scale?

**Deliverable**: Optimized memory architecture with cost model

---

## Next Steps

1. ✅ **Decisions documented** (this file)
2. ⏭️ **Update ARCHITECTURE.md** with authentication flow + memory tiers
3. ⏭️ **Generate BLUEPRINT.yaml** with spikes as separate work items
4. ⏭️ **Create GitHub issues** including spike tasks
5. ⏭️ **Begin MVP implementation** (email auth + basic memory first)

---

**Status**: Core product decisions finalized. Ready for blueprint generation with identified spikes.
