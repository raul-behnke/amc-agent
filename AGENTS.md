# AGENTS.md

Quick-reference for AI agents working in this repo. Read `CLAUDE.md` for full context.

## Commands

```bash
source venv/bin/activate                         # always activate venv first
uvicorn api.main:app --host 0.0.0.0 --port 8000  # dev server
./scripts/start_dev.sh                           # server + ngrok sandbox
docker-compose up --build                        # containerized (Postgres + Redis + API)
ruff check .                                     # lint
ruff format .                                    # format
python -m pytest tests/                          # run tests (stdlib unittest, no pytest config)
python -m pytest tests/test_qualification.py     # single test file
python tests/test_qualification.py               # also works (unittest.main)
```

## Architecture (read this before editing)

```
GHL Webhook
  → api/webhooks/chat.py      (payload extraction, tag validation, background dispatch)
  → runtime/orchestrator.py   (message buffering, intent extraction, context injection, agent invocation)
  → agents/lucas.py           (Agno Agent factory with session-scoped tool closures)
  → tools/                    (stateless functions called by agent)
  → services/ghl.py           (ONLY module that touches GHL API — never bypass)
```

Two sub-agents run per message: the **Intent Extractor** (`runtime/intent_extractor.py`) silently extracts facts/triggers, then the **Lucas SDR agent** (`agents/lucas.py`) generates the reply.

## Critical conventions

- **`services/ghl.py` is the sole GHL adapter.** Never call GHL HTTP endpoints from tools, agents, or webhooks. Use the sync (`_ghl_request_sync`) or async (`_ghl_request_async`) helpers there.
- **Tools receive `session_id` via closure injection** in `_make_agent_tools()`, never from globals or arguments.
- **Prompts live in `prompts/lucas_sdr.py`** only. Do not put behavioral instructions in agent code.
- **Lead state is in-memory** (`_lead_states` dict in `tools/qualification.py`). Not persisted to disk — lost on restart. Agent conversation history is in SQLite (`data/agent_sessions.db`).
- **`session_id` = GHL contact ID.** Used to key both lead state and agent session DB.
- **Agent output goes to WhatsApp** — `markdown=False` on the agent, `**` is converted to `*`, and URLs/markdown images are stripped from replies.
- **User-facing text is Brazilian Portuguese.** Code, comments, logs are English.
- **Use Loguru**, never `print()`.

## Testing

- Tests use `unittest` (stdlib), not pytest fixtures. Run with `python -m pytest` or `python -m unittest`.
- Tests that touch lead state call `_lead_states.clear()` in `setUp()` to avoid cross-test contamination.
- Integration tests requiring GHL API are skipped or mocked — there are no live external calls in the test suite.
- The QA battery script: `python scripts/run_lucas_qa_battery.py`.

## Gotchas

- `.env` is required with at minimum: `OPENAI_API_KEY`, `OPENAI_MODEL`, `GHL_PIT_TOKEN`, `GHL_LOCATION_ID`, `GHL_INVENTORY_CUSTOM_VALUE_ID`. Copy from `.env.example` and fill in.
- `GHL_REQUIRED_TAG` controls which GHL contacts the agent responds to (security gate). Without it, agent may respond to all contacts or none depending on webhook logic.
- Agno tools run synchronously. The orchestrator uses `agent.arun()` (async), but tool closures must be sync wrappers around async service methods.
- The `api/main.py` inserts the project root into `sys.path` and loads `.env` via `python-dotenv` — imports work without `PYTHONPATH` tricks when launched via uvicorn.
- `.gitignore` excludes `*.log` and `logs/` — don't commit log files.
