"""
Validation harness for consultar_estoque() filtering capability.
Runs a battery of realistic queries and prints planner filters + matches.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from tools.inventory import consultar_estoque
from services.ghl import fetch_inventory_sync


SCENARIOS = [
    # (label, kwargs)
    ("Categoria simples - SUV", {"prompt_busca": "quero um SUV"}),
    ("Categoria - sedan automatico", {"prompt_busca": "tem sedan automatico?"}),
    ("Categoria - picape", {"prompt_busca": "alguma caminhonete diesel?"}),
    ("Faixa preco - ate 40 mil", {"prompt_busca": "carro ate 40 mil"}),
    ("Faixa preco - entre 50 e 80 mil", {"prompt_busca": "tenho de 50 a 80 mil pra gastar"}),
    ("Faixa preco - acima 100 mil", {"prompt_busca": "algo acima de 100 mil"}),
    ("Ano minimo", {"prompt_busca": "algum carro 2018 pra cima"}),
    ("KM maximo", {"prompt_busca": "queria com pouca rodagem, ate 50 mil km"}),
    ("Cambio automatico", {"prompt_busca": "so automatico"}),
    ("Combo: SUV automatico ate 80 mil", {"prompt_busca": "SUV automatico ate 80 mil"}),
    ("Semantico - Uber", {"prompt_busca": "carro pra rodar de Uber"}),
    ("Semantico - familia", {"prompt_busca": "algo espacoso pra familia"}),
    ("Semantico - primeiro carro", {"prompt_busca": "primeiro carro, barato"}),
    ("Modelo especifico", {"prompt_busca": "tem Onix?"}),
    ("Marca especifica", {"prompt_busca": "alguma Honda?"}),
    ("Alternativa ao referencia", {"prompt_busca": "algo parecido", "reference_vehicle": "Renault Fluence", "modo": "alternatives"}),
    ("Mais barato", {"prompt_busca": "qual o mais barato", "prefer": "cheaper"}),
    ("Mais novo", {"prompt_busca": "o mais novo que tiver", "prefer": "newer"}),
]


def short(v):
    if v is None: return "-"
    s = str(v)
    return s[:60] + ("..." if len(s) > 60 else "")


def run():
    print("Carregando estoque...")
    inv = fetch_inventory_sync()
    print(f"Estoque total: {len(inv)} veiculos\n")
    print("=" * 100)

    for label, kwargs in SCENARIOS:
        print(f"\n>>> {label}")
        print(f"    Input: {kwargs}")
        try:
            raw = consultar_estoque(limite=3, **kwargs)
            data = json.loads(raw)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        q = data.get("query", {})
        planner = q.get("planner_filters") or {}
        print(f"    Planner -> tipo={planner.get('tipo_veiculo')} | faixa={planner.get('faixa_preco')} | "
              f"ano_min={planner.get('ano_minimo')} | km_max={planner.get('km_maximo')} | "
              f"cambio={planner.get('cambio')} | prefer={planner.get('prefer')} | modo={planner.get('modo')}")
        print(f"    Rationale: {short(planner.get('rationale'))}")
        print(f"    Mode={data.get('response_mode')} | count={data.get('count')} | fallback={data.get('fallback_used')}")
        for m in (data.get("matches") or [])[:3]:
            print(f"      - {m.get('titulo')} | {m.get('ano')} | {m.get('preco_formatado')} | "
                  f"{m.get('quilometragem_formatada')} | {m.get('cambio')}")
        print("-" * 100)


if __name__ == "__main__":
    run()
