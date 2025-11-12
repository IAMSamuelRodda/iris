# ADR-001: Star Atlas Data Sourcing Strategy

**Date**: 2025-11-12
**Status**: Proposed
**Deciders**: Architecture Team
**Related Issues**: #141 (Research Spike), #25 (MCP Server Implementation)

---

## Context

The MCP Server needs access to Star Atlas game data for fleet management, market analysis, and crafting tools. We need to determine the optimal data sourcing strategy that balances:
- **Cost efficiency**: Minimize Solana RPC calls and Bedrock token usage
- **Data freshness**: Real-time data where needed, cached where acceptable
- **Implementation complexity**: Leverage existing APIs vs building custom solutions

## Decision Drivers

1. **Cost Optimization**: Current projection shows $30-50/month for full real-time RPC queries
2. **API Availability**: Star Atlas provides official APIs and SDKs
3. **Data Characteristics**: Mix of static metadata and real-time blockchain state
4. **User Experience**: <500ms response time for agent queries

## Research Findings

### Official Star Atlas APIs

#### 1. Galaxy API (REST)
- **URL**: `https://galaxy.staratlas.com`
- **Endpoint**: `GET /nfts` - Returns all Star Atlas items with metadata
- **Data Provided**:
  - Ship blueprints (name, description, tier, class, rarity)
  - Item attributes (crew slots, component slots, module slots)
  - Marketplace info (mint address, supply, markets, prices)
  - Media assets (images, 3D models, thumbnails)
  - Collection metadata
