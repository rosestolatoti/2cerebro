from dotenv import load_dotenv
from langwatch import trace
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

import pytest
from embeddings import gerar_embeddings, similaridades, construir_grafo, construir_clusters


@trace(name="test_regressao_embeddings_basico")
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
