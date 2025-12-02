/**
 * IRIS Agent Core
 *
 * Claude Agent SDK orchestrator for IRIS - voice-first AI companion for Star Atlas.
 *
 * Uses the Claude Agent SDK for:
 * - Agentic conversation loops with tool use
 * - In-process MCP server for memory and Star Atlas tools
 * - Session management for multi-turn conversations
 * - Streaming responses for voice latency requirements
 */

// Agent
export { IrisAgent, createAgent, quickChat, type IrisAgentConfig, type AgentResponse, type StreamChunk } from "./agent.js";

// System prompt
export { IRIS_BASE_PROMPT, buildSystemPrompt, generateUserContext } from "./system-prompt.js";

// MCP Server
export { createIrisMcpServer } from "./mcp-server.js";

// API Server
export { createApiServer, type ApiServerConfig } from "./api-server.js";

// Voice Styles
export {
  type VoiceStyleId,
  type VoiceStyle,
  voiceStyles,
  getVoiceStyle,
  buildVoiceStylePrompt,
  getVoiceStyleOptions,
  isValidVoiceStyleId,
} from "./voice-styles.js";

// Fast Layer (Quick Acknowledgments)
export {
  generateQuickAcknowledgment,
  needsAcknowledgment,
  getQuickFallback,
  type QuickAcknowledgment,
  type FastLayerConfig,
} from "./fast-layer.js";

export const VERSION = "0.1.0";
