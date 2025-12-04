/**
 * IRIS Agent API Server
 *
 * HTTP API for interacting with the IRIS agent.
 * Uses Hono for lightweight, fast request handling.
 * Supports Server-Sent Events (SSE) for streaming responses.
 */

import { config } from "dotenv";
import { resolve } from "path";

// Load .env from project root
config({ path: resolve(process.cwd(), ".env") });

import { Hono } from "hono";
import { cors } from "hono/cors";
import { streamSSE } from "hono/streaming";
import { serve } from "@hono/node-server";
import { z } from "zod";
import { createAgent, type IrisAgentConfig } from "./agent.js";
import { createLocalAgent } from "./local-agent.js";
import { getVoiceStyleOptions, isValidVoiceStyleId } from "./voice-styles.js";
import { warmupOllama } from "./ollama-client.js";
import {
  getModel,
  getModelOptions,
  isValidModelId,
  DEFAULT_LAYER_CONFIG,
} from "./model-config.js";

// ============================================================================
// Request/Response Schemas
// ============================================================================

const ChatRequestSchema = z.object({
  userId: z.string().min(1),
  message: z.string().min(1),
  sessionId: z.string().optional(),
  voiceStyle: z.string().optional(),
  /** Model ID for thinking layer (default: from DEFAULT_LAYER_CONFIG) */
  modelId: z.string().optional(),
});


// ============================================================================
// API Server
// ============================================================================

export interface ApiServerConfig {
  port: number;
  cors?: {
    origin: string | string[];
  };
}

const DEFAULT_CONFIG: ApiServerConfig = {
  port: 3001,
  cors: {
    origin: "*",
  },
};

/**
 * Create and start the IRIS Agent API server.
 */
export function createApiServer(config: Partial<ApiServerConfig> = {}) {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  const startTime = Date.now();

  const app = new Hono();

  // CORS middleware
  app.use(
    "*",
    cors({
      origin: finalConfig.cors?.origin || "*",
      allowMethods: ["GET", "POST", "OPTIONS"],
      allowHeaders: ["Content-Type", "Authorization"],
    })
  );

  // =========================================================================
  // Health Check
  // =========================================================================

  app.get("/health", (c) => {
    return c.json({
      status: "ok",
      version: "0.1.0",
      uptime: Math.floor((Date.now() - startTime) / 1000),
    });
  });

  // =========================================================================
  // Voice Styles Endpoint
  // =========================================================================

  app.get("/api/styles", (c) => {
    return c.json({
      styles: getVoiceStyleOptions(),
    });
  });

  // =========================================================================
  // Models Endpoint
  // =========================================================================

  app.get("/api/models", (c) => {
    return c.json({
      models: getModelOptions("thinking"),
      default: DEFAULT_LAYER_CONFIG.thinking,
    });
  });

  // =========================================================================
  // Chat Endpoint (Streaming via SSE)
  // =========================================================================

  app.post("/api/chat", async (c) => {
    const body = await c.req.json();
    const parseResult = ChatRequestSchema.safeParse(body);

    if (!parseResult.success) {
      return c.json(
        {
          error: "Invalid request",
          details: parseResult.error.issues,
        },
        400
      );
    }

    const { userId, message, sessionId, voiceStyle, modelId } = parseResult.data;

    // Validate voiceStyle if provided
    const validatedStyle = voiceStyle && isValidVoiceStyleId(voiceStyle) ? voiceStyle : undefined;

    // Validate and resolve model
    const resolvedModelId = modelId && isValidModelId(modelId) ? modelId : DEFAULT_LAYER_CONFIG.thinking;
    const modelConfig = getModel(resolvedModelId);

    if (!modelConfig) {
      return c.json({ error: "Invalid model" }, 400);
    }

    console.log(`[API] Chat request using model: ${modelConfig.name} (${modelConfig.provider})`);

    // Route to appropriate agent based on provider
    if (modelConfig.provider === "ollama") {
      // Use LocalAgent for Ollama models
      const agent = createLocalAgent({
        userId,
        modelId: resolvedModelId,
        voiceStyle: validatedStyle,
      });

      return streamSSE(c, async (stream) => {
        try {
          for await (const chunk of agent.chat(message)) {
            await stream.writeSSE({
              event: chunk.type,
              data: JSON.stringify({
                type: chunk.type,
                content: chunk.content,
                isInterim: chunk.isInterim,
              }),
            });
          }
        } catch (error) {
          await stream.writeSSE({
            event: "error",
            data: JSON.stringify({
              type: "error",
              content: error instanceof Error ? error.message : "Unknown error",
            }),
          });
        }
      });
    } else {
      // Use IrisAgent (Claude) for Anthropic models
      const agentConfig: IrisAgentConfig = {
        userId,
        sessionId,
        voiceStyle: validatedStyle,
        model: modelConfig.modelId,
      };

      const agent = createAgent(agentConfig);

      return streamSSE(c, async (stream) => {
        try {
          for await (const chunk of agent.chat(message)) {
            await stream.writeSSE({
              event: chunk.type,
              data: JSON.stringify({
                type: chunk.type,
                content: chunk.content,
                toolName: chunk.toolName,
                sessionId: chunk.sessionId,
                isInterim: chunk.isInterim,
              }),
            });
          }
        } catch (error) {
          await stream.writeSSE({
            event: "error",
            data: JSON.stringify({
              type: "error",
              content: error instanceof Error ? error.message : "Unknown error",
            }),
          });
        }
      });
    }
  });

  // =========================================================================
  // Chat Endpoint (Non-streaming)
  // =========================================================================

  app.post("/api/chat/complete", async (c) => {
    const body = await c.req.json();
    const parseResult = ChatRequestSchema.safeParse(body);

    if (!parseResult.success) {
      return c.json(
        {
          error: "Invalid request",
          details: parseResult.error.issues,
        },
        400
      );
    }

    const { userId, message, sessionId } = parseResult.data;

    const agent = createAgent({ userId, sessionId });
    const response = await agent.chatComplete(message);

    return c.json(response);
  });

  return {
    app,
    start: async () => {
      console.log(`IRIS Agent API starting on port ${finalConfig.port}...`);

      // Warmup Ollama for fast acknowledgments (non-blocking)
      warmupOllama().catch(() => {
        // Warmup failure is not critical - will fallback to simple acks
      });

      const server = serve({
        fetch: app.fetch,
        port: finalConfig.port,
      });
      console.log(`IRIS Agent API listening on http://localhost:${finalConfig.port}`);
      return server;
    },
  };
}

// ============================================================================
// Standalone Entry Point
// ============================================================================

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = parseInt(process.env.AGENT_API_PORT || "3001", 10);
  const { start } = createApiServer({ port });
  start();
}
