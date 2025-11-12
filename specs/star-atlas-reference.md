# Star Atlas Reference & Learnings

> **Purpose**: Living document for Star Atlas API references, undocumented behaviors, and team learnings
> **Lifecycle**: Living (update as we discover new API capabilities or workarounds)
> **Last Updated**: 2025-11-12

## 📍 Official Documentation Quick Links

### Main Documentation Hub
- **Build Portal**: https://build.staratlas.com/
- **Dev Resources**: https://build.staratlas.com/dev-resources/apis-and-data
- **GitHub Organization**: https://github.com/staratlasmeta

### Core APIs

#### SAGE (Strategic Game Mechanics)
- **Documentation**: https://build.staratlas.com/dev-resources/apis-and-data/sage
- **NPM Package**: `@staratlas/sage` (v1.8.10 as of 2025-11-12)
- **Repository**: github.com/staratlasmeta/star-atlas-programs
- **Install**: `pnpm add @staratlas/sage`

**What it provides:**
- Fleet management (position, status, inventory)
- Crew management
- Cargo operations
- Player profiles and progression
- Core game mechanics and state

**Key Account Types:**
- `Sector`, `Star`, `Planet`
- `Fleet`, `Ship`, `FleetShips`
- `StarbasePlayer`
- See package documentation for complete list

#### Galactic Marketplace
- **Documentation**: https://build.staratlas.com/dev-resources/on-chain-game-systems/galactic-marketplace
- **NPM Package**: `@staratlas/factory` (for transaction construction)
- **Install**: `pnpm add @staratlas/factory`

**What it provides:**
- **GmOrderbookService**: Real-time list of all open orders
- **GmClientService**: Order data fetching with price information

**Key Concepts:**
- Decentralized trading protocol on Solana
- Escrow system for NFTs/SFTs (itemMint) and currency (quoteMint)
- Order book with bid/ask spreads
- Price field in base units, `uiPrice` for decimal-adjusted values

#### Galaxy API
- **Documentation**: https://build.staratlas.com/dev-resources/apis-and-data/galaxy-api
- **Base URL**: https://galaxy.staratlas.com

**Endpoints:**
- `/items` - Asset catalog and metadata
- `/tokens` - ATLAS/POLIS and other token data
- `/showroom` - Display/showcase functionality

#### Factory SDK
- **Documentation**: https://build.staratlas.com/apis-and-data/factory
- **NPM Package**: `@staratlas/factory`
- **Repository**: https://github.com/staratlasmeta/factory
- **Purpose**: Transaction construction helper for Solana on-chain programs

### Additional Game Systems
- **Cargo API**: Inventory and logistics management
- **Crafting API**: Item creation and manufacturing
- **Profile Faction**: Player faction affiliation
- **Atlas Prime**: Premium/governance token interactions
- **Fleet Rentals**: Vehicle leasing mechanics
- **Claim Stakes**: Land claim and territorial systems

---

## 🔧 Discovered Behaviors & Undocumented Features

> **Note**: This section captures behaviors not explicitly documented in official docs.
> Always verify against latest API version as these may be subject to change.

### SAGE API

#### Account Refresh Patterns
*To be documented as we discover refresh timing and state synchronization*

**Observed behavior:**
- [TBD - add observations here]

**Workaround:**
- [TBD - add solutions here]

#### WebSocket Subscription Quirks
*Document any issues with real-time account monitoring*

**Known issues:**
- [TBD - add issues here]

**Solution:**
- [TBD - add solutions here]

### Galactic Marketplace

#### Order Book Latency
*Document observed delays between blockchain state and API cache*

**Observations:**
- [TBD - measure latency in production]

**Mitigation:**
- [TBD - add caching strategies]

#### Price Calculation Edge Cases
*Document cases where `price` vs `uiPrice` cause confusion*

**Edge cases:**
- [TBD - document token decimal mismatches]

---

## 🎯 Integration Patterns & Best Practices

### RPC Provider Selection

**Recommended providers for production:**
1. **Helius** - Reliable, enhanced APIs, WebSocket support
2. **QuickNode** - Fast, global CDN
3. **Public RPC** - Development only (rate limited)

**Configuration:**
```typescript
import { Connection } from '@solana/web3.js';

const connection = new Connection(
  process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com',
  {
    wsEndpoint: process.env.SOLANA_WS_URL,
    commitment: 'confirmed'
  }
);
```

### SAGE Client Initialization

**Pattern:**
```typescript
import { getProgram } from '@staratlas/sage';
import { AnchorProvider } from '@coral-xyz/anchor';
import { Connection, Keypair } from '@solana/web3.js';

// Setup connection
const connection = new Connection(rpcUrl, 'confirmed');

// Create provider (read-only, no wallet needed for queries)
const provider = new AnchorProvider(
  connection,
  {} as any, // No wallet for read operations
  { commitment: 'confirmed' }
);

// Get SAGE program
const program = getProgram(provider);

// Query fleet account
const fleetAccount = await program.account.fleet.fetch(fleetPublicKey);
```

### Marketplace Order Queries

**Pattern:**
```typescript
import { GmClientService } from '@staratlas/factory';

const gmClient = new GmClientService();

// Get all orders for an asset
const orders = await gmClient.getOrdersByAsset(assetMint);

// Filter buy orders
const buyOrders = orders.filter(order => order.orderType === 'buy');

// Sort by price (best first)
buyOrders.sort((a, b) => b.uiPrice - a.uiPrice);
```

