from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.real_scenario_harness import (  # noqa: E402
    parse_real_scenarios,
    run_many_real_scenarios,
    write_reports,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa simulações conversacionais com cenários reais da AMC."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limita a quantidade de cenários."
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=None,
        help="Executa apenas IDs específicos, ex: real-001.",
    )
    parser.add_argument(
        "--simulator",
        choices=["auto", "llm", "rule"],
        default="auto",
        help="Modo do Lead Simulator.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=6,
        help="Máximo de turnos lead->Lucas por cenário.",
    )
    parser.add_argument(
        "--slug", default="reais", help="Sufixo para os arquivos em tests/results."
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=5,
        help="Quantidade máxima de cenários rodando em paralelo.",
    )
    return parser


async def main() -> int:
    args = _build_parser().parse_args()
    scenarios = parse_real_scenarios()

    if args.scenario_id:
        allowed = set(args.scenario_id)
        scenarios = [
            scenario for scenario in scenarios if scenario.scenario_id in allowed
        ]
    if args.limit is not None:
        scenarios = scenarios[: args.limit]
    if not scenarios:
        print("Nenhum cenário selecionado.")
        return 1

    results = await run_many_real_scenarios(
        scenarios=scenarios,
        max_turns=args.max_turns,
        simulator_mode=args.simulator,
        incremental_slug=args.slug,
        session_namespace=args.slug,
        max_parallel=args.max_parallel,
    )
    md_path, json_path = write_reports(results, slug=args.slug)
    approved = sum(
        1 for result in results if result.evaluation["status"] == "✅ Aprovado"
    )

    print(f"Cenários executados: {len(results)}")
    print(f"Aprovados: {approved}")
    print(f"Markdown: {md_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
