/**
 * MCP Server implementation for Star Atlas & Solana
 *
 * Handles server lifecycle, tool registration, and request routing.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { tools, handleToolCall } from "./tools/index.js";

const SERVER_NAME = "iris-staratlas";
const SERVER_VERSION = "0.1.0";

export function createServer(): Server {
  const server = new Server(
    {
      name: SERVER_NAME,
      version: SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Register tool listing handler
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
  });

  // Register tool call handler
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    return handleToolCall(name, args);
  });

  // Log server events
  server.onerror = (error) => {
    console.error("[MCP Error]", error);
  };

  return server;
}
