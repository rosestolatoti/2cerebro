"""Rotas de embeddings: rebuild, similares."""

from fastapi import APIRouter, HTTPException, Query

from backend.db import repositories as repo
from backend.services.embedding_service import (
    rebuild_embeddings_batch,
    similares,
    total_embeddings,
)

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


@router.post("/rebuild", summary="Regenera todos os embeddings")
async def rebuild():
    fotos = await repo.listar_fotos(limit=5000)
    return await rebuild_embeddings_batch(fotos)


@router.post("/rebuild/{numero}", summary="Regenera embedding de uma foto")
async def rebuild_um(numero: str):
    foto = await repo.buscar_foto(numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")
    if not foto.get("ocr_limpo"):
        raise HTTPException(
            status_code=422, detail="Foto sem OCR, execute OCR primeiro"
        )
    return await rebuild_embeddings_batch([foto])


@router.get("/similares/{numero}", summary="Fotos similares a uma foto")
async def get_similares(numero: str, limit: int = Query(default=5, ge=1, le=20)):
    resultado = await similares(numero, limit=limit)
    return {
        "numero": numero,
        "similares": [{"numero": n, "score": s} for n, s in resultado],
    }


@router.get("/total", summary="Total de embeddings no ChromaDB")
async def get_total():
    return {"total": total_embeddings(), "total_sqlite": await repo.contar_embeddings()}
