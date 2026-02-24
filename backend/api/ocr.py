"""Rotas de OCR: extrair, re-extrair, comparar."""

from fastapi import APIRouter, HTTPException

from backend.db import repositories as repo
from backend.services.ocr_service import (
    processar_imagem,
    extrair_usernames,
    extrair_repos_github,
)
from backend.services.embedding_service import gerar_e_salvar_embedding

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/{numero}", summary="Executa OCR em uma foto")
async def extrair_ocr(numero: str):
    foto = await repo.buscar_foto(numero)
    if not foto:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")

    resultado = await processar_imagem(foto["filepath"], numero, foto["filename"])
    if not resultado["sucesso"]:
        raise HTTPException(
            status_code=500, detail=resultado.get("erro", "Erro no OCR")
        )

    texto_limpo = resultado["texto_limpo"]
    await repo.atualizar_ocr(numero, resultado["texto_bruto"], texto_limpo)

    # Extrai entidades e atualiza tabelas auxiliares
    users = extrair_usernames(texto_limpo)
    repos_gh = extrair_repos_github(texto_limpo)
    await repo.atualizar_palavras(numero, resultado["palavras"])
    if users:
        await repo.atualizar_usuarios(numero, users)
    if repos_gh:
        await repo.atualizar_repos(numero, repos_gh)

    # Gera embedding automaticamente
    await gerar_e_salvar_embedding(numero, texto_limpo, {"filename": foto["filename"]})

    return {
        "sucesso": True,
        "numero": numero,
        "texto_bruto": resultado["texto_bruto"],
        "texto_limpo": texto_limpo,
        "palavras": resultado["palavras"],
        "usuarios": users,
        "repos": repos_gh,
        "caracteres": resultado["caracteres"],
    }


@router.post("/batch/all", summary="Executa OCR em todas as fotos pendentes")
async def ocr_batch():
    fotos = await repo.listar_fotos(limit=5000)
    pendentes = [f for f in fotos if not f.get("ocr_limpo")]
    resultados = {"ok": 0, "erro": 0, "pulados": len(fotos) - len(pendentes)}
    for foto in pendentes:
        try:
            resultado = await processar_imagem(
                foto["filepath"], foto["numero"], foto["filename"]
            )
            if resultado["sucesso"]:
                texto_limpo = resultado["texto_limpo"]
                await repo.atualizar_ocr(
                    foto["numero"], resultado["texto_bruto"], texto_limpo
                )
                users = extrair_usernames(texto_limpo)
                repos_gh = extrair_repos_github(texto_limpo)
                await repo.atualizar_palavras(foto["numero"], resultado["palavras"])
                if users:
                    await repo.atualizar_usuarios(foto["numero"], users)
                if repos_gh:
                    await repo.atualizar_repos(foto["numero"], repos_gh)
                await gerar_e_salvar_embedding(foto["numero"], texto_limpo)
                resultados["ok"] += 1
            else:
                resultados["erro"] += 1
        except Exception:
            resultados["erro"] += 1
    return resultados
