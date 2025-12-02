/**
 * Tool registry for IRIS MCP Server
 *
 * Exports all available tools and the unified call handler.
 */

import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import { getWalletBalance, getWalletBalanceSchema } from "./wallet.js";
import { ToolError } from "../errors.js";

// Tool definitions for MCP protocol
export const tools: Tool[] = [
  {
    name: "getWalletBalance",
    description:
      "Get the SOL and token balances for a Solana wallet address. Returns native SOL balance and any SPL token holdings.",
    inputSchema: getWalletBalanceSchema,
  },
];

// Tool name to handler mapping
const toolHandlers: Record<
  string,
  (args: Record<string, unknown>) => Promise<unknown>
> = {
  getWalletBalance,
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
