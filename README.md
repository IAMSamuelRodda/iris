# Star Atlas Agent

> Cortana-like AI assistant for Star Atlas on-chain economy and game control

## Overview

Star Atlas Agent is an AI-powered assistant that brings natural language and voice interaction to the Star Atlas metaverse. Monitor on-chain activities, track material prices, control fleets and ships, optimize crafting, and interact through voice commands - all powered by Claude's advanced reasoning and the Star Atlas ecosystem's APIs.

## Features

### 📈 On-Chain Monitoring
- Real-time price tracking for materials and assets
- Material availability monitoring across the ecosystem
- Fleet and ship status via SAGE API
- Transaction notifications and blockchain events
- Economic indicator tracking (ATLAS/POLIS)

### 🚀 Natural Language Game Control
- Fleet management commands ("Move my fleet to sector 7")
- Ship control and resource management
- Crafting optimization queries
- Market analysis and trading insights
- Game state queries and status checks

### 🎤 Voice Interaction (Cortana-like)
- Speech-to-text command input
- Natural voice responses
- Push-to-talk interface
- Context-aware conversations
- Voice-optimized formatting

### 🛠️ Crafting Optimization
- Recipe analysis and cost calculation
- Resource allocation planning
- Production optimization
- Material requirement forecasting

### 💰 Market Intelligence
- Price trend analysis
- Trading recommendations
- Alert system for price thresholds
- Marketplace search and discovery

## Architecture

### Technology Stack

- **Frontend**: React + Vite + Three.js (visualization)
- **Agent**: Claude Agent SDK (TypeScript)
- **MCP Server**: Star Atlas + Solana integration
- **Voice**: Whisper (STT) + ElevenLabs (TTS) + WebRTC
- **Backend**: Firebase Functions (serverless)
- **Database**: Firestore (proven with galactic-data)
- **Blockchain**: Solana (migrating to z.ink)
- **Hosting**: Firebase Hosting

### Architecture Diagram

```
┌─────────────┐
│   Web App   │  React + Voice Interface
└──────┬──────┘
       │
┌──────▼──────┐
│ Voice Service│  Whisper + ElevenLabs + WebRTC
└──────┬──────┘
       │
┌──────▼──────┐
│ Agent Core  │  Claude Agent SDK
└──────┬──────┘
       │
┌──────▼──────┐
│ MCP Server  │  Star Atlas + Solana APIs
└──────┬──────┘
       │
┌──────▼──────┐   ┌──────────────┐
│ Star Atlas  │   │    Solana    │
│    APIs     │   │  Blockchain  │
└─────────────┘   └──────────────┘
```

## Getting Started

### Prerequisites

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Firebase CLI (`npm install -g firebase-tools`)
- Solana CLI (optional, for development)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd star-atlas-agent
   ```

2. **Install dependencies:**
   ```bash
   pnpm install
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Set up API keys:**
   ```env
   # Claude API
   ANTHROPIC_API_KEY=your_api_key

   # Solana RPC
   SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
   SOLANA_WS_URL=wss://api.mainnet-beta.solana.com

   # Voice Services
   OPENAI_API_KEY=your_whisper_key
   ELEVENLABS_API_KEY=your_elevenlabs_key

   # Firebase (from existing galactic-data setup)
   FIREBASE_PROJECT_ID=your_project_id
   ```

5. **Initialize Firebase:**
   ```bash
   firebase login
   firebase use <project-id>
   ```

### Development

**Run in development mode:**
```bash
pnpm dev
```

This starts:
- MCP server on `http://localhost:3000`
- Agent core on `http://localhost:3001`
- Voice service on `http://localhost:3002`
- Web app on `http://localhost:5173`

**Build for production:**
```bash
pnpm build
```

**Run tests:**
```bash
pnpm test
```

### Deployment

**Deploy to Firebase:**
```bash
firebase deploy
```

## Usage Examples

### Market Intelligence

