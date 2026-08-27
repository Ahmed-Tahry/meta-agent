import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import load_env_file  # noqa: E402 - after sys.path fix

load_env_file(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.meta_agent.orchestrator import orchestrator  # noqa: E402 - after manual .env load
from src.shared_state.redis_store import store  # noqa: E402
from src.tools import tool_registry  # noqa: E402

# Clean up any leftover tools
prebuilt = {"web_search", "file_reader", "code_executor"}
for name in list(tool_registry.list_tools()):
    if name not in prebuilt:
        tool_registry._tools.pop(name, None)


async def main():
    await store.connect()

    goal = "i wanna know about quantum computers"
    import time

    task_id = f"test_{int(time.time())}"

    print(f"Task: {task_id}")
    print(f"Goal: {goal}")
    print()

    orchestrator.start(goal, task_id)

    # Poll for completion
    while True:
        status = await store.get_task_status(task_id)
        print(f"  status: {status}")
        if status in ("done", "failed"):
            break
        await asyncio.sleep(3)

    result = await store.get_result(task_id)
    print("\n=== RESULT ===")
    print(result[:500] if result else "(no result)")

    trace = await store.get_trace(task_id)
    print(f"\n=== TRACE ({len(trace)} events) ===")
    for entry in trace:
        t = entry.get("type", "")
        if t in ("plan", "agent_start", "agent_done", "tool_call_limit_reached"):
            preview = json.dumps(entry, default=str)[:200]
            print(f"  {t}: {preview}")

    # Count tool calls per agent
    from collections import Counter

    agent_tool_calls = Counter()
    for entry in trace:
        if entry.get("type") == "tool_call":
            agent_tool_calls[entry.get("agent_id", "?")] += 1
    print("\n=== TOOL CALLS ===")
    for agent_id, count in agent_tool_calls.most_common():
        print(f"  {agent_id}: {count} calls")

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
