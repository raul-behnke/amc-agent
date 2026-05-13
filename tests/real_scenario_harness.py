from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from agno.agent import Agent  # noqa: E402
from agno.db.sqlite import SqliteDb  # noqa: E402
from agno.models.openai import OpenAIChat  # noqa: E402

import agents.lucas as lucas_module  # noqa: E402
import runtime.orchestrator as orchestrator_module  # noqa: E402
import tools.calendar as calendar_module  # noqa: E402
import tools.crm as crm_module  # noqa: E402
import tools.inventory as inventory_module  # noqa: E402
from runtime.orchestrator import process_message  # noqa: E402
from state.lead_model import LeadQualification  # noqa: E402
from tools.qualification import _get_lead, _lead_states  # noqa: E402


RESULTS_DIR = ROOT / "tests" / "results"
RAW_INVENTORY_PATH = ROOT / "data" / "raw_inventory_response.json"
DEFAULT_SCENARIOS_PATH = ROOT / "tests" / "cenarios_comerciais_reais.md"


@dataclass
class ScenarioDefinition:
    source_index: int
    scenario_id: str
    lead_name: str
    contact_id: str
    phone: str
    commercial_summary: str
    derived_scenarios: list[str]
    selected_scenario: str


@dataclass
class ToolTrace:
    tool: str
    payload: dict[str, Any]
    result: Any | None = None


@dataclass
class ConversationTurn:
    role: Literal["lead", "lucas"]
    message: str
    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationCheck:
    name: str
    status: Literal["pass", "partial", "fail"]
    evidence: str


class ConversationJudgeResponse(BaseModel):
    status: Literal["✅ Aprovado", "⚠️ Parcial", "❌ Reprovado"]
    score: float = Field(ge=0, le=10)
    analysis: str
    summary: str


@dataclass
class ScenarioResult:
    scenario_id: str
    lead_name: str
    summary: str
    selected_scenario: str
    transcript: list[ConversationTurn]
    simulator_notes: list[str]
    tool_traces: list[ToolTrace]
    stock_queries: list[dict[str, Any]]
    stock_results: list[dict[str, Any]]
    photos_sent: list[str]
    crm_actions: list[dict[str, Any]]
    scheduling_actions: list[dict[str, Any]]
    errors: list[str]
    final_lead_state: dict[str, Any]
    evaluation: dict[str, Any]


def load_inventory_snapshot(path: Path = RAW_INVENTORY_PATH) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    value = raw.get("customValue", {}).get("value", "{}")
    return json.loads(value).get("vehicles", [])


def parse_real_scenarios(
    path: Path = DEFAULT_SCENARIOS_PATH,
) -> list[ScenarioDefinition]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    scenarios: list[ScenarioDefinition] = []

    for section in sections[1:]:
        lines = [line.rstrip() for line in section.splitlines()]
        header = lines[0].strip()
        source_match = re.match(r"(\d+)\.\s+(.*)", header)
        if not source_match:
            continue

        source_index = int(source_match.group(1))
        lead_name = source_match.group(2).strip()
        body = "\n".join(lines[1:])

        contact_id = _search_group(body, r"Contact ID:\s*`([^`]+)`")
        phone = _search_group(body, r"Telefone:\s*([^\n]+)")
        summary = _extract_block(body, "### Resumo comercial", "### Cenários derivados")
        derived_block = _extract_block(body, "### Cenários derivados", None)
        derived = [
            re.sub(r"^\d+\.\s*", "", line).strip()
            for line in derived_block.splitlines()
            if re.match(r"^\d+\.\s+", line.strip())
        ]
        selected = derived[0] if derived else summary
        scenario_id = f"real-{source_index:03d}"

        scenarios.append(
            ScenarioDefinition(
                source_index=source_index,
                scenario_id=scenario_id,
                lead_name=lead_name,
                contact_id=contact_id or scenario_id,
                phone=phone or "",
                commercial_summary=summary.strip(),
                derived_scenarios=derived,
                selected_scenario=selected.strip(),
            )
        )

    return scenarios


