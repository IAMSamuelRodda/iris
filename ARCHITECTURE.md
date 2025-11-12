# Star Atlas Agent - Architecture Documentation

## System Architecture

### High-Level Overview

Star Atlas Agent follows a voice-first, multi-tier architecture optimized for real-time blockchain monitoring and natural language interaction:

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Web App (React + Vite + Three.js)              │  │
│  │  - Voice interface (push-to-talk / wake word)         │  │
│  │  - 3D star map visualization                          │  │
│  │  - Real-time market dashboard                         │  │
│  │  - Fleet management UI                                │  │
│  └────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │ WebRTC + WebSocket
┌─────────────────────────┼──────────────────────────────────┐
│                 Voice Interaction Layer                     │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │            Voice Service (Dedicated)                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ Whisper  │  │ WebRTC   │  │  ElevenLabs TTS  │  │  │
│  │  │   STT    │→ │ Signaling│ ←│   Voice Synth    │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │ Text (processed commands)
┌─────────────────────────┼──────────────────────────────────┐
│                  Agent Intelligence Layer                   │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │    Agent Orchestrator (Claude Agent SDK)             │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │  │   Market    │  │   Fleet     │  │  Craft     │  │  │
│  │  │  Analyst    │  │  Commander  │  │ Optimizer  │  │  │
│  │  │  (Agent)    │  │   (Agent)   │  │  (Agent)   │  │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  └────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │ MCP Protocol (JSON-RPC)
┌─────────────────────────┼──────────────────────────────────┐
│                  Integration Layer                          │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │    MCP Server (Star Atlas + Solana Integration)      │  │
│  │                                                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐   │  │
│  │  │  SAGE    │  │ Galactic │  │  Solana Web3.js │   │  │
│  │  │  Client  │  │ Mkt API  │  │  (Blockchain)   │   │  │
│  │  └──────────┘  └──────────┘  └─────────────────┘   │  │
│  └────────────────────┬─────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │ REST + WebSocket
┌─────────────────────────┼──────────────────────────────────┐
│              External Services & Blockchain                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │  Star Atlas   │  │    Solana     │  │    z.ink     │  │
│  │     APIs      │  │   Blockchain  │  │  (Future L1) │  │
│  │               │  │               │  │              │  │
│  │ - SAGE        │  │ - RPC Nodes   │  │ - zProfiles  │  │
│  │ - Marketplace │  │ - WebSockets  │  │ - dApp Perms │  │
│  │ - Galaxy      │  │ - Programs    │  │              │  │
│  └───────────────┘  └───────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 Data & Services Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Firestore   │  │   Firebase   │  │   Galactic   │     │
│  │   Database   │  │   Functions  │  │     Data     │     │
│  │              │  │              │  │   (Price)    │     │
│  │ - Sessions   │  │ - Webhooks   │  │              │     │
│  │ - Alerts     │  │ - Scheduled  │  │ - Historical │     │
│  │ - User prefs │  │   jobs       │  │   prices     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Web Application

**Technology:** React + Vite + Three.js + TypeScript

**Responsibilities:**
- Voice interface (microphone input, audio playback)
- Real-time market data visualization
- 3D star map for fleet positioning
- Fleet management dashboard
- Crafting calculator interface

**Key Features:**

**Voice Interface:**
- Push-to-talk button with visual feedback
- Wake word detection ("Hey Cortana")
- Voice activity detection (VAD)
- Audio playback for agent responses
- Waveform visualization during recording

**3D Visualization:**
- Three.js for star map rendering
- Fleet positions and movement paths
- Sector information overlays
- Interactive camera controls

**Real-Time Dashboard:**
- WebSocket connection for live updates
- Price charts (TradingView-like)
- Fleet status cards
- Alert notifications

