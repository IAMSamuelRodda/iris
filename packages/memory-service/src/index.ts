/**
 * IRIS Memory Service
 *
 * SQLite-based knowledge graph for user context, preferences,
 * and conversation history.
 *
 * Pattern: sqlite-knowledge-graph (from agentic-framework)
 * Reference: https://github.com/IAMSamuelRodda/agentic-framework/blob/main/patterns/sqlite-knowledge-graph.md
 */

export { KnowledgeGraphManager, type Entity, type Relation, type KnowledgeGraph } from "./knowledge-graph.js";
export {
  initializeMemoryDb,
  getMemoryManager,
  closeMemoryDb,
  getDbInstance,
  addConversationMessage,
  getConversationHistory,
  cleanupExpiredConversations,
  clearConversationHistory,
  type ConversationMessage,
} from "./database.js";
export { memoryToolDefinitions, executeMemoryTool } from "./mcp-tools.js";

export const VERSION = "0.1.0";
