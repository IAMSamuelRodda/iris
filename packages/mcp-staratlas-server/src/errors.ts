/**
 * Custom error types for the MCP server
 */

export type ErrorCode =
  | "UNKNOWN_TOOL"
  | "INVALID_ARGS"
  | "INVALID_ADDRESS"
  | "RPC_ERROR"
  | "RATE_LIMITED"
  | "NOT_FOUND";

export class ToolError extends Error {
  constructor(
    message: string,
    public readonly code: ErrorCode
  ) {
    super(message);
    this.name = "ToolError";
  }
}
