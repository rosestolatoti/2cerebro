"""
GigU Brain — File Manager
Gerencia e renumera fotos automaticamente
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from config import FOTOS_DIR, EXTENSOES_VALIDAS, MAX_UPLOAD_MB
from database import registrar_foto, listar_fotos, foto_existe, hash_existe

_lock = Lock()


def _sanitizar_nome(nome: str) -> str:
    nome = Path(nome).name
    nome = re.sub(r"[^a-zA-Z0-9._-]+", "_", nome).strip("._-")
    return nome or "arquivo"


def _detectar_formato(file_bytes: bytes) -> str | None:
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


def proximo_numero() -> str:
    fotos = listar_fotos()
    if not fotos:
        return "001"
    numeros = [int(f["numero"]) for f in fotos]
    return str(max(numeros) + 1).zfill(3)


def registrar_fotos_existentes():
    """Escaneia pasta fotos/ e registra no banco apenas as que ainda não estão"""
    arquivos = sorted(
        [f for f in FOTOS_DIR.iterdir() if f.suffix.lower() in EXTENSOES_VALIDAS]
    )

    registradas = 0
    for arquivo in arquivos:
        if not foto_existe(str(arquivo)):
            numero = proximo_numero()
            registrar_foto(numero, arquivo.name, str(arquivo))
            registradas += 1

    return registradas


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


def sincronizar_pasta_fotos() -> int:
    with _lock:
        arquivos = sorted(
            [f for f in FOTOS_DIR.iterdir() if f.suffix.lower() in EXTENSOES_VALIDAS],
            key=lambda p: p.name.lower(),
        )

        registradas = 0
        for arquivo in arquivos:
            if foto_existe(str(arquivo)):
                continue
            file_bytes = arquivo.read_bytes()
            hash_md5 = hashlib.md5(file_bytes).hexdigest()
            if hash_existe(hash_md5):
                continue
            numero = proximo_numero()
            data_tag = _extrair_data(
                arquivo.name, datetime.fromtimestamp(arquivo.stat().st_mtime)
            )
            novo_nome = f"{numero}_{data_tag}{arquivo.suffix.lower()}"
            destino = FOTOS_DIR / novo_nome
            while destino.exists():
                numero = str(int(numero) + 1).zfill(3)
                novo_nome = f"{numero}_{data_tag}{arquivo.suffix.lower()}"
                destino = FOTOS_DIR / novo_nome
            arquivo.rename(destino)
            registrar_foto(numero, novo_nome, str(destino), hash_md5=hash_md5)
            registradas += 1

        return registradas


def salvar_upload(file_bytes: bytes, filename: str) -> dict:
    """Salva arquivo enviado via upload com número sequencial e checagem de duplicata"""
    tamanho_max = MAX_UPLOAD_MB * 1024 * 1024
    if not file_bytes:
        return {"sucesso": False, "erro": "Arquivo vazio"}
    if len(file_bytes) > tamanho_max:
        return {"sucesso": False, "erro": f"Arquivo maior que {MAX_UPLOAD_MB}MB"}

    nome_seguro = _sanitizar_nome(filename)
    sufixo = Path(nome_seguro).suffix.lower()
    formato = _detectar_formato(file_bytes)
    if sufixo not in EXTENSOES_VALIDAS or (formato and formato != sufixo):
        return {"sucesso": False, "erro": "Formato não suportado"}
    if formato is None:
        return {"sucesso": False, "erro": "Formato inválido"}

    with _lock:
        hash_md5 = hashlib.md5(file_bytes).hexdigest()
        existente = hash_existe(hash_md5)
        if existente:
            filename: str = (
                existente.get("filename")
                or f"{existente['numero']}_{Path(nome_seguro).stem}{sufixo}"
            )
            destino = FOTOS_DIR / filename
            if not destino.exists():
                with open(destino, "wb") as f:
                    f.write(file_bytes)
            filepath = str(destino)
            return {
                "sucesso": True,
                "numero": existente["numero"],
                "filename": filename,
                "filepath": filepath,
                "duplicada": True,
                "mensagem": f"Foto #{existente['numero']} já existe",
            }

        numero = proximo_numero()
        novo_nome = f"{numero}_{Path(nome_seguro).stem}{sufixo}"
        destino = FOTOS_DIR / novo_nome
        while destino.exists():
            numero = str(int(numero) + 1).zfill(3)
            novo_nome = f"{numero}_{Path(nome_seguro).stem}{sufixo}"
            destino = FOTOS_DIR / novo_nome

        with open(destino, "wb") as f:
            f.write(file_bytes)

        registrar_foto(numero, novo_nome, str(destino), hash_md5=hash_md5)

        return {
            "sucesso": True,
            "numero": numero,
            "filename": novo_nome,
            "filepath": str(destino),
        }


def listar_fotos_disco() -> list:
    """Lista fotos existentes na pasta com metadados"""
    return sorted(
        [
            {
                "filename": f.name,
                "filepath": str(f),
                "tamanho_kb": round(f.stat().st_size / 1024, 1),
            }
            for f in FOTOS_DIR.iterdir()
            if f.suffix.lower() in EXTENSOES_VALIDAS
        ],
        key=lambda x: x["filename"],
    )