**Directory Structure:**
```
web-app/
├── public/
│   ├── manifest.json          # PWA config
│   ├── service-worker.js      # Offline support
│   └── icons/
├── src/
│   ├── components/
│   │   ├── chat/              # Text chat interface
│   │   ├── voice/             # Voice controls
│   │   │   ├── PushToTalk.tsx
│   │   │   ├── WaveformViz.tsx
│   │   │   └── VoiceSettings.tsx
│   │   ├── market/            # Market dashboard
│   │   │   ├── PriceChart.tsx
│   │   │   ├── TrendingAssets.tsx
│   │   │   └── AlertManager.tsx
│   │   ├── fleet/             # Fleet management
│   │   │   ├── FleetCard.tsx
│   │   │   ├── FleetCommands.tsx
│   │   │   └── ShipDetails.tsx
│   │   ├── crafting/          # Crafting calculator
│   │   │   ├── RecipeSearch.tsx
│   │   │   ├── CostAnalysis.tsx
│   │   │   └── MaterialList.tsx
│   │   └── map/               # 3D star map
│   │       ├── StarMap.tsx (Three.js)
│   │       ├── FleetMarkers.tsx
│   │       └── SectorInfo.tsx
│   ├── services/
│   │   ├── api.ts             # Backend API client
│   │   ├── voice.ts           # Voice service client
│   │   ├── wallet.ts          # Solana wallet (Phantom/Solflare)
│   │   └── websocket.ts       # Real-time connection
│   ├── stores/                # Zustand state management
│   │   ├── market.ts          # Market data
│   │   ├── fleet.ts           # Fleet state
│   │   ├── voice.ts           # Voice session
│   │   └── wallet.ts          # Wallet connection
│   └── hooks/
│       ├── useVoice.ts        # Voice interaction hook
│       ├── useWallet.ts       # Wallet connection hook
│       └── useWebSocket.ts    # Real-time updates hook
└── vite.config.ts
```

### 2. Voice Service (Dedicated Microservice)

**Technology:** Node.js + TypeScript + WebRTC

**Responsibilities:**
- Audio stream handling
- Speech-to-text processing
- Text-to-speech generation
- WebRTC signaling

**Why Separate Service:**
- Lower latency (dedicated resources)
- Independent scaling
- Specialized audio processing
- Isolate heavy API calls (Whisper, ElevenLabs)

**Architecture:**

```typescript
// Voice Pipeline
Audio Input (WebRTC) → VAD → STT (Whisper) → Text
                                               ↓
                                         Agent Processing
                                               ↓
Text Response ← TTS (ElevenLabs) ← Voice Handler
       ↓
Audio Output (WebRTC)
```

**Directory Structure:**
```
voice-service/
└── src/
    ├── server.ts              # Express + WebRTC server
    ├── stt/
    │   ├── whisper.ts         # OpenAI Whisper API
    │   └── deepgram.ts        # Alternative STT
    ├── tts/
    │   ├── elevenlabs.ts      # ElevenLabs API
    │   └── coqui.ts           # Local TTS option
    ├── webrtc/
    │   ├── signaling.ts       # WebRTC signaling
    │   ├── peer-manager.ts    # Connection management
    │   └── audio-processor.ts # Audio stream handling
    ├── vad/
    │   └── voice-detector.ts  # Voice Activity Detection
    └── pipeline.ts            # Orchestrates STT → TTS flow
```

**WebRTC Flow:**

1. **Connection Setup:**
   ```
   Browser → Signaling Server: Offer (SDP)
   Signaling Server → Browser: Answer (SDP)
   ICE Candidate Exchange (STUN/TURN)
   Peer Connection Established
   ```

2. **Audio Streaming:**
   ```
   Browser captures audio → RTP packets → Voice Service
   Voice Service processes → RTP packets → Browser plays audio
   ```

3. **VAD (Voice Activity Detection):**
   - Monitors audio energy levels
   - Detects speech start/end
   - Triggers STT processing
   - Reduces unnecessary API calls

**Latency Optimization:**
- Streaming STT (partial results)
- Streaming TTS (audio chunks)
- WebRTC audio codec: Opus (low latency)
- Edge deployment (Cloud Run)

### 3. Agent Core (Claude Agent SDK)

**Technology:** Claude Agent SDK + TypeScript

**Responsibilities:**
- Conversation orchestration
- Task decomposition
- Sub-agent coordination
- Context management
- Voice-optimized formatting

**Architecture Pattern:** Orchestrator-Worker

**Main Agent (Orchestrator):**
- Maintains conversation context
- Determines user intent
- Delegates to specialized sub-agents
- Aggregates results
- Formats responses (text vs. voice)

**Sub-Agents (Specialized Workers):**

1. **Market Analyst Agent**
   - Price analysis
   - Trend identification
   - Trading recommendations
   - Alert management

2. **Fleet Commander Agent**
   - Fleet status queries
   - Movement commands
   - Resource management
   - Mission planning

