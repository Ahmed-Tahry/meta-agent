import asyncio
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

from src.meta_agent.orchestrator import orchestrator
from src.shared_state.redis_store import store
from src.tools import tool_registry


GOAL = (
    "Count how many vowels are in the string 'hello world custom tool test'. "
    "Write a custom Python tool that counts vowels in a text. "
    "Use the tool to perform the count. Then write a short report with the result."
)


async def main():
    # Clean up any tool registrations from previous runs
    prebuilt = {"web_search", "file_reader", "code_executor"}
    for name in list(tool_registry.list_tools()):
        if name not in prebuilt:
            tool_registry._tools.pop(name, None)
            print(f"  cleaned up leftover tool: {name}")

    await store.connect()

    task_id = f"e2e_{int(time.time())}"

    print(f"Task ID: {task_id}")
    print(f"Goal: {GOAL}")

    orchestrator.start(GOAL, task_id)

    while True:
        status = await store.get_task_status(task_id)
        print(f"  status: {status}")
        if status in ("done", "failed"):
            break
        await asyncio.sleep(2)

    result = await store.get_result(task_id)
    print(f"\n=== FINAL RESULT ===")
    print(result)
    print()

    trace = await store.get_trace(task_id)
    print(f"\n=== TRACE ({len(trace)} events) ===")
    for entry in trace:
        t = entry.get("type", "")
        if t in ("plan", "agent_start", "agent_done", "tool_call_limit_reached"):
            preview = json.dumps(entry, default=str)[:300]
            print(f"  {t}: {preview}")

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
