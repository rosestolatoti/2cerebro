"""
Configuracao base para os testes (pytest)
"""

import asyncio
import os
from pathlib import Path
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

# Forca uso de um banco de dados em memoria ou de teste antes de importar configs
import tempfile

_temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_temp_db.close()
os.environ["DB_PATH"] = _temp_db.name
os.environ["API_TOKEN"] = ""
os.environ["CHROMA_DIR"] = "./chroma_data_test"

from backend.main import app
from backend.db.database import init_db

# Evita q o watcher fique rodando nos testes
import backend.main

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
backend.main._watchdog_task = loop.create_future()
backend.main._watchdog_task.set_result(None)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    await init_db()
    yield


@pytest_asyncio.fixture
async def async_client(setup_db):
    """Cliente HTTP asincrono para testes de API"""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
