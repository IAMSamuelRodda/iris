#!/usr/bin/env python3
"""
Test Todoist tool triggering with three tiers of prompting.

Tests whether the LLM correctly identifies when to use todoist_create_task
based on varying levels of explicitness in the user prompt.
"""

import json
import requests
import logging
from src.tools import TOOLS, execute_tool, supports_tools, TODOIST_API_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:7b"

SYSTEM_PROMPT = """You are IRIS, a voice assistant.

TOOLS AVAILABLE:
- todo_add: Track tasks during THIS session only (temporary)
- todoist_create_task: Create PERSISTENT reminders in Todoist (survives after conversation)
- todoist_list_tasks: List user's Todoist tasks
- get_current_time: Get current time/date

IMPORTANT DISTINCTIONS:
- "remind me" / "reminder" / "don't forget" → use todoist_create_task (persistent)
- "track this" / "add to my session list" → use todo_add (temporary)

When user asks for a reminder, use todoist_create_task with appropriate content and due_string."""

# Three tiers of prompting
TEST_PROMPTS = [
    {
        "tier": 1,
        "description": "Vague - just asks for reminder",
        "prompt": "Hey, remind me to check the fleet fuel levels",
        "expected_tool": "todoist_create_task",
    },
    {
        "tier": 2,
        "description": "Direct - mentions Todoist",
        "prompt": "Can you create a reminder in Todoist to review the mining routes?",
        "expected_tool": "todoist_create_task",
    },
    {
        "tier": 3,
        "description": "Detailed - explicit with timing",
        "prompt": "Add a task to my Todoist to check Star Atlas marketplace prices, and set it for tomorrow morning",
        "expected_tool": "todoist_create_task",
    },
]


def call_llm_with_tools(prompt: str) -> dict:
    """Call Ollama with tools and return the response."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "tools": TOOLS,
        "options": {"num_predict": 150},
    }

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=60,
    )

    return response.json()


def run_test(test: dict, execute: bool = False) -> dict:
    """Run a single test and return results."""
    print(f"\n{'='*60}")
    print(f"TIER {test['tier']}: {test['description']}")
    print(f"{'='*60}")
    print(f"Prompt: \"{test['prompt']}\"")
    print(f"Expected tool: {test['expected_tool']}")
    print("-" * 60)

    result = call_llm_with_tools(test["prompt"])

    message = result.get("message", {})
    tool_calls = message.get("tool_calls", [])
    content = message.get("content", "")

    # Analyze result
    tool_used = None
    tool_args = None

    if tool_calls:
        tool_call = tool_calls[0]
        tool_used = tool_call.get("function", {}).get("name")
        tool_args = tool_call.get("function", {}).get("arguments", {})

        print(f"✓ Tool called: {tool_used}")
        print(f"  Arguments: {json.dumps(tool_args, indent=2)}")

        # Execute the tool if requested
        if execute and tool_used:
            print(f"\n  Executing tool...")
            tool_result = execute_tool(tool_used, tool_args)
            print(f"  Result: {tool_result}")
    else:
        print(f"✗ No tool called")
        print(f"  Response: {content[:200]}...")

    success = tool_used == test["expected_tool"]
    print(f"\nResult: {'PASS ✓' if success else 'FAIL ✗'}")

    return {
        "tier": test["tier"],
        "prompt": test["prompt"],
        "expected": test["expected_tool"],
        "actual": tool_used,
        "arguments": tool_args,
        "success": success,
    }


def main():
    print("\n" + "=" * 60)
    print("TODOIST TOOL TRIGGERING TEST")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Todoist configured: {bool(TODOIST_API_TOKEN)}")
    print(f"Tools available: {[t['function']['name'] for t in TOOLS]}")

    # Check model supports tools
    if not supports_tools(MODEL):
        print(f"\n⚠ Warning: {MODEL} may not support tool calling")

    # Ask user if they want to execute tools (creates real tasks)
    print("\n" + "-" * 60)
    execute = input("Execute tools (creates REAL Todoist tasks)? [y/N]: ").lower() == 'y'

    results = []
    for test in TEST_PROMPTS:
        result = run_test(test, execute=execute)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  Tier {r['tier']}: {status} (expected: {r['expected']}, got: {r['actual']})")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All tiers passed! LLM correctly triggers Todoist tool.")
    else:
        print("\n⚠ Some tiers failed. May need prompt engineering in system prompt.")


if __name__ == "__main__":
    main()
