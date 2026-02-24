"""Monta todos os routers da API."""

from fastapi import APIRouter

from backend.api.fotos import router as fotos_router
from backend.api.ocr import router as ocr_router
from backend.api.busca import router as busca_router
from backend.api.embeddings import router as embeddings_router
from backend.api.insights import router as insights_router
from backend.api.llm import router as llm_router
from backend.api.health import router as health_router

api_router = APIRouter()

api_router.include_router(fotos_router)
api_router.include_router(ocr_router)
api_router.include_router(busca_router)
api_router.include_router(embeddings_router)
api_router.include_router(insights_router)
api_router.include_router(llm_router)
api_router.include_router(health_router)
