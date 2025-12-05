"""
IRIS Native Tools - Ollama tool calling integration.

Tools are defined as JSON schemas and executed locally.
Pattern from: specs/RESEARCH-tool-integration-architecture.md

Usage:
    from src.tools import TOOLS, execute_tool

    # Pass TOOLS to Ollama /api/chat
    # If response has tool_calls, execute them:
    result = execute_tool(tool_name, arguments)
"""

import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

# API keys from environment
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")


# ==============================================================================
# Tool Definitions (JSON Schema for Ollama)
# ==============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time and date. Use when user asks what time it is, the current date, or day of the week.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone (e.g., 'Australia/Brisbane', 'America/New_York', 'UTC'). Defaults to local time if not specified.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations. Use for any math: arithmetic, percentages, unit conversions, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2', '15% of 200', '100 * 1.5')",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use when user asks about recent events, news, facts you don't know, or anything that might need up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'weather in Brisbane', 'latest news about Star Atlas', 'who won the 2024 election')",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of results to return (1-5, default 3)",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

# Models that support tool calling (prefix match)
TOOL_CAPABLE_MODELS = ["qwen2.5", "qwen2", "llama3.1", "llama3.2", "mistral", "mixtral"]


def supports_tools(model_name: str) -> bool:
    """Check if a model supports tool calling."""
    model_lower = model_name.lower()
    return any(model_lower.startswith(prefix) for prefix in TOOL_CAPABLE_MODELS)


# ==============================================================================
# Tool Implementations
# ==============================================================================


def _get_current_time(timezone: str | None = None) -> str:
    """Get current time, optionally in a specific timezone."""
    try:
        if timezone:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
            tz_name = timezone
        else:
            now = datetime.now()
            tz_name = "local time"

        # Format: "3:45 PM on Friday, December 6th, 2025"
        day = now.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        time_str = now.strftime(f"%-I:%M %p on %A, %B {day}{suffix}, %Y")
        return f"It's {time_str} ({tz_name})"

    except Exception as e:
        logger.warning(f"[Tools] Timezone error: {e}")
        # Fallback to local time
        now = datetime.now()
        day = now.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        time_str = now.strftime(f"%-I:%M %p on %A, %B {day}{suffix}, %Y")
        return f"It's {time_str} (local time)"


def _calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # Handle percentage syntax first: "15% of 200" -> "0.15 * 200"
        expr = expression.lower()
        if "% of" in expr:
            parts = expr.split("% of")
            if len(parts) == 2:
                try:
                    percent = float(parts[0].strip())
                    value = float(parts[1].strip())
                    result = (percent / 100) * value
                    return f"{expression} = {result:g}"
                except ValueError:
                    pass

        # Handle standalone percentage: "15%" -> 0.15
        if "%" in expression:
            expr = expression.replace("%", "/100")
        else:
            expr = expression

        # Sanitize: only allow safe characters for eval
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expr):
            return f"Cannot evaluate: expression contains invalid characters"

        # Evaluate safely (no builtins, limited scope)
        result = eval(expr, {"__builtins__": {}}, {})
        return f"{expression} = {result:g}"

    except ZeroDivisionError:
        return "Cannot divide by zero"
    except Exception as e:
        return f"Cannot calculate: {str(e)}"


def _web_search(query: str, count: int = 3) -> str:
    """Search the web using Brave Search API."""
    if not BRAVE_API_KEY:
        return (
            "Web search is not configured. To enable it:\n"
            "1. Get a free API key at https://brave.com/search/api/\n"
            "2. Set BRAVE_API_KEY environment variable\n"
            "3. Restart IRIS"
        )

    # Clamp count to 1-5
    count = max(1, min(5, count))

    try:
        logger.info(f"[Tools] Web search: '{query}' (count={count})")

        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={
                "q": query,
                "count": count,
                "safesearch": "moderate",
            },
            timeout=10,
        )

        if response.status_code == 401:
            return "Web search API key is invalid. Please check your BRAVE_API_KEY."
        elif response.status_code == 429:
            return "Web search rate limit reached. Please try again later."
        elif response.status_code != 200:
            logger.error(f"[Tools] Brave API error: {response.status_code} {response.text}")
            return f"Web search failed (HTTP {response.status_code})"

        data = response.json()
        web_results = data.get("web", {}).get("results", [])

        if not web_results:
            return f"No results found for '{query}'"

        # Format results for LLM consumption
        results = []
        for i, result in enumerate(web_results[:count], 1):
            title = result.get("title", "No title")
            description = result.get("description", "No description")
            url = result.get("url", "")
            results.append(f"{i}. {title}\n   {description}\n   URL: {url}")

        return f"Search results for '{query}':\n\n" + "\n\n".join(results)

    except requests.Timeout:
        return "Web search timed out. Please try again."
    except requests.RequestException as e:
        logger.error(f"[Tools] Web search error: {e}")
        return f"Web search failed: {str(e)}"
    except Exception as e:
        logger.error(f"[Tools] Web search unexpected error: {e}")
        return f"Web search error: {str(e)}"


# ==============================================================================
# Tool Execution
# ==============================================================================

# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_current_time": _get_current_time,
    "calculate": _calculate,
    "web_search": _web_search,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Execute a tool by name with given arguments.

    Args:
        name: Tool name (must match a key in TOOL_FUNCTIONS)
        arguments: Dict of arguments to pass to the tool

    Returns:
        Tool result as a string
    """
    if name not in TOOL_FUNCTIONS:
        logger.warning(f"[Tools] Unknown tool: {name}")
        return f"Error: Unknown tool '{name}'"

    try:
        logger.info(f"[Tools] Executing {name}({arguments})")
        result = TOOL_FUNCTIONS[name](**arguments)
        logger.info(f"[Tools] Result: {result}")
        return result
    except Exception as e:
        logger.error(f"[Tools] Error executing {name}: {e}")
        return f"Error executing {name}: {str(e)}"


def get_tool_names() -> list[str]:
    """Get list of available tool names."""
    return list(TOOL_FUNCTIONS.keys())


# ==============================================================================
# Testing
# ==============================================================================

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    print("Testing tools:")
    print(f"  Time: {execute_tool('get_current_time', {})}")
    print(f"  Time (UTC): {execute_tool('get_current_time', {'timezone': 'UTC'})}")
    print(f"  Calc: {execute_tool('calculate', {'expression': '2 + 2'})}")
    print(f"  Calc: {execute_tool('calculate', {'expression': '15% of 200'})}")
    print(f"  Calc: {execute_tool('calculate', {'expression': '100 * 1.5'})}")

    print(f"\nWeb search test:")
    if BRAVE_API_KEY:
        print(f"  API key: configured")
        result = execute_tool('web_search', {'query': 'Star Atlas game', 'count': 2})
        print(f"  Result:\n{result}")
    else:
        print(f"  API key: NOT configured (set BRAVE_API_KEY to test)")
        print(f"  Without key: {execute_tool('web_search', {'query': 'test'})}")

    print(f"\nTool-capable models check:")
    for model in ["qwen2.5:7b", "llama3.1:8b", "mistral:7b", "phi3:mini"]:
        print(f"  {model}: {supports_tools(model)}")

    print(f"\nAvailable tools: {get_tool_names()}")
