import math
import re
from config import STOPWORDS, EMBEDDING_DIM, EMBEDDING_THRESHOLD, EMBEDDING_MAX_LINKS, SEMANTIC_MODEL_NAME, MODELS_DIR

try:
    import numpy as np
except Exception:
    np = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

_semantic_model = None


def _get_semantic_model():
    global _semantic_model
    if _semantic_model is not None:
        return _semantic_model
    if SentenceTransformer is None:
        return None
    local_dir = MODELS_DIR / "all-MiniLM-L6-v2"
    if local_dir.exists():
        _semantic_model = SentenceTransformer(str(local_dir))
    else:
        _semantic_model = SentenceTransformer(SEMANTIC_MODEL_NAME, cache_folder=str(MODELS_DIR))
    return _semantic_model


def _tokenizar(texto: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-ZÀ-ÿ]{2,}\b", texto.lower())
    return [t for t in tokens if t not in STOPWORDS]


def _tfidf_matrix(textos: list[str]):
    docs_tokens = [_tokenizar(t) for t in textos]
    vocab = {}
    for tokens in docs_tokens:
        for t in tokens:
            if t not in vocab:
                vocab[t] = len(vocab)

    n_docs = len(docs_tokens)
    df = [0] * len(vocab)
    for tokens in docs_tokens:
        vistos = set(tokens)
        for t in vistos:
            df[vocab[t]] += 1

    idf = [math.log((1 + n_docs) / (1 + df_i)) + 1 for df_i in df]
    matriz = []
    for tokens in docs_tokens:
        total = len(tokens) or 1
        contagem = {}
        for t in tokens:
            contagem[t] = contagem.get(t, 0) + 1
        linha = [0.0] * len(vocab)
        for t, c in contagem.items():
            idx = vocab[t]
            tf = c / total
            linha[idx] = tf * idf[idx]
        matriz.append(linha)
    return vocab, idf, docs_tokens, matriz


def gerar_embeddings(fotos: list[dict], modelo: str = "auto"):
    if np is None:
        return {"sucesso": False, "erro": "numpy não instalado"}

    textos = [f.get("ocr_limpo", "") or "" for f in fotos]
    tokens = [_tokenizar(t) for t in textos]
    modelo = (modelo or "auto").lower()

    if modelo in {"semantic", "auto"}:
        model = _get_semantic_model()
        if model is not None:
            emb = model.encode(textos, normalize_embeddings=True)
            emb = np.array(emb, dtype=float)
            vetores = {fotos[i]["numero"]: emb[i].tolist() for i in range(len(fotos))}
            return {
                "sucesso": True,
                "vetores": vetores,
                "tokens": tokens,
                "vocab": {},
                "idf": [],
                "dimensao": emb.shape[1],
                "modelo": "semantic_v1"
            }

    vocab, idf, docs_tokens, matriz = _tfidf_matrix(textos)
    if not matriz:
        return {"sucesso": False, "erro": "sem textos para vetorização"}

    tfidf = np.array(matriz, dtype=float)
    if tfidf.shape[0] < 2 or tfidf.shape[1] < 2:
        return {"sucesso": False, "erro": "dados insuficientes para SVD"}

    u, s, vt = np.linalg.svd(tfidf, full_matrices=False)
    k = min(EMBEDDING_DIM, s.shape[0])
    doc_vecs = u[:, :k] * s[:k]
    norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
    doc_vecs = doc_vecs / np.where(norms == 0, 1, norms)

    vetores = {fotos[i]["numero"]: doc_vecs[i].tolist() for i in range(len(fotos))}
    return {
        "sucesso": True,
        "vetores": vetores,
        "tokens": docs_tokens,
        "vocab": vocab,
        "idf": idf,
        "dimensao": k,
        "modelo": "tfidf_svd_v1"
    }


def gerar_embedding_query(texto: str, modelo: str):
    if np is None:
        return None
    modelo = (modelo or "").lower()
    if modelo.startswith("semantic"):
        model = _get_semantic_model()
        if model is None:
            return None
        emb = model.encode([texto], normalize_embeddings=True)
        return np.array(emb[0], dtype=float)
    return None


def similaridades(vetores: dict, alvo: str):
    if np is None:
        return []
    if alvo not in vetores:
        return []
    numeros = list(vetores.keys())
    matriz = np.array([vetores[n] for n in numeros], dtype=float)
    alvo_vec = vetores[alvo]
    sims = matriz @ np.array(alvo_vec, dtype=float)
    resultado = []
    for i, n in enumerate(numeros):
        if n == alvo:
            continue
        resultado.append((n, float(sims[i])))
    resultado.sort(key=lambda x: x[1], reverse=True)
    return resultado


def similaridades_query(vetores: dict, query_vec):
    if np is None or query_vec is None:
        return []
    numeros = list(vetores.keys())
    if not numeros:
        return []
    matriz = np.array([vetores[n] for n in numeros], dtype=float)
    sims = matriz @ np.array(query_vec, dtype=float)
    resultado = []
    for i, n in enumerate(numeros):
        resultado.append((n, float(sims[i])))
    resultado.sort(key=lambda x: x[1], reverse=True)
    return resultado


def construir_grafo(vetores: dict):
    if np is None:
        return {"nodes": [], "links": []}
    numeros = list(vetores.keys())
    matriz = np.array([vetores[n] for n in numeros], dtype=float)
    sims = matriz @ matriz.T
    nodes = [{"id": n} for n in numeros]
    links = []
    for i, n in enumerate(numeros):
        pares = [(numeros[j], float(sims[i][j])) for j in range(len(numeros)) if j != i]
        pares = [p for p in pares if p[1] >= EMBEDDING_THRESHOLD]
        pares.sort(key=lambda x: x[1], reverse=True)
        for alvo, score in pares[:EMBEDDING_MAX_LINKS]:
            if n < alvo:
                links.append({"source": n, "target": alvo, "value": score})
    return {"nodes": nodes, "links": links}


def construir_clusters(vetores: dict):
    if np is None:
        return {}
    numeros = list(vetores.keys())
    if not numeros:
        return {}
    matriz = np.array([vetores[n] for n in numeros], dtype=float)
    sims = matriz @ matriz.T
    visitado = set()
    cluster_map = {}
    cluster_id = 0
    for i, n in enumerate(numeros):
        if n in visitado:
            continue
        fila = [i]
        visitado.add(n)
        cluster_map[n] = cluster_id
        while fila:
            idx = fila.pop()
            for j, m in enumerate(numeros):
                if m in visitado:
                    continue
                if sims[idx][j] >= EMBEDDING_THRESHOLD:
                    visitado.add(m)
                    cluster_map[m] = cluster_id
                    fila.append(j)
        cluster_id += 1
    return cluster_map


def termos_por_cluster(fotos: list[dict], tokens: list[list[str]], cluster_map: dict, top_n: int = 6):
    contagens = {}
    for i, f in enumerate(fotos):
        numero = f["numero"]
        cid = cluster_map.get(numero, -1)
        if cid not in contagens:
            contagens[cid] = {}
        for t in tokens[i]:
            contagens[cid][t] = contagens[cid].get(t, 0) + 1
    resultado = {}
    for cid, mapa in contagens.items():
        ordenado = sorted(mapa.items(), key=lambda x: x[1], reverse=True)[:top_n]
        resultado[cid] = [t for t, _ in ordenado]
    return resultado
