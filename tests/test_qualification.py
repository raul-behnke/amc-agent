import json
import unittest

from state.lead_model import LeadQualification, LeadStatus
from tools.qualification import _lead_states, consultar_qualificacao, registrar_estado, registrar_qualificacao


class QualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        _lead_states.clear()

    def test_data_visita_sem_horario_mantem_status_scheduling(self) -> None:
        session_id = "sessao-teste"

        registrar_qualificacao(
            session_id=session_id,
            data_visita="segunda",
        )

        lead = _lead_states[session_id]
        self.assertEqual(lead.status, LeadStatus.SCHEDULING)
        self.assertIn("horário exato", lead.proximo_passo().lower())

    def test_data_visita_com_horario_vira_scheduled(self) -> None:
        session_id = "sessao-teste-horario"

        registrar_qualificacao(
            session_id=session_id,
            data_visita="2026-05-11 10:00",
        )

        lead = _lead_states[session_id]
        self.assertEqual(lead.status, LeadStatus.SCHEDULED)

    def test_trade_vehicle_sem_ano_pede_detalhes(self) -> None:
        lead = LeadQualification(nome="Raul", interesse="HB20", intencao="Troca", tem_troca=True, veiculo_troca="Gol")
        self.assertFalse(lead.trade_vehicle_has_details())
        self.assertIn("ano/modelo completo", lead.proximo_passo().lower())
        self.assertEqual(lead.next_qualification_field(), "veiculo_troca")

    def test_next_qualification_question_prioriza_motivacao_depois_de_troca(self) -> None:
        lead = LeadQualification(
            nome="Raul",
            interesse="HB20",
            intencao="Troca",
            tem_troca=True,
            veiculo_troca="Gol 2011",
        )

        self.assertEqual(lead.next_qualification_field(), "motivacao")
        self.assertEqual(lead.next_qualification_question(), "O que te fez pensar em trocar agora?")

    def test_next_qualification_question_pede_detalhe_quando_troca_incompleta(self) -> None:
        lead = LeadQualification(
            nome="Raul",
            interesse="HB20",
            intencao="Troca",
            tem_troca=True,
            veiculo_troca="Gol",
        )

        self.assertEqual(lead.next_qualification_field(), "veiculo_troca")
        self.assertEqual(lead.next_qualification_question(), "Qual o ano e o modelo do seu carro de troca?")

    def test_registrar_estado_popula_vehicle_focus_e_lead_answers(self) -> None:
        session_id = "sessao-estado"
        result = json.loads(
            registrar_estado(
                session_id=session_id,
                nome="Camila",
                interesse="Honda Fit EX 1.5",
                intencao="Compra",
                motivacao="Precisa de um carro automático para uso diário",
                negociacao="Financiamento",
                cidade="Joinville",
                observacoes="Prefere opções com baixo km",
                conversation_summary="Lead quer um compacto automático até 70 mil.",
                alternatives_shown=[
                    {
                        "titulo": "Honda Fit EX 1.5",
                        "marca": "Honda",
                        "modelo": "Fit",
                        "ano": 2021,
                        "preco": 67900,
                        "quilometragem": 45000,
                        "cambio": "Automático",
                    },
                    {
                        "titulo": "Hyundai HB20 1.6",
                        "marca": "Hyundai",
                        "modelo": "HB20",
                        "ano": 2022,
                        "preco": 66900,
                        "quilometragem": 48000,
                        "cambio": "Mecânico",
                    },
                ],
            )
        )

        lead = _lead_states[session_id]
        self.assertEqual(lead.vehicle_focus.current, "Honda Fit EX 1.5")
        self.assertEqual(lead.vehicle_focus.last_valid, "Honda Fit EX 1.5")
        self.assertEqual(lead.lead_answers["interesse"], "Honda Fit EX 1.5")
        self.assertEqual(lead.lead_answers["cidade"], "Joinville")
        self.assertEqual(lead.lead_answers["negociacao"], "Financiamento")
        self.assertEqual(lead.observacoes, "Prefere opções com baixo km")
        self.assertEqual(result["qualificacao"]["interesse"], "Honda Fit EX 1.5")
        self.assertEqual(result["vehicle_focus"]["alternatives_shown"][1]["titulo"], "Hyundai HB20 1.6")

    def test_consultar_qualificacao_retorna_snapshot_json(self) -> None:
        session_id = "sessao-consulta"
        registrar_estado(
            session_id=session_id,
            nome="Lucas",
            interesse="Hyundai HB20",
            intencao="Compra",
            motivacao="Quer trocar de carro",
            negociacao="À vista",
            cidade="Joinville",
            observacoes="Sem observações adicionais",
        )

        result = json.loads(consultar_qualificacao(session_id))

        self.assertEqual(result["status"], "QUALIFIED")
        self.assertEqual(result["filled"]["nome"], "Lucas")
        self.assertEqual(result["qualificacao"]["cidade"], "Joinville")
        self.assertIn("next_qualification_question", result)

    def test_registrar_estado_mescla_active_filters_no_vehicle_focus(self) -> None:
        session_id = "sessao-filtros"
        registrar_estado(
            session_id=session_id,
            vehicle_focus_current="Hyundai HB20",
            active_filters={"faixa_preco": "até 70 mil"},
        )
        registrar_estado(
            session_id=session_id,
            active_filters={"ano_minimo": 2020},
        )

        lead = _lead_states[session_id]
        self.assertEqual(lead.vehicle_focus.active_filters["faixa_preco"], "até 70 mil")
        self.assertEqual(lead.vehicle_focus.active_filters["ano_minimo"], 2020)


if __name__ == "__main__":
    unittest.main()
