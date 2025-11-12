# Star Atlas Data Inventory

**Purpose**: Complete inventory of Star Atlas data types needed for MCP Server tools
**Date**: 2025-11-12
**Related**: ADR-001 (Data Sourcing Strategy), Issue #141 (Research Spike)

---

## Overview

This document catalogs all Star Atlas data types required for the MCP Server's tools (fleet management, market analysis, crafting ROI calculators). Each data type includes:
- **Description**: What the data represents
- **Source**: Galaxy API, SAGE SDK, Crafting SDK, or Solana RPC
- **Update Frequency**: How often the data changes
- **Recommended Caching**: Based on ADR-001 strategy
- **Sample Structure**: TypeScript types or JSON examples

---

## 1. Ship & Item Metadata (Static)

### 1.1 Ship Blueprints

**Description**: Complete ship specifications (stats, class, tier, rarity)

**Source**: Galaxy API (`GET /nfts` filtered by `attributes.itemType == 'ship'`)

**Update Frequency**: Rarely (only on game updates/new ship releases)

**Recommended Caching**: Weekly S3 snapshot + CloudFront CDN

**Sample Structure**:
```typescript
interface Ship {
  _id: string;                    // MongoDB ObjectId
  name: string;                   // "Pearce X4"
  symbol: string;                 // "PEARCEX4"
  description: string;            // Ship lore/description
  mint: string;                   // Solana mint address
  network: "mainnet-beta";

  attributes: {
    class: "xxSmall" | "xSmall" | "small" | "medium" | "large" | "capital" | "commander" | "titan";
    itemType: "ship";
    tier: number;                 // 0-5
    rarity: "common" | "uncommon" | "rare" | "epic" | "legendary" | "anomaly";

    // Capacity slots
    crewSlots: number;
    componentSlots: number;
    moduleSlots: number;

    // Combat stats
    maxHealth: number;
    maxShield: number;
    armorLevel: number;

    // Cargo & fuel
    cargoCapacity: number;        // m³
    fuelCapacity: number;         // tons
    fuelBurnRate: number;         // tons/second at full thrust

    // Movement
    maxWarpSpeed: number;
    subWarpSpeed: number;
    planetExitFuelAmount: number;

    // Mining/Scanning
    miningRate?: number;
    scanningPowerLevel?: number;
  };

  // Marketplace data
  markets: Array<{
    id: string;                   // Market ID
    quotePair: "ATLAS" | "USDC";
    _id: string;
  }>;

  primarySales: Array<{
    listTimestamp: number;
    supply: number;
    price: number;
    currencySymbol: "ATLAS" | "USDC";
  }>;

  // Media assets
  image: string;                  // CDN URL to ship image
  media: {
    thumbnailUrl: string;
    qrInstagramUrl?: string;
    qrFacebookUrl?: string;
    sketchfabUrl?: string;
    audioUrl?: string;
  };
}
```

**MCP Tools Using This**:
- `getShipInfo(mint)` - Retrieve ship specs for fleet planning
- `compareShips(mint1, mint2)` - Compare ship capabilities
- `recommendShipForRole(role)` - AI ship recommendations

---

### 1.2 Resource & Commodity Items

**Description**: Crafting resources, food, fuel, ammo, components

**Source**: Galaxy API (`GET /nfts` filtered by `attributes.itemType != 'ship'`)

**Update Frequency**: Rarely (only on game updates)

**Recommended Caching**: Weekly S3 snapshot + CloudFront CDN

**Sample Structure**:
```typescript
interface Resource {
  _id: string;
  name: string;                   // "Hydrogen", "Food", "Ammunition"
  symbol: string;                 // "HYDROGEN"
  mint: string;

  attributes: {
    itemType: "resource" | "food" | "fuel" | "ammunition" | "component" | "collectible";
    category?: string;             // "Raw Material", "Refined Resource"

    // Resource-specific
    unitOfMeasure?: "kg" | "m³" | "unit";
    mass?: number;
    volume?: number;
  };

  // Marketplace
  markets: Array<{
    id: string;
    quotePair: "ATLAS" | "USDC";
  }>;

  tradeSettings?: {
    msrp?: number;
    vwap?: number;                // Volume-weighted average price
  };

  image: string;
}
```

**MCP Tools Using This**:
- `getResourcePrice(mint)` - Current market price
- `calculateCraftingCost(recipeId)` - Sum ingredient costs
- `findCheapestSupplier(resourceMint, starbaseId)` - Marketplace comparison

---

## 2. Fleet & Player Data (Real-Time)

