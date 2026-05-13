import unittest

from prompts.lucas_sdr import LUCAS_INSTRUCTIONS


class PromptRulesTests(unittest.TestCase):
    def test_prompt_orients_qualification_after_objective_request(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("Depois de responder uma solicitação objetiva do lead", full_text)
        self.assertIn("Depois de enviar fotos", full_text)
        self.assertIn("Evite repetir mecanicamente o que o lead acabou de dizer.", full_text)

    def test_prompt_orients_llm_to_analyze_inventory_options(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("Use consultar_estoque com prompt_busca, prompt_contexto, perfil_cliente, vehicle_focus e modo sempre que possível.", full_text)
        self.assertIn("Se a intenção for comparar carros, use modo='alternatives'.", full_text)
        self.assertIn("Se a tool devolver presentation.cards ou selected_vehicle, trate como dados estruturados", full_text)
        self.assertIn("candidate_pool", full_text)

    def test_prompt_orients_immediate_stock_search_on_filters(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("use consultar_estoque imediatamente", full_text)
        self.assertIn("a primeira resposta deve mostrar o estoque", full_text)

    def test_prompt_orients_proactive_photo_followup(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("Depois de enviar fotos, faça uma pergunta proativa e objetiva de preferência ou qualificação.", full_text)
        self.assertIn("Evite perguntas genéricas como 'quer mais detalhes?'", full_text)

    def test_prompt_orients_exact_vehicle_matching_from_context(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("VEHICLE_FOCUS_ALTERNATIVES_JSON", full_text)
        self.assertIn("use esse histórico para identificar exatamente qual opção o lead está citando", full_text)
        self.assertIn("não volte para o veículo genérico em foco", full_text)
        self.assertIn("veiculos_ignorados", full_text)
        self.assertIn("mesma alternativa exata usada nas fotos", full_text)


if __name__ == "__main__":
    unittest.main()
