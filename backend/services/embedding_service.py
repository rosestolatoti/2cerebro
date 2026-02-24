"""
2 Cerebro — Embedding Service
all-MiniLM-L6-v2 (local) + ChromaDB. Batch de 32 para nao explodir RAM.
"""

from __future__ import annotations
import asyncio
import json
from functools import partial
from typing import Optional

from backend.config import settings
from backend.stores.chroma_store import (
    chroma_upsert,
    chroma_query_similar,
    chroma_get_embedding,
    chroma_total,
)
from backend.db import repositories as repo
from backend.utils.logger import get_logger

log = get_logger(__name__)

_model = None
_MODEL_NAME = str(settings.embedding_model_path)
_MODELO_ID = settings.embedding_model_name.replace("-", "_").replace("/", "_")


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
        log.info("Modelo de embeddings carregado", extra={"modelo": _MODEL_NAME})
    except Exception as e:
        log.error("Falha ao carregar modelo de embeddings", extra={"erro": str(e)})
        _model = None
    return _model


def _encode_batch(textos: list[str]) -> list[list[float]]:
    model = _get_model()
    if model is None:
        return []
    vecs = model.encode(
        textos,
        normalize_embeddings=True,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vecs]


# ─── API publica async ────────────────────────────────────────────────────────


async def gerar_e_salvar_embedding(
    numero: str, texto: str, metadata: Optional[dict] = None
) -> bool:
    """Gera embedding para uma foto e salva no ChromaDB + SQLite."""
    if not texto or not texto.strip():
        return False
    loop = asyncio.get_event_loop()
    vecs = await loop.run_in_executor(None, partial(_encode_batch, [texto]))
    if not vecs:
        return False
    vetor = vecs[0]

    # Salva no ChromaDB
    from backend.stores.chroma_store import chroma_upsert_texto

    chroma_upsert_texto(_MODELO_ID, numero, vetor, metadata)

    # Backup no SQLite
    await repo.salvar_embedding(numero, _MODELO_ID, vetor, len(vetor))
    log.info("Embedding salvo", extra={"numero": numero, "dim": len(vetor)})
    return True


async def rebuild_embeddings_batch(fotos: list[dict]) -> dict:
    """Gera embeddings para lista de fotos em batch."""
    pendentes = [f for f in fotos if f.get("ocr_limpo")]
    if not pendentes:
        return {"sucesso": True, "processados": 0, "modelo": _MODELO_ID}

    textos = [f["ocr_limpo"] for f in pendentes]
    numeros = [f["numero"] for f in pendentes]

    loop = asyncio.get_event_loop()
    # Processa em batches de 32
    batch = settings.embedding_batch_size
    todos_vetores: list[list[float]] = []
    for i in range(0, len(textos), batch):
        vecs = await loop.run_in_executor(
            None, partial(_encode_batch, textos[i : i + batch])
        )
        todos_vetores.extend(vecs)

    if not todos_vetores:
        return {
            "sucesso": False,
            "processados": 0,
            "modelo": _MODELO_ID,
            "erro": "Modelo indisponivel",
        }

    # Upsert no ChromaDB em batch
    vetores_map = {numeros[i]: todos_vetores[i] for i in range(len(numeros))}
    chroma_upsert(_MODELO_ID, pendentes, vetores_map)

    # Backup SQLite
    for numero, vetor in vetores_map.items():
        await repo.salvar_embedding(numero, _MODELO_ID, vetor, len(vetor))

    log.info("Batch embeddings concluido", extra={"n": len(vetores_map)})
    return {"sucesso": True, "processados": len(vetores_map), "modelo": _MODELO_ID}


async def busca_semantica(query: str, limit: int = 20) -> list[tuple[str, float]]:
    """Retorna lista de (numero, score) ordenada por similaridade."""
    loop = asyncio.get_event_loop()
    vecs = await loop.run_in_executor(None, partial(_encode_batch, [query]))
    if not vecs:
        return []
    return chroma_query_similar(_MODELO_ID, vecs[0], limit)


async def similares(numero: str, limit: int = 5) -> list[tuple[str, float]]:
    """Retorna fotos similares a uma foto especifica."""
    vetor = chroma_get_embedding(_MODELO_ID, numero)
    if vetor is None:
        # Tenta recuperar do SQLite
        rows = await repo.listar_embeddings(_MODELO_ID)
        for r in rows:
            if r["numero"] == numero:
                vetor = json.loads(r["vetor"])
                break
    if vetor is None:
        return []
    resultados = chroma_query_similar(_MODELO_ID, vetor, limit + 1)
    return [(n, s) for n, s in resultados if n != numero][:limit]


def total_embeddings() -> int:
    return chroma_total(_MODELO_ID)
