"""Rotas de fotos: listagem, detalhes, upload, delete, imagem."""

from __future__ import annotations
import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from backend.db import repositories as repo
from backend.services.file_service import (
    salvar_upload,
    sincronizar_pasta_fotos,
)

router = APIRouter(prefix="/api/fotos", tags=["fotos"])


@router.get("", summary="Lista todas as fotos")
async def listar(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    fotos = await repo.listar_fotos(limit=limit, offset=offset)
    total = await repo.contar_fotos()
    return {"fotos": fotos, "total": total}


@router.get("/stats", summary="Estatisticas gerais")
async def stats():
    total = await repo.contar_fotos()
    com_ocr = await repo.contar_fotos_com_ocr()
    top_pal = await repo.top_palavras(20)
    top_usr = await repo.top_usuarios(10)
    top_rep = await repo.top_repos(10)
    por_semana = await repo.fotos_por_semana()
    por_mes = await repo.fotos_por_mes()
    return {
        "total_fotos": total,
        "fotos_com_ocr": com_ocr,
        "top_palavras": top_pal,
        "top_usuarios": top_usr,
        "top_repos": top_rep,
        "por_semana": por_semana,
        "por_mes": por_mes,
    }


@router.get("/{numero}", summary="Detalhes de uma foto")
async def detalhe(numero: str):
    foto = await repo.buscar_foto(numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")
    return foto


@router.get("/{numero}/imagem", summary="Serve o arquivo de imagem")
async def imagem(numero: str):
    foto = await repo.buscar_foto(numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")
    path = Path(foto["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado no disco")
    media_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return FileResponse(str(path), media_type=media_type)


@router.post("/upload", summary="Upload de imagem(ns)")
async def upload(files: list[UploadFile] = File(...)):
    resultados = []
    for file in files:
        content = await file.read()
        resultado = await salvar_upload(content, file.filename or "upload.jpg")
        resultados.append(resultado)
    return {"resultados": resultados, "total": len(resultados)}


@router.post("/sincronizar", summary="Sincroniza pasta fotos/ com o banco")
async def sincronizar():
    n = await sincronizar_pasta_fotos()
    return {"sincronizadas": n}


@router.delete("/{numero}", summary="Deleta foto do banco e disco")
async def deletar(numero: str):
    foto = await repo.buscar_foto(numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")
    from backend.stores.chroma_store import chroma_delete
    from backend.config import settings

    modelo = settings.embedding_model_name.replace("-", "_").replace("/", "_")
    chroma_delete(modelo, [numero])
    path = Path(foto["filepath"])
    if path.exists():
        path.unlink()
    await repo.deletar_foto(numero)
    return {"ok": True, "numero": numero}
