from dotenv import load_dotenv
import os
import re
from typing import Any

from config import CHROMA_DIR

load_dotenv()

try:
    import chromadb
except Exception:
    chromadb = None

_client = None
_collections: dict[str, Any] = {}


def _nome_colecao(modelo: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", modelo or "default").strip("_")
    return f"embeddings_{base}" if base else "embeddings_default"


def _get_client():
    global _client
    if _client is not None:
        return _client
    if chromadb is None:
        return None
    _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


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
    return collection


def chroma_disponivel() -> bool:
    return chromadb is not None


def chroma_total(modelo: str) -> int:
    collection = _get_collection(modelo)
    if collection is None:
        return 0
    return int(collection.count() or 0)


def chroma_upsert(
    modelo: str, fotos: list[dict], vetores: dict[str, list[float]]
) -> int:
    collection = _get_collection(modelo)
    if collection is None or not vetores:
        return 0
    mapa = {str(f.get("numero")): f for f in fotos}
    ids = []
    embeddings = []
    metadatas = []
    for numero, vetor in vetores.items():
        numero_str = str(numero)
        ids.append(numero_str)
        embeddings.append(vetor)
        foto = mapa.get(numero_str, {})
        metadatas.append(
            {
                "numero": numero_str,
                "filename": foto.get("filename") or "",
                "semana": foto.get("semana") or "",
                "mes": foto.get("mes") or "",
            }
        )
    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
    return len(ids)


def chroma_get_embedding(modelo: str, numero: str):
    collection = _get_collection(modelo)
    if collection is None:
        return None
    data = collection.get(ids=[str(numero)], include=["embeddings"])
    embeddings = data.get("embeddings") if data else None
    if embeddings is None:
        return None
    try:
        if len(embeddings) == 0:
            return None
    except TypeError:
        return None
    return embeddings[0]


def chroma_query_similar(
    modelo: str, query_vec: list[float], limit: int
) -> list[tuple[str, float]]:
    collection = _get_collection(modelo)
    if collection is None:
        return []
    result = collection.query(query_embeddings=[query_vec], n_results=limit)
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    saida = []
    for i, doc_id in enumerate(ids):
        dist = distances[i] if i < len(distances) else None
        score = 1 - float(dist) if dist is not None else 0.0
        saida.append((str(doc_id), score))
    return saida
