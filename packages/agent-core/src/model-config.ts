/**
 * Model Configuration System
 *
 * Defines available models for each layer (fast-ack, thinking) with support
 * for both cloud (Anthropic) and local (Ollama) providers.
 *
 * Architecture:
 * - Fast-ack layer: Quick acknowledgments (~130ms target)
 * - Thinking layer: Main reasoning and tool use
 *
 * Goal: Run entire stack locally (no internet required) while keeping
 * option for power users to use cloud models.
 */

// ============================================================================
// Types
// ============================================================================

export type ModelProvider = "anthropic" | "ollama";
export type ModelLayer = "fast-ack" | "thinking";

export interface ModelConfig {
  /** Unique identifier for the model */
  id: string;
  /** Display name for UI */
  name: string;
  /** Provider (anthropic or ollama) */
  provider: ModelProvider;
  /** Model ID to use with the provider's API */
  modelId: string;
  /** Which layer this model is suitable for */
  layers: ModelLayer[];
  /** Whether this model supports tool use */
  supportsTools: boolean;
  /** Whether this model requires internet */
  requiresInternet: boolean;
  /** UI badge: best, fast, cheap, local */
  badge?: "best" | "fast" | "cheap" | "local";
  /** Approximate cost per 1M tokens (input) in USD, null for local */
  costPer1MTokens?: number | null;
  /** Estimated latency category */
  latency: "ultra-fast" | "fast" | "medium" | "slow";
}

export interface LayerConfig {
  /** Currently selected model for fast-ack layer */
  fastAck: string;
  /** Currently selected model for thinking layer */
  thinking: string;
}

// ============================================================================
// Model Registry
// ============================================================================

/**
 * All available models in the system.
 * Ordered by recommendation (best first within each provider).
 */
export const MODEL_REGISTRY: ModelConfig[] = [
  // ==========================================================================
  // Anthropic Cloud Models
  // ==========================================================================
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    modelId: "claude-sonnet-4-5-20250929",
    layers: ["thinking"],
    supportsTools: true,
    requiresInternet: true,
    badge: "best",
    costPer1MTokens: 3.0,
    latency: "medium",
  },
  {
    id: "claude-haiku-4",
    name: "Claude Haiku 4",
    provider: "anthropic",
    modelId: "claude-haiku-4-5-20251001",
    layers: ["thinking"],
    supportsTools: true,
    requiresInternet: true,
    badge: "fast",
    costPer1MTokens: 0.8,
    latency: "fast",
  },

  // ==========================================================================
  // Ollama Local Models
  // ==========================================================================
  {
    id: "qwen-2.5-7b",
    name: "Qwen 2.5 7B",
    provider: "ollama",
    modelId: "qwen2.5:7b",
    layers: ["fast-ack", "thinking"],
    supportsTools: false, // Ollama tool support is limited
    requiresInternet: false,
    badge: "local",
    costPer1MTokens: null,
    latency: "fast",
  },
  {
    id: "llama-3.1-8b",
    name: "Llama 3.1 8B",
    provider: "ollama",
    modelId: "llama3.1:8b",
    layers: ["thinking"],
    supportsTools: false,
    requiresInternet: false,
    badge: "local",
    costPer1MTokens: null,
    latency: "fast",
  },
  {
    id: "qwen-2.5-14b",
    name: "Qwen 2.5 14B",
    provider: "ollama",
    modelId: "qwen2.5:14b",
    layers: ["thinking"],
    supportsTools: false,
    requiresInternet: false,
    badge: "local",
    costPer1MTokens: null,
    latency: "medium",
  },
];

// ============================================================================
// Default Configuration
// ============================================================================

/**
 * Default model selection for each layer.
 * Optimized for local-first operation.
 */
export const DEFAULT_LAYER_CONFIG: LayerConfig = {
  fastAck: "qwen-2.5-7b", // Local Qwen for ~130ms acknowledgments
  thinking: "qwen-2.5-7b", // Local Qwen for offline operation (switchable to Claude)
};

/**
 * Cloud-optimized configuration for power users.
 */
export const CLOUD_LAYER_CONFIG: LayerConfig = {
  fastAck: "qwen-2.5-7b", // Still use local for speed
  thinking: "claude-sonnet-4", // Best quality for thinking
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get a model configuration by ID.
 */
export function getModel(id: string): ModelConfig | undefined {
  return MODEL_REGISTRY.find((m) => m.id === id);
}

/**
 * Get all models suitable for a specific layer.
 */
export function getModelsForLayer(layer: ModelLayer): ModelConfig[] {
  return MODEL_REGISTRY.filter((m) => m.layers.includes(layer));
}

/**
 * Get all local models (no internet required).
 */
export function getLocalModels(): ModelConfig[] {
  return MODEL_REGISTRY.filter((m) => !m.requiresInternet);
}

/**
 * Get all cloud models.
 */
export function getCloudModels(): ModelConfig[] {
  return MODEL_REGISTRY.filter((m) => m.requiresInternet);
}

/**
 * Check if a model ID is valid.
 */
export function isValidModelId(id: string): boolean {
  return MODEL_REGISTRY.some((m) => m.id === id);
}

/**
 * Get the provider's model ID from our internal ID.
 */
export function getProviderModelId(id: string): string | undefined {
  return getModel(id)?.modelId;
}

/**
 * Check if a model supports tool use.
 */
export function modelSupportsTools(id: string): boolean {
  return getModel(id)?.supportsTools ?? false;
}

/**
 * Format model options for API/UI consumption.
 */
export function getModelOptions(layer?: ModelLayer): Array<{
  id: string;
  name: string;
  provider: ModelProvider;
  badge?: string;
  local: boolean;
}> {
  const models = layer ? getModelsForLayer(layer) : MODEL_REGISTRY;
  return models.map((m) => ({
    id: m.id,
    name: m.name,
    provider: m.provider,
    badge: m.badge,
    local: !m.requiresInternet,
  }));
}