3. **Craft Optimizer Agent**
   - Recipe search
   - Cost calculation
   - Material optimization
   - Production planning

4. **Voice Handler Agent**
   - Voice command parsing
   - Response formatting for TTS
   - Clarification questions
   - Context-aware responses

**Directory Structure:**
```
agent-core/
└── src/
    ├── agent.ts               # Main orchestrator
    ├── session.ts             # Session management
    ├── context.ts             # Context tracking
    ├── voice-controller.ts    # Voice interaction logic
    ├── permissions.ts         # Tool permissions
    └── subagents/
        ├── market-analyst.ts
        ├── fleet-commander.ts
        ├── craft-optimizer.ts
        └── voice-handler.ts
```

**Voice-Optimized Responses:**

```typescript
// Text response
"Fleet Alpha is currently in Sector 42 with 5 ships. Fuel at 78%, health at 95%."

// Voice response (more natural)
"Your Fleet Alpha is doing well in Sector 42. You've got 5 ships there,
fuel's at seventy-eight percent, and everyone's healthy at ninety-five percent."
```

**Context Management:**

```typescript
interface ConversationContext {
  userId: string;
  sessionId: string;
  mode: 'text' | 'voice';
  history: Message[];
  userPreferences: {
    voiceEnabled: boolean;
    selectedVoice: string;
    alertThresholds: Record<string, number>;
  };
  activeFleets: Fleet[];
  watchedAssets: Asset[];
}
```

### 4. MCP Server (Star Atlas + Solana Integration)

**Technology:** @modelcontextprotocol/sdk + @staratlas/sage + @solana/web3.js

**Responsibilities:**
- Star Atlas API integration
- Solana blockchain queries
- Real-time blockchain monitoring
- Tool definitions for agents

**Tool Categories:**

**Marketplace Tools:**
```typescript
@tool("get_asset_price")
async getAssetPrice(assetId: string): Promise<PriceData> {
  // Query galactic-data or marketplace API
  return { price, change24h, volume, lastUpdated };
}

@tool("track_price_history")
async trackPriceHistory(assetId: string, range: TimeRange): Promise<PricePoint[]> {
  // Retrieve from Firestore (galactic-data)
  return historicalPrices;
}

@tool("set_price_alert")
async setPriceAlert(assetId: string, threshold: number, direction: 'above' | 'below'): Promise<Alert> {
  // Store in Firestore, trigger via Cloud Function
  return alert;
}
```

**Fleet Management Tools (SAGE API):**
```typescript
@tool("get_fleet_status")
async getFleetStatus(fleetId: PublicKey): Promise<FleetStatus> {
  // Query SAGE program account
  const fleetAccount = await sageClient.getFleet(fleetId);
  return parseFleetStatus(fleetAccount);
}

@tool("move_fleet")
async moveFleet(fleetId: PublicKey, destination: Coordinates): Promise<Transaction> {
  // Build Solana transaction for fleet movement
  const tx = await sageClient.buildMoveFleetTx(fleetId, destination);
  // Return for user approval (don't auto-sign)
  return { transaction: tx, requiresApproval: true };
}

@tool("get_fleet_inventory")
async getFleetInventory(fleetId: PublicKey): Promise<Inventory> {
  // Query cargo account
  const cargoAccount = await cargoClient.getInventory(fleetId);
  return parseInventory(cargoAccount);
}
```

**Crafting Tools:**
```typescript
@tool("get_crafting_recipes")
async getCraftingRecipes(query?: string): Promise<Recipe[]> {
  // Fetch from Star Atlas API
  const recipes = await galaxyApi.getCraftingRecipes();
  return query ? filterRecipes(recipes, query) : recipes;
}

@tool("calculate_crafting_cost")
async calculateCraftingCost(recipeId: string): Promise<CostBreakdown> {
  const recipe = await getCraftingRecipe(recipeId);
  const materialPrices = await Promise.all(
    recipe.materials.map(m => getAssetPrice(m.assetId))
  );
  return {
    totalCost: sum(materialPrices),
    breakdown: materialPrices,
    alternatives: findCheaperAlternatives(recipe)
  };
}
```

