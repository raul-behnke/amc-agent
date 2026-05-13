import unittest

from prompts.lucas_sdr import LUCAS_INSTRUCTIONS


class PromptRulesTests(unittest.TestCase):
    def test_prompt_reforca_resposta_direta_e_qualificacao(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("RESPOSTA DIRETA", full_text)
        self.assertIn("ESTRUTURA DE CADA TURNO", full_text)
        self.assertIn("Faça UMA pergunta comercial objetiva", full_text)

    def test_prompt_reforca_ordem_da_qualificacao_de_troca(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("modelo/ano, km, quitado, estado, fotos", full_text)
        self.assertIn("siga esta sequência sem pular etapas", full_text)
        self.assertIn("DADOS_TROCA_PENDENTES", full_text)

    def test_prompt_proibe_perguntas_financeiras_fora_do_fluxo(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("Qual valor você pretende financiar?", full_text)
        self.assertIn("Quanto quer dar de entrada?", full_text)
        self.assertIn("Qual parcela cabe no seu bolso?", full_text)
        self.assertIn("qual valor pretende pagar por mês?", full_text.lower())

    def test_prompt_orienta_resposta_para_parcelas_com_troca_pendente(self) -> None:
        full_text = "\n".join(LUCAS_INSTRUCTIONS)

        self.assertIn("Se o lead perguntar sobre parcelas do restante", full_text)
        self.assertIn("primeiro precisamos avaliar o carro de troca", full_text)
        self.assertIn("só então simular melhor as parcelas", full_text)


if __name__ == "__main__":
    unittest.main()
