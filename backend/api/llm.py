"""Rotas de interacao direta com LLM."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.llm_service import analisar_texto
from backend.db import repositories as repo

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LlmRequest(BaseModel):
    numero: str
    prompt_extra: str = ""


@router.post("/analisar", summary="Analisa o texto de uma foto com LLM")
async def analisar_foto(req: LlmRequest):
    foto = await repo.buscar_foto(req.numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")

    texto = foto.get("ocr_limpo")
    if not texto:
        raise HTTPException(status_code=422, detail="Foto sem OCR")

    resposta, provider = await analisar_texto(texto, req.prompt_extra)
    return {
        "sucesso": bool(resposta),
        "numero": req.numero,
        "resposta": resposta,
        "provider": provider,
    }