### 2.1 Fleet Status

**Description**: Current fleet state (location, fuel, cargo, health)

**Source**: SAGE SDK + Solana RPC (`readFromRPC(Fleet, fleetId)`)

**Update Frequency**: Real-time (seconds)

**Recommended Caching**: 30s in-memory TTL (avoid duplicate queries in same session)

**Sample Structure**:
```typescript
interface FleetAccount {
  publicKey: PublicKey;           // Fleet PDA

  data: {
    gameId: PublicKey;            // SAGE game instance
    ownerProfile: PublicKey;      // Player profile PDA

    // Ship composition
    shipCounts: {
      [shipMint: string]: number; // Ship mint → quantity
    };

    // Current state
    state: {
      Idle?: { sector: PublicKey };
      MoveWarp?: { fromSector: PublicKey; toSector: PublicKey; warpStart: number; warpFinish: number };
      MineAsteroid?: { asteroid: PublicKey; start: number };
      StarbaseLoadingBay?: { starbase: PublicKey };
      Respawn?: {};
    };

    // Resources
    fuelCurrent: number;          // Current fuel (tons)
    fuelMax: number;              // Max capacity
    cargoStats: {
      cargoCapacity: number;      // m³
      cargoUsed: number;
    };

    // Combat stats
    stats: {
      health: number;
      shield: number;
      armor: number;
    };

    // Cargo hold
    cargoHold: PublicKey;         // CargoHold PDA (separate account)

    // Misc
    subwarpSpeed: number;
    warpSpeed: number;
    scannerPower: number;
    miningRate: number;
  };
}
```

**MCP Tools Using This**:
- `getFleetStatus(fleetId)` - Real-time fleet diagnostics
- `canFleetReach(fleetId, destinationSector)` - Fuel range check
- `estimateFleetArrival(fleetId)` - ETA calculation
- `alertLowFuel(fleetId)` - Proactive warnings

---

### 2.2 Cargo Hold Contents

**Description**: Items currently stored in fleet cargo

**Source**: SAGE SDK + Solana RPC (`readFromRPC(CargoHold, cargoHoldId)`)

**Update Frequency**: Real-time (changes on loading/unloading)

**Recommended Caching**: No cache (query on demand)

**Sample Structure**:
```typescript
interface CargoHoldAccount {
  publicKey: PublicKey;

  data: {
    inventory: Array<{
      mint: PublicKey;            // Resource mint
      amount: number;             // Quantity
    }>;

    capacityUsed: number;         // m³
    capacityMax: number;
  };
}
```

**MCP Tools Using This**:
- `getCargoInventory(fleetId)` - List cargo contents
- `calculateCargoValue(fleetId)` - Total cargo market value
- `optimizeCargoLoad(fleetId, destination)` - Load planning

---

### 2.3 Wallet Balances

**Description**: Player's ATLAS, USDC, resource token balances

**Source**: Solana RPC (`getTokenAccountsByOwner`)

**Update Frequency**: Real-time (blocks, ~400ms)

**Recommended Caching**: No cache (query on demand)

**Sample Structure**:
```typescript
interface WalletBalances {
  walletAddress: string;

  balances: {
    SOL: number;                  // Native SOL
    ATLAS: number;
    USDC: number;

    // Resource tokens
    [resourceMint: string]: number;
  };

  // Token accounts
  tokenAccounts: Array<{
    mint: string;
    address: string;              // Associated token account
    amount: number;
  }>;
}
```

**MCP Tools Using This**:
- `getWalletBalance(walletAddress)` - Check purchasing power
- `canAffordPurchase(walletAddress, itemMint, quantity)` - Affordability check

---

## 3. Game World Data (Static/Infrequent)

### 3.1 Starbases

**Description**: Starbase locations, facilities, services

**Source**: SAGE SDK + Solana RPC (fetch all Starbase accounts once)

**Update Frequency**: Rarely (new starbases added infrequently)

**Recommended Caching**: Weekly S3 snapshot

**Sample Structure**:
```typescript
interface StarbaseAccount {
  publicKey: PublicKey;

  data: {
    gameId: PublicKey;
    sector: PublicKey;            // Location in sector grid

    name: string;                 // "MUD Territory"
    level: number;

    // Facilities
    craftingFacilities: PublicKey[]; // CraftingFacility PDAs
    marketplaces: PublicKey[];

    // Services
    services: {
      refueling: boolean;
      repair: boolean;
      recruitment: boolean;
      trading: boolean;
      crafting: boolean;
    };

    // Coordinates (from sector account)
    coordinates: [number, number]; // [x, y]
  };
}
```

