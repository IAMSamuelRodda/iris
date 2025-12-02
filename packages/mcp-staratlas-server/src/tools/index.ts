/**
 * Tool registry for IRIS MCP Server
 *
 * Exports all available tools and the unified call handler.
 */

import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import { getWalletBalance, getWalletBalanceSchema } from "./wallet.js";
import {
  getTransactionHistory,
  getTransactionHistorySchema,
} from "./transactions.js";
import { getFleetStatus, getFleetStatusSchema } from "./fleet.js";
import { ToolError } from "../errors.js";

// Tool definitions for MCP protocol
export const tools: Tool[] = [
  {
    name: "getWalletBalance",
    description:
      "Get the SOL and token balances for a Solana wallet address. Returns native SOL balance and any SPL token holdings.",
    inputSchema: getWalletBalanceSchema,
  },
  {
    name: "getTransactionHistory",
    description:
      "Get recent transaction history for a Solana wallet address. Returns signatures, timestamps, status, fees, and transaction types with pagination support.",
    inputSchema: getTransactionHistorySchema,
  },
  {
    name: "getFleetStatus",
    description:
      "Check Star Atlas SAGE player profile and fleet status for a wallet address. Verifies if the wallet has a SAGE profile. MVP: Returns profile verification; full fleet data requires SAGE SDK integration.",
    inputSchema: getFleetStatusSchema,
  },
];

// Tool name to handler mapping
const toolHandlers: Record<
  string,
  (args: Record<string, unknown>) => Promise<unknown>
> = {
  getWalletBalance,
  getTransactionHistory,
  getFleetStatus,
};

/**
 * Route a tool call to the appropriate handler
 */
export async function handleToolCall(
  name: string,
  args: Record<string, unknown> | undefined
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const handler = toolHandlers[name];

  if (!handler) {
    throw new ToolError(`Unknown tool: ${name}`, "UNKNOWN_TOOL");
  }

  try {
    const result = await handler(args ?? {});
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    if (error instanceof ToolError) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: error.message,
              code: error.code,
            }),
          },
        ],
      };
    }
    throw error;
  }
}