**Blockchain Query Tools:**
```typescript
@tool("get_wallet_balance")
async getWalletBalance(address: PublicKey): Promise<Balance> {
  const balance = await connection.getBalance(address);
  const tokenAccounts = await connection.getTokenAccountsByOwner(address, {
    programId: TOKEN_PROGRAM_ID
  });
  return {
    sol: balance / LAMPORTS_PER_SOL,
    tokens: parseTokenAccounts(tokenAccounts),
    nfts: await getNFTs(address)
  };
}

@tool("monitor_address")
async monitorAddress(address: PublicKey): Promise<SubscriptionId> {
  // Set up WebSocket subscription
  const subscriptionId = connection.onAccountChange(
    address,
    (accountInfo) => {
      // Emit event to agent
      eventEmitter.emit('account_change', { address, accountInfo });
    }
  );
  return subscriptionId;
}
```

**Directory Structure:**
```
mcp-staratlas-server/
└── src/
    ├── server.ts              # MCP server entry
    ├── tools/
    │   ├── marketplace.ts     # Market data tools
    │   ├── sage.ts            # SAGE game mechanics
    │   ├── fleet.ts           # Fleet management
    │   ├── crafting.ts        # Crafting tools
    │   ├── profile.ts         # Player profile
    │   └── blockchain.ts      # Solana queries
    ├── clients/
    │   ├── galaxy-api.ts      # Galaxy API wrapper
    │   ├── sage-client.ts     # SAGE program client
    │   └── solana-client.ts   # Web3.js wrapper
    ├── websockets/
    │   ├── solana-monitor.ts  # Account monitoring
    │   └── event-emitter.ts   # Event distribution
    └── schemas/
        └── staratlas-schemas.ts # Zod validation
```

**Real-Time Blockchain Monitoring:**

```typescript
// WebSocket subscription for account changes
class SolanaMonitor {
  private connection: Connection;
  private subscriptions: Map<string, number>;

  async subscribeToAccount(address: PublicKey): Promise<number> {
    const subscriptionId = this.connection.onAccountChange(
      address,
      (accountInfo, context) => {
        this.handleAccountUpdate(address, accountInfo, context);
      },
      'confirmed'
    );

    this.subscriptions.set(address.toBase58(), subscriptionId);
    return subscriptionId;
  }

  async subscribeToProgram(programId: PublicKey): Promise<number> {
    const subscriptionId = this.connection.onProgramAccountChange(
      programId,
      (keyedAccountInfo, context) => {
        this.handleProgramUpdate(keyedAccountInfo, context);
      },
      'confirmed'
    );

    return subscriptionId;
  }

  private handleAccountUpdate(address: PublicKey, accountInfo: AccountInfo, context: Context) {
    // Parse account data
    // Emit event to agent
    // Trigger alerts if thresholds met
  }
}
```

### 5. Galactic Data (Existing Price Monitoring)

**Status:** Preserved and extended from original repo

**Technology:** TypeScript + Firebase + Docker

**Responsibilities:**
- Historical price tracking
- Price aggregation
- Data storage in Firestore

**Integration Strategy:**

1. **Preserve existing architecture:**
   - Keep Firebase/Firestore setup
   - Maintain Docker containerization
   - Continue using Cloud Build CI/CD

2. **Extend with MCP integration:**
   ```typescript
   // Wrap existing price queries as MCP tools
   @tool("get_price_history")
   async getPriceHistory(assetId: string, range: TimeRange) {
     return galacticData.queryPriceHistory(assetId, range);
   }
   ```

3. **Add real-time updates:**
   - WebSocket connection to Firestore
   - Push price updates to connected clients

**Directory Structure (from cloned repo):**
```
galactic-data/
├── src/                       # TypeScript source
├── scripts/                   # Utility scripts
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local dev setup
├── firebase.json              # Firebase config
├── firestore.indexes.json     # DB indexes
├── firestore.rules            # Security rules
└── package.json
```

### 6. Backend Services (Firebase Functions)

**Technology:** Firebase Functions + TypeScript

**Responsibilities:**
- Scheduled tasks
- Webhook handlers
- Data processing
- Alert delivery

**Function Categories:**

**Agent Functions:**
```typescript
// functions/agent/chat.ts
export const chat = onRequest(async (req, res) => {
  const { message, sessionId, mode } = req.body;

  // Load session context
  const session = await getSession(sessionId);

  // Process with agent
  const response = await agent.process(message, session, mode);

  // Save session
  await saveSession(sessionId, response.newContext);

  res.json({ response: response.text, audio: response.audioUrl });
});

// functions/agent/voice.ts
export const voiceSession = onRequest(async (req, res) => {
  // WebSocket upgrade for voice session
  const sessionId = req.query.sessionId;
  // Handle voice streaming
});
```

