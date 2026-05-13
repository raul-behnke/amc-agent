import unittest

from scripts.run_lucas_qa_battery import evaluate_result


class QABatteryTests(unittest.TestCase):
    def test_evaluate_result_approves_audio_fallback_when_text_request_present(self) -> None:
        result = {
            "id": "qa-c14",
            "name": "Audio sem transcricao util",
            "interactions": [
                {
                    "lead": "> Voice Note <",
                    "agent": "Desculpa, não consegui escutar seu áudio agora 😅 Pode mandar por texto pra mim?",
                }
            ],
            "qualification": {},
            "score": 0,
            "status": "NEW_LEAD",
        }

        evaluation = evaluate_result(result)

        self.assertTrue(evaluation["approved"])
        self.assertEqual(evaluation["failed_count"], 0)

    def test_evaluate_result_reproves_handoff_absent_when_explicit_human_request(self) -> None:
        result = {
            "id": "qa-c16",
            "name": "Pedido explicito de humano",
            "interactions": [
                {
                    "lead": "Quero falar com um consultor",
                    "agent": "Posso te ajudar por aqui primeiro. Qual carro você procura?",
                }
            ],
            "qualification": {},
            "score": 0,
            "status": "QUALIFYING",
        }

        evaluation = evaluate_result(result)

        self.assertFalse(evaluation["approved"])
        self.assertGreaterEqual(evaluation["failed_count"], 1)

    def test_evaluate_result_reproves_multiple_questions_in_same_message(self) -> None:
        result = {
            "id": "qa-c99",
            "name": "Genérico",
            "interactions": [
                {
                    "lead": "Oi",
                    "agent": "Tudo bem? Você tem troca? Vai financiar?",
                }
            ],
            "qualification": {},
            "score": 0,
            "status": "NEW_LEAD",
        }

        evaluation = evaluate_result(result)

        self.assertFalse(evaluation["approved"])
        self.assertTrue(any(not check["passed"] for check in evaluation["checks"]))


if __name__ == "__main__":
    unittest.main()
