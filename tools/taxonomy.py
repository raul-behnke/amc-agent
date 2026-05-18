"""
Vehicle Taxonomy — Mapa canônico marca|modelo → categoria de carroceria.

Fonte da verdade local (`data/vehicle_taxonomy.json`) gerada via LLM em
`scripts/build_taxonomy.py`. Consultada antes dos fallbacks por keyword/regex.
"""

import json
import threading
import unicodedata
from pathlib import Path
from typing import Any

from loguru import logger

VALID_CATEGORIES = {
    "hatch", "sedan", "suv", "picape", "pickup", "minivan",
    "perua", "esportivo", "cupe", "conversivel", "compacto",
}

_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "vehicle_taxonomy.json"
_CACHE: dict[str, str] = {}
_CACHE_MTIME: float | None = None
_LOCK = threading.Lock()


def _normalize_key(marca: str, modelo: str) -> str:
    raw = f"{marca}|{modelo}".lower().strip()
    normalized = unicodedata.normalize("NFKD", raw)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _load_taxonomy() -> dict[str, str]:
    global _CACHE, _CACHE_MTIME
    with _LOCK:
        if not _TAXONOMY_PATH.exists():
            return {}
        mtime = _TAXONOMY_PATH.stat().st_mtime
        if _CACHE_MTIME == mtime and _CACHE:
            return _CACHE
        try:
            data = json.loads(_TAXONOMY_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Falha ao carregar taxonomy | err={err}", err=str(exc))
            return _CACHE
        entries = data.get("entries", {}) if isinstance(data, dict) else {}
        normalized: dict[str, str] = {}
        for key, value in entries.items():
            categoria = (value.get("categoria") if isinstance(value, dict) else value) or ""
            categoria = str(categoria).strip().lower()
            if categoria in VALID_CATEGORIES:
                normalized[key.lower().strip()] = categoria
        _CACHE = normalized
        _CACHE_MTIME = mtime
        logger.info("Taxonomy carregada | entries={n}", n=len(normalized))
        return normalized


def get_vehicle_category(vehicle: dict[str, Any]) -> str | None:
    """Retorna a categoria canônica do veículo a partir da taxonomy local."""
    taxonomy = _load_taxonomy()
    if not taxonomy:
        return None
    key = _normalize_key(str(vehicle.get("marca", "")), str(vehicle.get("modelo", "")))
    return taxonomy.get(key)


def invalidate_cache() -> None:
    global _CACHE, _CACHE_MTIME
    with _LOCK:
        _CACHE = {}
        _CACHE_MTIME = None