---

## 🚧 Known Limitations & Workarounds

### SAGE API Limitations

**Rate Limits:**
- Public RPC: ~10 req/s
- Helius Free: ~100 req/s
- Helius Premium: Higher limits (check current plan)

**Workaround:**
- Implement request batching
- Use WebSocket subscriptions for real-time updates (fewer RPC calls)
- Cache frequently accessed accounts locally

### Marketplace Data Freshness

**Issue:** GmOrderbookService cache may lag blockchain state by 1-5 seconds

**Workaround:**
- For critical operations, verify against blockchain directly
- Use WebSocket subscriptions for order placement confirmations
- Implement optimistic UI updates with rollback on error

### Galaxy API Response Times

**Issue:** Some endpoints can be slow (>1s response time)

**Workaround:**
- Cache responses locally (items/tokens change infrequently)
- Implement stale-while-revalidate pattern
- Use background refresh for non-critical data

---

## 📊 Data Models & Schemas

### Fleet Account Structure

```typescript
interface FleetAccount {
  version: number;
  gameId: PublicKey;
  ownerProfile: PublicKey;
  fleetLabel: string;
  shipCounts: ShipCounts;
  warpCooldownExpiresAt: BN;
  scanCooldownExpiresAt: BN;
  stats: FleetStats;
  fuelTank: FuelTank;
  cargoHold: CargoHold;
  ammoBank: AmmoBank;
}

interface FleetStats {
  cargoCapacity: number;
  fuelCapacity: number;
  ammoCapacity: number;
  health: number;
  movementSpeed: number;
  warpSpeed: number;
}
```

### Marketplace Order Structure

```typescript
interface Order {
  id: string;
  orderType: 'buy' | 'sell';
  itemMint: PublicKey;
  quoteMint: PublicKey;
  price: BN;           // Base units
  uiPrice: number;     // Decimal-adjusted
  quantity: BN;
  seller: PublicKey;
  buyer?: PublicKey;
  createdAt: number;
  expiresAt?: number;
}
```

---

## 🧪 Testing Strategies

### Devnet Testing

**Solana Devnet:**
- RPC: https://api.devnet.solana.com
- Faucet: https://faucet.solana.com/

**Note:** Star Atlas programs may not be deployed on devnet. Use localnet or mainnet-fork for testing.

### Mainnet-Fork Testing

**Using Solana Test Validator:**
```bash
# Clone mainnet state for testing
solana-test-validator \
  --url https://api.mainnet-beta.solana.com \
  --clone <SAGE_PROGRAM_ID> \
  --clone <MARKETPLACE_PROGRAM_ID>
```

### Mock Data Generation

**Fleet Mock:**
```typescript
const mockFleet = {
  publicKey: new PublicKey('...'),
  label: 'Test Fleet Alpha',
  sector: [0, 0],
  ships: 5,
  fuel: 75,
  health: 95,
  cargoCapacity: 1000,
  cargoUsed: 250
};
```

---

## 🔄 z.ink Migration Notes

> Star Atlas is migrating to z.ink Layer 1 (December 2025)

**What we know:**
- SVM-compatible (Solana Virtual Machine)
- Existing Solana tooling will largely work
- New features: zProfiles, dApp permissioning

**What to monitor:**
- RPC endpoint changes
- Program ID updates
- New SDK releases for z.ink-specific features

**Migration strategy:**
- Maintain dual-chain support during transition
- Abstract RPC connections for easy switching
- Test thoroughly on z.ink testnet before launch

---

## 📝 Team Learnings

> This section captures insights from actual implementation that aren't in official docs.
> Add dated entries as we discover new patterns or solutions.

### 2025-11-12: Project Initialization Learnings

**Discovery:** Star Atlas has excellent TypeScript support with `@staratlas/sage` and `@staratlas/factory` packages.

**Insight:** Unlike some blockchain projects, Star Atlas provides well-typed interfaces for all on-chain accounts, making TypeScript development smooth.

**Action:** Prioritize using official NPM packages over manual program interaction.

---

### [Template for New Learnings]

**Date:** YYYY-MM-DD

**Discovery:** [What we found]

**Context:** [Why this matters]

**Impact:** [How it affects our implementation]

**Solution/Workaround:** [What we did about it]

**References:**
- [Link to related code]
- [Link to relevant docs]

---

## 🔗 Community Resources

### Developer Communities
- **Star Atlas Discord**: discord.gg/staratlas (check #dev channel)
- **GitHub Discussions**: github.com/staratlasmeta
- **Star Atlas Builders**: Community showcases and examples

### Useful Third-Party Tools
- **atlas.eveeye.com**: Excellent data visualization for Star Atlas
- **galactic-prices**: Price tracking tool (our galactic-data package is based on this)

---

## 📚 Related Internal Documents

- `ARCHITECTURE.md` - System architecture and tech stack
- `CONTRIBUTING.md` - How to contribute API discoveries
- `STATUS.md` - Current implementation status and issues

---

**Maintenance Notes:**
- Update this document whenever you discover undocumented API behavior
- Add dated entries to Team Learnings section for knowledge sharing
- Keep Quick Links updated with latest package versions
- Review and clean up outdated workarounds as APIs stabilize