- **Update Frequency**: Infrequent (items/ships don't change often)
- **Cost**: **FREE** (no authentication required)

#### 2. Data Source SDK (`@staratlas/data-source`)
- **Purpose**: Abstraction over Solana RPC for Star Atlas programs
- **Data Access**: Direct blockchain queries via Solana RPC
- **Use Cases**: Fleet status, cargo levels, real-time game state
- **Update Frequency**: Real-time
- **Cost**: ~$0.001 per RPC request (paid to Solana RPC provider)

#### 3. SAGE SDK (`@staratlas/sage` v1.8.10)
- **Purpose**: TypeScript bindings for SAGE game program
- **Account Types**: Fleet, Planet, Starbase, Sector, etc.
- **Data Access**: On-chain via Solana RPC
- **Use Cases**: Game mechanics, fleet management
- **Cost**: RPC calls (same as Data Source SDK)

#### 4. Crafting SDK (`@staratlas/crafting`)
- **Purpose**: TypeScript bindings for crafting program
- **Account Types**: Recipe, CraftingProcess, CraftingFacility, RecipeCategory
- **Data Access**: On-chain (recipes stored as program accounts)
- **Note**: Documentation incomplete ("Examples - Coming Soon...")

### Data Categorization by Update Frequency

#### Static/Rarely Change (✅ Perfect for Caching)
| Data Type | Source | Update Frequency | Caching Strategy |
|-----------|--------|------------------|------------------|
| Ship blueprints & stats | Galaxy API | Rarely (game updates) | Weekly snapshot + CDN |
| Item metadata (names, images) | Galaxy API | Rarely | Weekly snapshot + CDN |
| Crafting recipes | Crafting SDK | Rarely | Weekly snapshot |
| Starbase locations | SAGE SDK | Rarely | Weekly snapshot |
| Resource types | Galaxy API | Rarely | Weekly snapshot |

#### Infrequent Changes (⚠️ Daily/Hourly Snapshots)
| Data Type | Source | Update Frequency | Caching Strategy |
|-----------|--------|------------------|------------------|
| Marketplace listings | Galaxy API `markets` | Hours | 1-hour cache |
| Token prices (ATLAS/POLIS) | CoinGecko API | Minutes | 5-minute cache (already planned) |

#### Real-Time Required (🔴 Direct RPC Queries)
| Data Type | Source | Update Frequency | Caching Strategy |
|-----------|--------|------------------|------------------|
| Fleet fuel/cargo/health | SAGE SDK + RPC | Seconds | No cache (query on demand) |
| User wallet balances | Solana RPC | Seconds | No cache |
| Active transactions | Solana RPC | Blocks (~400ms) | No cache |
| Crafting process status | Crafting SDK + RPC | Seconds | No cache |

## Decision

**Use a Hybrid Data Sourcing Strategy**:

### 1. Static Metadata: Galaxy API + Weekly Snapshots

**Approach**:
- Scheduled Lambda (weekly): Fetch `GET /nfts` from Galaxy API
- Store as structured JSON in S3 (`staratlas-static-data/v{version}/`)
- Serve via CloudFront CDN for fast access
- MCP Server checks S3 first, falls back to API if cache miss

**Benefits**:
- **FREE**: Galaxy API has no cost
- **Fast**: CloudFront CDN delivers <50ms
- **Predictable**: No RPC call variability
- **Rich Context**: Complete ship/item metadata for agent prompts

**Implementation**:
```typescript
// MCP Server pseudocode
async function getShipMetadata(shipMint: string) {
  // Check S3 cache first
  const cached = await s3.getObject('staratlas-static-data/v1/ships.json');
  const ships = JSON.parse(cached);
  return ships.find(s => s.mint === shipMint);

  // Fallback to Galaxy API if cache miss (rare)
  if (!ship) {
    const response = await fetch('https://galaxy.staratlas.com/nfts');
    // ... update cache
  }
}
```

### 2. Real-Time Data: Solana RPC via SAGE SDK

**Approach**:
- Use `@staratlas/sage` + `@staratlas/data-source` for fleet queries
- Direct Solana RPC calls only when user asks about their fleet
- Implement request deduplication (don't query same fleet twice in 30s)

**Benefits**:
- **Current**: Always fresh data for critical decisions
- **Official**: Leverages Star Atlas SDKs (maintained, type-safe)
- **Controlled Cost**: Only query when user explicitly asks

**Implementation**:
```typescript
// MCP tool: getFleetStatus
async function getFleetStatus(fleetId: string) {
  // Check recent query cache (30s TTL in-memory)
  if (recentQueries.has(fleetId)) {
    return recentQueries.get(fleetId);
  }

  // Query Solana RPC via SAGE SDK
  const fleet = await readFromRPC(connection, sageProgram, Fleet, fleetId);

  // Cache for 30s to avoid duplicate queries in same conversation
  recentQueries.set(fleetId, fleet, { ttl: 30 });
  return fleet;
}
```

### 3. Crafting Recipes: Snapshot from Solana RPC

**Approach**:
- One-time fetch: Query all Recipe accounts from crafting program
- Store in S3 (recipes don't change frequently)
- Update on game version changes or manual trigger

**Benefits**:
- **Complete**: All recipes available offline
- **Cost-Effective**: One-time RPC cost (~$0.10 for all recipes)
- **Fast**: S3/CloudFront delivery

**Unknown**: Crafting SDK documentation incomplete. May need to explore program accounts directly or wait for official examples.

## Cost Analysis

### Current Baseline (No Caching)
- Ship metadata lookups: 1000 requests/day × $0.001 = $30/month
- Bedrock context: 500 tokens/query × $0.003/1K × 100 queries = $15/month
- **Total**: **~$45/month**

### Proposed Hybrid (Galaxy API + Snapshots)
- Galaxy API calls: **$0/month** (FREE)
- S3 storage: <$1/month (JSON files)
- CloudFront: **$0/month** (Free Tier: 1TB transfer)
- Weekly Lambda snapshot: **$0/month** (Free Tier: 1M requests)
- Solana RPC (real-time only): ~100 requests/day × $0.001 = $3/month
- **Total**: **~$4/month**

**Savings**: **$41/month (91% reduction)**

## Consequences

### Positive
- ✅ **91% cost reduction** on data access
- ✅ **Faster responses** via CDN (50ms vs 200-500ms RPC)
- ✅ **Reduced Bedrock token usage** (smaller prompts with pre-fetched metadata)
- ✅ **FREE official API** (Galaxy API)
- ✅ **Reliable**: Less dependent on RPC provider uptime
- ✅ **Type-safe**: Official Star Atlas SDKs with TypeScript

### Negative
- ⚠️ **Weekly lag** on static metadata (acceptable for ships/items)
- ⚠️ **Additional complexity**: Snapshot Lambda + S3 management
- ⚠️ **Storage costs** if data grows large (unlikely: <10MB estimated)

### Neutral
- 🔄 **Version management**: Need to handle game updates (monitor Star Atlas Discord/changelog)
- 🔄 **Crafting SDK**: Documentation incomplete, may need direct program account queries

## Implementation Plan

### Phase 1: Galaxy API Integration (Week 1)
1. Create `packages/static-data-service/` package
2. Implement Galaxy API fetcher (`/nfts` endpoint)
3. Parse and structure data (ships, items, metadata)
4. Store in S3 with versioning
5. CloudFront distribution for CDN

### Phase 2: Snapshot Lambda (Week 1)
1. Create Lambda function in `terraform/lambda.tf`
2. Schedule: EventBridge weekly trigger
3. Output: S3 bucket `{project}-static-data-{env}`
4. Notifications: SNS alert on failure

### Phase 3: MCP Server Integration (Week 2)
1. MCP tool: `getShipInfo(mint)` - fetches from S3 cache
2. MCP tool: `getFleetStatus(fleetId)` - real-time via SAGE SDK
3. MCP tool: `getCraftingRecipe(recipeId)` - fetches from S3 cache
4. Implement 30s in-memory cache for RPC deduplication

### Phase 4: Monitoring & Optimization (Week 2)
1. CloudWatch metrics: RPC call count, S3 cache hit rate
2. Cost dashboard: Daily spend on RPC vs snapshot
3. Alert: If RPC costs exceed $10/month

## Alternative Considered

### Alternative 1: Full Real-Time (No Caching)
**Rejected**: 10x more expensive ($45/month vs $4/month), slower responses

### Alternative 2: Community APIs/Indexers
**Deferred**: No reliable free tier found, official APIs sufficient

### Alternative 3: Build Custom Indexer
**Rejected**: High development cost, official APIs cover our needs

## References

- [Star Atlas Build Portal](https://build.staratlas.com/)
- [Galaxy API Docs](https://build.staratlas.com/dev-resources/apis-and-data/galaxy-api)
- [SAGE SDK npm](https://www.npmjs.com/package/@staratlas/sage)
- [Data Source SDK](https://build.staratlas.com/dev-resources/apis-and-data/data-source)
- [Crafting SDK](https://build.staratlas.com/dev-resources/apis-and-data/crafting)
- Issue #141: Star Atlas Data API Research

## Review & Approval

- [ ] Architecture review
- [ ] Cost validation
- [ ] Security review (S3 bucket policies)
- [ ] Implementation approval

---

**Next Steps**: Implement Phase 1 (Galaxy API Integration) in new package `packages/static-data-service/`
