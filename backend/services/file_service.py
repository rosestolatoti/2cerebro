"""
2 Cerebro — File Service
Gerencia uploads, sincronizacao de pasta, deduplicacao por MD5, renomeacao.
"""

from __future__ import annotations
import hashlib
from datetime import datetime
from pathlib import Path
from threading import Lock
import re
from typing import Optional

from backend.config import settings
from backend.db import repositories as repo
from backend.utils.logger import get_logger

log = get_logger(__name__)

_lock = Lock()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _sanitizar_nome(nome: str) -> str:
    nome = Path(nome).name
    nome = re.sub(r"[^a-zA-Z0-9._-]+", "_", nome).strip("._-")
    return nome or "arquivo"


def _detectar_formato(file_bytes: bytes) -> Optional[str]:
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if (
        len(file_bytes) >= 12
        and file_bytes[:4] == b"RIFF"
        and file_bytes[8:12] == b"WEBP"
    ):
        return ".webp"
    if file_bytes.startswith(b"BM"):
        return ".bmp"
    return None


def _extrair_data(nome: str, fallback_dt: datetime) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})[^\d]?(\d{2})[-_](\d{2})[-_](\d{2})", nome)
    if m:
        return f"{m.group(1)}_{m.group(2)}-{m.group(3)}-{m.group(4)}"
    m = re.search(r"(\d{8})[-_](\d{2})(\d{2})(\d{2})", nome)
    if m:
        d = datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
        return f"{d}_{m.group(2)}-{m.group(3)}-{m.group(4)}"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nome)
    if m:
        return m.group(1)
    m = re.search(r"(\d{8})", nome)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
    return fallback_dt.strftime("%Y-%m-%d")


async def _proximo_numero() -> str:
    fotos = await repo.listar_fotos(limit=10000)
    if not fotos:
        return "001"
    numeros = [int(f["numero"]) for f in fotos if f["numero"].isdigit()]
    return str(max(numeros) + 1).zfill(3) if numeros else "001"


# ─── Upload via HTTP ──────────────────────────────────────────────────────────


async def salvar_upload(file_bytes: bytes, filename: str) -> dict:
    """Salva arquivo enviado via upload com numero sequencial e checagem de duplicata."""
    tamanho_max = settings.max_upload_mb * 1024 * 1024
    if not file_bytes:
        return {"sucesso": False, "erro": "Arquivo vazio"}
    if len(file_bytes) > tamanho_max:
        return {
            "sucesso": False,
            "erro": f"Arquivo maior que {settings.max_upload_mb}MB",
        }

    nome_seguro = _sanitizar_nome(filename)
    sufixo = Path(nome_seguro).suffix.lower()
    formato = _detectar_formato(file_bytes)
    if sufixo not in settings.extensoes_validas or (formato and formato != sufixo):
        return {"sucesso": False, "erro": "Formato nao suportado"}
    if formato is None:
        return {"sucesso": False, "erro": "Formato invalido"}

    hash_md5 = hashlib.md5(file_bytes).hexdigest()
    existente = await repo.hash_existe(hash_md5)
    if existente:
        fn: str = (
            existente.get("filename")
            or f"{existente['numero']}_{Path(nome_seguro).stem}{sufixo}"
        )
        destino = settings.fotos_dir / fn
        if not destino.exists():
            destino.write_bytes(file_bytes)
        return {
            "sucesso": True,
            "numero": existente["numero"],
            "filename": fn,
            "filepath": str(destino),
            "duplicada": True,
            "mensagem": f"Foto #{existente['numero']} ja existe",
        }

    numero = await _proximo_numero()
    novo_nome = f"{numero}_{Path(nome_seguro).stem}{sufixo}"
    destino = settings.fotos_dir / novo_nome
    while destino.exists():
        numero = str(int(numero) + 1).zfill(3)
        novo_nome = f"{numero}_{Path(nome_seguro).stem}{sufixo}"
        destino = settings.fotos_dir / novo_nome

    destino.write_bytes(file_bytes)
    await repo.registrar_foto(numero, novo_nome, str(destino), hash_md5=hash_md5)
    log.info("Foto salva", extra={"numero": numero, "filename": novo_nome})
    return {
        "sucesso": True,
        "numero": numero,
        "filename": novo_nome,
        "filepath": str(destino),
    }


# ─── Sincronizacao de pasta ───────────────────────────────────────────────────


async def sincronizar_pasta_fotos() -> int:
    """Escaneia pasta fotos/ e registra no banco as que nao estao ainda."""
    arquivos = sorted(
        [
            f
            for f in settings.fotos_dir.iterdir()
            if f.suffix.lower() in settings.extensoes_validas
        ],
        key=lambda p: p.name.lower(),
    )
    registradas = 0
    for arquivo in arquivos:
        if await repo.foto_existe(str(arquivo)):
            continue
        file_bytes = arquivo.read_bytes()
        hash_md5 = hashlib.md5(file_bytes).hexdigest()
        if await repo.hash_existe(hash_md5):
            continue
        numero = await _proximo_numero()
        data_tag = _extrair_data(
            arquivo.name, datetime.fromtimestamp(arquivo.stat().st_mtime)
        )
        novo_nome = f"{numero}_{data_tag}{arquivo.suffix.lower()}"
        destino = settings.fotos_dir / novo_nome
        while destino.exists():
            numero = str(int(numero) + 1).zfill(3)
            novo_nome = f"{numero}_{data_tag}{arquivo.suffix.lower()}"
            destino = settings.fotos_dir / novo_nome
        arquivo.rename(destino)
        await repo.registrar_foto(numero, novo_nome, str(destino), hash_md5=hash_md5)
        registradas += 1
        log.info("Foto sincronizada", extra={"numero": numero, "filename": novo_nome})
    return registradas


def listar_fotos_disco() -> list[dict]:
    return sorted(
        [
            {
                "filename": f.name,
                "filepath": str(f),
                "tamanho_kb": round(f.stat().st_size / 1024, 1),
            }
            for f in settings.fotos_dir.iterdir()
            if f.suffix.lower() in settings.extensoes_validas
        ],
        key=lambda x: x["filename"],
    )
