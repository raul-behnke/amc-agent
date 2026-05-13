"""
Executa a bateria de QA do Lucas SDR localmente, avalia critérios mínimos
por cenário e gera um relatório Markdown.

Uso:
    ./venv/bin/python scripts/run_lucas_qa_battery.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from runtime.orchestrator import process_message
from tools.qualification import _get_lead, _lead_states, registrar_estado

load_dotenv(ROOT / ".env")

PAYLOADS_PATH = ROOT / "docs" / "qa" / "lucas-go-live-payloads-2026-05-08.json"
OUTPUT_DIR = ROOT / "docs" / "qa" / "reports"


def _reset_session(session_id: str) -> None:
    _lead_states.pop(session_id, None)


def _apply_setup(session_id: str, setup: dict[str, Any] | None) -> None:
    if not setup:
        return

    registrar_estado(
        session_id=session_id,
        nome=setup.get("nome"),
        tipo_veiculo=setup.get("tipo_veiculo"),
        marca_preferida=setup.get("marca_preferida"),
        modelo_preferido=setup.get("modelo_preferido"),
        tem_troca=setup.get("tem_troca"),
        veiculo_troca=setup.get("veiculo_troca"),
        motivo_troca=setup.get("motivo_troca"),
        precisa_financiamento=setup.get("precisa_financiamento"),
        e_local=setup.get("e_local"),
        veiculo_interesse=setup.get("veiculo_interesse"),
        data_visita=setup.get("data_visita"),
    )


def _contains_any(text: str, options: list[str]) -> bool:
    lowered = text.lower()
    return any(option.lower() in lowered for option in options)


def _last_agent_text(result: dict[str, Any]) -> str:
    interactions = result.get("interactions", [])
    if not interactions:
        return ""
    return str(interactions[-1].get("agent", ""))


def _all_agent_text(result: dict[str, Any]) -> str:
    return "\n".join(str(item.get("agent", "")) for item in result.get("interactions", []))


def _max_questions_per_message(result: dict[str, Any], max_questions: int = 1) -> bool:
    for item in result.get("interactions", []):
        if str(item.get("agent", "")).count("?") > max_questions:
            return False
    return True


def _scenario_checks() -> dict[str, list[tuple[str, Callable[[dict[str, Any]], bool]]]]:
    return {
        "qa-c01": [
            ("status final agendado", lambda r: r["status"] == "SCHEDULED"),
            ("resposta oferece ou confirma horário", lambda r: _contains_any(_all_agent_text(r), ["09:00", "17:", "horário", "horario"])),
        ],
        "qa-c02": [
            ("pede ano/modelo completo do Gol", lambda r: _contains_any(_last_agent_text(r), ["ano/modelo", "qual ano", "modelo completo"])),
            ("não pula direto para financiamento", lambda r: "financ" not in _last_agent_text(r).lower()),
        ],
        "qa-c03": [
            ("confirma avaliação por WhatsApp", lambda r: _contains_any(_all_agent_text(r), ["whatsapp", "avali", "fotos", "km"])),
            ("não faz handoff", lambda r: r["status"] != "HANDOFF"),
        ],
        "qa-c04": [
            ("não marca troca após lead negar troca", lambda r: r["qualification"].get("tem_troca") is False),
        ],
        "qa-c05": [
            ("responde a dúvida de cartão", lambda r: _contains_any(_last_agent_text(r), ["cartão", "cartao"])),
        ],
        "qa-c06": [
            ("responde a dúvida sobre entrada", lambda r: _contains_any(_all_agent_text(r), ["entrada", "financi"])),
        ],
        "qa-c08": [
            ("não repete pergunta de cidade", lambda r: not _contains_any(_last_agent_text(r), ["qual cidade", "de onde você é", "de onde voce e"])),
        ],
        "qa-c10": [
            ("mantém fluxo de fotos", lambda r: _contains_any(_all_agent_text(r), ["[foto 1]", "fotos", "foto"])),
        ],
        "qa-c12": [
            ("não agenda sem horário exato", lambda r: r["status"] != "SCHEDULED"),
        ],
        "qa-c14": [
            ("pede texto quando áudio não transcreve", lambda r: "Pode mandar por texto pra mim?" in _last_agent_text(r)),
        ],
        "qa-c16": [
            ("faz handoff quando pedido humano é explícito", lambda r: r["status"] == "HANDOFF"),
        ],
    }


def evaluate_result(result: dict[str, Any]) -> dict[str, Any]:
    checks = _scenario_checks().get(result["id"], [])
    generic_checks = [
        ("máximo de uma pergunta por mensagem", lambda r: _max_questions_per_message(r, max_questions=1)),
    ]
    all_checks = generic_checks + checks

    outcomes = []
    for description, fn in all_checks:
        passed = False
        try:
            passed = bool(fn(result))
        except Exception:
            passed = False
        outcomes.append({"description": description, "passed": passed})

    passed_count = sum(1 for item in outcomes if item["passed"])
    failed_count = len(outcomes) - passed_count
    return {
        "checks": outcomes,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "approved": failed_count == 0,
    }


async def _run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    session_id = scenario["id"]
    _reset_session(session_id)
    _apply_setup(session_id, scenario.get("setup"))

    interactions: list[dict[str, str]] = []
    for message in scenario["messages"]:
        result = await process_message(session_id=session_id, user_message=message)
        interactions.append({"lead": message, "agent": result.get("reply", "")})

    lead = _get_lead(session_id)
    scenario_result = {
        "id": session_id,
        "name": scenario["name"],
        "interactions": interactions,
        "qualification": lead.to_dict(),
        "score": lead.completeness_score(),
        "status": lead.status.value,
    }
    scenario_result["evaluation"] = evaluate_result(scenario_result)
    return scenario_result


def _render_report(results: list[dict[str, Any]]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    approved = sum(1 for result in results if result["evaluation"]["approved"])

    lines = [
        "# Relatório de Execução - Bateria Lucas SDR",
        "",
        f"Gerado em: {generated_at}",
        f"Fonte: `{PAYLOADS_PATH.relative_to(ROOT)}`",
        f"Cenários aprovados: {approved}/{total}",
        "",
    ]

    for result in results:
        evaluation = result["evaluation"]
        badge = "APROVADO" if evaluation["approved"] else "REPROVADO"
        lines.extend(
            [
                f"## {result['id']} - {result['name']}",
                "",
                f"- Resultado: `{badge}`",
                f"- Status final: `{result['status']}`",
                f"- Score final: `{result['score']}%`",
                f"- Qualificação final: `{json.dumps(result['qualification'], ensure_ascii=False)}`",
                "",
                "### Checks",
                "",
            ]
        )
        for check in evaluation["checks"]:
            prefix = "PASS" if check["passed"] else "FAIL"
            lines.append(f"- [{prefix}] {check['description']}")
        lines.extend(["", "### Interações", ""])

        for idx, item in enumerate(result["interactions"], start=1):
            lines.extend(
                [
                    f"**{idx}. Lead:** {item['lead']}",
                    "",
                    f"**{idx}. Lucas:** {item['agent']}",
                    "",
                ]
            )

        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


async def main() -> None:
    data = json.loads(PAYLOADS_PATH.read_text(encoding="utf-8"))
    results = []
    for scenario in data["scenarios"]:
        results.append(await _run_scenario(scenario))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"lucas-go-live-report-{timestamp}.md"
    output_path.write_text(_render_report(results), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    asyncio.run(main())
