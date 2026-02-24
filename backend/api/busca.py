"""Rotas de busca: textual e semantica unificadas."""

from fastapi import APIRouter, Query

from backend.services.search_service import buscar, dossie

router = APIRouter(prefix="/api/busca", tags=["busca"])


@router.get("", summary="Busca unificada (semantica + textual)")
async def busca(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    semantica: bool = Query(default=True),
):
    return await buscar(q, limit=limit, usar_semantica=semantica)


@router.get("/dossie/{termo}", summary="Dossie completo de um termo")
async def get_dossie(termo: str):
    return await dossie(termo)
