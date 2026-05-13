import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tests.real_scenario_harness import (
    ConversationTurn,
    ScenarioDefinition,
    SimulationSandbox,
    evaluate_real_scenario,
    parse_real_scenarios,
    render_markdown_report,
    run_real_scenario,
)
from tools.qualification import _lead_states, _get_lead


class RealScenarioHarnessTests(unittest.TestCase):
    def test_parse_real_scenarios_extracts_sections(self) -> None:
        content = textwrap.dedent(
            """
            # Cenários Comerciais Reais

            ## 1. Fulano
            - Contact ID: `abc123`
            - Telefone: +5511999999999

            ### Resumo comercial

            Lead demonstrou interesse em um Honda Fit.

            ### Cenários derivados

            1. Lead pede fotos do Honda Fit.
            2. Lead pergunta valor.
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as handle:
            handle.write(content)
            temp_path = Path(handle.name)

        scenarios = parse_real_scenarios(temp_path)

        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].scenario_id, "real-001")
        self.assertEqual(scenarios[0].lead_name, "Fulano")
        self.assertEqual(scenarios[0].contact_id, "abc123")
        self.assertEqual(
            scenarios[0].derived_scenarios[0], "Lead pede fotos do Honda Fit."
        )

    def test_simulation_sandbox_exposes_local_history(self) -> None:
        with SimulationSandbox(inventory_snapshot=[]) as sandbox:
            sandbox.add_lead_messages(["oi", "tem fotos?"])
            sandbox.add_lucas_reply(
                "Aqui estão as fotos", attachments=["https://img/1.jpg"]
            )
            history = sandbox.history_messages()

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["direction"], "inbound")
        self.assertEqual(history[-1]["attachments"][0]["url"], "https://img/1.jpg")

    def test_evaluate_real_scenario_uses_llm_judge_result(self) -> None:
        scenario = ScenarioDefinition(
            source_index=1,
            scenario_id="real-001",
            lead_name="Fulano",
            contact_id="abc123",
            phone="+5511999999999",
            commercial_summary="Lead pediu fotos de um Honda Fit.",
            derived_scenarios=["Lead pede fotos de um Honda Fit."],
            selected_scenario="Lead pede fotos de um Honda Fit.",
        )
        transcript = [
            ConversationTurn(role="lead", message="tem fotos do honda fit?"),
            ConversationTurn(
                role="lucas", message="Tudo bem? Qual seu nome? Você é de Joinville?"
            ),
        ]
        mocked_evaluation = {
            "status": "⚠️ Parcial",
            "score": 6.0,
            "summary": "Conversa respondeu parcialmente bem.",
            "analysis": "O Lucas respondeu, mas ainda conduziu a conversa com rigidez e sem priorizar bem o pedido inicial.",
        }
        with (
            SimulationSandbox(inventory_snapshot=[]) as sandbox,
            patch(
                "tests.real_scenario_harness._judge_conversation_with_llm",
                return_value=mocked_evaluation,
            ),
        ):
            evaluation = evaluate_real_scenario(
                scenario, transcript, sandbox, {"status": "NEW_LEAD"}
            )

        self.assertEqual(evaluation["status"], "⚠️ Parcial")
        self.assertEqual(evaluation["score"], 6.0)
        self.assertIn("rigidez", evaluation["analysis"])

    def test_render_markdown_report_contains_llm_analysis(self) -> None:
        result = type(
            "FakeResult",
            (),
            {
                "scenario_id": "real-001",
                "lead_name": "Fulano",
                "selected_scenario": "Lead pede fotos",
                "summary": "Lead quer ver o veículo.",
                "evaluation": {
                    "status": "✅ Aprovado",
                    "score": 8.5,
                    "summary": "Condução comercial adequada.",
                    "analysis": "A conversa progrediu bem, respondeu o pedido inicial e avançou a qualificação sem soar mecânica.",
                },
                "transcript": [
                    ConversationTurn(role="lead", message="oi"),
                    ConversationTurn(role="lucas", message="olá"),
                ],
                "simulator_notes": ["Mensagem inicial do cenário."],
                "tool_traces": [],
                "crm_actions": [],
                "scheduling_actions": [],
                "photos_sent": [],
                "errors": [],
            },
        )()

        report = render_markdown_report([result])

        self.assertIn("real-001", report)
        self.assertIn("✅ Aprovado", report)
        self.assertIn("Condução comercial adequada.", report)
        self.assertIn("progrediu bem", report)


class RealScenarioIsolationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    async def test_run_real_scenario_uses_namespaced_session_id(self) -> None:
        scenario = ScenarioDefinition(
            source_index=1,
            scenario_id="real-001",
            lead_name="Fulano",
            contact_id="abc123",
            phone="+5511999999999",
            commercial_summary="Lead demonstrou interesse em um Honda Fit.",
            derived_scenarios=["Lead pergunta valor."],
            selected_scenario="Lead pergunta valor.",
        )

        async def fake_process_message(
            session_id: str,
            user_message: str,
            contact_id: str | None = None,
            conversation_id: str | None = None,
        ) -> dict:
            _get_lead(session_id).nome = "Cliente isolado"
            return {"reply": "Qual seu nome?", "attachments": None}

        with (
            patch(
                "tests.real_scenario_harness.process_message",
                new=AsyncMock(side_effect=fake_process_message),
            ),
            patch(
                "tests.real_scenario_harness.evaluate_real_scenario",
                return_value={"status": "✅ Aprovado", "score": 8.0, "summary": "ok", "analysis": "ok"},
            ),
        ):
            result = await run_real_scenario(
                scenario=scenario,
                max_turns=1,
                simulator_mode="rule",
                inventory_snapshot=[],
                session_namespace="job-1",
            )

        self.assertEqual(result.evaluation["status"], "✅ Aprovado")
        self.assertIn("job-1:abc123", _lead_states)
        self.assertNotIn("abc123", _lead_states)


if __name__ == "__main__":
    unittest.main()
