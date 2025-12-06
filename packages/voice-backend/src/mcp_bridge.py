"""
MCP Bridge - Connect IRIS to MCP servers (Todoist, etc.) via stdio.

Directly spawns MCP servers and communicates via JSON-RPC over stdio.
This bypasses lazy-mcp proxy for simpler setup.

SETUP:
======
1. Add TODOIST_API_TOKEN to ~/.config/iris/secrets.env
2. MCP servers are spawned on-demand

Usage:
    from src.mcp_bridge import MCPBridge, get_mcp_tools, execute_mcp_tool

    # Check if Todoist is configured
    bridge = MCPBridge()
    print(bridge.is_available())

    # Execute a tool
    result = execute_mcp_tool("mcp_create_reminder", {
        "content": "Check fleet fuel",
        "due_string": "in 4 hours"
    })

Architecture:
    IRIS → MCPBridge → stdio → todoist_mcp.py → Todoist API
"""

import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_secrets() -> dict[str, str]:
    """Load secrets from ~/.config/iris/secrets.env"""
    secrets = {}
    secrets_path = Path.home() / ".config" / "iris" / "secrets.env"

    if secrets_path.exists():
        try:
            with open(secrets_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        secrets[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"[MCP] Failed to load secrets: {e}")

    return secrets


_secrets = _load_secrets()
# Accept both KEY and TOKEN naming conventions
TODOIST_API_TOKEN = (
    _secrets.get("TODOIST_API_TOKEN") or
    _secrets.get("TODOIST_API_KEY") or
    os.environ.get("TODOIST_API_TOKEN") or
    os.environ.get("TODOIST_API_KEY") or
    ""
)

# Path to MCP servers
MCP_SERVERS_PATH = Path.home() / ".claude" / "mcp-servers"


class MCPStdioClient:
    """
    Simple MCP client that communicates via stdio JSON-RPC.
    """

    def __init__(self, command: list[str], env: dict[str, str] = None):
        self.command = command
        self.env = {**os.environ, **(env or {})}
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()

    def _ensure_started(self):
        """Start the MCP server process if not running."""
        if self._process is None or self._process.poll() is not None:
            logger.info(f"[MCP] Starting: {' '.join(self.command)}")
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
                bufsize=1,
            )
            # Initialize MCP connection
            self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "iris", "version": "0.1.0"}
            })

    def _send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request and get response."""
        with self._lock:
            self._ensure_started()

            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params
            }

            try:
                self._process.stdin.write(json.dumps(request) + "\n")
                self._process.stdin.flush()

                # Read response
                response_line = self._process.stdout.readline()
                if response_line:
                    return json.loads(response_line)
                return {"error": "No response from MCP server"}

            except Exception as e:
                logger.error(f"[MCP] Request failed: {e}")
                return {"error": str(e)}

    def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool."""
        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        if "error" in result:
            return f"MCP error: {result['error']}"

        # Extract content from MCP response
        content = result.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(content)

        return json.dumps(result.get("result", result))

    def close(self):
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            self._process = None


