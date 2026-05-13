import json
import os
import unittest
from unittest.mock import patch

from tools.inventory import (
    _match_vehicle_flexible,
    buscar_fotos_veiculo,
    consultar_estoque,
    infer_vehicle_interest_from_text,
)


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = patch.dict(os.environ, {"INVENTORY_USE_LLM": "0"}, clear=False)
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

    def test_match_gol_nao_confunde_com_golf(self) -> None:
        gol = {"marca": "Volkswagen", "modelo": "Gol", "titulo": "Volkswagen Gol 1.0"}
        golf = {"marca": "Volkswagen", "modelo": "Golf", "titulo": "Volkswagen Golf Highline 1.4"}

        self.assertTrue(_match_vehicle_flexible(gol, "Gol"))
        self.assertFalse(_match_vehicle_flexible(golf, "Gol"))

    def test_consultar_estoque_sem_termo_retorna_erro_de_tool(self) -> None:
        result = json.loads(consultar_estoque())
        self.assertFalse(result["ok"])
        self.assertIn("ERRO_TOOL_ESTOQUE", result["error"])

    def test_consultar_estoque_por_faixa_preco_sugere_veiculos(self) -> None:
        inventory = [
            {"marca": "Citroën", "modelo": "C3", "titulo": "Citroën C3 1.6", "ano": 2010, "preco": 26900, "quilometragem": 130000, "cambio": "Automático"},
            {"marca": "Jeep", "modelo": "Renegade", "titulo": "Jeep Renegade 1.8", "ano": 2020, "preco": 73900, "quilometragem": 97000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(consultar_estoque(faixa_preco="até 30 mil"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["titulo"], "Citroën C3 1.6")
        self.assertEqual(result["response_mode"], "single")
        self.assertEqual(result["selected_vehicle"]["titulo"], "Citroën C3 1.6")
        self.assertEqual(len(result["candidate_pool"][0]["imagens"]), 0)

    def test_consultar_estoque_por_categoria_e_faixa(self) -> None:
        inventory = [
            {"marca": "Renault", "modelo": "Fluence", "titulo": "Renault Fluence Sedan 2.0", "ano": 2012, "preco": 43900, "quilometragem": 128000, "cambio": "Automático"},
            {"marca": "Jeep", "modelo": "Renegade", "titulo": "Jeep Renegade 1.8", "ano": 2020, "preco": 73900, "quilometragem": 97000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(consultar_estoque(tipo_veiculo="sedan", faixa_preco="até 50 mil"))

        self.assertEqual(result["count"], 1)
        self.assertIn("Fluence", result["matches"][0]["titulo"])

    def test_infer_vehicle_interest_ignora_pedido_generico_de_filtro(self) -> None:
        self.assertIsNone(infer_vehicle_interest_from_text("Tem algum mais novo? acima de 2020?"))

    def test_consultar_estoque_por_modelo_e_ano_minimo(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V", "ano": 2017, "preco": 48900, "quilometragem": 120000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution Bluelink 1.0 Flex 12V Mec", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Mecânico"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(consultar_estoque(modelo="Hyundai HB20", ano_minimo=2020))

        self.assertEqual(result["count"], 1)
        self.assertIn("Evolution", result["matches"][0]["titulo"])

    def test_consultar_estoque_usa_reference_vehicle_para_manter_mesma_familia(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2018, "preco": 49900, "quilometragem": 80000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Automático"},
            {"marca": "Honda", "modelo": "Fit", "titulo": "Honda Fit EX 1.5", "ano": 2021, "preco": 67900, "quilometragem": 45000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    reference_vehicle="Hyundai HB20 Comfort 1.0",
                    prefer="newer",
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["resolved_reference_vehicle"]["modelo"], "HB20")
        self.assertEqual(result["matches"][0]["modelo"], "HB20")
        self.assertNotIn("Fit", result["matches"][0]["titulo"])

    def test_consultar_estoque_lista_opcoes_com_pool_estruturado(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2018, "preco": 49900, "quilometragem": 80000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(consultar_estoque(modelo="Hyundai HB20"))

        self.assertEqual(result["response_mode"], "alternatives")
        self.assertEqual(len(result["candidate_pool"]), 2)
        self.assertEqual(len(result["candidate_pool"][0]["imagens"]), 0)
        self.assertEqual(result["candidate_pool"][0]["vehicle_key"].startswith("hyundai|hb20"), True)

    def test_consultar_estoque_com_prompt_busca_retorna_curada_rag(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Automático"},
            {"marca": "Volkswagen", "modelo": "Gol", "titulo": "Volkswagen Gol 1.6", "ano": 2019, "preco": 48900, "quilometragem": 62000, "cambio": "Manual"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    prompt_busca="cliente quer um carro com preço bom e de preferência 1.6",
                    perfil_cliente="Lead quer comparar opções econômicas",
                    modo="alternatives",
                )
            )

        self.assertTrue(result["ok"])
        self.assertIn("search_brief", result)
        self.assertGreaterEqual(len(result["candidate_pool"]), 1)
        self.assertIn(result["response_mode"], {"alternatives", "single", "confirm", "vehicle_info"})

    def test_consultar_estoque_alternatives_para_vehicle_focus_preenche_varias_opcoes(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2018, "preco": 49900, "quilometragem": 80000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Sense 1.0", "ano": 2020, "preco": 56900, "quilometragem": 62000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    prompt_busca="tem fotos?",
                    vehicle_focus="Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V",
                    reference_vehicle="Hyundai HB20 Comf./C.Plus/C.Style 1.0 Flex 12V",
                    modo="alternatives",
                    limite=3,
                )
            )

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["candidate_pool"]), 3)
        self.assertEqual(result["candidate_pool"][0]["modelo"], "HB20")

    def test_consultar_estoque_alternatives_nao_trunca_lista_completa(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": f"Hyundai HB20 Opção {index}", "ano": 2018 + index, "preco": 49900 + (index * 1000), "quilometragem": 80000 - (index * 5000), "cambio": "Mecânico"}
            for index in range(6)
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    prompt_busca="quero ver opções do hb20",
                    vehicle_focus="Hyundai HB20",
                    reference_vehicle="Hyundai HB20",
                    modo="alternatives",
                    limite=3,
                )
        )

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["candidate_pool"]), 6)
        self.assertEqual(result["candidate_pool"][0]["titulo"], "Hyundai HB20 Opção 0")

    def test_consultar_estoque_prefer_newer_destaca_motivo(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2018, "preco": 49900, "quilometragem": 80000, "cambio": "Mecânico", "imagens": ["https://img/comfort/1.jpg", "https://img/comfort/2.jpg", "https://img/comfort/3.jpg"]},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Automático", "imagens": ["https://img/evolution/1.jpg", "https://img/evolution/2.jpg", "https://img/evolution/3.jpg"]},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    reference_vehicle="Hyundai HB20 Comfort 1.0",
                    prefer="newer",
                )
            )

        self.assertEqual(result["response_mode"], "alternatives")
        self.assertEqual(len(result["candidate_pool"][0]["imagens"]), 2)
        self.assertEqual(len(result["candidate_pool"][1]["imagens"]), 2)

    def test_consultar_estoque_alternatives_exclui_referencia_ja_apresentada(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2017, "preco": 48900, "quilometragem": 120000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2017, "preco": 48900, "quilometragem": 110000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Mecânico"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    reference_vehicle="Hyundai HB20 Comfort 1.0",
                    prefer="newer",
                    modo="alternatives",
                )
            )

        self.assertTrue(result["ok"])
        self.assertNotEqual(result["candidate_pool"][0]["quilometragem"], 120000)
        self.assertEqual(result["candidate_pool"][0]["ano"], 2022)

    def test_consultar_estoque_alternatives_exclui_veiculos_ignorados(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2017, "preco": 48900, "quilometragem": 110000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2017, "preco": 48900, "quilometragem": 120000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Evolution 1.0", "ano": 2022, "preco": 66900, "quilometragem": 48000, "cambio": "Mecânico"},
        ]
        ignored_vehicle = {
            "marca": "Hyundai",
            "modelo": "HB20",
            "titulo": "Hyundai HB20 Comfort 1.0",
            "ano": 2017,
            "preco": 48900,
            "quilometragem": 110000,
            "cambio": "Mecânico",
        }
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    vehicle_focus="Hyundai HB20",
                    modo="alternatives",
                    veiculos_ignorados=[ignored_vehicle],
                )
            )

        self.assertTrue(result["ok"])
        shown_kms = {item["quilometragem"] for item in result["candidate_pool"]}
        self.assertNotIn(110000, shown_kms)

    def test_consultar_estoque_single_vehicle_allows_more_photos(self) -> None:
        inventory = [
            {
                "marca": "Honda",
                "modelo": "Fit",
                "titulo": "Honda Fit EX 1.5",
                "ano": 2019,
                "preco": 68900,
                "quilometragem": 55000,
                "cambio": "Automático",
                "imagens": [f"https://img/{index}.jpg" for index in range(12)],
            }
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(consultar_estoque(modelo="Honda Fit"))

        self.assertEqual(result["response_mode"], "single")
        self.assertEqual(len(result["candidate_pool"][0]["imagens"]), 10)

    def test_consultar_estoque_prefer_cheaper_limita_pelo_referencia(self) -> None:
        inventory = [
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Comfort 1.0", "ano": 2018, "preco": 49900, "quilometragem": 80000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Sense 1.0", "ano": 2019, "preco": 45900, "quilometragem": 70000, "cambio": "Mecânico"},
            {"marca": "Hyundai", "modelo": "HB20", "titulo": "Hyundai HB20 Platinum 1.0", "ano": 2022, "preco": 73900, "quilometragem": 35000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    reference_vehicle="Hyundai HB20 Comfort 1.0",
                    prefer="cheaper",
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["matches"][0]["titulo"], "Hyundai HB20 Sense 1.0")
        self.assertLessEqual(result["matches"][0]["preco"], 49900)

    def test_consultar_estoque_prefer_automatic_aplica_cambio(self) -> None:
        inventory = [
            {"marca": "Jeep", "modelo": "Renegade", "titulo": "Jeep Renegade Sport 1.8", "ano": 2019, "preco": 71900, "quilometragem": 69000, "cambio": "Mecânico"},
            {"marca": "Jeep", "modelo": "Renegade", "titulo": "Jeep Renegade Longitude 1.8", "ano": 2020, "preco": 78900, "quilometragem": 55000, "cambio": "Automático"},
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(
                consultar_estoque(
                    reference_vehicle="Jeep Renegade Sport 1.8",
                    prefer="automatic",
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["matches"][0]["cambio"], "Automático")

    def test_busca_fotos_veiculo_retorna_payload_estruturado(self) -> None:
        inventory = [
            {
                "marca": "Honda",
                "modelo": "Fit",
                "titulo": "Honda Fit EX 1.5",
                "ano": 2019,
                "preco": 68900,
                "quilometragem": 55000,
                "cambio": "Automático",
                "imagens": ["https://img/1.jpg", "https://img/2.jpg"],
            }
        ]
        with patch("tools.inventory.fetch_inventory_sync", return_value=inventory):
            result = json.loads(buscar_fotos_veiculo("Honda Fit", limit=1))

        self.assertTrue(result["ok"])
        self.assertEqual(result["photo_count"], 1)
        self.assertEqual(result["photos"], ["https://img/1.jpg"])


if __name__ == "__main__":
    unittest.main()
