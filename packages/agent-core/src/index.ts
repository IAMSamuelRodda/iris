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

// Agent (Claude - cloud)
export { IrisAgent, createAgent, quickChat, type IrisAgentConfig, type AgentResponse, type StreamChunk } from "./agent.js";

// Local Agent (Ollama - offline)
export { LocalAgent, createLocalAgent, quickLocalChat, type LocalAgentConfig, type LocalAgentResponse, type LocalStreamChunk } from "./local-agent.js";

// System prompt
export { IRIS_BASE_PROMPT, buildSystemPrompt, generateUserContext } from "./system-prompt.js";

// MCP Server
export { createIrisMcpServer } from "./mcp-server.js";

// API Server
export { createApiServer, type ApiServerConfig } from "./api-server.js";

// Model Configuration
export {
  MODEL_REGISTRY,
  DEFAULT_LAYER_CONFIG,
  CLOUD_LAYER_CONFIG,
  getModel,
  getModelsForLayer,
  getLocalModels,
  getCloudModels,
  isValidModelId,
  getProviderModelId,
  modelSupportsTools,
  getModelOptions,
  type ModelProvider,
  type ModelLayer,
  type ModelConfig,
  type LayerConfig,
} from "./model-config.js";

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
  resetOllamaAvailability,
  type QuickAcknowledgment,
  type FastLayerConfig,
} from "./fast-layer.js";

// Ollama Client (Local LLM for fast acknowledgments)
export { warmupOllama, isOllamaAvailable, FAST_ACK_MODEL } from "./ollama-client.js";

// Ollama Chat (Local LLM for thinking layer)
export {
  ollamaChatComplete,
  ollamaChatStream,
  toOllamaMessages,
  collectStreamResponse,
  type OllamaChatMessage,
  type OllamaChatRequest,
  type OllamaChatResponse,
  type OllamaChatStreamChunk,
} from "./ollama-chat.js";

// Narrator (Streaming context vocalization)
export {
  createNarrator,
  createSnippet,
  OllamaNarrator,
  HaikuNarrator,
  ComparisonNarrator,
  BaseNarrator,
  NARRATOR_SYSTEM_PROMPT,
  NARRATOR_MODEL,
  HAIKU_MODEL,
  DEFAULT_NARRATOR_CONFIG,
  type Narrator,
  type NarratorConfig,
  type NarratorProvider,
  type Snippet,
  type SnippetSource,
  type SnippetType,
  type SnippetPriority,
  type VocalizationResult,
  type VerbosityLevel,
  type NarratorMetrics,
  type ComparisonMetrics,
} from "./narrator/index.js";

export const VERSION = "0.1.0";