**Webhook Functions:**
```typescript
// functions/webhooks/blockchain.ts
export const blockchainWebhook = onRequest(async (req, res) => {
  const { address, transaction } = req.body;

  // Process blockchain event
  // Check for user alerts
  const alerts = await checkAlerts(address, transaction);

  // Notify users
  await sendNotifications(alerts);

  res.json({ success: true });
});
```

**Scheduled Functions:**
```typescript
// functions/scheduled/price-sync.ts
export const priceSync = onSchedule('every 5 minutes', async (context) => {
  // Refresh price data from marketplace
  const assets = await getTrackedAssets();
  await Promise.all(assets.map(updateAssetPrice));
});

// functions/scheduled/alert-checker.ts
export const alertChecker = onSchedule('every 1 minute', async (context) => {
  // Check all active price alerts
  const alerts = await getActiveAlerts();
  const triggered = await checkAlertConditions(alerts);
  await notifyTriggeredAlerts(triggered);
});

// functions/scheduled/session-cleanup.ts
export const sessionCleanup = onSchedule('every 24 hours', async (context) => {
  // Remove expired sessions
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
  await deleteOldSessions(cutoff);
});
```

### 7. Data Layer (Firestore)

**Database Schema:**

**Collections:**

1. **users**
   ```typescript
   {
     uid: string;
     walletAddress?: string;
     preferences: {
       voiceEnabled: boolean;
       selectedVoice: string;
       alertsEnabled: boolean;
     };
     createdAt: Timestamp;
     lastLoginAt: Timestamp;
   }
   ```

2. **sessions**
   ```typescript
   {
     id: string;
     userId: string;
     mode: 'text' | 'voice';
     context: {
       history: Message[];
       activeFleets: string[];
       watchedAssets: string[];
     };
     createdAt: Timestamp;
     updatedAt: Timestamp;
     expiresAt: Timestamp;
   }
   ```

3. **alerts**
   ```typescript
   {
     id: string;
     userId: string;
     type: 'price' | 'fleet' | 'transaction';
     conditions: {
       assetId?: string;
       threshold?: number;
       direction?: 'above' | 'below';
     };
     active: boolean;
     lastTriggered?: Timestamp;
     createdAt: Timestamp;
   }
   ```

4. **prices** (from galactic-data)
   ```typescript
   {
     assetId: string;
     timestamp: Timestamp;
     price: number;
     volume: number;
     source: string;
   }
   ```

5. **fleets** (cached state)
   ```typescript
   {
     id: string;
     userId: string;
     publicKey: string;
     name: string;
     sector: number;
     ships: number;
     fuel: number;
     health: number;
     status: string;
     lastUpdated: Timestamp;
   }
   ```

**Indexes:**

```javascript
// firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "prices",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "assetId", "order": "ASCENDING" },
        { "fieldPath": "timestamp", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "alerts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "userId", "order": "ASCENDING" },
        { "fieldPath": "active", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    }
  ]
}
```

## Data Flow

### Voice Command Flow

```
1. User: [Speaking] "What's my fleet status?"
   ↓
2. Browser: Capture audio via WebRTC
   ↓
3. Voice Service: Receive audio stream
   ↓
4. VAD: Detect speech end
   ↓
5. Whisper STT: Convert to text → "What's my fleet status?"
   ↓
6. Agent Core: Parse intent → Fleet status query
   ↓
7. Agent Core: Delegate to Fleet Commander Agent
   ↓
8. Fleet Commander: Call MCP tool "get_fleet_status"
   ↓
9. MCP Server: Query SAGE program accounts (Solana)
   ↓
10. Solana: Return fleet account data
    ↓
11. MCP Server: Parse and transform data
    ↓
12. Fleet Commander: Format response for voice
    ↓
13. Voice Handler: Optimize for TTS
    ↓
14. ElevenLabs TTS: Generate audio
    ↓
15. Voice Service: Stream audio to browser
    ↓
16. Browser: Play audio response
```

### Real-Time Price Monitoring Flow

