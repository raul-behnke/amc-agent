import unittest

from tools.crm import _build_structured_note
from tools.qualification import _lead_states, registrar_estado


class CRMToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    def test_build_structured_note_accepts_observacoes_from_lead_state(self) -> None:
        session_id = "sessao-crm"
        registrar_estado(
            session_id=session_id,
            nome="Raul",
            interesse="Gol 2013",
            cidade="Joinville",
            observacoes="Lead pediu retorno humano",
            veiculo_interesse="Gol 2013",
            motivo_handoff="cliente_prefere_humano",
        )

        note = _build_structured_note(_lead_states[session_id], "cliente_prefere_humano")

        self.assertIn("Observações: Lead pediu retorno humano", note)
        self.assertIn("Veículo do estoque: Gol 2013", note)


if __name__ == "__main__":
    unittest.main()