**MCP Tools Using This**:
- `findNearestStarbase(currentSector)` - Navigation helper
- `listStarbaseServices(starbaseId)` - Service directory
- `planRoute(fromSector, toSector)` - Multi-hop routing with refuel stops

---

### 3.2 Sectors

**Description**: Sector grid system (navigation coordinates)

**Source**: SAGE SDK + Solana RPC (fetch all Sector accounts once)

**Update Frequency**: Rarely

**Recommended Caching**: Weekly S3 snapshot

**Sample Structure**:
```typescript
interface SectorAccount {
  publicKey: PublicKey;

  data: {
    gameId: PublicKey;
    coordinates: [number, number]; // [x, y]

    // Sector contents
    planets: PublicKey[];
    asteroids: PublicKey[];
    starbases: PublicKey[];

    // Sector type
    sectorType: "safe" | "contested" | "hostile";
  };
}
```

**MCP Tools Using This**:
- `getSectorInfo(coordinates)` - Sector lookup
- `calculateDistance(sector1, sector2)` - Travel distance
- `findResourceNodes(resourceType)` - Mining location discovery

---

## 4. Crafting System (Static/Infrequent)

### 4.1 Crafting Recipes

**Description**: Recipe definitions (inputs → outputs)

**Source**: Crafting SDK + Solana RPC (`readAllFromRPC(Recipe, ...)`)

**Update Frequency**: Rarely (game updates)

**Recommended Caching**: Weekly S3 snapshot

**Sample Structure**:
```typescript
interface RecipeAccount {
  publicKey: PublicKey;

  data: {
    category: PublicKey;          // RecipeCategory PDA

    // Inputs
    ingredients: Array<{
      mint: PublicKey;            // Resource mint
      amount: number;
    }>;

    // Outputs
    outputs: Array<{
      mint: PublicKey;
      amount: number;
    }>;

    // Crafting requirements
    domain: "crafting" | "cooking" | "manufacturing";
    craftingDuration: number;     // Seconds
    craftingXpEarned: number;

    // Facility requirements
    minFacilityLevel: number;
  };
}
```

**MCP Tools Using This**:
- `getCraftingRecipe(recipeId)` - Recipe lookup
- `calculateCraftingROI(recipeId)` - Profit analysis
- `findOptimalCraftingChain(targetItem)` - Multi-step crafting optimization

---

### 4.2 Crafting Processes (Active)

**Description**: In-progress crafting jobs

**Source**: Crafting SDK + Solana RPC (`readFromRPC(CraftingProcess, processId)`)

**Update Frequency**: Real-time (status changes as crafting progresses)

**Recommended Caching**: No cache (query on demand)

**Sample Structure**:
```typescript
interface CraftingProcessAccount {
  publicKey: PublicKey;

  data: {
    craftingFacility: PublicKey;
    recipe: PublicKey;
    owner: PublicKey;             // Player profile

    // Status
    status: {
      Queued?: {};
      InProgress?: { startTime: number; completionTime: number };
      Completed?: {};
    };

    // Inputs consumed
    ingredientsConsumed: Array<{
      mint: PublicKey;
      amount: number;
    }>;

    // Outputs ready
    outputsProduced: Array<{
      mint: PublicKey;
      amount: number;
    }>;

    numCrew: number;              // Crew assigned to job
    xpEarned: number;
  };
}
```

**MCP Tools Using This**:
- `listActiveCrafting(walletAddress)` - Show all player's active crafts
- `estimateCraftingCompletion(processId)` - ETA for completion
- `claimCraftingOutput(processId)` - Claim finished items

---

## 5. Market Data (Infrequent)

### 5.1 Marketplace Listings

**Description**: Active buy/sell orders on Galactic Marketplace

**Source**: Galaxy API (`markets` field) OR Serum DEX on-chain data

**Update Frequency**: Infrequent (hourly changes)

**Recommended Caching**: 1-hour cache

**Sample Structure**:
```typescript
interface MarketListing {
  itemMint: string;
  quotePair: "ATLAS" | "USDC";

  // Order book
  bids: Array<{
    price: number;
    quantity: number;
  }>;

  asks: Array<{
    price: number;
    quantity: number;
  }>;

  // Market stats
  lastPrice: number;
  volume24h: number;
  priceChange24h: number;
}
```

**MCP Tools Using This**:
- `getMarketPrice(itemMint)` - Current best bid/ask
- `findArbitrage()` - Cross-market price differences
- `trackPriceHistory(itemMint, duration)` - Price charts

