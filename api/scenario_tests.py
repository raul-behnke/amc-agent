"""
Painel simples para acompanhar a execução dos cenários reais.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger

from api.schemas import ScenarioTestRunRequest
from tests.real_scenario_harness import (
    parse_real_scenarios,
    run_many_real_scenarios,
    write_reports,
)

router = APIRouter(prefix="/scenario-tests", tags=["scenario-tests"])

_jobs: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _build_job_state(job_id: str, payload: ScenarioTestRunRequest) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "status": "queued",
        "progress_pct": 0,
        "completed": 0,
        "total": 0,
        "current_scenario": None,
        "started_at": _now(),
        "finished_at": None,
        "limit": payload.limit,
        "simulator": payload.simulator,
        "max_turns": payload.max_turns,
        "max_parallel": payload.max_parallel,
        "results": [],
        "scenario_streams": {},
        "logs": ["Job criado."],
        "error": None,
        "report_markdown": None,
        "report_json": None,
    }


def _append_log(job: dict[str, Any], message: str) -> None:
    job["logs"].append(f"[{_now()}] {message}")
    job["logs"] = job["logs"][-120:]


def _public_job_view(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress_pct": job["progress_pct"],
        "completed": job["completed"],
        "total": job["total"],
        "current_scenario": job["current_scenario"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "limit": job["limit"],
        "simulator": job["simulator"],
        "max_turns": job["max_turns"],
        "max_parallel": job["max_parallel"],
        "results": job["results"],
        "scenario_streams": job["scenario_streams"],
        "logs": job["logs"],
        "error": job["error"],
        "report_markdown": job["report_markdown"],
        "report_json": job["report_json"],
    }


async def _run_job(job_id: str, payload: ScenarioTestRunRequest) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    _append_log(job, "Carregando cenários reais.")

    try:
        scenarios = parse_real_scenarios()
        if payload.limit is not None:
            scenarios = scenarios[: payload.limit]
        job["total"] = len(scenarios)
        _append_log(job, f"{len(scenarios)} cenário(s) selecionado(s).")

        def on_progress(event: dict[str, Any]) -> None:
            if event["event"] == "scenario_started":
                job["current_scenario"] = f"{event['scenario_id']} - {event['lead_name']}"
                job["scenario_streams"].setdefault(
                    event["scenario_id"],
                    {
                        "scenario_id": event["scenario_id"],
                        "lead_name": event["lead_name"],
                        "status": "running",
                        "score": None,
                        "summary": None,
                        "chat": [],
                        "events": [],
                    },
                )
                _append_log(job, f"Iniciado {job['current_scenario']}.")
                return

            if event["event"] == "conversation_turn":
                scenario_stream = job["scenario_streams"].setdefault(
                    event["scenario_id"],
                    {
                        "scenario_id": event["scenario_id"],
                        "lead_name": event["lead_name"],
                        "status": "running",
                        "score": None,
                        "summary": None,
                        "chat": [],
                        "events": [],
                    },
                )
                scenario_stream["chat"].append(
                    {
                        "role": event["role"],
                        "message": event["message"],
                        "attachments": event.get("attachments") or [],
                        "kind": event.get("kind"),
                        "at": _now(),
                    }
                )
                label = "Cliente" if event["role"] == "lead" else "Lucas"
                scenario_stream["events"].append(
                    f"[{_now()}] {label}: {event['message']}"
                )
                scenario_stream["events"] = scenario_stream["events"][-120:]
                return

            job["completed"] = event["index"]
            job["total"] = event["total"]
            job["progress_pct"] = int((event["index"] / max(event["total"], 1)) * 100)
            scenario_stream = job["scenario_streams"].setdefault(
                event["scenario_id"],
                {
                    "scenario_id": event["scenario_id"],
                    "lead_name": event["lead_name"],
                    "status": "running",
                    "score": None,
                    "summary": None,
                    "chat": [],
                    "events": [],
                },
            )
            scenario_stream["status"] = event["status"]
            scenario_stream["score"] = event["score"]
            scenario_stream["summary"] = event.get("summary")
            scenario_stream["events"].append(
                f"[{_now()}] Cenário concluído com status {event['status']} e nota {event['score']}."
            )
            scenario_stream["events"] = scenario_stream["events"][-120:]
            job["results"].append(
                {
                    "scenario_id": event["scenario_id"],
                    "lead_name": event["lead_name"],
                    "status": event["status"],
                    "score": event["score"],
                    "summary": event.get("summary"),
                }
            )
            _append_log(
                job,
                f"Concluído {event['scenario_id']} com status {event['status']} e nota {event['score']}.",
            )

        results = await run_many_real_scenarios(
            scenarios=scenarios,
            max_turns=payload.max_turns,
            simulator_mode=payload.simulator,
            progress_callback=on_progress,
            session_namespace=job_id,
            max_parallel=payload.max_parallel,
        )
        md_path, json_path = write_reports(results, slug=f"ui-{job_id}")
        job["status"] = "completed"
        job["finished_at"] = _now()
        job["current_scenario"] = None
        job["progress_pct"] = 100
        job["report_markdown"] = md_path.name
        job["report_json"] = json_path.name
        _append_log(job, "Execução finalizada.")
    except Exception as exc:
        logger.exception("Falha no job de cenários reais | job_id={job_id}", job_id=job_id)
        job["status"] = "failed"
        job["finished_at"] = _now()
        job["error"] = str(exc)
        _append_log(job, f"Erro: {exc}")


@router.get("/ui", response_class=HTMLResponse)
async def scenario_tests_ui() -> HTMLResponse:
    return HTMLResponse(_PAGE_HTML)


@router.post("/jobs")
async def create_scenario_test_job(payload: ScenarioTestRunRequest) -> dict[str, Any]:
    if payload.simulator not in {"auto", "llm", "rule"}:
        raise HTTPException(status_code=400, detail="simulator inválido")

    job_id = uuid4().hex[:8]
    _jobs[job_id] = _build_job_state(job_id, payload)
    asyncio.create_task(_run_job(job_id, payload))
    return _public_job_view(_jobs[job_id])


@router.get("/jobs/latest")
async def get_latest_job() -> dict[str, Any]:
    if not _jobs:
        raise HTTPException(status_code=404, detail="nenhum job encontrado")
    latest = next(reversed(_jobs.values()))
    return _public_job_view(latest)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job não encontrado")
    return _public_job_view(job)


_PAGE_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Lucas SDR • Cenários Reais</title>
  <style>
    :root {
      --bg: #f6f1e7;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #ded6c9;
      --accent: #b45309;
      --accent-2: #d97706;
      --ok: #15803d;
      --warn: #b45309;
      --bad: #b91c1c;
      --lead: #f3ede3;
      --lucas: #1f2937;
      --lucas-ink: #fff;
      --shadow: 0 18px 40px rgba(65, 44, 14, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(217, 119, 6, 0.16), transparent 28%),
        linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .wrap {
      max-width: 1360px;
      margin: 0 auto;
      padding: 32px 20px 60px;
    }
    .hero {
      display: grid;
      gap: 18px;
      margin-bottom: 22px;
    }
    .eyebrow {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--accent);
      font-weight: 700;
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 5vw, 62px);
      line-height: 0.95;
      max-width: 10ch;
    }
    .sub {
      max-width: 62ch;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.5;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 18px;
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 18px;
    }
    .form-grid,
    .main-grid,
    .inspector-grid {
      display: grid;
      gap: 12px;
    }
    .main-grid {
      gap: 18px;
    }
    .inspector-grid {
      grid-template-columns: 360px 1fr;
      align-items: start;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 14px;
      color: var(--muted);
    }
    input, select, button {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 11px 12px;
      font-size: 15px;
      background: #fff;
      color: var(--ink);
    }
    button {
      border: none;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: wait; }
    .status-strip {
      display: grid;
      gap: 14px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .stat {
      padding: 14px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.7);
    }
    .stat .k { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
    .stat .v { margin-top: 8px; font-size: 28px; font-weight: 700; }
    .bar-shell {
      position: relative;
      overflow: hidden;
      border-radius: 999px;
      height: 18px;
      background: #ece3d6;
      border: 1px solid var(--line);
    }
    .bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #d97706, #f59e0b);
      transition: width 0.35s ease;
    }
    .muted { color: var(--muted); }
    .links a { color: var(--accent); text-decoration: none; }
    .scenario-list {
      display: grid;
      gap: 10px;
      max-height: 780px;
      overflow: auto;
      padding-right: 4px;
    }
    .scenario-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: #fffaf2;
      cursor: pointer;
    }
    .scenario-card.active {
      border-color: var(--accent);
      box-shadow: inset 0 0 0 1px rgba(180, 83, 9, 0.2);
      background: #fff7eb;
    }
    .scenario-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }
    .scenario-summary {
      font-size: 14px;
      line-height: 1.35;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .ok { background: #dcfce7; color: var(--ok); }
    .partial { background: #fef3c7; color: var(--warn); }
    .fail { background: #fee2e2; color: var(--bad); }
    .chat-shell, .log-shell {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #fffaf2;
      padding: 14px;
    }
    .chat-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }
    .chat {
      display: grid;
      gap: 12px;
      min-height: 280px;
      max-height: 420px;
      overflow: auto;
      padding-right: 4px;
    }
    .bubble-row {
      display: flex;
    }
    .bubble-row.lead { justify-content: flex-start; }
    .bubble-row.lucas { justify-content: flex-end; }
    .bubble {
      max-width: 78%;
      border-radius: 18px;
      padding: 12px 14px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .bubble.lead {
      background: var(--lead);
      border-top-left-radius: 6px;
    }
    .bubble.lucas {
      background: var(--lucas);
      color: var(--lucas-ink);
      border-top-right-radius: 6px;
    }
    .bubble-label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
      opacity: 0.72;
    }
    .attachment {
      margin-top: 8px;
      font-size: 12px;
      opacity: 0.8;
    }
    .log {
      background: #1a1a1a;
      color: #e5e7eb;
      border-radius: 16px;
      padding: 14px;
      min-height: 220px;
      max-height: 320px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      line-height: 1.45;
      white-space: pre-wrap;
    }
    .empty {
      min-height: 180px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 14px;
      padding: 20px;
      background: rgba(255,255,255,0.4);
    }
    @media (max-width: 1080px) {
      .layout,
      .inspector-grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 860px) {
      .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .bubble { max-width: 92%; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="eyebrow">Lucas SDR • regressão comercial</div>
      <h1>Monitor de Cenários Reais</h1>
      <div class="sub">Acompanhe o andamento dos testes, abra cada cenário como um chat entre cliente e Lucas e veja o log vivo de cada movimentação durante a simulação.</div>
    </div>

    <div class="layout">
      <section class="panel">
        <h2>Nova Execução</h2>
        <div class="form-grid">
          <label>Quantidade de cenários
            <input id="limit" type="number" min="1" value="5" />
          </label>
          <label>Simulador do lead
            <select id="simulator">
              <option value="auto">auto</option>
              <option value="rule">rule</option>
              <option value="llm">llm</option>
            </select>
          </label>
          <label>Máximo de turnos
            <input id="maxTurns" type="number" min="1" max="20" value="6" />
          </label>
          <label>Paralelismo
            <input id="maxParallel" type="number" min="1" max="5" value="5" />
          </label>
          <button id="startBtn">Iniciar Testes</button>
          <div class="muted" id="jobMeta">Nenhum job em execução.</div>
        </div>
      </section>

      <section class="main-grid">
        <section class="panel status-strip">
          <div class="stats">
            <div class="stat"><div class="k">Status</div><div class="v" id="statusText">idle</div></div>
            <div class="stat"><div class="k">Progresso</div><div class="v" id="progressText">0%</div></div>
            <div class="stat"><div class="k">Concluídos</div><div class="v" id="countText">0/0</div></div>
            <div class="stat"><div class="k">Atual</div><div class="v" id="currentText">-</div></div>
          </div>
          <div class="bar-shell"><div class="bar-fill" id="barFill"></div></div>
          <div class="links muted" id="reportLinks"></div>
        </section>

        <section class="inspector-grid">
          <section class="panel">
            <h2>Cenários</h2>
            <div id="resultsList" class="scenario-list">
              <div class="empty">Sem cenários carregados ainda.</div>
            </div>
          </section>

          <section class="main-grid">
            <section class="panel chat-shell">
              <div class="chat-meta">
                <div>
                  <h2 id="chatTitle">Conversa</h2>
                  <div class="muted" id="chatSummary">Selecione um cenário para acompanhar o chat.</div>
                </div>
                <div id="chatBadge"></div>
              </div>
              <div id="chatBox" class="chat">
                <div class="empty">As mensagens do cliente e do Lucas vão aparecer aqui em tempo real.</div>
              </div>
            </section>

            <section class="panel log-shell">
              <h2>Movimentações do cenário</h2>
              <div id="scenarioLogBox" class="log">Selecione um cenário para ver o log detalhado.</div>
            </section>

            <section class="panel log-shell">
              <h2>Log do job</h2>
              <div id="jobLogBox" class="log">Aguardando início.</div>
            </section>
          </section>
        </section>
      </section>
    </div>
  </div>

  <script>
    let currentJobId = null;
    let currentJob = null;
    let pollHandle = null;
    let selectedScenarioId = null;

    function badgeClass(status) {
      if (!status) return "badge partial";
      if (status.includes("Aprovado")) return "badge ok";
      if (status.includes("Parcial")) return "badge partial";
      if (status.includes("Reprovado")) return "badge fail";
      return "badge partial";
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function buildScenarioIndex(job) {
      const map = {};
      (job.results || []).forEach((item) => { map[item.scenario_id] = item; });
      Object.entries(job.scenario_streams || {}).forEach(([scenarioId, stream]) => {
        map[scenarioId] = {
          scenario_id: scenarioId,
          lead_name: stream.lead_name,
          status: stream.status || "running",
          score: stream.score,
          summary: stream.summary,
        };
      });
      return Object.values(map).sort((a, b) => a.scenario_id.localeCompare(b.scenario_id));
    }

    function ensureSelectedScenario(job, orderedScenarios) {
      if (selectedScenarioId && (job.scenario_streams || {})[selectedScenarioId]) return;
      if (job.current_scenario) {
        const currentId = job.current_scenario.split(" - ")[0];
        if ((job.scenario_streams || {})[currentId]) {
          selectedScenarioId = currentId;
          return;
        }
      }
      if (orderedScenarios.length) {
        selectedScenarioId = orderedScenarios[orderedScenarios.length - 1].scenario_id;
      } else {
        selectedScenarioId = null;
      }
    }

    function renderScenarioList(job) {
      const items = buildScenarioIndex(job);
      ensureSelectedScenario(job, items);
      const resultsEl = document.getElementById("resultsList");
      if (!items.length) {
        resultsEl.innerHTML = '<div class="empty">Sem cenários carregados ainda.</div>';
        return;
      }
      resultsEl.innerHTML = items.map((item) => `
        <div class="scenario-card ${item.scenario_id === selectedScenarioId ? "active" : ""}" data-scenario-id="${item.scenario_id}">
          <div class="scenario-head">
            <div><strong>${escapeHtml(item.scenario_id)}</strong></div>
            <div class="${badgeClass(item.status)}">${escapeHtml(item.status || "em andamento")}</div>
          </div>
          <div>${escapeHtml(item.lead_name || "-")}</div>
          <div class="scenario-summary muted">${escapeHtml(item.summary || "Cenário em execução.")}</div>
          <div class="muted" style="margin-top:8px;">Nota: ${item.score == null ? "-" : escapeHtml(item.score)}</div>
        </div>
      `).join("");
      resultsEl.querySelectorAll(".scenario-card").forEach((card) => {
        card.addEventListener("click", () => {
          selectedScenarioId = card.dataset.scenarioId;
          renderScenarioList(job);
          renderScenarioInspector(job);
        });
      });
    }

    function renderScenarioInspector(job) {
      const stream = (job.scenario_streams || {})[selectedScenarioId];
      const chatTitle = document.getElementById("chatTitle");
      const chatSummary = document.getElementById("chatSummary");
      const chatBadge = document.getElementById("chatBadge");
      const chatBox = document.getElementById("chatBox");
      const scenarioLogBox = document.getElementById("scenarioLogBox");

      if (!stream) {
        chatTitle.textContent = "Conversa";
        chatSummary.textContent = "Selecione um cenário para acompanhar o chat.";
        chatBadge.innerHTML = "";
        chatBox.innerHTML = '<div class="empty">As mensagens do cliente e do Lucas vão aparecer aqui em tempo real.</div>';
        scenarioLogBox.textContent = "Selecione um cenário para ver o log detalhado.";
        return;
      }

      chatTitle.textContent = `${stream.scenario_id} • ${stream.lead_name || "-"}`;
      chatSummary.textContent = stream.summary || "Cenário em andamento.";
      chatBadge.innerHTML = `<span class="${badgeClass(stream.status)}">${escapeHtml(stream.status || "em andamento")}</span>`;

      const turns = stream.chat || [];
      if (!turns.length) {
        chatBox.innerHTML = '<div class="empty">Aguardando as primeiras mensagens desta simulação.</div>';
      } else {
        chatBox.innerHTML = turns.map((turn) => `
          <div class="bubble-row ${turn.role === "lucas" ? "lucas" : "lead"}">
            <div class="bubble ${turn.role === "lucas" ? "lucas" : "lead"}">
              <div class="bubble-label">${turn.role === "lucas" ? "Lucas" : "Cliente"}</div>
              <div>${escapeHtml(turn.message)}</div>
              ${(turn.attachments || []).length ? `<div class="attachment">Anexos: ${escapeHtml((turn.attachments || []).join(", "))}</div>` : ""}
            </div>
          </div>
        `).join("");
        chatBox.scrollTop = chatBox.scrollHeight;
      }

      scenarioLogBox.textContent = (stream.events || []).join("\\n") || "Sem eventos ainda.";
      scenarioLogBox.scrollTop = scenarioLogBox.scrollHeight;
    }

    function renderJob(job) {
      currentJob = job;
      currentJobId = job.job_id;
      document.getElementById("statusText").textContent = job.status;
      document.getElementById("progressText").textContent = `${job.progress_pct}%`;
      document.getElementById("countText").textContent = `${job.completed}/${job.total}`;
      document.getElementById("currentText").textContent = job.current_scenario || "-";
      document.getElementById("barFill").style.width = `${job.progress_pct}%`;
      document.getElementById("jobMeta").textContent = `Job ${job.job_id} • início ${job.started_at}`;
      document.getElementById("jobLogBox").textContent = (job.logs || []).join("\\n");
      document.getElementById("jobLogBox").scrollTop = document.getElementById("jobLogBox").scrollHeight;

      renderScenarioList(job);
      renderScenarioInspector(job);

      const links = [];
      if (job.report_markdown) links.push(`<a href="/artifacts/${job.report_markdown}" target="_blank">relatório .md</a>`);
      if (job.report_json) links.push(`<a href="/artifacts/${job.report_json}" target="_blank">relatório .json</a>`);
      document.getElementById("reportLinks").innerHTML = links.join(" • ");

      const btn = document.getElementById("startBtn");
      btn.disabled = job.status === "running" || job.status === "queued";
    }

    async function pollJob() {
      if (!currentJobId) return;
      const response = await fetch(`/scenario-tests/jobs/${currentJobId}`);
      if (!response.ok) return;
      const job = await response.json();
      renderJob(job);
      if (job.status === "completed" || job.status === "failed") {
        clearInterval(pollHandle);
        pollHandle = null;
      }
    }

    async function startJob() {
      selectedScenarioId = null;
      const payload = {
        limit: Number(document.getElementById("limit").value || 5),
        simulator: document.getElementById("simulator").value,
        max_turns: Number(document.getElementById("maxTurns").value || 6),
        max_parallel: Number(document.getElementById("maxParallel").value || 5),
      };
      const response = await fetch("/scenario-tests/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const job = await response.json();
      renderJob(job);
      if (pollHandle) clearInterval(pollHandle);
      pollHandle = setInterval(pollJob, 1500);
    }

    document.getElementById("startBtn").addEventListener("click", startJob);

    (async () => {
      const response = await fetch("/scenario-tests/jobs/latest");
      if (response.ok) {
        const job = await response.json();
        renderJob(job);
        if (job.status === "running" || job.status === "queued") {
          pollHandle = setInterval(pollJob, 1500);
        }
      }
    })();
  </script>
</body>
</html>
"""
