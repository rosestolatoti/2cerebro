"""Health check router."""

from fastapi import APIRouter
from backend.db import repositories as repo
from backend.stores.chroma_store import chroma_disponivel, chroma_total
from backend.services.llm_service import ollama_disponivel
from backend.config import settings

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", summary="Status geral do sistema")
async def health():
    total_fotos = await repo.contar_fotos()
    embed_total = await repo.contar_embeddings()
    modelo = settings.embedding_model_name.replace("-", "_").replace("/", "_")
    return {
        "status": "ok",
        "db": True,
        "chroma": chroma_disponivel(),
        "ollama": await ollama_disponivel(),
        "fotos_total": total_fotos,
        "embeddings_total": embed_total,
        "chroma_total": chroma_total(modelo),
        "version": "1.0.0",
    }
