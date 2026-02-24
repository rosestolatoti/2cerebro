"""
2 Cerebro — Security Utils
Token auth simples, CORS configurado, rate limiting basico.
"""

from __future__ import annotations
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import settings
from backend.utils.logger import get_logger

log = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def verificar_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """Dependency: valida token Bearer se API_TOKEN estiver configurado."""
    if not settings.api_token:
        return  # Modo dev sem auth
    if credentials is None or credentials.credentials != settings.api_token:
        log.warning(
            "Acesso negado",
            extra={"ip": request.client.host if request.client else "?"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_cors_origins() -> list[str]:
    return settings.cors_origins_list
