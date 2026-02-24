"""
2 Cerebro — Search Service
Busca textual (SQL LIKE) + semantica (ChromaDB) unificadas.
"""

from __future__ import annotations

from backend.db import repositories as repo
from backend.services.embedding_service import busca_semantica
from backend.stores.chroma_store import chroma_disponivel
from backend.utils.logger import get_logger

log = get_logger(__name__)


async def buscar(
    query: str,
    limit: int = 20,
    usar_semantica: bool = True,
) -> dict:
    """
    Busca unificada: semantica se disponivel, textual como fallback.
    Retorna dict com resultados e modo usado.
    """
    if not query.strip():
        return {"query": query, "resultados": [], "total": 0, "modo": "vazio"}

    # Tenta semantica primeiro
    if usar_semantica and chroma_disponivel():
        try:
            similares = await busca_semantica(query, limit=limit)
            if similares:
                # Enriquece com dados da foto
                resultados = []
                for numero, score in similares:
                    foto = await repo.buscar_foto(numero)
                    if foto:
                        trecho = _trecho(foto.get("ocr_limpo") or "", query)
                        resultados.append(
                            {
                                "numero": numero,
                                "filename": foto.get("filename", ""),
                                "score": round(score, 4),
                                "trecho": trecho,
                            }
                        )
                log.info(
                    "Busca semantica", extra={"query": query, "n": len(resultados)}
                )
                return {
                    "query": query,
                    "resultados": resultados,
                    "total": len(resultados),
                    "modo": "semantica",
                }
        except Exception as e:
            log.warning(
                "Busca semantica falhou, usando textual", extra={"erro": str(e)}
            )

    # Fallback textual
    fotos = await repo.busca_textual(query, limit=limit)
    resultados = [
        {
            "numero": f["numero"],
            "filename": f["filename"],
            "score": 1.0,
            "trecho": _trecho(f.get("ocr_limpo") or "", query),
        }
        for f in fotos
    ]
    log.info("Busca textual", extra={"query": query, "n": len(resultados)})
    return {
        "query": query,
        "resultados": resultados,
        "total": len(resultados),
        "modo": "textual",
    }


def _trecho(texto: str, query: str, janela: int = 150) -> str:
    """Extrai trecho de texto em volta da query."""
    if not texto:
        return ""
    idx = texto.lower().find(query.lower())
    if idx == -1:
        return texto[:janela]
    inicio = max(0, idx - 60)
    fim = min(len(texto), idx + janela)
    trecho = texto[inicio:fim]
    if inicio > 0:
        trecho = "..." + trecho
    if fim < len(texto):
        trecho = trecho + "..."
    return trecho


async def dossie(termo: str) -> dict:
    """Monta dossie de um termo: fotos, coocorrencias, timeline."""
    fotos_rows = await repo.listar_fotos(limit=10000)
    termo_lower = termo.lower()

    fotos_ids = []
    cooc_map: dict[str, int] = {}
    timeline: dict[str, int] = {}

    for f in fotos_rows:
        texto = (f.get("ocr_limpo") or "").lower()
        if termo_lower not in texto:
            continue
        fotos_ids.append(f["numero"])
        semana = f.get("semana") or "?"
        timeline[semana] = timeline.get(semana, 0) + 1

        # Coocorrencias: palavras que aparecem junto
        palavras = set(texto.split())
        for p in palavras:
            if p != termo_lower and len(p) > 2:
                cooc_map[p] = cooc_map.get(p, 0) + 1

    top_cooc = sorted(cooc_map.items(), key=lambda x: -x[1])[:20]
    timeline_list = [{"semana": k, "total": v} for k, v in sorted(timeline.items())]

    # Ancoras: fotos com mais contexto
    ancoras = fotos_ids[:5]

    return {
        "termo": termo,
        "contagem": len(fotos_ids),
        "fotos": fotos_ids,
        "coocorrencias": [{"palavra": p, "contagem": c} for p, c in top_cooc],
        "timeline": timeline_list,
        "ancoras": ancoras,
    }
