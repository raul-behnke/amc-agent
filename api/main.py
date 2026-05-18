"""
ZOI Agent Framework — API Principal.

Ponto de entrada do FastAPI.
Registra routers e configura o ciclo de vida da aplicação.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger
from fastapi.staticfiles import StaticFiles
from services.logging import configure_logging

# Garantir que a raiz do projeto esteja no path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Carregar variáveis de ambiente
load_dotenv(ROOT_DIR / ".env")

# Configuração do logger
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ZAF Runtime Iniciado.")
    yield
    logger.info("ZAF Runtime Finalizado.")


app = FastAPI(
    title="ZOI Agent Framework",
    description="API do Runtime do Lucas SDR Agent — AMC Veículos",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Registrar Routers
# ---------------------------------------------------------------------------
from api.webhooks.chat import router as chat_router  # noqa: E402
from api.webhooks.leads import router as leads_router  # noqa: E402
from api.scenario_tests import router as scenario_tests_router  # noqa: E402
from api.admin import router as admin_router  # noqa: E402

app.include_router(chat_router)
app.include_router(leads_router)
app.include_router(scenario_tests_router)
app.include_router(admin_router)
app.mount("/artifacts", StaticFiles(directory=ROOT_DIR / "tests" / "results"), name="artifacts")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health")
async def healthcheck():
    return {"status": "ok", "framework": "ZOI Agent Framework", "version": "0.1.0"}
