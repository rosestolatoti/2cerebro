"""
2 Cerebro — FastAPI Application (Main)
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.db.database import init_db
from backend.api.router import api_router
from backend.dependencies import global_deps
from backend.utils.logger import get_logger
from backend.services.file_service import sincronizar_pasta_fotos

log = get_logger(__name__)


# ─── Watchdog para pasta de fotos ──────────────────────────────────────────────
_watchdog_task = None


async def _watchdog_loop():
    """Substitui o polling do loop antigo. Roda a cada X segundos sync e OCR pendentes."""
    while True:
        try:
            # 1. Sync
            syncadas = await sincronizar_pasta_fotos()
            if syncadas > 0:
                log.info("Watchdog sincronizou novas fotos", extra={"n": syncadas})

            # 2. Processa 1 foto pendente por vez (para nao travar o loop)
            # (Futuro: implementaremos o processamento em background aqui)

        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Erro no watchdog loop", extra={"erro": str(e)})

        await asyncio.sleep(settings.sync_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Iniciando 2 Cerebro", extra={"env": "dev" if settings.debug else "prod"})
    await init_db()

    # Inicia watchdog
    global _watchdog_task
    _watchdog_task = asyncio.create_task(_watchdog_loop())

    yield

    # Shutdown
    log.info("Desligando 2 Cerebro...")
    if _watchdog_task:
        _watchdog_task.cancel()
        try:
            await _watchdog_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="2 Cerebro API",
    description="API do sistema de memoria visual e semantica",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=global_deps,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount statics se existirem (para quando o React buildar)
app.mount(
    "/static",
    StaticFiles(directory=str(settings.base_dir / "static"), html=True),
    name="static",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else 4,
    )
