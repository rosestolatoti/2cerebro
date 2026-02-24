from dotenv import load_dotenv
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

import pytest
from embeddings import (
    gerar_embeddings,
    similaridades,
    construir_grafo,
    construir_clusters,
    similaridades_query,
)


def test_regressao_embeddings_basico() -> None:
    """
    Garante que embeddings, similares, grafo e clusters geram saída consistente.
    """
    pytest.importorskip("numpy")
    fotos = [
        {"numero": "001", "ocr_limpo": "agente mcp toolchain"},
        {"numero": "002", "ocr_limpo": "mcp agents workflow"},
        {"numero": "003", "ocr_limpo": "receita de bolo caseiro"},
    ]
    resultado = gerar_embeddings(fotos)
    assert resultado["sucesso"] is True
    vetores = resultado["vetores"]
    sims = similaridades(vetores, "001")
    assert len(sims) == 2
    grafo = construir_grafo(vetores)
    assert "nodes" in grafo and "links" in grafo
    clusters = construir_clusters(vetores)
    assert set(clusters.keys()) == {"001", "002", "003"}


def test_embeddings_tfidf_modelo() -> None:
    """
    Garante que o modo tf-idf expõe metadados de modelo.
    """
    pytest.importorskip("numpy")
    fotos = [
        {"numero": "010", "ocr_limpo": "python flask sqlite"},
        {"numero": "011", "ocr_limpo": "react typescript web"},
    ]
    resultado = gerar_embeddings(fotos, modelo="tfidf")
    assert resultado["sucesso"] is True
    assert resultado["modelo"] == "tfidf_svd_v1"


def test_similaridades_query_basico() -> None:
    """
    Garante ranking por similaridade de query.
    """
    pytest.importorskip("numpy")
    vetores = {
        "001": [1.0, 0.0],
        "002": [0.0, 1.0],
    }
    resultado = similaridades_query(vetores, [1.0, 0.2])
    assert resultado[0][0] == "001"
