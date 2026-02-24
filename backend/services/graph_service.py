"""
2 Cerebro — Graph Service
Grafo de conhecimento + clusters por similaridade.
"""

from __future__ import annotations
import json

from backend.db import repositories as repo
from backend.utils.logger import get_logger

log = get_logger(__name__)


async def construir_grafo_palavras(limit: int = 80) -> dict:
    """
    Grafo de palavras co-ocorrentes.
    Nodes = palavras top, links = co-ocorrencia em fotos.
    """
    palavras = await repo.top_palavras(limit)
    grupos = await repo.listar_grupos()

    # Mapa palavra -> cor/grupo
    cor_map: dict[str, str] = {}
    grupo_map: dict[str, str] = {}
    for g in grupos:
        gps = json.loads(g["palavras"] or "[]")
        for gp in gps:
            cor_map[gp] = g.get("cor", "#6b7280")
            grupo_map[gp] = g["nome"]

    nodes = []
    for p in palavras:
        palavra = p["palavra"]
        nodes.append(
            {
                "id": palavra,
                "label": palavra,
                "contagem": p["contagem"],
                "grupo": grupo_map.get(palavra),
                "cor": cor_map.get(palavra, "#6b7280"),
            }
        )

    # Links: palavras que aparecem na mesma foto
    palavra_set = {p["palavra"] for p in palavras}
    fotos = await repo.listar_fotos(limit=2000)

    cooc: dict[tuple, int] = {}
    for foto in fotos:
        texto = (foto.get("ocr_limpo") or "").lower().split()
        presentes = [t for t in set(texto) if t in palavra_set]
        for i in range(len(presentes)):
            for j in range(i + 1, len(presentes)):
                key = tuple(sorted([presentes[i], presentes[j]]))
                cooc[key] = cooc.get(key, 0) + 1

    # Top 150 links mais fortes
    links_sorted = sorted(cooc.items(), key=lambda x: -x[1])[:150]
    links = [
        {"source": a, "target": b, "weight": float(c)} for (a, b), c in links_sorted
    ]

    log.info("Grafo construido", extra={"nodes": len(nodes), "links": len(links)})
    return {"nodes": nodes, "links": links}


async def construir_clusters_embeddings() -> dict:
    """
    Clusters simples baseados em embeddings do SQLite.
    Usa K-means se sklearn disponivel, senao agrupa por decil de similaridade.
    """
    from backend.config import settings

    modelo = settings.embedding_model_name.replace("-", "_").replace("/", "_")
    rows = await repo.listar_embeddings(modelo)
    if not rows:
        return {"clusters": {}, "total_clusters": 0}

    try:
        import numpy as np
        from sklearn.cluster import KMeans

        numeros = [r["numero"] for r in rows]
        vetores = np.array([json.loads(r["vetor"]) for r in rows])
        n_clusters = min(8, max(2, len(numeros) // 5))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(vetores)
        clusters: dict[int, list[str]] = {}
        for i, lbl in enumerate(labels.tolist()):
            clusters.setdefault(lbl, []).append(numeros[i])
        return {"clusters": clusters, "total_clusters": len(clusters)}
    except ImportError:
        # Sem sklearn: agrupa por semana como fallback
        fotos = await repo.listar_fotos(limit=5000)
        clusters_sem: dict[str, list[str]] = {}
        for f in fotos:
            semana = f.get("semana") or "sem-data"
            clusters_sem.setdefault(semana, []).append(f["numero"])
        return {
            "clusters": {i: v for i, v in enumerate(clusters_sem.values())},
            "total_clusters": len(clusters_sem),
        }
    except Exception as e:
        log.error("Erro ao construir clusters", extra={"erro": str(e)})
        return {"clusters": {}, "total_clusters": 0}


async def timeline_semanas() -> list[dict]:
    return await repo.fotos_por_semana()


async def timeline_meses() -> list[dict]:
    return await repo.fotos_por_mes()