```
1. User: "Alert me when titanium drops below 0.04 ATLAS"
   ↓
2. Agent Core: Parse alert request
   ↓
3. MCP Server: Create alert in Firestore
   ↓
4. Scheduled Function (every 1 min): Check alerts
   ↓
5. Query current titanium price from galactic-data
   ↓
6. Compare with threshold (0.04 ATLAS)
   ↓
7. If triggered:
   ↓
8. Send push notification via Firebase Cloud Messaging
   ↓
9. Update alert status (lastTriggered timestamp)
   ↓
10. If user online: Send real-time WebSocket message
    ↓
11. Browser: Display notification banner
```

### Fleet Movement Flow

```
1. User: "Move Fleet Alpha to sector 50"
   ↓
2. Agent Core: Parse command
   ↓
3. Fleet Commander: Validate fleet exists and is idle
   ↓
4. Fleet Commander: Call MCP tool "move_fleet"
   ↓
5. MCP Server: Build Solana transaction
   ↓
6. MCP Server: Return unsigned transaction
   ↓
7. Agent Core: Request user approval
   ↓
8. Browser: Display transaction preview
   ↓
9. User: Approve via Phantom/Solflare wallet
   ↓
10. Wallet: Sign transaction
    ↓
11. MCP Server: Submit signed transaction to Solana
    ↓
12. Solana: Execute SAGE program instruction
    ↓
13. WebSocket: Receive account change notification
    ↓
14. MCP Server: Emit event → Agent Core
    ↓
15. Agent Core: Notify user "Fleet Alpha is moving to sector 50"
    ↓
16. Browser: Update fleet position on star map
```

## Security Architecture

### Wallet Integration

**Connection Flow:**
```
User → Connect Wallet Button → Phantom/Solflare Adapter
       ↓
Wallet Extension: Request permission
       ↓
User: Approve connection
       ↓
Public Key → Store in session (not on server)
       ↓
Agent: Read-only access by default
```

**Transaction Signing:**
- All transactions require explicit user approval
- Preview transaction details before signing
- Simulate transaction outcome (Solana simulate)
- Set spending limits per session
- No private key access by agent

### Voice Privacy

**Recording Indicators:**
- Visual indicator when microphone active
- Audio waveform during recording
- Clear "processing" state

**Data Handling:**
- Audio not stored by default (optional)
- STT processed immediately, audio discarded
- User can enable voice history for debugging

**Local Processing Option:**
- Run Whisper locally (whisper.cpp)
- Use Coqui TTS locally
- No audio sent to external APIs

### API Key Management

**Environment Variables:**
```env
ANTHROPIC_API_KEY=sk-...       # Claude API
OPENAI_API_KEY=sk-...          # Whisper
ELEVENLABS_API_KEY=...         # TTS
SOLANA_RPC_URL=https://...     # Blockchain
```

**Firebase Secret Manager:**
```typescript
import { defineSecret } from 'firebase-functions/params';

const anthropicKey = defineSecret('ANTHROPIC_API_KEY');
const elevenLabsKey = defineSecret('ELEVENLABS_API_KEY');

export const chat = onRequest(
  { secrets: [anthropicKey, elevenLabsKey] },
  async (req, res) => {
    // Access via process.env.ANTHROPIC_API_KEY
  }
);
```

## Scalability

### Horizontal Scaling

**Stateless Services:**
- Agent Core: Stateless (context in Firestore)
- MCP Server: Stateless (can run multiple instances)
- Voice Service: Session-based but load balanceable

**Firebase Auto-Scaling:**
- Functions scale automatically (0 to thousands)
- Firestore handles millions of ops/sec
- No manual capacity planning

**Voice Service Scaling:**
- Deploy on Cloud Run (auto-scaling containers)
- Regional instances for lower latency
- WebRTC connection pooling

### Caching Strategy

**Firestore Cache:**
- Fleet status: 30 second TTL
- Price data: 5 second TTL (real-time)
- Crafting recipes: 1 hour TTL (rarely changes)
- User preferences: Session duration

**Browser Cache:**
- Star map assets (3D models)
- Audio clips for common responses
- UI components (lazy loaded)

### WebSocket Connection Management

**Connection Pooling:**
- Reuse Solana WebSocket connections
- Share subscriptions across users (same asset)
- Automatic reconnection on disconnect

**Backpressure Handling:**
- Rate limit account subscriptions per user
- Queue high-frequency updates
- Batch small updates

## Monitoring & Observability

### Metrics

**Voice Service:**
- STT latency (p50, p95, p99)
- TTS latency
- WebRTC connection success rate
- Audio quality (jitter, packet loss)

