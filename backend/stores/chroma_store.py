"""
2 Cerebro — ChromaDB Store (wrapper limpo)
Singleton lazy-loaded, cosine similarity, metadados ricos.
"""

from __future__ import annotations
import re
from typing import Optional

from backend.config import settings
from backend.utils.logger import get_logger

log = get_logger(__name__)

try:
    import chromadb

    _CHROMA_OK = True
except ImportError:
    chromadb = None  # type: ignore
    _CHROMA_OK = False

_client: Optional[object] = None
_collections: dict[str, object] = {}


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _CHROMA_OK:
        return None
    _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    log.info("ChromaDB client iniciado", extra={"path": str(settings.chroma_dir)})
    return _client


def _nome_colecao(modelo: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", modelo or "default").strip("_")
    return f"embeddings_{base}" if base else "embeddings_default"


def _get_collection(modelo: str):
    if modelo in _collections:
        return _collections[modelo]
    client = _get_client()
    if client is None:
        return None
    name = _nome_colecao(modelo)
    collection = client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"}
    )
    _collections[modelo] = collection
    log.info("ChromaDB collection pronta", extra={"collection": name})
    return collection


# ─── API publica ──────────────────────────────────────────────────────────────


def chroma_disponivel() -> bool:
    return _CHROMA_OK


def chroma_total(modelo: str) -> int:
    col = _get_collection(modelo)
    if col is None:
        return 0
    return int(col.count() or 0)


def chroma_upsert(
    modelo: str,
    fotos: list[dict],
    vetores: dict[str, list[float]],
) -> int:
    col = _get_collection(modelo)
    if col is None or not vetores:
        return 0
    mapa = {str(f.get("numero")): f for f in fotos}
    ids, embeddings, metadatas = [], [], []
    for numero, vetor in vetores.items():
        ids.append(str(numero))
        embeddings.append(vetor)
        foto = mapa.get(str(numero), {})
        metadatas.append(
            {
                "numero": str(numero),
                "filename": foto.get("filename") or "",
                "semana": foto.get("semana") or "",
                "mes": foto.get("mes") or "",
                "fonte": foto.get("fonte") or "",
                "tema": foto.get("tema") or "",
                "sentimento": foto.get("sentimento") or "",
            }
        )
    col.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
    log.info("ChromaDB upsert", extra={"modelo": modelo, "n": len(ids)})
    return len(ids)


def chroma_upsert_texto(
    modelo: str,
    numero: str,
    vetor: list[float],
    metadata: Optional[dict] = None,
) -> None:
    """Upsert de embedding individual com metadados opcionais."""
    col = _get_collection(modelo)
    if col is None:
        return
    meta = metadata or {}
    meta["numero"] = str(numero)
    col.upsert(ids=[str(numero)], embeddings=[vetor], metadatas=[meta])


def chroma_get_embedding(modelo: str, numero: str) -> Optional[list[float]]:
    col = _get_collection(modelo)
    if col is None:
        return None
    data = col.get(ids=[str(numero)], include=["embeddings"])
    embeddings = data.get("embeddings") if data else None
    if not embeddings:
        return None
    try:
        return list(embeddings[0]) if len(embeddings) > 0 else None
    except (TypeError, IndexError):
        return None


def chroma_query_similar(
    modelo: str,
    query_vec: list[float],
    limit: int = 10,
    where: Optional[dict] = None,
) -> list[tuple[str, float]]:
    col = _get_collection(modelo)
    if col is None:
        return []
    kwargs: dict = dict(query_embeddings=[query_vec], n_results=limit)
    if where:
        kwargs["where"] = where
    result = col.query(**kwargs)
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [(str(doc_id), 1.0 - float(dist)) for doc_id, dist in zip(ids, distances)]


def chroma_delete(modelo: str, numeros: list[str]) -> None:
    col = _get_collection(modelo)
    if col is None or not numeros:
        return
    col.delete(ids=[str(n) for n in numeros])
