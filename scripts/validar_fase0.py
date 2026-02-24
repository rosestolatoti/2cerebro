"""
Script de validacao da Fase 0 — 2 Cerebro
Testa: all-MiniLM-L6-v2, ChromaDB e Ollama API
"""

import sys
import json
import time


def testar_minilm():
    print("\n[1/3] Testando all-MiniLM-L6-v2 com sentence-transformers...")
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("models/all-MiniLM-L6-v2")
        textos = [
            "Claude Code agora suporta MCP tools",
            "RAG com LangChain e ChromaDB",
            "Como fazer fine-tuning de LLM local",
        ]
        t0 = time.time()
        embeddings = model.encode(textos, normalize_embeddings=True)
        elapsed = time.time() - t0
        assert embeddings.shape == (3, 384), f"Shape inesperado: {embeddings.shape}"
        print(f"  OK - Shape: {embeddings.shape}, tempo: {elapsed:.2f}s")
        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        return False


def testar_chromadb():
    print("\n[2/3] Testando ChromaDB (criar, upsert, query)...")
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        client = chromadb.PersistentClient(path="./chroma_data")
        collection = client.get_or_create_collection(
            name="cerebro_v2_test", metadata={"hnsw:space": "cosine"}
        )

        model = SentenceTransformer("models/all-MiniLM-L6-v2")
        textos = [
            "Claude Code agora suporta MCP tools",
            "RAG com LangChain e ChromaDB",
            "Como fazer fine-tuning de LLM local",
        ]
        embeddings = model.encode(textos, normalize_embeddings=True)

        collection.upsert(
            ids=["t1", "t2", "t3"],
            embeddings=embeddings.tolist(),
            documents=textos,
            metadatas=[{"fonte": "twitter"}, {"fonte": "github"}, {"fonte": "site"}],
        )

        query = "otimizar modelo de linguagem"
        query_emb = model.encode([query], normalize_embeddings=True)
        results = collection.query(query_embeddings=query_emb.tolist(), n_results=3)

        ids_retornados = results["ids"][0]
        print(f"  OK - Total na colecao: {collection.count()}")
        print(f"  Query: '{query}'")
        print(f"  Top resultado: '{results['documents'][0][0]}'")
        assert "t3" in ids_retornados, "fine-tuning de LLM deveria ser o mais similar"
        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        return False


def testar_ollama():
    print("\n[3/3] Testando Ollama API (classificacao simples)...")
    try:
        import httpx
        import json

        url = "http://localhost:11434/api/tags"
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        modelos = [m["name"] for m in resp.json().get("models", [])]
        print(f"  Modelos disponíveis: {modelos}")

        # Teste de geracao
        payload = {
            "model": "qwen2.5:7b",
            "prompt": 'Responda APENAS com JSON valido: {"ok": true}',
            "stream": False,
            "options": {"num_predict": 20},
        }
        t0 = time.time()
        resp = httpx.post(
            "http://localhost:11434/api/generate", json=payload, timeout=60
        )
        elapsed = time.time() - t0
        resp.raise_for_status()
        response_text = resp.json().get("response", "")
        print(f"  Resposta: {response_text.strip()}")
        print(f"  Tempo: {elapsed:.2f}s")
        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        return False


if __name__ == "__main__":
    resultados = {
        "minilm": testar_minilm(),
        "chromadb": testar_chromadb(),
        "ollama": testar_ollama(),
    }

    print("\n" + "=" * 50)
    print("RESULTADO FASE 0 — VALIDACAO")
    print("=" * 50)
    ok = True
    for nome, passou in resultados.items():
        status = "PASS" if passou else "FAIL"
        print(f"  {status} - {nome}")
        if not passou:
            ok = False

    sys.exit(0 if ok else 1)
