# meta-agent

Dynamic Meta-Agent System: FastAPI + LangGraph + Google Gemini. Decomposes a goal into a DAG of subtasks, runs agents (researcher/coder/writer) with optional tool generation, and synthesizes results. SSE streaming, Redis shared state, Docker sandboxed tool execution.

## Setup

```bash
cp .env.example .env    # needs GEMINI_API_KEY
docker compose up -d    # Redis (required)
pip install -e ".[dev]"
```

`.env` is loaded manually in `src/main.py:8-15` and `scripts/*.py` — **not** via python-dotenv.

## Commands

| Action | Command |
|--------|---------|
| Run all tests | `.venv/bin/python -m pytest` |
| Run single test | `.venv/bin/python -m pytest tests/test_planner.py::TestPlanner::test_decompose_returns_subtasks -v` |
| Start server | `.venv/bin/python -m uvicorn src.main:app --reload` |
| E2E test | `.venv/bin/python scripts/e2e_test.py` (needs real API key + Redis) |

No linter, formatter, or typechecker configured. `pytest` uses `asyncio_mode = auto`.

## Architecture

```
POST /run → 202 {task_id} → background task
  Planner (Gemini → DAG of subtasks)
  → for each subtask: Spawner → Executor → Evaluator (retry up to 3×)
  → Synthesizer → SSE "complete" event
```

- **Subtask scheduling**: DAG-based; independent subtasks run in parallel via `asyncio.gather` (`orchestrator.py:157`)
- **SSE**: In-memory `asyncio.Queue` per task_id (`event_bus/bus.py`)
- **Shared state**: Redis — task/subtask statuses, summaries, trace log (trimmed to 1000 entries at `redis_store.py:91`)

## Singletons (module-level)

- `orchestrator` (`orchestrator.py:201`)
- `store` (`redis_store.py:101`)
- `event_bus` (`bus.py:23`)
- `tool_registry` (`tools/__init__.py:51`, pre-registers `web_search`, `file_reader`, `code_executor` at import time)

## Pipeline Logging

Every task run produces a detailed log file at `logs/{task_id}.log`. The log captures:
- **Planner**: prompt sent to Gemini, raw response, parsed subtasks
- **Orchestrator**: subtask scheduling, retry attempts, dependency resolution
- **Agents**: tool calls with args, tool results, LLM responses, output length
- **Evaluator**: pass/fail per subtask with reason
- **Synthesizer**: input summaries, LLM call, final result

Access via `from src.task_logger import get_logger, close_logger`.

## Testing patterns

- `conftest.py` sets `GEMINI_API_KEY=test-key` for all tests
- Unit tests mock LLM via `agent._llm = AsyncMock()` or `planner._llm = AsyncMock()`
- Route tests use `httpx.AsyncClient(transport=ASGITransport(app=app))`
- Integration tests (`test_integration.py`) are **skipped by default** — require a real `GEMINI_API_KEY`
- Agent subclasses (`ResearcherAgent`, `CoderAgent`, `WriterAgent`) are empty wrappers — test via `Agent` base

## Gotchas

- `web_search` uses **Wikipedia API** only. `file_reader` and `code_executor` are **stubs** returning placeholder messages
- Tool cleanup in e2e scripts accesses `tool_registry._tools` (private `dict`)
- Docker sandbox (`sandbox.Dockerfile`) exists but not auto-built; `Sandbox.build()` must be called explicitly
- Default Gemini model: `gemini-3.1-flash-lite` (env `GEMINI_MODEL`)
- **Week 4** (sandboxed tool generation) and **Week 5** (evaluation loop) are **not yet implemented**

## Key files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI entrypoint, manual .env load, Redis connect on startup |
| `src/api/routes.py` | `POST /run`, `GET /tasks/{id}`, `GET /tasks/{id}/stream` (SSE) |
| `src/meta_agent/orchestrator.py` | Core loop: DAG scheduling, retry, event emission |
| `src/meta_agent/planner.py` | Gemini → subtask list; JSON parsing with code-fence/ bracket fallback |
| `src/factory/agent_factory.py` | Creates agents; resolves tools; generates missing tools via LLM |
| `src/agents/base.py` | Agent run loop: LLM + tool calls (max 10 rounds) + message history |
| `src/tools/generator.py` | LLM generates Python function → tests in Docker → registers on pass |
| `src/tools/sandbox.py` | Docker sandbox: `--network none --memory 256m --pids-limit 50`, 30s timeout |
| `src/task_logger.py` | Per-task pipeline logger: writes `logs/{task_id}.log` |
| `config/agents.yaml` | System prompts for researcher, coder, writer |
| `plan.md` | Full architecture doc and build plan |
