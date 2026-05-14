import os
import json
import unittest
from unittest.mock import patch

from tools.calendar import agendar_visita, buscar_horarios_livres


class CalendarToolTests(unittest.TestCase):
    def test_agendar_visita_envia_contact_id_correto_no_payload(self) -> None:
        captured = {}

        def fake_request(method: str, path: str, **kwargs):
            captured["method"] = method
            captured["path"] = path
            if method == "GET":
                return {
                    "slots": [
                        "2026-05-09T10:00:00-03:00",
                        "2026-05-09T11:00:00-03:00",
                    ]
                }
            captured["json"] = kwargs["json"]
            return {"id": "appt_123"}

        with patch.dict(
            os.environ,
            {
                "GHL_CALENDAR_ID": "cal_123",
                "GHL_LOCATION_ID": "loc_456",
            },
            clear=False,
        ):
            with patch("tools.calendar._ghl_request_sync", side_effect=fake_request):
                reply = agendar_visita(
                    data_hora_iso="2026-05-09T10:00:00",
                    nome="Ricardo",
                    email="ricardo@example.com",
                    telefone="47999998888",
                    contact_id="contact_789",
                )

        payload = json.loads(reply)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "confirmed")
        self.assertTrue(payload["creation_verified"])
        self.assertEqual(payload["appointment_id"], "appt_123")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["path"], "/calendars/events/appointments")
        self.assertEqual(captured["json"]["contactId"], "contact_789")
        self.assertEqual(captured["json"]["calendarId"], "cal_123")
        self.assertEqual(captured["json"]["locationId"], "loc_456")
        self.assertEqual(captured["json"]["appointmentStatus"], "confirmed")
        self.assertEqual(captured["json"]["email"], "ricardo@example.com")
        self.assertEqual(captured["json"]["phone"], "47999998888")

    def test_agendar_visita_falha_sem_contact_id(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GHL_CALENDAR_ID": "cal_123",
                "GHL_LOCATION_ID": "loc_456",
            },
            clear=False,
        ):
            with patch("tools.calendar._ghl_request_sync") as request_mock:
                reply = agendar_visita(
                    data_hora_iso="2026-05-09T10:00:00",
                    nome="Ricardo",
                    email="",
                    telefone="47999998888",
                    contact_id="",
                )

        payload = json.loads(reply)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "contact_id_obrigatorio")
        request_mock.assert_not_called()

    def test_agendar_visita_retorna_horarios_parecidos_quando_slot_indisponivel(self) -> None:
        def fake_request(method: str, path: str, **kwargs):
            if method == "GET":
                return {
                    "slots": [
                        "2026-05-09T09:30:00-03:00",
                        "2026-05-09T10:30:00-03:00",
                        "2026-05-09T11:00:00-03:00",
                    ]
                }
            self.fail("POST não deveria acontecer quando o horário não está livre")

        with patch.dict(
            os.environ,
            {
                "GHL_CALENDAR_ID": "cal_123",
                "GHL_LOCATION_ID": "loc_456",
                "GHL_CALENDAR_TIMEZONE": "America/Sao_Paulo",
            },
            clear=False,
        ):
            with patch("tools.calendar._ghl_request_sync", side_effect=fake_request):
                reply = agendar_visita(
                    data_hora_iso="2026-05-09T10:00:00-03:00",
                    nome="Ricardo",
                    email="",
                    telefone="47999998888",
                    contact_id="contact_789",
                )

        payload = json.loads(reply)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "horario_indisponivel")
        self.assertEqual(payload["requested_time"], "10:00")
        self.assertEqual(payload["suggested_slots"], ["09:30", "10:30", "11:00"])

    def test_buscar_horarios_livres_informa_disponibilidade_do_horario_exato(self) -> None:
        def fake_request(method: str, path: str, **kwargs):
            return {
                "slots": [
                    "2026-05-09T09:30:00-03:00",
                    "2026-05-09T10:00:00-03:00",
                    "2026-05-09T10:30:00-03:00",
                ]
            }

        with patch.dict(
            os.environ,
            {
                "GHL_CALENDAR_ID": "cal_123",
                "GHL_CALENDAR_TIMEZONE": "America/Sao_Paulo",
            },
            clear=False,
        ):
            with patch("tools.calendar._ghl_request_sync", side_effect=fake_request):
                reply = buscar_horarios_livres("2026-05-09T10:00:00-03:00")

        payload = json.loads(reply)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["requested_time"], "10:00")
        self.assertTrue(payload["requested_slot_available"])
        self.assertEqual(payload["suggested_slots"], ["10:00", "09:30", "10:30"])


if __name__ == "__main__":
    unittest.main()