```
User: What's the current price of titanium?

Agent: Titanium is currently trading at 0.045 ATLAS per unit, down 2.3%
from yesterday. The 24-hour volume is 1.2M units. Based on recent trends,
this represents a good buying opportunity.

Would you like me to set up a price alert?
```

### Fleet Management

```
User: Check my fleet status

Agent: You have 3 fleets currently active:

Fleet Alpha (Sector 42):
- 5 ships (2 mining, 3 combat)
- Fuel: 78%
- Health: 95%
- Current mission: Resource extraction

Fleet Bravo (Sector 15):
- 3 ships (transport)
- Fuel: 45% (refuel recommended)
- Health: 100%
- Status: In transit to trading hub

Fleet Charlie (Home base):
- 7 ships (mixed)
- Status: Docked for maintenance

Would you like details on any specific fleet?
```

### Voice Command (via microphone)

```
User: [Speaking] "Hey Cortana, move Fleet Alpha to sector 50"

Agent: [Voice response] "Moving Fleet Alpha from sector 42 to sector 50.
Estimated travel time is 2 hours and 15 minutes. The fleet has sufficient
fuel for this journey."

[Visual] Fleet movement initiated, showing route on map
```

### Crafting Optimization

```
User: What's the cheapest way to craft a medium fighter?

Agent: Analyzing crafting options for Medium Fighter...

Option 1: Direct craft from raw materials
- Cost: 127 ATLAS
- Time: 6 hours
- Materials needed: Iron (500), Titanium (200), Electronics (50)

Option 2: Buy sub-components
- Cost: 98 ATLAS (23% savings)
- Time: 2 hours
- Components: Pre-fab hull (50 ATLAS), Engine module (35 ATLAS),
  Electronics (50 units, 13 ATLAS)

Recommendation: Option 2 is more cost-effective and faster.
Would you like me to prepare the shopping list?
```

## Project Structure

```
star-atlas-agent/
├── .claude/                    # Claude Code configuration
│   ├── agents/                 # Specialized sub-agents
│   ├── skills/                 # Star Atlas & Solana knowledge
│   └── commands/               # Custom commands
├── packages/
│   ├── galactic-data/          # Existing price monitoring
│   ├── mcp-staratlas-server/   # MCP server
│   ├── agent-core/             # Agent orchestrator
│   ├── voice-service/          # Voice pipeline
│   └── web-app/                # Web interface
├── backend/functions/          # Serverless functions
├── infrastructure/             # Firebase config
└── docs/                       # Documentation
```

## Configuration

### Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-...
SOLANA_RPC_URL=https://...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
FIREBASE_PROJECT_ID=...

