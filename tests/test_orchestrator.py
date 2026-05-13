import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from runtime.orchestrator import (
    _build_initial_greeting,
    _build_session_context,
    _detect_unanswered,
    _filter_stock_payload,
    _format_pending_messages,
    _sanitize_agent_reply,
    process_message,
)
from tools.qualification import _lead_states, registrar_qualificacao


class OrchestratorBufferTests(unittest.TestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    def test_detect_unanswered_collects_pending_in_order(self):
        ghl_messages = [
            {"direction": "outbound", "body": "Olá"},
            {"direction": "inbound", "body": "Legal, gostei desse Honda Fit, qual a cor?"},
            {"direction": "inbound", "body": "Tenho um Gol pra dar na troca"},
        ]

        self.assertEqual(
            _detect_unanswered(ghl_messages),
            [
                "Legal, gostei desse Honda Fit, qual a cor?",
                "Tenho um Gol pra dar na troca",
            ],
        )

    def test_format_pending_messages_guides_model_without_funil_hardcode(self):
        pending = [
            "Me manda as fotos do Honda Fit",
            "Tenho um Gol pra dar na troca",
        ]

        formatted = _format_pending_messages(pending)

        self.assertIsNotNone(formatted)
        self.assertIn("[MENSAGENS PENDENTES DO LEAD]", formatted)
        self.assertIn("1. Me manda as fotos do Honda Fit", formatted)
        self.assertIn("2. Tenho um Gol pra dar na troca", formatted)
        self.assertIn("sem ignorar pedidos objetivos", formatted)

    def test_format_pending_messages_ignores_single_message(self):
        self.assertIsNone(_format_pending_messages(["Tenho um Gol pra dar na troca"]))



    def test_initial_greeting_uses_previous_vehicle_template(self):
        self.assertEqual(
            _build_initial_greeting("[SAUDAÇÃO INICIAL] Veículo: Hyunday HB20 Comf./C.Plus/C.Style 1.0 Flex 12V"),
            "Olá! 👋 Bem-vindo à AMC Veículos. Vi que você demonstrou interesse no Hyunday HB20 Comf./C.Plus/C.Style 1.0 Flex 12V 🚗. Posso te passar mais informações sobre ele?",
        )

    def test_build_session_context_contains_only_factual_state(self):
        session_id = "sessao-contexto"
        registrar_qualificacao(
            session_id=session_id,
            veiculo_interesse="Honda Fit LXL 1.4",
            tem_troca=True,
            veiculo_troca="Gol 2010",
            precisa_financiamento=True,
        )

        context = _build_session_context(session_id)

        self.assertIn("[CONTEXTO SESSAO]", context)
        self.assertIn("LEAD_STATUS_ATUAL=QUALIFYING", context)
        self.assertIn("VEICULO_INTERESSE_ATUAL=Honda Fit LXL 1.4", context)
        self.assertIn("VEICULO_TROCA_ATUAL=Gol 2010", context)
        self.assertIn("PRECISA_FINANCIAMENTO_ATUAL=True", context)
        self.assertIn("DADOS_TROCA_PENDENTES=km, quitado, estado, fotos", context)
        self.assertNotIn("PROXIMO_PASSO_OBRIGATORIO", context)

    def test_sanitize_agent_reply_preserva_quebras_de_linha(self):
        reply = "🚗 *OPÇÕES DISPONÍVEIS NO ESTOQUE:*\n\n✨ *1. HB20*\n📅 2022 | 🕹️ Automático | 🛣️ 48.000 km\n💰 *R$ 66.900*"
        sanitized = _sanitize_agent_reply(reply)

        self.assertIn("\n\n✨ *1. HB20*", sanitized)
        self.assertIn("\n📅 2022 |", sanitized)

    def test_filter_stock_payload_nao_confunde_crv_com_outros_honda(self):
        payload = json.dumps(
            {
                "ok": True,
                "count": 3,
                "matches": [
                    {"titulo": "Honda Fit EX 1.5", "marca": "Honda", "modelo": "Fit", "ano": 2021, "preco": 67900},
                    {"titulo": "Honda CR-V EXL 2.0", "marca": "Honda", "modelo": "CR-V", "ano": 2015, "preco": 87900},
                    {"titulo": "Honda Civic LXR 2.0", "marca": "Honda", "modelo": "Civic", "ano": 2016, "preco": 73900},
                ],
            }
        )

        filtered = _filter_stock_payload(payload, "CRV")

        self.assertIsNotNone(filtered)
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["matches"][0]["modelo"], "CR-V")


class ProcessMessageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    async def test_process_message_passes_factual_context_to_agent(self):
        session_id = "sessao-process"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda Fit LXL 1.4")

        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta do agente")))

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(return_value=[]),
        ):
            result = await process_message(
                session_id=session_id,
                user_message="Tem fotos?",
                conversation_id="conv-123",
            )

        self.assertEqual(result["reply"], "Resposta do agente")
        called_input = fake_agent.arun.await_args.kwargs["input"]
        self.assertIn("VEICULO_INTERESSE_ATUAL=Honda Fit LXL 1.4", called_input)
        self.assertIn("[MSG DO LEAD]\nTem fotos?", called_input)
        self.assertNotIn("PROXIMO_PASSO_OBRIGATORIO", called_input)

    async def test_process_message_uses_pending_messages_when_available(self):
        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta em bloco")))

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(
                return_value=[
                    {"direction": "outbound", "body": "Olá"},
                    {"direction": "inbound", "body": "Tenho um Gol pra dar na troca"},
                    {"direction": "inbound", "body": "Sou de Joinville"},
                ]
            ),
        ):
            await process_message(
                session_id="sessao-pendencias",
                user_message="Sou de Joinville",
                conversation_id="conv-456",
            )

        called_input = fake_agent.arun.await_args.kwargs["input"]
        self.assertIn("[MENSAGENS PENDENTES DO LEAD]", called_input)
        self.assertIn("1. Tenho um Gol pra dar na troca", called_input)
        self.assertIn("2. Sou de Joinville", called_input)

    async def test_process_message_sends_all_pending_to_agent(self):
        """Com buffer reduction removido, TODAS as mensagens pendentes devem chegar ao agente."""
        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta objetiva")))

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(
                return_value=[
                    {"direction": "outbound", "body": "Olá! Posso te passar mais informações?"},
                    {"direction": "inbound", "body": "Olá"},
                    {"direction": "inbound", "body": "Pode sim!"},
                    {"direction": "inbound", "body": "Qual o valor?"},
                ]
            ),
        ):
            await process_message(
                session_id="sessao-buffer-completo",
                user_message="Olá",
                conversation_id="conv-789",
            )

        called_input = fake_agent.arun.await_args.kwargs["input"]
        self.assertIn("[MENSAGENS PENDENTES DO LEAD]", called_input)
        self.assertIn("1. Olá", called_input)
        self.assertIn("2. Pode sim!", called_input)
        self.assertIn("3. Qual o valor?", called_input)

    async def test_process_message_busca_multiplos_veiculos_e_mantem_memoria(self):
        session_id = "sessao-multiplos"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda CR-V")
        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta do agente")))

        stock_payload = {
            "ok": True,
            "count": 1,
            "matches": [
                {
                    "vehicle_key": "vw-gol",
                    "titulo": "Volkswagen Gol 1.6",
                    "marca": "Volkswagen",
                    "modelo": "Gol",
                    "ano": 2019,
                    "preco": 48900,
                    "quilometragem": 62000,
                    "cambio": "Manual",
                }
            ],
        }

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "runtime.orchestrator.extract_intent_from_message",
            return_value=SimpleNamespace(
                is_asking_for_vehicle=True,
                vehicle_query="Gol",
                is_asking_for_photos=False,
                is_accepting_info=False,
                wants_human=False,
                qualification_facts=SimpleNamespace(model_dump=lambda exclude_none=True: {}),
            ),
        ), patch(
            "runtime.orchestrator.detect_vehicle_mentions",
            return_value=["Volkswagen Gol", "Honda CR-V"],
        ), patch(
            "runtime.orchestrator.consultar_estoque",
            return_value=json.dumps(stock_payload),
        ) as mocked_stock:
            await process_message(
                session_id=session_id,
                user_message="Também vi um Gol aí e queria saber se a CR-V ainda está disponível",
            )

        self.assertEqual(mocked_stock.call_count, 2)
        lead = _lead_states[session_id]
        self.assertEqual(lead.vehicle_journey.primary_interest, "Honda CR-V")
        self.assertIn("Volkswagen Gol", lead.vehicle_journey.secondary_interests)
        self.assertEqual(lead.vehicle_journey.current_request, "Volkswagen Gol")

    async def test_process_message_pede_fotos_do_veiculo_citado_no_turno_atual(self):
        session_id = "sessao-fotos-gol"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda CR-V")
        lead = _lead_states[session_id]
        lead.register_presented_vehicles(
            [
                {"titulo": "Honda CR-V EXL 2.0", "marca": "Honda", "modelo": "CR-V", "ano": 2015, "preco": 87900, "quilometragem": 98000, "cambio": "Automático"},
                {"titulo": "Volkswagen Gol 1.6", "marca": "Volkswagen", "modelo": "Gol", "ano": 2019, "preco": 48900, "quilometragem": 62000, "cambio": "Manual"},
            ],
            source="seed",
        )

        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta do agente")))

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "runtime.orchestrator.extract_intent_from_message",
            return_value=SimpleNamespace(
                is_asking_for_vehicle=False,
                vehicle_query="Gol",
                is_asking_for_photos=True,
                is_accepting_info=False,
                wants_human=False,
                qualification_facts=SimpleNamespace(model_dump=lambda exclude_none=True: {}),
            ),
        ), patch(
            "runtime.orchestrator.detect_vehicle_mentions",
            return_value=["Volkswagen Gol"],
        ), patch(
            "runtime.orchestrator.get_vehicle_photo_urls",
            return_value=["https://img/gol/1.jpg"],
        ) as mocked_photos:
            result = await process_message(
                session_id=session_id,
                user_message="Tem fotos do Golzinho?",
            )

        mocked_photos.assert_called_once_with("Volkswagen Gol 1.6", limit=10)
        self.assertEqual(result["attachments"], ["https://img/gol/1.jpg"])
        self.assertEqual(_lead_states[session_id].vehicle_journey.photo_target, "Volkswagen Gol 1.6")

    async def test_process_message_prioriza_veiculo_citado_no_turno_sobre_saudacao(self):
        session_id = "sessao-troca-foco"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda CR-V")
        _lead_states[session_id].vehicle_journey.greeting_vehicle = "Honda CR-V"
        fake_agent = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(content="Resposta do agente")))

        stock_payload = {
            "ok": True,
            "count": 1,
            "matches": [
                {
                    "vehicle_key": "vw-gol",
                    "titulo": "Volkswagen Gol 1.6",
                    "marca": "Volkswagen",
                    "modelo": "Gol",
                    "ano": 2019,
                    "preco": 48900,
                    "quilometragem": 62000,
                    "cambio": "Manual",
                }
            ],
        }

        with patch("runtime.orchestrator.create_lucas_agent", return_value=fake_agent), patch(
            "runtime.orchestrator.get_messages_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "runtime.orchestrator.extract_intent_from_message",
            return_value=SimpleNamespace(
                is_asking_for_vehicle=True,
                vehicle_query="Gol",
                is_asking_for_photos=False,
                is_accepting_info=False,
                wants_human=False,
                qualification_facts=SimpleNamespace(model_dump=lambda exclude_none=True: {}),
            ),
        ), patch(
            "runtime.orchestrator.detect_vehicle_mentions",
            return_value=["Volkswagen Gol"],
        ), patch(
            "runtime.orchestrator.consultar_estoque",
            return_value=json.dumps(stock_payload),
        ):
            await process_message(
                session_id=session_id,
                user_message="Vi também um Gol. Ainda está disponível?",
            )

        lead = _lead_states[session_id]
        self.assertEqual(lead.vehicle_journey.greeting_vehicle, "Honda CR-V")
        self.assertEqual(lead.vehicle_journey.current_focus, "Volkswagen Gol")
        self.assertEqual(lead.vehicle_journey.current_request, "Volkswagen Gol")


if __name__ == "__main__":
    unittest.main()
