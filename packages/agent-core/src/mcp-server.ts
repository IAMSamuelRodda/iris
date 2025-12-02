/**
 * IRIS In-Process MCP Server
 *
 * Creates an MCP server that runs in the same process as the agent.
 * Combines Star Atlas tools and Memory tools into a single interface.
 *
 * Uses the Claude Agent SDK's createSdkMcpServer() for zero-overhead tool execution.
 */

import { createSdkMcpServer, tool, type McpSdkServerConfigWithInstance } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { getMemoryManager, getConversationHistory } from "@iris/memory-service";

/**
 * Create the IRIS MCP server with all tools.
 *
 * This server provides:
 * - Memory tools (knowledge graph, conversation history)
 * - Star Atlas tools (will be added when CITADEL integration is ready)
 */
export function createIrisMcpServer(): McpSdkServerConfigWithInstance {
  return createSdkMcpServer({
    name: "iris",
    version: "0.1.0",
    tools: [
      // =========================================================================
      // Memory Tools - Knowledge Graph
      // =========================================================================

      tool(
        "search_memory",
        `Search IRIS's memory for entities matching a query.
ALWAYS call this before answering questions about the user's fleet, preferences, or history.`,
        {
          userId: z.string().describe("User ID to search memory for"),
          query: z.string().describe("Search query"),
          limit: z.number().optional().default(10).describe("Max results"),
        },
        async (args) => {
          const { userId, query, limit } = args as { userId: string; query: string; limit: number };
          const manager = getMemoryManager(userId);
          const entities = manager.searchNodes(query, limit);

          if (entities.length === 0) {
            return {
              content: [{ type: "text" as const, text: `No memories found matching "${query}".` }],
            };
          }

          const formatted = entities
            .map((e) => {
              const obs = e.observations.length > 0 ? `\n  - ${e.observations.join("\n  - ")}` : "";
              return `**${e.name}** (${e.entityType})${obs}`;
            })
            .join("\n\n");

          return {
            content: [{ type: "text" as const, text: `Found ${entities.length} memories:\n\n${formatted}` }],
          };
        }
      ),

      tool(
        "remember",
        `Store information in IRIS's memory about an entity.
Use when the user shares something worth remembering (fleet names, preferences, goals).
Set isUserEdit=true when user explicitly says "remember that..." or similar.`,
        {
          userId: z.string().describe("User ID"),
          name: z.string().describe("Entity name (e.g., 'The Armada', 'Commander Sam')"),
          entityType: z
            .enum(["person", "organization", "fleet", "ship", "location", "concept", "event", "preference"])
            .describe("Type of entity"),
          observations: z.array(z.string()).describe("Facts to remember about this entity"),
          isUserEdit: z.boolean().optional().default(false).describe("True if user explicitly requested this memory"),
        },
        async (args) => {
          const { userId, name, entityType, observations, isUserEdit } = args as {
            userId: string;
            name: string;
            entityType: string;
            observations: string[];
            isUserEdit: boolean;
          };
          const manager = getMemoryManager(userId);
          manager.createEntities([{ name, entityType, observations }], isUserEdit);

          return {
            content: [
              {
                type: "text" as const,
                text: `Remembered: ${name} (${entityType}) with ${observations.length} observation(s).`,
              },
            ],
          };
        }
      ),

      tool(
        "add_observation",
        `Add new facts to an existing entity in memory.
Use when user shares new information about something IRIS already knows.`,
        {
          userId: z.string().describe("User ID"),
          entityName: z.string().describe("Name of existing entity"),
          facts: z.array(z.string()).describe("New facts to add"),
          isUserEdit: z.boolean().optional().default(false).describe("True if user explicitly requested this"),
        },
        async (args) => {
          const { userId, entityName, facts, isUserEdit } = args as {
            userId: string;
            entityName: string;
            facts: string[];
            isUserEdit: boolean;
          };
          const manager = getMemoryManager(userId);
          const results = manager.addObservations([{ entityName, contents: facts }], isUserEdit);

          if (results.length === 0) {
            return {
              content: [
                { type: "text" as const, text: `Entity "${entityName}" not found. Create it first with remember().` },
              ],
            };
          }

          return {
            content: [{ type: "text" as const, text: `Added ${results[0].added.length} fact(s) to ${entityName}.` }],
          };
        }
      ),

      tool(
        "create_relation",
        `Create a relationship between two entities in memory.
Use active voice for relation types (e.g., "commands", "owns", "located_at").`,
        {
          userId: z.string().describe("User ID"),
          from: z.string().describe("Source entity name"),
          to: z.string().describe("Target entity name"),
          relationType: z.string().describe("Relationship type in active voice"),
        },
        async (args) => {
          const { userId, from, to, relationType } = args as {
            userId: string;
            from: string;
            to: string;
            relationType: string;
          };
          const manager = getMemoryManager(userId);
          const created = manager.createRelations([{ from, to, relationType }]);

          if (created.length === 0) {
            return {
              content: [{ type: "text" as const, text: `Relation already exists or entities not found.` }],
            };
          }

          return {
            content: [{ type: "text" as const, text: `Created relation: ${from} → ${relationType} → ${to}` }],
          };
        }
      ),

      tool(
        "get_memory_summary",
        `Get a summary of what IRIS knows about the user.
Use when user asks "what do you know about me?" or at session start.`,
        {
          userId: z.string().describe("User ID"),
        },
        async (args) => {
          const { userId } = args as { userId: string };
          const manager = getMemoryManager(userId);
          const summary = manager.getSummary();
          const graph = manager.readGraph();

          if (graph.entities.length === 0) {
            return {
              content: [{ type: "text" as const, text: "I don't have any memories stored for you yet." }],
            };
          }

          const entityCount = graph.entities.length;
          const obsCount = graph.entities.reduce((sum, e) => sum + e.observations.length, 0);

          let text = `I have ${entityCount} entities with ${obsCount} observations stored.\n\n`;

          if (summary && !manager.isSummaryStale()) {
            text += `**Summary**: ${summary.summary}`;
          } else {
            // Generate a quick overview
            const topEntities = graph.entities.slice(0, 5);
            text += "**Top entities**:\n";
            for (const e of topEntities) {
              text += `- ${e.name} (${e.entityType})\n`;
            }
          }

          return {
            content: [{ type: "text" as const, text }],
          };
        }
      ),

      // =========================================================================
      // Memory Tools - Conversation History
      // =========================================================================

      tool(
        "get_recent_conversation",
        `Get recent conversation history with this user.
Use to understand context from previous turns in the current session.`,
        {
          userId: z.string().describe("User ID"),
          limit: z.number().optional().default(10).describe("Number of recent messages"),
        },
        async (args) => {
          const { userId, limit } = args as { userId: string; limit: number };
          const history = getConversationHistory(userId, limit);

          if (history.length === 0) {
            return {
              content: [{ type: "text" as const, text: "No recent conversation history." }],
            };
          }

          const formatted = history
            .map((m) => `**${m.role}**: ${m.content.slice(0, 200)}${m.content.length > 200 ? "..." : ""}`)
            .join("\n\n");

          return {
            content: [
              { type: "text" as const, text: `Recent conversation (${history.length} messages):\n\n${formatted}` },
            ],
          };
        }
      ),

      // =========================================================================
      // Placeholder: Star Atlas Tools
      // These will call CITADEL REST API when ready (ARCH-001)
      // =========================================================================

      tool(
        "get_wallet_balance",
        `Get SOL and token balances for a Solana wallet.
Returns native SOL balance and SPL token holdings.`,
        {
          walletAddress: z.string().describe("Solana wallet address (base58)"),
        },
        async (args) => {
          const { walletAddress } = args as { walletAddress: string };
          // TODO: Replace with CITADEL REST API call when ready
          return {
            content: [
              {
                type: "text" as const,
                text: `[CITADEL API not yet available]\n\nWould query balance for: ${walletAddress}`,
              },
            ],
          };
        }
      ),

      tool(
        "get_fleet_status",
        `Check Star Atlas SAGE fleet status for a wallet.
Returns fleet composition, current state, and resource levels.`,
        {
          walletAddress: z.string().describe("Solana wallet address"),
        },
        async (args) => {
          const { walletAddress } = args as { walletAddress: string };
          // TODO: Replace with CITADEL REST API call when ready
          return {
            content: [
              {
                type: "text" as const,
                text: `[CITADEL API not yet available]\n\nWould query fleet status for: ${walletAddress}`,
              },
            ],
          };
        }
      ),

      tool(
        "predict_fuel_depletion",
        `Calculate when a fleet will run out of fuel.
Requires current fuel level and consumption rate.`,
        {
          currentFuel: z.number().describe("Current fuel amount"),
          maxFuel: z.number().describe("Maximum fuel capacity"),
          consumptionRate: z.number().describe("Fuel consumption per hour"),
        },
        async (args) => {
          const { currentFuel, maxFuel, consumptionRate } = args as {
            currentFuel: number;
            maxFuel: number;
            consumptionRate: number;
          };

          if (consumptionRate <= 0) {
            return {
              content: [{ type: "text" as const, text: "Invalid consumption rate. Must be positive." }],
            };
          }

          const hoursRemaining = currentFuel / consumptionRate;
          const percentRemaining = (currentFuel / maxFuel) * 100;

          let status: string;
          if (percentRemaining < 10) status = "CRITICAL";
          else if (percentRemaining < 25) status = "LOW";
          else if (percentRemaining < 50) status = "MODERATE";
          else if (percentRemaining < 90) status = "GOOD";
          else status = "FULL";

          const depletionTime = new Date(Date.now() + hoursRemaining * 60 * 60 * 1000);

          return {
            content: [
              {
                type: "text" as const,
                text: `**Fuel Status**: ${status}
**Current**: ${currentFuel.toFixed(1)} / ${maxFuel} (${percentRemaining.toFixed(1)}%)
**Time to Empty**: ${hoursRemaining.toFixed(1)} hours
**Depletion Time**: ${depletionTime.toLocaleString()}

${status === "CRITICAL" ? "⚠️ URGENT: Refuel immediately!" : status === "LOW" ? "Consider refueling soon." : "Fuel levels acceptable."}`,
              },
            ],
          };
        }
      ),
    ],
  });
}
