import unittest
import json
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.webhooks.chat import _build_outbound_messages, _run_agent_and_respond, router
from tools.qualification import _get_lead, _lead_states, registrar_estado, registrar_qualificacao


class ChatWebhookPhotoTests(unittest.TestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    def test_placeholder_photos_are_converted_to_attachments(self):
        session_id = "sessao-fotos"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda Fit LXL 1.4")

        with patch(
            "api.webhooks.chat.get_vehicle_photo_urls",
            return_value=["https://img/1.jpg", "https://img/2.jpg"],
        ):
            messages = _build_outbound_messages(
                "Aqui estão as fotos do Honda Fit que você pediu: [FOTO 1] [FOTO 2] ||| Qual ano/modelo é o seu Gol?",
                session_id=session_id,
            )

        self.assertEqual(
            messages,
            [
                {"text": "Aqui estão as fotos do Honda Fit que você pediu:", "attachments": None},
                {"text": "", "attachments": ["https://img/1.jpg", "https://img/2.jpg"]},
                {"text": "Qual ano/modelo é o seu Gol?", "attachments": None},
            ],
        )

    def test_photo_placeholder_prefers_vehicle_mentioned_in_text_over_stale_session_interest(self):
        session_id = "sessao-fotos-stale"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Hyundai HB20")

        with patch(
            "api.webhooks.chat.infer_vehicle_interest_from_text",
            return_value="HONDA FIT LXL 1.4/ 1.4 FLEX 8V/16V 5P AUT.",
        ), patch(
            "api.webhooks.chat.get_vehicle_photo_urls",
            return_value=["https://fit/1.jpg", "https://fit/2.jpg"],
        ) as mocked_photos:
            messages = _build_outbound_messages(
                "Aqui estão as fotos do Honda Fit: [FOTO 1] [FOTO 2]",
                session_id=session_id,
            )

        mocked_photos.assert_called_once_with(
            vehicle_query="HONDA FIT LXL 1.4/ 1.4 FLEX 8V/16V 5P AUT.",
            limit=2,
        )
        self.assertEqual(messages[1]["attachments"], ["https://fit/1.jpg", "https://fit/2.jpg"])

    def test_inline_photo_urls_still_become_attachments(self):
        messages = _build_outbound_messages(
            "Fotos: [FOTO 1]: https://img/1.jpg [FOTO 2]: https://img/2.jpg",
            session_id="sessao-vazia",
        )

        self.assertEqual(
            messages,
            [
                {"text": "Fotos:", "attachments": None},
                {"text": "", "attachments": ["https://img/1.jpg", "https://img/2.jpg"]},
            ],
        )

    def test_plain_numbered_image_urls_also_become_attachments(self):
        messages = _build_outbound_messages(
            "Aqui estão algumas fotos:\n1. https://img/1.jpg\n2. https://img/2.jpeg",
            session_id="sessao-vazia",
        )

        self.assertEqual(
            messages,
            [
                {"text": "Aqui estão algumas fotos:\n1. \n2.", "attachments": None},
                {"text": "", "attachments": ["https://img/1.jpg", "https://img/2.jpeg"]},
            ],
        )

    def test_malformed_photo_template_uses_stock_fallback(self):
        session_id = "sessao-fallback-foto"
        registrar_estado(
            session_id=session_id,
            veiculo_interesse="Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V",
            alternatives_shown=[
                {
                    "titulo": "Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V",
                    "marca": "Hyundai",
                    "modelo": "HB20",
                    "ano": 2022,
                    "preco": 66900,
                    "quilometragem": 48000,
                    "cambio": "Mecânico",
                }
            ],
        )

        stock_payload = {
            "ok": True,
            "resolved_reference_vehicle": {"modelo": "HB20", "titulo": "Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V"},
            "matches": [
                {"titulo": "Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V", "marca": "Hyundai", "modelo": "HB20", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Mecânico"},
                {"titulo": "Hyundai HB20 Sense 1.0", "marca": "Hyundai", "modelo": "HB20", "ano": 2020, "preco": 56900, "quilometragem": 62000, "cambio": "Mecânico"},
                {"titulo": "Hyundai HB20 Sense 1.0", "marca": "Hyundai", "modelo": "HB20", "ano": 2020, "preco": 56900, "quilometragem": 62000, "cambio": "Mecânico"},
            ],
            "fallback_matches": [],
        }

        with patch("api.webhooks.chat.consultar_estoque", return_value=json.dumps(stock_payload)), patch(
            "api.webhooks.chat.get_vehicle_card_text",
            side_effect=lambda title, request_text="": f"CARD::{title}",
        ), patch(
            "api.webhooks.chat.get_vehicle_photo_urls",
            side_effect=lambda title, limit=2: [f"https://img/{title.replace(' ', '_')}/1.jpg", f"https://img/{title.replace(' ', '_')}/2.jpg"],
        ):
            messages = _build_outbound_messages(
                "Aqui estão algumas fotos do Hyundai HB20:\n📸 Foto 1\n📸 Foto 2\nQuer que eu te passe mais detalhes?",
                session_id=session_id,
            )

        self.assertEqual(messages[0]["text"], "Como você pediu fotos, separei as opções de HB20 que temos no estoque:")
        self.assertEqual(messages[1]["text"], "CARD::Hyundai HB20 Sense 1.0")
        self.assertEqual(messages[1]["attachments"], [
            "https://img/Hyundai_HB20_Sense_1.0/1.jpg",
            "https://img/Hyundai_HB20_Sense_1.0/2.jpg",
        ])
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[-1]["text"], "Me diz o que faz mais sentido pra você: automático, mais novo ou melhor preço?")

    def test_payload_vehicle_should_not_overwrite_existing_interest(self):
        session_id = "sessao-interest"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="HONDA FIT LXL 1.4/ 1.4 FLEX 8V/16V 5P AUT.")

        lead = _get_lead(session_id)
        veiculo_payload = "Hyunday HB20 Comf./C.Plus/C.Style 1.0 Flex 12V"
        inferred_vehicle = None

        if inferred_vehicle:
            registrar_qualificacao(session_id=session_id, veiculo_interesse=inferred_vehicle)
        elif veiculo_payload and not lead.veiculo_interesse:
            registrar_qualificacao(session_id=session_id, veiculo_interesse=veiculo_payload)

        self.assertEqual(
            _get_lead(session_id).veiculo_interesse,
            "HONDA FIT LXL 1.4/ 1.4 FLEX 8V/16V 5P AUT.",
        )

    def test_inbound_message_does_not_infer_vehicle_interest_anymore(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch("api.webhooks.chat.infer_vehicle_interest_from_text") as mocked_infer, patch(
            "api.webhooks.chat._run_agent_and_respond",
            new=AsyncMock(),
        ), patch(
            "api.webhooks.chat.has_tag",
            new=AsyncMock(return_value=True),
        ):
            response = client.post(
                "/webhook/message",
                json={
                    "contactId": "5511999999999",
                    "body": "Tenho interesse no Honda Fit",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")
        self.assertIsNone(_get_lead("5511999999999").veiculo_interesse)
        mocked_infer.assert_not_called()


class ChatWebhookFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    async def test_run_agent_and_respond_envia_blocos_texto_e_fotos(self):
        session_id = "sessao-fluxo-fotos"
        registrar_qualificacao(session_id=session_id, veiculo_interesse="Honda Fit LXL 1.4")

        with patch(
            "api.webhooks.chat.process_message",
            new=AsyncMock(
                return_value={
                    "reply": "Aqui estão as fotos do Fit: [FOTO 1] [FOTO 2] ||| Qual ano/modelo é o seu carro?",
                }
            ),
        ), patch(
            "api.webhooks.chat.get_vehicle_photo_urls",
            return_value=["https://img/1.jpg", "https://img/2.jpg"],
        ), patch(
            "api.webhooks.chat.send_message_async",
            new=AsyncMock(),
        ) as mocked_send, patch(
            "api.webhooks.chat.asyncio.sleep",
            new=AsyncMock(),
        ):
            await _run_agent_and_respond(
                session_id=session_id,
                user_message="Tem fotos?",
                contact_id="contact-123",
                conversation_id="conv-123",
            )

        self.assertEqual(mocked_send.await_count, 3)
        first_call = mocked_send.await_args_list[0].kwargs
        second_call = mocked_send.await_args_list[1].kwargs
        third_call = mocked_send.await_args_list[2].kwargs
        self.assertEqual(first_call["text"], "Aqui estão as fotos do Fit:")
        self.assertIsNone(first_call["attachments"])
        self.assertEqual(second_call["attachments"], ["https://img/1.jpg", "https://img/2.jpg"])
        self.assertEqual(third_call["text"], "Qual ano/modelo é o seu carro?")

    async def test_run_agent_and_respond_nao_envia_sem_contact_ou_conversation(self):
        with patch(
            "api.webhooks.chat.process_message",
            new=AsyncMock(return_value={"reply": "Olá"}),
        ), patch(
            "api.webhooks.chat.send_message_async",
            new=AsyncMock(),
        ) as mocked_send:
            await _run_agent_and_respond(
                session_id="sessao-sem-envio",
                user_message="Oi",
                contact_id=None,
                conversation_id=None,
            )

        mocked_send.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
