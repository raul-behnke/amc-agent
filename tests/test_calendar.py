import os
import json
import unittest
from unittest.mock import patch

from tools.calendar import agendar_visita


class CalendarToolTests(unittest.TestCase):
    def test_agendar_visita_envia_contact_id_correto_no_payload(self) -> None:
        captured = {}

        def fake_request(method: str, path: str, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = kwargs["json"]
            return {}

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


if __name__ == "__main__":
    unittest.main()
