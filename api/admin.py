"""
Admin endpoints — protegido por token simples (header X-Admin-Token).
"""

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from loguru import logger

from tools.taxonomy import _load_taxonomy, invalidate_cache

router = APIRouter(prefix="/admin", tags=["admin"])

ROOT_DIR = Path(__file__).resolve().parent.parent


def _check_token(token: str | None) -> None:
    expected = os.getenv("ADMIN_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/taxonomy")
async def get_taxonomy(x_admin_token: str | None = Header(default=None)):
    _check_token(x_admin_token)
    invalidate_cache()
    entries = _load_taxonomy()
    return {"count": len(entries), "entries": entries}


@router.post("/taxonomy/refresh")
async def refresh_taxonomy(x_admin_token: str | None = Header(default=None)):
    _check_token(x_admin_token)
    logger.info("Refresh taxonomy disparado via admin endpoint")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.build_taxonomy"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        timeout=180,
    )
    invalidate_cache()
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr[-2000:] or "build_taxonomy falhou")
    return {"ok": True, "stdout_tail": result.stdout[-1000:], "stderr_tail": result.stderr[-500:]}