---

### 5.2 Token Prices (ATLAS/POLIS)

**Description**: ATLAS and POLIS token prices in USD

**Source**: CoinGecko API (already planned in original galactic-data package)

**Update Frequency**: Minutes

**Recommended Caching**: 5-minute cache (already planned)

**Sample Structure**:
```typescript
interface TokenPrice {
  symbol: "ATLAS" | "POLIS";
  priceUSD: number;
  priceChange24h: number;
  marketCap: number;
  volume24h: number;
  lastUpdated: number;          // Unix timestamp
}
```

**MCP Tools Using This**:
- `getATLASPrice()` - Current ATLAS/USD rate
- `convertToUSD(atlasAmount)` - Currency conversion

---

## 6. Player Profile Data (Real-Time)

### 6.1 Player Profile

**Description**: Player account metadata (XP, faction, stats)

**Source**: SAGE SDK + Solana RPC (`readFromRPC(Profile, profileId)`)

**Update Frequency**: Real-time (XP gains, faction changes)

**Recommended Caching**: No cache (query on demand)

**Sample Structure**:
```typescript
interface ProfileAccount {
  publicKey: PublicKey;

  data: {
    gameId: PublicKey;
    owner: PublicKey;             // Wallet address

    // Player identity
    playerName?: string;
    faction: "ONI" | "MUD" | "Ustur";

    // Experience
    xp: number;
    level: number;

    // Stats
    stats: {
      fleetCommandLevel: number;
      craftingLevel: number;
      miningLevel: number;
      pilotingLevel: number;
    };

    // Reputation
    reputation: {
      [faction: string]: number;
    };
  };
}
```

**MCP Tools Using This**:
- `getPlayerProfile(walletAddress)` - Player lookup
- `checkLevelRequirement(profileId, requiredLevel)` - Level gating

---

## 7. Data Size Estimates

| Data Type | Item Count | Size per Item | Total Size | Update Frequency |
|-----------|-----------|---------------|------------|------------------|
| Ship blueprints | ~200 | ~3 KB | ~600 KB | Weekly |
| Resource/item metadata | ~500 | ~2 KB | ~1 MB | Weekly |
| Crafting recipes | ~300 | ~1 KB | ~300 KB | Weekly |
| Starbases | ~50 | ~500 B | ~25 KB | Weekly |
| Sectors | ~10,000 | ~200 B | ~2 MB | Weekly |
| **Total Static Data** | - | - | **~4 MB** | **Weekly snapshot** |
| Fleet status (per query) | 1 | ~2 KB | ~2 KB | Real-time |
| Cargo hold (per query) | 1 | ~500 B | ~500 B | Real-time |
| Market listings (per item) | 1 | ~5 KB | ~5 KB | 1-hour cache |

**Conclusion**: Static data snapshot is <5 MB, easily cacheable in S3 with negligible storage costs.

---

## 8. Data Access Patterns

### MCP Server Data Flow

```
┌─────────────────┐
│   User Query    │ "What's my fleet status?"
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│          MCP Server (Agent Core)                │
├─────────────────────────────────────────────────┤
│  1. Parse intent: "fleet status"               │
│  2. Extract fleetId from context/wallet        │
│  3. Call: getFleetStatus(fleetId)              │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│         Data Layer (Hybrid Strategy)            │
├─────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌─────────────────────┐ │
│  │  S3/CloudFront   │  │   Solana RPC        │ │
│  │  (Static Cache)  │  │   (Real-Time)       │ │
│  ├──────────────────┤  ├─────────────────────┤ │
│  │ Ship metadata    │  │ Fleet status        │ │
│  │ Recipes          │  │ Cargo contents      │ │
│  │ Starbases        │  │ Wallet balances     │ │
│  │ Sectors          │  │ Crafting processes  │ │
│  └──────────────────┘  └─────────────────────┘ │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│         Response Enrichment                     │
├─────────────────────────────────────────────────┤
│  1. Fleet status (real-time RPC)               │
│  2. + Ship names (S3 cache)                    │
│  3. + Nearest starbase (S3 cache)              │
│  4. + Fuel range estimate (calculated)         │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Rich Response  │ "Your fleet is at sector [120,45],
│  to User        │  fuel: 80%, nearest refuel: MUD HQ"
└─────────────────┘
```

### Example: "Calculate crafting ROI for Titanium"