**Agent Performance:**
- Response time by agent type
- Tool call latency
- Context size
- Error rates

**Blockchain:**
- RPC call latency
- WebSocket connection stability
- Transaction success rate
- Account subscription count

### Logging

**Structured Logs:**
```typescript
logger.info('Fleet movement initiated', {
  userId: 'user123',
  fleetId: 'fleet-alpha',
  from: 'sector-42',
  to: 'sector-50',
  estimatedTime: '2h15m',
  transactionSignature: 'abc123...'
});
```

**Correlation IDs:**
- Track requests across services
- Voice session ID → Agent session ID → Tool call ID

### Alerting

**Critical Alerts:**
- Voice service down (>5% error rate)
- Solana RPC unavailable
- Transaction failure spike
- Firestore write errors

**Warning Alerts:**
- High latency (p95 > 2s)
- Low cache hit rate
- WebSocket disconnection rate increasing

## Deployment Architecture

### Multi-Region Deployment

**Primary Region:** us-central1 (Firebase default)
**Secondary Regions:**
- Voice Service: us-west1, europe-west1, asia-east1
- Reduces latency for voice interaction

**Deployment Strategy:**

```yaml
# Cloud Run deployment (voice-service)
gcloud run deploy voice-service \
  --image gcr.io/project/voice-service \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 100 \
  --memory 2Gi \
  --cpu 2
```

### CI/CD Pipeline

```
GitHub Push → GitHub Actions
  ↓
Build & Test
  ├── TypeScript compilation (all packages)
  ├── Unit tests (agent, MCP, voice)
  ├── Integration tests (Solana devnet)
  └── Linting & formatting
  ↓
Security Scan
  ├── Dependency audit (npm audit)
  ├── Secret scanning (git-secrets)
  └── SAST (Semgrep)
  ↓
Build Docker Images
  ├── Voice service
  └── Galactic data (price monitoring)
  ↓
Deploy to Staging
  ├── Firebase Hosting (staging)
  ├── Firebase Functions (staging)
  ├── Cloud Run (voice-service-staging)
  └── Firestore rules (staging)
  ↓
E2E Tests (staging)
  ├── Voice interaction test
  ├── Fleet command test
  └── Price alert test
  ↓
Manual Approval
  ↓
Deploy to Production
  ├── Firebase Hosting
  ├── Firebase Functions
  ├── Cloud Run (multi-region)
  └── Firestore rules
```

### z.ink Migration Strategy (December 2025)

**Preparation:**
- Monitor z.ink testnet launch
- Test SAGE program compatibility on SVM
- Validate WebSocket API changes

**Migration Plan:**
1. **Phase 1:** Support both Solana and z.ink simultaneously
2. **Phase 2:** Default to z.ink for new features (zProfiles, dApp permissions)
3. **Phase 3:** Deprecate Solana-specific code
4. **Rollback:** Maintain Solana fallback for 6 months

## Future Enhancements

### Planned Features

1. **Advanced Voice Interaction**
   - Wake word detection ("Hey Cortana")
   - Continuous conversation mode
   - Emotion detection in voice
   - Multiple language support

2. **Proactive Suggestions**
   - AI-driven trading opportunities
   - Fleet optimization recommendations
   - Resource shortage warnings
   - Mission suggestions based on market

3. **Social Features**
   - Faction-specific insights
   - Guild coordination tools
   - Shared fleet analytics
   - Leaderboards

4. **VR/AR Integration**
   - VR star map navigation
   - AR overlay for mobile (ship info)
   - Spatial audio for voice assistant

5. **Advanced Analytics**
   - Portfolio tracking
   - ROI analysis for crafting
   - Economic forecasting
   - Whale activity monitoring

### Technical Debt

- Migrate to GraphQL for more efficient queries
- Implement request batching for Solana RPC
- Add Redis cache for high-frequency data
- Consider Rust for performance-critical paths

## References

- [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)
- [Star Atlas Build](https://build.staratlas.com/)
- [@staratlas/sage](https://www.npmjs.com/package/@staratlas/sage)
- [Solana Web3.js](https://solana-labs.github.io/solana-web3.js/)
- [WebRTC API](https://webrtc.org/)
- [Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [ElevenLabs API](https://elevenlabs.io/docs/)
- [z.ink](https://z.ink/) (coming December 2025)
