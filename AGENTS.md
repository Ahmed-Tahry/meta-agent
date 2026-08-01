# meta-agent

Dynamic Meta-Agent System: FastAPI + LangGraph + Google Gemini. Decomposes a goal into a DAG of subtasks, runs agents (researcher/coder/writer) with optional tool generation, and synthesizes results. SSE streaming, Redis shared state, Docker sandboxed tool execution.

## Setup

```bash
cp .env.example .env    # needs GEMINI_API_KEY
docker compose up -d redis   # Redis only for local dev; `up -d` (bare) also builds & starts the app
pip install -e ".[dev]"
```

`.env` is loaded manually in `src/main.py:8-15` and `scripts/*.py` — **not** via python-dotenv.

## Commands

| Action | Command |
|--------|---------|
| Run all tests | `.venv/bin/python -m pytest` |
| Run single test | `.venv/bin/python -m pytest tests/test_planner.py::TestPlanner::test_decompose_returns_subtasks -v` |
| Lint + format check | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` |
| Auto-fix lint + format | `.venv/bin/ruff check . --fix && .venv/bin/ruff format .` |
| Install git hooks | `.venv/bin/pre-commit install` |
| Run all hooks | `.venv/bin/pre-commit run --all-files` |
| Start server | `.venv/bin/python -m uvicorn src.main:app --reload` |
| Run with Docker | `docker compose up --build` (needs `.env` with `GEMINI_API_KEY`) |
| E2E test | `.venv/bin/python scripts/e2e_test.py` (needs real API key + Redis) |

Lint/format tooling: **ruff** (lint rules `E/F/I/UP`, line-length 100) via pre-commit hooks (`.pre-commit-config.yaml`, pinned to ruff `v0.16.1`) and CI (`.github/workflows/ci.yml` → lint → test → build image). No typechecker configured. `pytest` uses `asyncio_mode = auto`. CI: integration tests skip without a real `GEMINI_API_KEY`; the sandbox e2e test (`test_sandbox.py::test_real_sandbox_e2e`) runs on ubuntu runners and builds the qiskit image (~2-4 min).

## Architecture

```
POST /run → 202 {task_id} → background task
  Planner (Gemini → DAG of subtasks)
  → for each subtask: Spawner → Executor → Evaluator (retry up to 3×)
  → Synthesizer → SSE "complete" event
```

- **Subtask scheduling**: DAG-based; independent subtasks run in parallel via `asyncio.gather` (`orchestrator.py:199`)
- **SSE**: In-memory `asyncio.Queue` per task_id (`event_bus/bus.py`)
- **Shared state**: Redis — task/subtask statuses, summaries, trace log (trimmed to 1000 entries at `redis_store.py:91`)

## Singletons (module-level)

- `orchestrator` (`orchestrator.py:255`)
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

- `web_search` uses **Wikipedia API** only. `file_reader` runs **un-sandboxed on the host** and can read any readable local file
- Subtask tools can be pipelines: a tool name containing `|` chains tools via `ToolComposer` (`src/tools/composer.py`), registered under the `|`-joined name (`agent_factory.py:35-48`)
- `code_executor` and `ToolGenerator._make_fn` run Python code in Docker sandbox (`--network none --memory 256m --pids-limit 50`, 30s timeout). Docker is required at runtime, not just tests.
- Docker sandbox image auto-builds on first use by `code_executor` or `ToolGenerator`; `Sandbox.build()` can be called explicitly
- In the Docker setup (`docker compose up --build`), the app container mounts the host `/var/run/docker.sock` (`:ro`) and sandboxes run through the **host** daemon. `SANDBOX_MOUNT=<volume>:<dir>` switches `Sandbox.run` to named-volume tmp mounts, and `SANDBOX_DOCKERFILE_DIR` points `Sandbox.build` at the in-image `docker/` dir (both auto-set in compose; host/dev behavior unchanged when unset — module-relative fallback)
- `Sandbox.cleanup()` is dead code — if ever invoked it runs `docker image prune -f` against the connected daemon (the host's, when containerized)
- The containerized app runs a **single** uvicorn worker (in-memory SSE bus, `orchestrator._tasks`) — do not scale or add `--workers`
- `src/web/` ships `dashboard.html` via `[tool.setuptools.package-data]` + empty `src/web/__init__.py` — keep both if you add web assets
- Tool cleanup in e2e scripts accesses `tool_registry._tools` (private `dict`)
- Default Gemini model: `gemini-3.1-flash-lite` (env `GEMINI_MODEL`)
- All tunables (`MAX_TOOL_CALLS`, `MAX_RETRIES`, `LLM_TIMEOUT`, `SANDBOX_TIMEOUT`, …) are env vars read **at import time** in `src/config.py` — changing them requires a process restart (no runtime re-read)
- `src/web/dashboard.html` is read **once at startup** (`src/main.py:30-32`) into a module global — edits need a server restart; in Docker, rebuild the image
- `scripts/test_quantum.py` mirrors `scripts/e2e_test.py`: manual `.env` load, private `tool_registry._tools` cleanup, needs real API key + Redis
- `plan.md` is gitignored/untracked — local-only architecture doc, not in the repo
- **Week 5** (evaluation loop) is **not yet implemented**

## Key files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI entrypoint, manual .env load, Redis connect on startup |
| `src/config.py` | All env-var tunables (model, timeouts, retries) — read at import time |
| `src/api/routes.py` | `POST /run`, `GET /tasks/{id}`, `GET /tasks/{id}/stream` (SSE) |
| `src/meta_agent/orchestrator.py` | Core loop: DAG scheduling, retry, event emission |
| `src/meta_agent/planner.py` | Gemini → subtask list; JSON parsing with code-fence/ bracket fallback |
| `src/factory/agent_factory.py` | Creates agents; resolves tools; generates missing tools via LLM |
| `src/agents/base.py` | Agent run loop: LLM + tool calls (max 10 rounds) + message history |
| `src/tools/generator.py` | LLM generates Python function → tests in Docker → registers on pass; generated tools also execute in Docker sandbox |
| `src/tools/composer.py` | Chains tools into pipelines (tool names joined with `\|`) |
| `src/tools/sandbox.py` | Docker sandbox: `--network none --memory 256m --pids-limit 50`, 30s timeout |
| `src/task_logger.py` | Per-task pipeline logger: writes `logs/{task_id}.log` |
| `config/agents.yaml` | System prompts for researcher, coder, writer |
| `plan.md` | Full architecture doc and build plan |