def _search_group(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _extract_block(text: str, start_heading: str, end_heading: str | None) -> str:
    if start_heading not in text:
        return ""
    start = text.index(start_heading) + len(start_heading)
    end = (
        text.index(end_heading, start)
        if end_heading and end_heading in text[start:]
        else len(text)
    )
    return text[start:end].strip()


class LeadSimulatorResponse(BaseModel):
    messages: list[str] = Field(default_factory=list)
    rationale: str = ""
    done: bool = False


class LeadSimulationPlan:
    def __init__(self, scenario: ScenarioDefinition) -> None:
        combined = (
            f"{scenario.commercial_summary}\n{scenario.selected_scenario}".lower()
        )
        self.scenario = scenario
        self.vehicle_interest = _infer_vehicle_interest(scenario)
        self.name = (
            scenario.lead_name
            if "lead" not in scenario.lead_name.lower()
            else "Cliente"
        )
        self.city = "Joinville"
        self.trade_vehicle = "Gol 2011"
        self.trade_km = "145 mil km"
        self.trade_paid_off = "sim, está quitado"
        self.trade_condition = "tem detalhes normais de uso"
        self.payment = "financiamento"
        self.motivation = "quero algo mais estiloso"
        self.wants_photos = "foto" in combined
        self.wants_price = any(
            token in combined for token in ("valor", "preço", "preco")
        )
        self.wants_km = any(token in combined for token in ("quilometragem", "km"))
        self.wants_trade = "troca" in combined
        self.wants_financing = any(
            token in combined for token in ("financi", "crédito", "credito")
        )
        self.wants_schedule = any(
            token in combined
            for token in (
                "agendar",
                "visita",
                "a caminho da loja",
                "finalizar a compra",
            )
        )
        self.wants_human = any(
            token in combined for token in ("consultor", "humano", "encaminh")
        )
        self.focus_only_specific_model = "apenas" in combined or "somente" in combined
        self.vehicle_sold = "já foi vendido" in combined or "ja foi vendido" in combined
        self.credit_question = "score" in combined
        self.initial_fragments = self._build_initial_fragments()
        self.remaining_fragments = list(self.initial_fragments)
        self.facts_sent: set[str] = set()
        self.completed_objectives: set[str] = set()

    def _build_initial_fragments(self) -> list[str]:
        if self.credit_question:
            return ["dá pra consultar sem baixar meu score?"]
        if self.vehicle_sold:
            vehicle = self.vehicle_interest or "esse carro"
            return [f"oi, ainda tem {vehicle}?", "me manda fotos e km por favor"]
        if self.wants_schedule:
            if "a caminho" in self.scenario.commercial_summary.lower():
                return ["tô indo pra loja agora", "me passa o endereço certinho"]
            return ["quero ir ver o carro", "tem como marcar amanhã de manhã?"]
        if self.wants_financing and self.wants_price:
            return [
                f"tenho interesse no {self.vehicle_interest}",
                "quanto fica financiado?",
            ]
        if self.wants_trade:
            return [f"tenho interesse no {self.vehicle_interest}", "aceita troca?"]
        if self.wants_photos:
            return [f"tem fotos do {self.vehicle_interest}?"]
        if self.wants_price:
            return [f"qual o valor do {self.vehicle_interest}?"]
        return [f"tenho interesse no {self.vehicle_interest}"]

    def next_rule_based_messages(
        self, transcript: list[ConversationTurn], lead_state: LeadQualification
    ) -> LeadSimulatorResponse:
        if self.remaining_fragments:
            message = self.remaining_fragments.pop(0)
            return LeadSimulatorResponse(
                messages=[message], rationale="Mensagem inicial do cenário.", done=False
            )

        last_agent = _last_lucas_message(transcript).lower()
        if lead_state.status.value in {"SCHEDULED", "HANDOFF"}:
            return LeadSimulatorResponse(
                messages=[], rationale="Fluxo encerrado pelo sistema.", done=True
            )

        if "nome" in last_agent and "nome" not in self.facts_sent:
            self.facts_sent.add("nome")
            return LeadSimulatorResponse(
                messages=[self.name], rationale="Responder nome solicitado.", done=False
            )
        if (
            "qual carro" in last_agent
            or "qual veículo" in last_agent
            or "qual veiculo" in last_agent
        ) and "interesse" not in self.facts_sent:
            self.facts_sent.add("interesse")
            return LeadSimulatorResponse(
                messages=[self.vehicle_interest],
                rationale="Confirmar veículo de interesse.",
                done=False,
            )
        if "cidade" in last_agent and "cidade" not in self.facts_sent:
            self.facts_sent.add("cidade")
            return LeadSimulatorResponse(
                messages=[self.city], rationale="Responder cidade.", done=False
            )
        if (
            (
                "troca" in last_agent
                or "ano/modelo" in last_agent
                or "ano e o modelo" in last_agent
            )
            and self.wants_trade
            and "trade_vehicle" not in self.facts_sent
        ):
            self.facts_sent.add("trade_vehicle")
            return LeadSimulatorResponse(
                messages=[self.trade_vehicle],
                rationale="Informar veículo de troca.",
                done=False,
            )
        if (
            "km" in last_agent
            and self.wants_trade
            and "trade_km" not in self.facts_sent
        ):
            self.facts_sent.add("trade_km")
            return LeadSimulatorResponse(
                messages=[self.trade_km],
                rationale="Informar km do carro de troca.",
                done=False,
            )
        if (
            "quitado" in last_agent
            and self.wants_trade
            and "trade_paid_off" not in self.facts_sent
        ):
            self.facts_sent.add("trade_paid_off")
            return LeadSimulatorResponse(
                messages=[self.trade_paid_off],
                rationale="Informar quitação.",
                done=False,
            )
        if (
            (
                "detalhe" in last_agent
                or "avaria" in last_agent
                or "estado geral" in last_agent
            )
            and self.wants_trade
            and "trade_condition" not in self.facts_sent
        ):
            self.facts_sent.add("trade_condition")
            return LeadSimulatorResponse(
                messages=[self.trade_condition],
                rationale="Informar estado do carro.",
                done=False,
            )
        if (
            "motivo" in last_agent or "te fez pensar" in last_agent
        ) and "motivacao" not in self.facts_sent:
            self.facts_sent.add("motivacao")
            return LeadSimulatorResponse(
                messages=[self.motivation], rationale="Responder motivação.", done=False
            )
        if (
            "financi" in last_agent
            or "pagamento" in last_agent
            or "negociação" in last_agent
            or "negociacao" in last_agent
        ) and "payment" not in self.facts_sent:
            self.facts_sent.add("payment")
            return LeadSimulatorResponse(
                messages=[self.payment],
                rationale="Responder forma de negociação.",
                done=False,
            )
        if (
            (
                "amanhã" in last_agent
                or "amanha" in last_agent
                or "horário" in last_agent
                or "horario" in last_agent
            )
            and self.wants_schedule
            and "schedule" not in self.facts_sent
        ):
            self.facts_sent.add("schedule")
            return LeadSimulatorResponse(
                messages=["amanhã às 10h pode ser"],
                rationale="Sugerir horário.",
                done=False,
            )

        if (
            self.wants_human
            and "human" not in self.completed_objectives
            and len([t for t in transcript if t.role == "lucas"]) >= 2
        ):
            self.completed_objectives.add("human")
            return LeadSimulatorResponse(
                messages=["prefiro falar com um consultor"],
                rationale="Pedir atendimento humano.",
                done=False,
            )
        if (
            self.wants_photos
            and "photos" not in self.completed_objectives
            and len([t for t in transcript if t.role == "lucas"]) >= 1
        ):
            self.completed_objectives.add("photos")
            return LeadSimulatorResponse(
                messages=["me manda as fotos por favor"],
                rationale="Reforçar pedido de fotos.",
                done=False,
            )
        if (
            self.wants_financing
            and self.credit_question
            and "score" not in self.completed_objectives
        ):
            self.completed_objectives.add("score")
            return LeadSimulatorResponse(
                messages=["essa consulta afeta o score?"],
                rationale="Pergunta de crédito.",
                done=False,
            )

        return LeadSimulatorResponse(
            messages=["pode ser"],
            rationale="Resposta curta realista para manter o fluxo.",
            done=False,
        )


class LLMLeadSimulator:
    def __init__(self, scenario: ScenarioDefinition, plan: LeadSimulationPlan) -> None:
        self.scenario = scenario
        self.plan = plan
        model_id = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        self.agent = Agent(
            name="Lead Simulator",
            model=OpenAIChat(id=model_id, api_key=api_key),
            instructions=[self._instructions()],
            output_schema=LeadSimulatorResponse,
            markdown=False,
        )

    def _instructions(self) -> str:
        return (
            "Você simula um lead real de concessionária no WhatsApp.\n"
            "Responda com mensagens curtas, humanas e imperfeitas.\n"
            "Pode quebrar em até 3 mensagens curtas.\n"
            "Não explique sua estratégia para o Lucas.\n"
            "Mantenha coerência com o cenário e com os fatos já informados.\n"
            "Se o Lucas já resolveu o objetivo e o fluxo está encerrado, marque done=true.\n"
            "Prefira respostas como cliente real: 'sim', 'pode ser', 'quanto fica?', 'sou de Joinville'."
        )

    def next_messages(
        self, transcript: list[ConversationTurn], lead_state: LeadQualification
    ) -> LeadSimulatorResponse:
        if self.plan.remaining_fragments:
            return self.plan.next_rule_based_messages(transcript, lead_state)

        prompt = {
            "scenario_summary": self.scenario.commercial_summary,
            "selected_scenario": self.scenario.selected_scenario,
            "lead_profile": {
                "name": self.plan.name,
                "vehicle_interest": self.plan.vehicle_interest,
                "city": self.plan.city,
                "trade_vehicle": self.plan.trade_vehicle
                if self.plan.wants_trade
                else None,
                "payment": self.plan.payment if self.plan.wants_financing else None,
                "motivation": self.plan.motivation,
            },
            "transcript": [asdict(turn) for turn in transcript],
            "lead_state": lead_state.to_dict(),
        }
        response = self.agent.run(json.dumps(prompt, ensure_ascii=False))
        if isinstance(response.content, LeadSimulatorResponse):
            return response.content
        if isinstance(response, LeadSimulatorResponse):
            return response
        raise ValueError("Lead simulator retornou formato inválido.")


class SimulationSandbox:
    def __init__(self, inventory_snapshot: list[dict[str, Any]]) -> None:
        self.inventory_snapshot = inventory_snapshot
        self.tool_traces: list[ToolTrace] = []
        self.stock_queries: list[dict[str, Any]] = []
        self.stock_results: list[dict[str, Any]] = []
        self.photos_sent: list[str] = []
        self.crm_actions: list[dict[str, Any]] = []
        self.scheduling_actions: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.transcript: list[dict[str, Any]] = []
        self.contact_tags: dict[str, set[str]] = {}
        self._temp_db_file: tempfile.NamedTemporaryFile[str] | None = None

    def history_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for turn in self.transcript:
            messages.append(
                {
                    "direction": turn["direction"],
                    "body": turn["body"],
                    "attachments": [
                        {"url": item} for item in turn.get("attachments", [])
                    ],
                    "dateAdded": turn["date"],
                }
            )
        return messages

    def add_lead_messages(self, messages: list[str]) -> None:
        for msg in messages:
            self.transcript.append(
                {
                    "direction": "inbound",
                    "body": msg,
                    "attachments": [],
                    "date": datetime.now(UTC).isoformat(),
                }
            )

    def add_lucas_reply(self, reply: str, attachments: list[str] | None = None) -> None:
        self.transcript.append(
            {
                "direction": "outbound",
                "body": reply,
                "attachments": attachments or [],
                "date": datetime.now(UTC).isoformat(),
            }
        )
        self.photos_sent.extend(attachments or [])

    def __enter__(self) -> "SimulationSandbox":
        self._temp_db_file = tempfile.NamedTemporaryFile(
            prefix="lucas-sim-", suffix=".db", delete=False
        )
        temp_db = SqliteDb(db_file=self._temp_db_file.name)

        original_stock = orchestrator_module.consultar_estoque
        original_photos = orchestrator_module.get_vehicle_photo_urls

        def logged_stock(*args: Any, **kwargs: Any) -> Any:
            payload = {"args": list(args), "kwargs": kwargs}
            self.stock_queries.append(payload)
            result = original_stock(*args, **kwargs)
            parsed = _safe_json_loads(result)
            self.stock_results.append(
                parsed if isinstance(parsed, dict) else {"raw": result}
            )
            self.tool_traces.append(
                ToolTrace(tool="consultar_estoque", payload=payload, result=parsed)
            )
            return result

        def logged_photos(*args: Any, **kwargs: Any) -> list[str]:
            payload = {"args": list(args), "kwargs": kwargs}
            result = original_photos(*args, **kwargs)
            self.tool_traces.append(
                ToolTrace(tool="get_vehicle_photo_urls", payload=payload, result=result)
            )
            return result

        def fake_upsert_contact(phone: str, name: str | None = None) -> dict[str, Any]:
            contact = {
                "id": f"mock-contact-{re.sub(r'\\W+', '', phone or 'lead')}",
                "phone": phone,
                "firstName": name,
            }
            self.crm_actions.append({"action": "upsert_contact", "contact": contact})
            return contact

        def fake_upsert_opportunity(
            contact_id: str,
            pipeline_id: str,
            stage_id: str,
            title: str,
            status: str = "open",
        ) -> dict[str, Any]:
            payload = {
                "action": "upsert_opportunity",
                "contact_id": contact_id,
                "pipeline_id": pipeline_id,
                "stage_id": stage_id,
                "title": title,
                "status": status,
            }
            self.crm_actions.append(payload)
            return payload

        def fake_add_contact_note(contact_id: str, body: str) -> dict[str, Any]:
            payload = {
                "action": "add_contact_note",
                "contact_id": contact_id,
                "body": body,
            }
            self.crm_actions.append(payload)
            return payload

        def fake_remove_tag(contact_id: str, tag: str) -> bool:
            self.crm_actions.append(
                {"action": "remove_contact_tag", "contact_id": contact_id, "tag": tag}
            )
            return True

        async def fake_trigger_workflow(contact_id: str) -> bool:
            self.crm_actions.append(
                {"action": "trigger_workflow", "contact_id": contact_id}
            )
            return True

        async def fake_notify_escalation(
            contact_id: str,
            conversation_id: str,
            reason: str,
            note: str,
            farewell_message: str,
        ) -> bool:
            self.crm_actions.append(
                {
                    "action": "notify_escalation",
                    "contact_id": contact_id,
                    "conversation_id": conversation_id,
                    "reason": reason,
                    "note": note,
                    "farewell_message": farewell_message,
                }
            )
            return True

        def fake_calendar_request(
            method: str, path: str, **kwargs: Any
        ) -> dict[str, Any]:
            payload = {"method": method, "path": path, "kwargs": kwargs}
            self.scheduling_actions.append(payload)
            if "free-slots" in path:
                return {
                    "slots": ["2026-05-13T10:00:00-03:00", "2026-05-13T14:00:00-03:00"]
                }
            if "appointments" in path:
                return {"ok": True, "appointmentId": "mock-appointment"}
            return {"ok": True}

        async def fake_messages(_: str, limit: int = 20) -> list[dict[str, Any]]:
            history = self.history_messages()
            return history[-limit:]

        self._stack = ExitStack()
        self._stack.enter_context(patch.object(lucas_module, "db", temp_db))
        self._stack.enter_context(
            patch.object(
                orchestrator_module, "consultar_estoque", side_effect=logged_stock
            )
        )
        self._stack.enter_context(
            patch.object(
                orchestrator_module, "get_vehicle_photo_urls", side_effect=logged_photos
            )
        )
        self._stack.enter_context(
            patch.object(
                orchestrator_module, "get_messages_async", side_effect=fake_messages
            )
        )
        self._stack.enter_context(
            patch.object(
                inventory_module,
                "fetch_inventory_sync",
                return_value=self.inventory_snapshot,
            )
        )
        self._stack.enter_context(
            patch.object(crm_module, "upsert_contact", side_effect=fake_upsert_contact)
        )
        self._stack.enter_context(
            patch.object(
                crm_module, "upsert_opportunity", side_effect=fake_upsert_opportunity
            )
        )
        self._stack.enter_context(
            patch.object(
                crm_module, "add_contact_note", side_effect=fake_add_contact_note
            )
        )
        self._stack.enter_context(
            patch.object(
                crm_module, "remove_contact_tag_sync", side_effect=fake_remove_tag
            )
        )
        self._stack.enter_context(
            patch.object(
                crm_module, "trigger_workflow", side_effect=fake_trigger_workflow
            )
        )
        self._stack.enter_context(
            patch.object(
                crm_module, "notify_escalation", side_effect=fake_notify_escalation
            )
        )
        self._stack.enter_context(
            patch.object(
                calendar_module, "_ghl_request_sync", side_effect=fake_calendar_request
            )
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._stack.close()
        if self._temp_db_file is not None:
            try:
                self._temp_db_file.close()
                os.unlink(self._temp_db_file.name)
            except FileNotFoundError:
                pass


async def run_real_scenario(
    scenario: ScenarioDefinition,
    max_turns: int = 6,
    simulator_mode: Literal["auto", "llm", "rule"] = "auto",
    inventory_snapshot: list[dict[str, Any]] | None = None,
    session_namespace: str | None = None,
    progress_callback: Any | None = None,
) -> ScenarioResult:
    inventory_snapshot = inventory_snapshot or load_inventory_snapshot()
    execution_session_id = (
        f"{session_namespace}:{scenario.contact_id}"
        if session_namespace
        else scenario.contact_id
    )
    execution_conversation_id = (
        f"sim-{session_namespace}-{scenario.scenario_id}"
        if session_namespace
        else f"sim-{scenario.scenario_id}"
    )
    _lead_states.pop(execution_session_id, None)

    plan = LeadSimulationPlan(scenario)
    simulator = _build_simulator(simulator_mode, scenario, plan)
    simulator_notes: list[str] = []

    with SimulationSandbox(inventory_snapshot) as sandbox:
        for _ in range(max_turns):
            lead_state = _get_lead(execution_session_id)
            if hasattr(simulator, "next_messages"):
                try:
                    decision = simulator.next_messages(
                        _conversation_turns(sandbox.transcript), lead_state
                    )
                except Exception as exc:
                    logger.warning(
                        "Lead simulator LLM falhou, usando fallback rule-based | err={err}",
                        err=str(exc),
                    )
                    sandbox.errors.append(f"lead_simulator_error: {exc}")
                    decision = plan.next_rule_based_messages(
                        _conversation_turns(sandbox.transcript), lead_state
                    )
            else:
                decision = plan.next_rule_based_messages(
                    _conversation_turns(sandbox.transcript), lead_state
                )

            simulator_notes.append(decision.rationale)
            if decision.done or not decision.messages:
                break

            sandbox.add_lead_messages(decision.messages)
            for message in decision.messages:
                if progress_callback:
                    progress_callback(
                        {
                            "event": "conversation_turn",
                            "scenario_id": scenario.scenario_id,
                            "lead_name": scenario.lead_name,
                            "role": "lead",
                            "message": message,
                            "attachments": [],
                            "kind": "lead_message",
                        }
                    )
            user_message = decision.messages[-1]

            try:
                response = await process_message(
                    session_id=execution_session_id,
                    user_message=user_message,
                    contact_id=scenario.contact_id,
                    conversation_id=execution_conversation_id,
                )
            except Exception as exc:
                sandbox.errors.append(f"process_message_error: {exc}")
                break

            reply = str(response.get("reply", ""))
            attachments = response.get("attachments") or []
            sandbox.add_lucas_reply(reply, attachments=attachments)
            if progress_callback:
                progress_callback(
                    {
                        "event": "conversation_turn",
                        "scenario_id": scenario.scenario_id,
                        "lead_name": scenario.lead_name,
                        "role": "lucas",
                        "message": reply,
                        "attachments": attachments,
                        "kind": "agent_reply",
                    }
                )

            lead_state = _get_lead(execution_session_id)
            if lead_state.status.value in {"SCHEDULED", "HANDOFF"}:
                break

    final_state = _get_lead(execution_session_id).to_dict()
    transcript = _conversation_turns(sandbox.transcript)
    evaluation = evaluate_real_scenario(scenario, transcript, sandbox, final_state)

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        lead_name=scenario.lead_name,
        summary=scenario.commercial_summary,
        selected_scenario=scenario.selected_scenario,
        transcript=transcript,
        simulator_notes=simulator_notes,
        tool_traces=sandbox.tool_traces,
        stock_queries=sandbox.stock_queries,
        stock_results=sandbox.stock_results,
        photos_sent=sandbox.photos_sent,
        crm_actions=sandbox.crm_actions,
        scheduling_actions=sandbox.scheduling_actions,
        errors=sandbox.errors,
        final_lead_state=final_state,
        evaluation=evaluation,
    )


def _build_simulator(
    simulator_mode: Literal["auto", "llm", "rule"],
    scenario: ScenarioDefinition,
    plan: LeadSimulationPlan,
) -> LeadSimulationPlan | LLMLeadSimulator:
    if simulator_mode == "rule":
        return plan
    if simulator_mode == "llm":
        return LLMLeadSimulator(scenario, plan)
    if os.getenv("OPENAI_API_KEY"):
        return LLMLeadSimulator(scenario, plan)
    return plan


def _conversation_turns(raw_transcript: list[dict[str, Any]]) -> list[ConversationTurn]:
    turns: list[ConversationTurn] = []
    for item in raw_transcript:
        turns.append(
            ConversationTurn(
                role="lead" if item["direction"] == "inbound" else "lucas",
                message=item["body"],
                attachments=list(item.get("attachments", [])),
            )
        )
    return turns


def _last_lucas_message(transcript: list[ConversationTurn]) -> str:
    for turn in reversed(transcript):
        if turn.role == "lucas":
            return turn.message
    return ""


def _infer_vehicle_interest(scenario: ScenarioDefinition) -> str:
    text = f"{scenario.commercial_summary} {scenario.selected_scenario}"
    patterns = [
        r"interesse em (?:um |uma |o |a )?([A-Z][A-Za-z0-9./+\-\s]+?)(?:,|\.| e | com )",
        r"especificamente (?:um |uma |o |a )?([A-Z][A-Za-z0-9./+\-\s]+?)(?:,|\.| e | com )",
        r"pelo ([A-Z][A-Za-z0-9./+\-\s]+?)(?:,|\.| e | com )",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    vehicle_match = re.findall(
        r"\b(?:Gol|HB20|Edge|Mobi|Ford Ka Sedan|Fit|Renegade|Cruze|Onix|Ka Sedan)\b(?:[\w./+\-\s]{0,20})?",
        text,
    )
    return vehicle_match[0].strip() if vehicle_match else "veículo anunciado"


def evaluate_real_scenario(
    scenario: ScenarioDefinition,
    transcript: list[ConversationTurn],
    sandbox: SimulationSandbox,
    final_state: dict[str, Any],
) -> dict[str, Any]:
    return _judge_conversation_with_llm(
        scenario=scenario,
        transcript=transcript,
        final_state=final_state,
        photos_sent=sandbox.photos_sent,
    )


def _judge_conversation_with_llm(
    scenario: ScenarioDefinition,
    transcript: list[ConversationTurn],
    final_state: dict[str, Any],
    photos_sent: list[str],
) -> dict[str, Any]:
    model_id = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY não configurada para avaliação LLM.")

    judge = Agent(
        name="Conversation Judge",
        model=OpenAIChat(id=model_id, api_key=api_key),
        instructions=[
            (
                "Você é um avaliador comercial sênior da AMC Veículos.\n"
                "Avalie SOMENTE se a conversa progrediu bem conforme o processo comercial proposto.\n"
                "Ignore ferramentas, arquitetura, logs internos e implementação técnica.\n"
                "O foco é exclusivamente a qualidade comercial da condução da conversa.\n"
                "Critérios:\n"
                "1. Responde primeiro o que o lead perguntou.\n"
                "2. Faz a conversa avançar de forma natural dentro do processo comercial.\n"
                "3. Não vira formulário rígido.\n"
                "4. Evita repetição e efeito papagaio.\n"
                "5. Faz no máximo uma pergunta principal por vez.\n"
                "6. Não tenta fechar cedo demais.\n"
                "7. Quando há troca, conduz a coleta de dados da troca de forma lógica.\n"
                "8. Mantém tom humano, consultivo e objetivo.\n"
                "9. A análise deve dizer claramente se o Lucas está apto, parcialmente apto ou inapto nesse cenário.\n"
                "Saída:\n"
                "- status: ✅ Aprovado, ⚠️ Parcial ou ❌ Reprovado\n"
                "- score: nota de 0 a 10\n"
                "- summary: frase curta com o veredito\n"
                "- analysis: análise em português, em parágrafo corrido, explicando o prosseguimento ou a quebra do processo comercial."
            )
        ],
        output_schema=ConversationJudgeResponse,
        markdown=False,
    )

    payload = {
        "scenario_id": scenario.scenario_id,
        "lead_name": scenario.lead_name,
        "commercial_summary": scenario.commercial_summary,
        "selected_scenario": scenario.selected_scenario,
        "transcript": [asdict(turn) for turn in transcript],
        "final_lead_state": final_state,
        "photos_sent_count": len(photos_sent),
    }
    response = judge.run(json.dumps(payload, ensure_ascii=False))
    result = response.content if hasattr(response, "content") else response
    if not isinstance(result, ConversationJudgeResponse):
        raise ValueError("Judge LLM retornou formato inválido.")

    return {
        "status": result.status,
        "score": result.score,
        "summary": result.summary,
        "analysis": result.analysis,
    }


def render_markdown_report(results: list[ScenarioResult]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    approved = sum(
        1 for result in results if result.evaluation["status"] == "✅ Aprovado"
    )
    lines = [
        "# Simulação de Cenários Reais - Lucas SDR",
        "",
        f"Gerado em: {generated_at}",
        f"Cenários executados: {len(results)}",
        f"Aprovados: {approved}",
        "",
    ]

    for result in results:
        lines.extend(
            [
                f"## {result.scenario_id} - {result.lead_name}",
                "",
                f"- Cenário escolhido: {result.selected_scenario}",
                f"- Status: `{result.evaluation['status']}`",
                f"- Nota geral: `{result.evaluation['score']}`",
                f"- Veredito: {result.evaluation.get('summary', '')}",
                "",
                result.evaluation.get("analysis", ""),
                "",
            ]
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def serialize_results(results: list[ScenarioResult]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for result in results:
        serialized.append(
            {
                "scenario_id": result.scenario_id,
                "lead_name": result.lead_name,
                "summary": result.summary,
                "selected_scenario": result.selected_scenario,
                "transcript": [asdict(turn) for turn in result.transcript],
                "simulator_notes": result.simulator_notes,
                "tool_traces": [asdict(trace) for trace in result.tool_traces],
                "stock_queries": result.stock_queries,
                "stock_results": result.stock_results,
                "photos_sent": result.photos_sent,
                "crm_actions": result.crm_actions,
                "scheduling_actions": result.scheduling_actions,
                "errors": result.errors,
                "final_lead_state": result.final_lead_state,
                "evaluation": result.evaluation,
            }
        )
    return serialized


def write_reports(
    results: list[ScenarioResult],
    output_dir: Path = RESULTS_DIR,
    slug: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"{slug}-{timestamp}" if slug else timestamp
    md_path = output_dir / f"simulacao_{suffix}.md"
    json_path = output_dir / f"simulacao_{suffix}.json"
    md_path.write_text(render_markdown_report(results), encoding="utf-8")
    json_path.write_text(
        json.dumps(serialize_results(results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


async def run_many_real_scenarios(
    scenarios: list[ScenarioDefinition],
    max_turns: int = 6,
    simulator_mode: Literal["auto", "llm", "rule"] = "auto",
    incremental_slug: str | None = None,
    progress_callback: Any | None = None,
    session_namespace: str | None = None,
    max_parallel: int = 1,
) -> list[ScenarioResult]:
    results: list[ScenarioResult | None] = [None] * len(scenarios)
    inventory_snapshot = load_inventory_snapshot()
    total = len(scenarios)
    semaphore = asyncio.Semaphore(max(1, max_parallel))
    completed_count = 0

    async def _run_one(position: int, scenario: ScenarioDefinition) -> None:
        nonlocal completed_count
        index = position + 1
        if progress_callback:
            progress_callback(
                {
                    "event": "scenario_started",
                    "index": index,
                    "total": total,
                    "scenario_id": scenario.scenario_id,
                    "lead_name": scenario.lead_name,
                }
            )
        async with semaphore:
            logger.info(
                "Rodando cenário {idx}/{total} | id={sid} | lead={lead}",
                idx=index,
                total=total,
                sid=scenario.scenario_id,
                lead=scenario.lead_name,
            )
            result = await run_real_scenario(
                scenario=scenario,
                max_turns=max_turns,
                simulator_mode=simulator_mode,
                inventory_snapshot=inventory_snapshot,
                session_namespace=session_namespace,
                progress_callback=progress_callback,
            )
        results[position] = result
        completed_count += 1
        if progress_callback:
            progress_callback(
                {
                    "event": "scenario_completed",
                    "index": completed_count,
                    "total": total,
                    "scenario_id": scenario.scenario_id,
                    "lead_name": scenario.lead_name,
                    "status": result.evaluation["status"],
                    "score": result.evaluation["score"],
                    "summary": result.evaluation.get("summary"),
                }
            )
        if incremental_slug:
            ordered_results = [item for item in results if item is not None]
            write_reports(ordered_results, slug=incremental_slug)

    await asyncio.gather(
        *[_run_one(position, scenario) for position, scenario in enumerate(scenarios)]
    )
    return [item for item in results if item is not None]


def _safe_json_loads(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
