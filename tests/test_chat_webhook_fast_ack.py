import unittest

from fastapi import BackgroundTasks
from starlette.requests import Request

from api.webhooks.chat import chat_webhook, greeting_webhook


def _request_with_json(payload: bytes) -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(scope, receive)


class ChatWebhookFastAckTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_webhook_acknowledges_and_enqueues_background_work(self):
        request = _request_with_json(
            b'{"contactId":"5511999999999","body":"Oi, quero saber o valor"}'
        )
        background_tasks = BackgroundTasks()

        response = await chat_webhook(request, background_tasks)

        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.session_id, "5511999999999")
        self.assertEqual(len(background_tasks.tasks), 1)

    async def test_greeting_webhook_acknowledges_and_enqueues_background_work(self):
        request = _request_with_json(
            b'{"contactId":"5511999999999","Ve\\u00edculo de Interesse":"HB20"}'
        )
        background_tasks = BackgroundTasks()

        response = await greeting_webhook(request, background_tasks)

        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.session_id, "5511999999999")
        self.assertEqual(len(background_tasks.tasks), 1)


if __name__ == "__main__":
    unittest.main()
