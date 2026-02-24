"""
Testes basicos das rotas FastAPI.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_listar_fotos(async_client):
    response = await async_client.get("/api/fotos")
    assert response.status_code == 200
    data = response.json()
    assert "fotos" in data
    assert "total" in data
    assert isinstance(data["fotos"], list)


async def test_estatisticas_gerais(async_client):
    response = await async_client.get("/api/fotos/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_fotos" in data
    assert "top_palavras" in data