```typescript
// MCP tool: calculateCraftingROI(recipeId)

async function calculateCraftingROI(recipeId: string) {
  // 1. Get recipe (S3 cache)
  const recipe = await s3.getObject('staratlas-static-data/v1/recipes.json');
  const recipeData = JSON.parse(recipe).find(r => r.id === recipeId);

  // 2. Get ingredient prices (Galaxy API markets + 1hr cache)
  const ingredientCosts = await Promise.all(
    recipeData.ingredients.map(async (ing) => {
      const price = await getMarketPrice(ing.mint); // 1hr cache
      return price * ing.amount;
    })
  );

  // 3. Get output price (Galaxy API markets + 1hr cache)
  const outputPrice = await getMarketPrice(recipeData.outputs[0].mint);
  const revenue = outputPrice * recipeData.outputs[0].amount;

  // 4. Calculate ROI
  const totalCost = ingredientCosts.reduce((sum, c) => sum + c, 0);
  const profit = revenue - totalCost;
  const roi = (profit / totalCost) * 100;

  return {
    recipe: recipeData.name,
    cost: totalCost,
    revenue,
    profit,
    roi: `${roi.toFixed(2)}%`,
    breakdownIngredients: ingredientCosts,
  };
}
```

---

## 9. Data Update Triggers

### Weekly Snapshot Lambda (EventBridge Schedule)

**Trigger**: Every Sunday at 00:00 UTC

**Actions**:
1. Fetch Galaxy API `/nfts` endpoint
2. Fetch all Starbase accounts (SAGE SDK)
3. Fetch all Sector accounts (SAGE SDK)
4. Fetch all Recipe accounts (Crafting SDK)
5. Structure data as JSON
6. Upload to S3 with versioning: `staratlas-static-data/v{timestamp}/`
7. Update CloudFront cache invalidation
8. Send SNS notification on success/failure

**Cost**: $0 (AWS Free Tier: 1M Lambda invocations/month)

---

### Market Data Cache (Lambda cron)

**Trigger**: Every hour

**Actions**:
1. Fetch Galaxy API market listings (if available)
2. Cache in ElastiCache or S3
3. Expire after 1 hour

**Cost**: $0 (Free Tier) or <$1/month for ElastiCache t4g.micro

---

### Real-Time Queries (On-Demand)

**Trigger**: MCP tool invocation by user

**Actions**:
1. Check 30s in-memory cache (LRU)
2. If miss: Query Solana RPC via SAGE SDK
3. Cache result for 30s
4. Return to user

**Cost**: ~$3/month (100 RPC queries/day × $0.001)

---

## 10. MCP Tools → Data Mapping

| MCP Tool | Data Sources | Caching Strategy |
|----------|-------------|------------------|
| `getShipInfo(mint)` | Galaxy API (S3 cache) | Weekly snapshot |
| `getFleetStatus(fleetId)` | SAGE SDK + RPC | 30s in-memory |
| `getCargoInventory(fleetId)` | SAGE SDK + RPC | No cache |
| `getCraftingRecipe(recipeId)` | Crafting SDK (S3 cache) | Weekly snapshot |
| `calculateCraftingROI(recipeId)` | Recipes (S3) + Markets (1hr) | Hybrid |
| `getMarketPrice(itemMint)` | Galaxy API markets | 1-hour cache |
| `findNearestStarbase(sector)` | Starbases (S3 cache) | Weekly snapshot |
| `planRoute(from, to)` | Sectors (S3 cache) | Weekly snapshot |
| `getWalletBalance(wallet)` | Solana RPC | No cache |
| `listActiveCrafting(wallet)` | Crafting SDK + RPC | No cache |

---

## 11. Unknown/TBD

### Crafting SDK Documentation Incomplete

**Issue**: Crafting SDK npm page shows "Examples - Coming Soon..."

**Workaround Options**:
1. **Explore program accounts directly**: Use Solana RPC `getProgramAccounts` to fetch Recipe accounts
2. **Community examples**: Check Star Atlas Discord or GitHub for unofficial examples
3. **Wait for official docs**: Monitor Star Atlas Build Portal for updates

**Decision**: Defer crafting implementation to Phase 3 (Week 2). Prioritize Galaxy API and fleet management first.

---

## References

- [Galaxy API Docs](https://build.staratlas.com/dev-resources/apis-and-data/galaxy-api)
- [SAGE SDK npm](https://www.npmjs.com/package/@staratlas/sage)
- [Crafting SDK](https://build.staratlas.com/dev-resources/apis-and-data/crafting)
- [Data Source SDK](https://build.staratlas.com/dev-resources/apis-and-data/data-source)
- ADR-001: Star Atlas Data Sourcing Strategy

---

**Last Updated**: 2025-11-12