class MCPBridge:
    """
    Bridge to MCP servers for external tool access.

    Manages connections to MCP servers (Todoist, etc.) via stdio.
    """

    def __init__(self):
        self._clients: dict[str, MCPStdioClient] = {}
        self._available = None

    def is_available(self) -> bool:
        """Check if Todoist MCP is configured."""
        if self._available is not None:
            return self._available

        # Check for API token
        if not TODOIST_API_TOKEN:
            logger.info("[MCP] TODOIST_API_TOKEN not configured")
            self._available = False
            return False

        # Check for MCP server
        todoist_server = MCP_SERVERS_PATH / "todoist" / "todoist_mcp.py"
        if not todoist_server.exists():
            logger.warning(f"[MCP] Todoist server not found: {todoist_server}")
            self._available = False
            return False

        self._available = True
        logger.info("[MCP] Todoist MCP available")
        return True

    def _get_todoist_client(self) -> MCPStdioClient:
        """Get or create Todoist MCP client."""
        if "todoist" not in self._clients:
            venv_python = MCP_SERVERS_PATH / "todoist" / ".venv" / "bin" / "python"
            server_script = MCP_SERVERS_PATH / "todoist" / "todoist_mcp.py"

            self._clients["todoist"] = MCPStdioClient(
                command=[str(venv_python), str(server_script)],
                env={"TODOIST_API_TOKEN": TODOIST_API_TOKEN}
            )

        return self._clients["todoist"]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Execute a Todoist MCP tool.

        Args:
            tool_name: Tool name (e.g., "todoist_create_task")
            arguments: Tool arguments

        Returns:
            Tool result as string
        """
        if not self.is_available():
            return "Todoist not configured. Add TODOIST_API_TOKEN to ~/.config/iris/secrets.env"

        try:
            client = self._get_todoist_client()
            logger.info(f"[MCP] Calling {tool_name}({arguments})")
            result = client.call_tool(tool_name, arguments)
            logger.info(f"[MCP] Result: {result[:100]}...")
            return result

        except Exception as e:
            logger.error(f"[MCP] Failed to execute {tool_name}: {e}")
            return f"MCP tool failed: {str(e)}"

    def close(self):
        """Close all MCP clients."""
        for client in self._clients.values():
            client.close()
        self._clients.clear()


# ==============================================================================
# Ollama Tool Definitions for MCP
# ==============================================================================

# These are exposed to Ollama as native tools, but execute via MCP bridge
MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mcp_create_reminder",
            "description": "Create a reminder/task for the user. Use when they say 'remind me to...', 'add a task...', or want to remember something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The reminder text (e.g., 'Check fleet fuel levels')",
                    },
                    "due_string": {
                        "type": "string",
                        "description": "When the reminder is due in natural language (e.g., 'in 4 hours', 'tomorrow at 3pm', 'next Monday')",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority 1-4 (1=urgent, 4=normal). Default 4.",
                    }
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_list_reminders",
            "description": "List the user's pending reminders/tasks. Use when they ask 'what do I need to do?', 'show my tasks', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Optional filter: 'today', 'overdue', or project name",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_complete_reminder",
            "description": "Mark a reminder/task as complete. Use when user says 'done with...', 'completed...', 'finished...'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to complete (from mcp_list_reminders)",
                    }
                },
                "required": ["task_id"],
            },
        },
    },
]


# Global bridge instance
_bridge: MCPBridge | None = None


def get_bridge() -> MCPBridge:
    """Get or create the global MCP bridge."""
    global _bridge
    if _bridge is None:
        _bridge = MCPBridge()
    return _bridge


def execute_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Execute an MCP tool by its IRIS-facing name.

    Maps IRIS tool names to Todoist MCP tool names:
    - mcp_create_reminder → todoist_create_task
    - mcp_list_reminders → todoist_list_tasks
    - mcp_complete_reminder → todoist_complete_task
    """
    bridge = get_bridge()

    # Map IRIS tool names to Todoist MCP tool names
    tool_mapping = {
        "mcp_create_reminder": ("todoist_create_task", {
            "content": arguments.get("content", ""),
            "due_string": arguments.get("due_string"),
            "priority": arguments.get("priority", 4),
        }),
        "mcp_list_reminders": ("todoist_list_tasks", {
            "filter": arguments.get("filter"),
        }),
        "mcp_complete_reminder": ("todoist_complete_task", {
            "task_id": arguments.get("task_id"),
        }),
    }

    if name not in tool_mapping:
        return f"Unknown MCP tool: {name}"

    tool_name, mapped_args = tool_mapping[name]

    # Remove None values
    mapped_args = {k: v for k, v in mapped_args.items() if v is not None}

    return bridge.execute(tool_name, mapped_args)


def get_mcp_tools() -> list[dict]:
    """
    Get MCP tool definitions for Ollama.

    Only returns tools if Todoist is configured.
    """
    bridge = get_bridge()

    if not bridge.is_available():
        logger.info("[MCP] Todoist not configured, MCP tools disabled")
        return []

    return MCP_TOOLS


def is_mcp_tool(name: str) -> bool:
    """Check if a tool name is an MCP tool."""
    return name.startswith("mcp_")


# ==============================================================================
# Testing
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("MCP Bridge Test")
    print("=" * 50)

    bridge = MCPBridge()

    print(f"\nlazy-mcp available: {bridge.is_available()}")

    if bridge.is_available():
        print("\nBrowsing tool categories:")
        categories = bridge.get_tools_in_category("")
        print(f"  Root: {categories.get('overview', 'N/A')[:100]}...")

        print("\nTodoist tools:")
        todoist = bridge.get_tools_in_category("todoist")
        print(f"  {todoist.get('overview', 'N/A')[:200]}...")

        print("\nMCP tools for Ollama:")
        tools = get_mcp_tools()
        for tool in tools:
            print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")
    else:
        print("\nTo test MCP integration:")
        print("  1. Start lazy-mcp: npx lazy-mcp")
        print("  2. Run this test again")

    print(f"\nMCP tool check:")
    print(f"  is_mcp_tool('mcp_create_reminder'): {is_mcp_tool('mcp_create_reminder')}")
    print(f"  is_mcp_tool('get_current_time'): {is_mcp_tool('get_current_time')}")