# Optional
SOLANA_WS_URL=wss://...
HELIUS_API_KEY=...
MORALIS_API_KEY=...
```

## Star Atlas Integration

### Supported APIs

- **SAGE API**: Game mechanics, fleet management
- **Galactic Marketplace**: Asset trading, price data
- **Galaxy API**: Items, tokens, showroom
- **Cargo API**: Inventory, logistics
- **Crafting API**: Recipe data, item creation
- **Player Profile API**: Progression, reputation
- **Fleet Rentals API**: Ship leasing

### Blockchain Integration

- **Solana Web3.js**: Account monitoring, transactions
- **WebSocket Subscriptions**: Real-time blockchain events
- **Token Tracking**: ATLAS, POLIS, and NFT assets
- **Transaction Simulation**: Preview before signing

### z.ink Migration (December 2025)

The agent is designed to support Star Atlas's migration to z.ink Layer 1:
- SVM compatibility maintains existing Solana tooling
- zProfiles for identity-linked accounts
- dApp permissioning for automatic transactions
- Gradual migration path from Solana mainnet

## Voice Interaction

### Voice Commands

**Market queries:**
- "What's the price of [material]?"
- "Show me trending assets"
- "Alert me when titanium drops below 0.04 ATLAS"

**Fleet commands:**
- "Move Fleet Alpha to sector [number]"
- "Check my fleet status"
- "Repair all ships in Fleet Bravo"

**Crafting queries:**
- "How do I craft a [item]?"
- "What's the cheapest way to make [item]?"
- "Do I have enough materials for [recipe]?"

**General:**
- "What's the latest Star Atlas news?"
- "How's the ATLAS price doing?"
- "Show my wallet balance"

### Voice Settings

- **Wake Word**: "Hey Cortana" (customizable)
- **Push-to-Talk**: Hold Space or on-screen button
- **Voice Selection**: Multiple ElevenLabs voices available
- **Audio Quality**: Adjustable for bandwidth

## Security

### Wallet Integration

- Read-only connections by default
- Explicit approval required for transactions
- Transaction simulation before signing
- Spending limits and safeguards
- Phantom/Solflare wallet support

### Voice Privacy

- Local processing option (Whisper local + Coqui TTS)
- Clear recording indicators
- Optional voice data storage
- Encrypted transmission

### API Security

- API keys in environment variables only
- Firebase secret management
- Rate limiting on all endpoints
- Audit logging for transactions

## Performance

### Latency Targets

- Voice round-trip: < 500ms
- Blockchain queries: < 200ms
- Market data updates: Real-time (WebSocket)
- Agent responses: < 2s

### Scalability

- Stateless services for horizontal scaling
- Firestore auto-scaling
- WebSocket connection pooling
- Edge caching for static data

## Testing

```bash
# Run all tests
pnpm test

# Unit tests
pnpm test:unit

# Integration tests (requires test wallet)
pnpm test:integration

# E2E tests
pnpm test:e2e

# Voice pipeline tests
pnpm test:voice
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Documentation

- [Architecture](ARCHITECTURE.md) - System design details
- [Development](DEVELOPMENT.md) - Development workflows
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions
- [Voice Commands](VOICE-COMMANDS.md) - Complete voice reference

## License

MIT License - see [LICENSE](../LICENSE) for details

## Support

- GitHub Issues: [Create an issue](../../issues)
- Discord: [Star Atlas Community](https://discord.gg/staratlas)
- Documentation: [docs/](.)

## Roadmap

### MVP (Current Phase)
- [x] Project structure and documentation
- [ ] Price monitoring integration (galactic-data)
- [ ] SAGE API fleet management
- [ ] Basic agent with text commands
- [ ] Voice service foundation (STT/TTS)
- [ ] Push-to-talk interface

### Phase 2
- [ ] Advanced market analysis
- [ ] Crafting optimization calculator
- [ ] WebSocket real-time updates
- [ ] Wake word activation
- [ ] Mobile-responsive interface

### Phase 3
- [ ] z.ink Layer 1 integration
- [ ] Advanced voice conversations
- [ ] 3D map visualization
- [ ] Multi-wallet support
- [ ] Trading automation (with approval)

### Phase 4 (Vision)
- [ ] Full Cortana-like experience
- [ ] Proactive suggestions
- [ ] Faction-specific features
- [ ] Social trading insights
- [ ] VR/AR integration

## Acknowledgments

Built with:
- [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)
- [Star Atlas APIs](https://build.staratlas.com/)
- [@staratlas/sage](https://www.npmjs.com/package/@staratlas/sage)
- [@solana/web3.js](https://solana-labs.github.io/solana-web3.js/)
- [Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [ElevenLabs](https://elevenlabs.io/)
- [Firebase](https://firebase.google.com/)

Inspired by:
- **Wingman AI**: Voice commands for Star Citizen
- **Cortana (Halo)**: AI companion vision
- **atlas.eveeye.com**: Data visualization excellence

## References

- [galactic-prices (original repo)](https://github.com/choutaLAN/galactic-prices)
- [Wingman AI](https://github.com/ShipBit/wingman-ai)
- [atlas.eveeye.com](https://atlas.eveeye.com/)
- [z.ink Documentation](https://z.ink/) (coming December 2025)
