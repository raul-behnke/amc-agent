# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZOI Agent Framework (ZAF) — operational framework for AI-driven commercial agents. The first production agent is **Lucas SDR**, a WhatsApp-based pre-qualification chatbot for AMC Veículos (a car dealership). It receives leads from GoHighLevel (GHL) CRM webhooks, qualifies them through structured conversation, consults real vehicle inventory, syncs data back to GHL, and performs handoff to human sales reps.

## Commands

```bash
# Run dev server locally
source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000

# Full sandbox (server + ngrok for GHL webhook testing)
./scripts/start_dev.sh

# Docker
docker-compose up --build

# Lint
ruff check .
ruff format .
```

## Architecture

```
GHL Webhook → api/webhooks/chat.py → runtime/orchestrator.py → agents/lucas.py
                                    ↓
                              tools/ (inventory, qualification, crm, faq)
                                    ↓
                              services/ghl.py (CRM adapter)
```

**Flow**: GHL sends WhatsApp messages to `POST /webhook/chat`. The webhook extracts the payload, validates security tags, and dispatches to a background task. The orchestrator instantiates the Lucas agent with session-scoped tools, runs it async via Agno, and sends the reply back through GHL API.

### Key modules

- **`agents/lucas.py`** — Agent factory (`create_lucas_agent`). Builds an Agno `Agent` with OpenAI model, session-persistent SqliteDb, and tools with injected `session_id`. Tools are wrapped in closures via `_make_agent_tools()` so session context is bound at creation time.
- **`prompts/lucas_sdr.py`** — All agent personality and behavioral instructions live here, separate from agent code. Prompts must NOT contain hard business rules.
- **`runtime/orchestrator.py`** — Central message processor. Handles GHL message buffering (detects unanswered messages) and async agent execution.
- **`services/ghl.py`** — The ONLY place that touches the GoHighLevel API. Provides both sync (for Agno tools) and async (for FastAPI handlers) methods. Everything else goes through this adapter.
- **`tools/`** — Stateless functions that the agent calls. `inventory.py` fetches real stock via GHL, `qualification.py` manages in-memory lead state, `crm.py` syncs to GHL contacts/opportunities, `faq.py` is a static knowledge base.
- **`state/lead_model.py`** — Pydantic model with `LeadStatus` enum (NEW_LEAD → QUALIFYING → QUALIFIED → SCHEDULING → SCHEDULED → HANDOFF) and auto-calculated completeness score.
- **`api/schemas.py`** — All request/response Pydantic models. `ChatRequest` uses `extra="allow"` to handle the variable GHL webhook payload.

### Session state

Lead qualification data is held in-memory via `_lead_states` dict in `tools/qualification.py`. Agent conversation history uses Agno's built-in SqliteDb session persistence (`data/agent_sessions.db`). Both are keyed by `session_id` (which is the GHL contact ID).

## Conventions

- **Language**: Code comments, docstrings, and logs are in English. User-facing agent responses and prompts are in Brazilian Portuguese.
- **Async by default** for API handlers; sync wrappers available for Agno tool execution (Agno runs tools synchronously).
- **Type hints required** on all function signatures.
- **Pydantic** for all data models and API schemas.
- **Loguru** for structured logging — never use `print()`.
- **Services are adapters** — `services/ghl.py` is the only module that makes HTTP requests to GHL. Never access external APIs directly from tools or agents.
- **Tools are stateless** — they receive `session_id` via closure injection from `_make_agent_tools()`, never from global state.
- **GHL_REQUIRED_TAG** env var controls which contacts the agent responds to (security gate for sandbox/production).

## Environment Variables

Required in `.env`: `OPENAI_API_KEY`, `OPENAI_MODEL`, `GHL_PIT_TOKEN`, `GHL_LOCATION_ID`, `GHL_INVENTORY_CUSTOM_VALUE_ID`. Optional: `GHL_REQUIRED_TAG`, `GHL_PIPELINE_ID`, `GHL_STAGE_*`.
