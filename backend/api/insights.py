"""Rotas de insights: grafo, clusters, timeline."""

from fastapi import APIRouter

from backend.services.graph_service import (
    construir_grafo_palavras,
    construir_clusters_embeddings,
    timeline_semanas,
    timeline_meses,
)
from backend.db import repositories as repo

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/grafo", summary="Grafo de co-ocorrencia de palavras")
async def grafo(limit: int = 80):
    return await construir_grafo_palavras(limit=limit)


@router.get("/clusters", summary="Clusters de fotos por embeddings")
async def clusters():
    return await construir_clusters_embeddings()


@router.get("/timeline", summary="Timeline por semana e mes")
async def timeline():
    return {
        "por_semana": await timeline_semanas(),
        "por_mes": await timeline_meses(),
    }


@router.get("/top-palavras", summary="Top palavras mais frequentes")
async def top_palavras(limit: int = 100):
    return await repo.top_palavras(limit)


@router.get("/top-usuarios", summary="Top @usuarios mencionados")
async def top_usuarios(limit: int = 20):
    return await repo.top_usuarios(limit)


@router.get("/top-repos", summary="Top repos GitHub")
async def top_repos(limit: int = 20):
    return await repo.top_repos(limit)


@router.get("/grupos", summary="Grupos semanticos configurados")
async def grupos():
    return await repo.listar_grupos()
