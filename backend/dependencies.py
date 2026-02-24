"""Injecao de dependencias do FastAPI."""

from fastapi import Depends
from backend.utils.security import verificar_token

# Lista de dependencias globais que todas as rotas irao requerer
global_deps = [Depends(verificar_token)]
