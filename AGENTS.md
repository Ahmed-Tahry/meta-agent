# meta-agent

FastAPI + LangGraph + Gemini. Decomposes a goal into a DAG of subtasks, runs agents (any role, dynamic tools) with Docker sandbox, synthesizes results. SSE streaming, Redis shared state.

## Setup

```bash
cp .env.example .env    # needs GEMINI_API_KEY; DOCKER_GID from `stat -c '%g' /var/run/docker.sock` for compose
docker compose up -d redis   # Redis only for local dev; bare `up -d` also builds & starts app
pip install -e ".[dev]"      # requires Python >=3.12 (pyproject.toml:5)
```

`.env` loaded manually in `src/main.py:8-15` and `scripts/*.py` — not via python-dotenv.

## Commands

| Action | Command |
|--------|---------|
| Run all tests | `.venv/bin/python -m pytest` |
| Single test | `.venv/bin/python -m pytest tests/test_planner.py::TestPlanner::test_decompose_returns_subtasks -v` |
| Lint + format check | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` |
| Auto-fix lint + format | `.venv/bin/ruff check . --fix && .venv/bin/ruff format .` |
| Hooks install/run | `.venv/bin/pre-commit install` / `.venv/bin/pre-commit run --all-files` |
| Start server | `.venv/bin/python -m uvicorn src.main:app --reload` |
| Run with Docker | `docker compose up --build` (needs `.env` with `GEMINI_API_KEY`) |
| E2E test | `.venv/bin/python scripts/e2e_test.py` (needs real API key + Redis) |

Ruff: `E/F/I/UP`, line-length 100 (`pyproject.toml:32-37`), pinned `v0.16.1` (`.pre-commit-config.yaml:14`). No typechecker. `pytest` `asyncio_mode = auto` (`pyproject.toml:30`). CI `.github/workflows/ci.yml`: `lint → test → build image`. Integration tests skip without real `GEMINI_API_KEY`; sandbox e2e (`test_sandbox.py::test_real_sandbox_e2e`) builds qiskit image (~2-4 min).

## Architecture

```
POST /run → 202 {task_id} → background task
  Planner (Gemini → DAG of subtasks)
  → for each subtask: Spawner → Executor → Evaluator (retry up to 3×)
  → Synthesizer → SSE "complete" event
```

- DAG scheduling: independent subtasks run in parallel via `asyncio.gather` (`src/meta_agent/orchestrator.py:243`)
- SSE: in-memory `asyncio.Queue` per task_id (`src/event_bus/bus.py:5-21`)
- Shared state: Redis — task/subtask statuses, summaries, trace log trimmed to 1000 (`src/shared_state/redis_store.py:93`)

## Singletons (module-level, do not re-instantiate)

- `orchestrator` (`src/meta_agent/orchestrator.py:311`)
- `store` (`src/shared_state/redis_store.py:103`)
- `event_bus` (`src/event_bus/bus.py:23`)
- `tool_registry` (`src/tools/__init__.py:51`, pre-registers `web_search`/`file_reader`/`code_executor` at `58-60`)

## Pipeline Logging

Every run writes `logs/{task_id}.log` (gitignored): planner prompt/response, orchestrator scheduling/retries, agent tool calls + LLM responses, evaluator pass/fail, synthesizer input/output. Use `from src.task_logger import get_logger, close_logger`.

## Testing

- `tests/conftest.py:3` sets `GEMINI_API_KEY=test-key` for all tests
- Mock LLM via `agent._llm = AsyncMock()` or `planner._llm = AsyncMock()`
- Route tests: `httpx.AsyncClient(transport=ASGITransport(app=app))`
- `tests/test_integration.py:13` skipped unless real `GEMINI_API_KEY` set (not `test-key`)
- `src/agents/base.py:15` is the only agent class — `AgentFactory` always returns `Agent` regardless of role (`src/factory/agent_factory.py:23-24`); roles/prompts are dynamic via `PromptBuilder` + `config/agents.yaml`

## Gotchas

- `web_search` is Wikipedia API only (`src/tools/prebuilt/web_search.py:5`). `file_reader` is un-sandboxed and can read any host file (`src/tools/prebuilt/file_reader.py:8`)
- Tool pipelines: name containing `|` chains via `ToolComposer` (`src/tools/composer.py`), auto-registered as `|`-joined name (`src/factory/agent_factory.py:35-48`)
- `code_executor` + `ToolGenerator._make_fn` run in Docker sandbox (`--network none --memory 256m --pids-limit 50`, 30s timeout via `SANDBOX_TIMEOUT` in `src/config.py:12`). Docker required at runtime; image `meta-agent-sandbox` auto-builds on first use (`Sandbox.build()` explicit)
- Compose mounts host `/var/run/docker.sock:ro` — sandboxes run via host daemon (root-equivalent). `SANDBOX_MOUNT=<volume>:<dir>` and `SANDBOX_DOCKERFILE_DIR` switch to named-volume mounts / in-image docker dir (auto-set in compose; unset = module-relative fallback in `src/tools/sandbox.py:6-11`)
- `Sandbox.cleanup()` is dead code — runs `docker image prune -f` on host daemon if called (`src/tools/sandbox.py:127-134`)
- Single uvicorn worker only — SSE bus (`event_bus._queues`) and `orchestrator._tasks` are in-memory; do not add `--workers` or scale app replicas (`docker-compose.yml:32`, `Dockerfile:36`)
- `src/web/dashboard.html` read once at startup into `DASHBOARD_HTML` (`src/main.py:30-32`) — edits need restart (rebuild image in Docker). Keep `src/web/__init__.py` + `[tool.setuptools.package-data]` (`pyproject.toml:43`) if adding web assets
- E2E scripts clean via private `tool_registry._tools` (`scripts/e2e_test.py:35`)
- Default model `gemini-3.1-flash-lite` (`src/config.py:5`, env `GEMINI_MODEL`)
- All tunables (`MAX_TOOL_CALLS`, `MAX_RETRIES`, `LLM_TIMEOUT`, `SANDBOX_TIMEOUT`, …) read at import in `src/config.py` — restart required to pick up changes
- `plan.md` is gitignored/untracked (local arch doc); `logs/` also gitignored. **Week 5** evaluation loop not yet implemented

## Key files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI entrypoint, manual .env load, Redis connect, dashboard serve |
| `src/config.py` | All env tunables — read at import |
| `src/api/routes.py` | `POST /run`, `GET /tasks/{id}`, `GET /tasks/{id}/stream` (SSE) |
| `src/meta_agent/orchestrator.py` | Core loop: DAG scheduling, retry, event emission |
| `src/meta_agent/planner.py` | Gemini → subtasks JSON; code-fence/bracket fallback parsing |
| `src/factory/agent_factory.py` | Creates agents; resolves/composes/generates tools |
| `src/agents/base.py` | Agent run loop: LLM + tool calls (max 10 rounds) |
| `src/tools/generator.py` | LLM generates Python fn → tests in Docker → registers; generated tools also sandboxed |
| `src/tools/composer.py` | Chains tools into pipelines (`|`-joined name) |
| `src/tools/sandbox.py` | Docker sandbox executor |
| `src/task_logger.py` | Per-task `logs/{task_id}.log` writer |
| `config/agents.yaml` | Optional base prompts for researcher/coder/writer (fallback if LLM prompt-builder fails) |
