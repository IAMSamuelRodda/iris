# Star Atlas Agent - Packages

This monorepo contains all packages for the Star Atlas Agent system.

## Package Structure

```
packages/
├── web-app/              # React frontend (Vite + React Router + TanStack Query)
├── agent-core/           # Claude Agent SDK orchestrator (AWS Lambda)
├── mcp-staratlas-server/ # MCP server for Star Atlas + Solana tools
├── voice-service/        # WebRTC voice service (WebSocket + Whisper + ElevenLabs)
└── memory-service/       # RAG and vector search (AWS Lambda)
```

## Development

### Prerequisites

- Node.js 20+
- pnpm 9+

### Setup

```bash
# Install all dependencies
pnpm install

# Build all packages
pnpm build

# Run all packages in dev mode
pnpm dev

# Run tests
pnpm test

# Type check
pnpm typecheck

# Lint and format
pnpm lint
pnpm format
```

### Package-Specific Commands

```bash
# Run dev mode for a specific package
pnpm --filter @star-atlas-agent/web-app dev

# Build a specific package
pnpm --filter @star-atlas-agent/agent-core build

# Test a specific package
pnpm --filter @star-atlas-agent/memory-service test
```

## Package Details

### web-app

React frontend with voice-first UI, fleet dashboard, and wallet integration.

**Tech Stack**: React 18, Vite, React Router, TanStack Query, Zustand, Solana Wallet Adapter

### agent-core

Claude Agent SDK orchestrator that manages conversation flow, memory retrieval, and MCP tool execution.

**Tech Stack**: Claude Agent SDK, AWS Lambda, AWS SDK (DynamoDB, S3, Bedrock)

### mcp-staratlas-server

MCP server providing tools for Star Atlas game state and Solana blockchain operations.

**Tech Stack**: MCP SDK, Solana Web3.js, Star Atlas SAGE SDK

### voice-service

Real-time voice streaming service with <500ms latency target.

**Tech Stack**: WebSocket (ws), WebRTC, OpenAI Whisper, ElevenLabs

### memory-service

Four-tier memory system with vector search for long-term personalization.

**Tech Stack**: AWS Lambda, Bedrock Titan v2, DynamoDB

## Architecture

See root `ARCHITECTURE.md` for complete system architecture and design decisions.

## Contributing

See root `CONTRIBUTING.md` for git workflow and development guidelines.
