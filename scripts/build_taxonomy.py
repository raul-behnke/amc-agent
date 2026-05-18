"""
Build vehicle taxonomy file from current GHL inventory using LLM classification.

Usage:
    python -m scripts.build_taxonomy
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from services.ghl import fetch_inventory_sync  # noqa: E402
from tools.taxonomy import VALID_CATEGORIES, _normalize_key, invalidate_cache  # noqa: E402

OUTPUT_PATH = ROOT_DIR / "data" / "vehicle_taxonomy.json"
SYSTEM_PROMPT = (
    "Você é um classificador de carrocerias automotivas brasileiras. "
    "Para cada veículo, retorne a CATEGORIA canônica de carroceria. "
    "Categorias válidas: hatch, sedan, suv, picape, minivan, perua, esportivo, cupe, conversivel, compacto. "
    "Use 'picape' para qualquer caminhonete (não use 'pickup'). "
    "Use 'suv' para crossovers/SUVs (Renegade, Compass, Kicks, Creta, HR-V, etc). "
    "Use 'compacto' APENAS quando o modelo não couber em outra categoria mais específica (prefira 'hatch' para Mobi, Up, Kwid). "
    "Retorne JSON válido: {\"items\": [{\"marca\": \"...\", \"modelo\": \"...\", \"categoria\": \"...\", \"confidence\": 0.0-1.0, \"notes\": \"...\"}]}."
)


def _unique_models(inventory: list[dict]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for v in inventory:
        marca = str(v.get("marca", "")).strip()
        modelo = str(v.get("modelo", "")).strip()
        versao = str(v.get("versao", "")).strip()
        titulo = str(v.get("titulo", "")).strip()
        if not marca or not modelo:
            continue
        key = _normalize_key(marca, modelo)
        if key in seen:
            continue
        seen.add(key)
        out.append({"marca": marca, "modelo": modelo, "versao_exemplo": versao, "titulo_exemplo": titulo})
    return out


def _classify(models: list[dict[str, str]]) -> list[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente.")
    client = OpenAI(api_key=api_key)
    model_id = os.getenv("TAXONOMY_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    payload = {"models": models}
    logger.info("Classificando {n} modelos via {m}", n=len(models), m=model_id)
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    items = data.get("items") or []
    valid: list[dict] = []
    for item in items:
        categoria = str(item.get("categoria", "")).strip().lower()
        if categoria not in VALID_CATEGORIES:
            logger.warning("Categoria inválida descartada: {marca} {modelo} -> {cat}",
                           marca=item.get("marca"), modelo=item.get("modelo"), cat=categoria)
            continue
        valid.append(item)
    return valid


def main() -> int:
    logger.info("Buscando estoque GHL...")
    inventory = fetch_inventory_sync()
    models = _unique_models(inventory)
    if not models:
        logger.error("Nenhum modelo no estoque.")
        return 1

    classified = _classify(models)
    entries: dict[str, dict] = {}
    for item in classified:
        key = _normalize_key(str(item.get("marca", "")), str(item.get("modelo", "")))
        if not key:
            continue
        entries[key] = {
            "marca": item.get("marca"),
            "modelo": item.get("modelo"),
            "categoria": str(item.get("categoria", "")).strip().lower(),
            "confidence": float(item.get("confidence") or 0.0),
            "notes": item.get("notes"),
        }

    existing: dict = {}
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    merged = {**(existing.get("entries") or {}), **entries}

    output = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(models),
        "classified_count": len(entries),
        "entries": merged,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    invalidate_cache()
    logger.info("Taxonomy gravada em {p} | total entries={n}", p=str(OUTPUT_PATH), n=len(merged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
