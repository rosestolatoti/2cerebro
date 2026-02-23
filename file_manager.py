"""
GigU Brain — File Manager
Gerencia e renumera fotos automaticamente
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from config import FOTOS_DIR, EXTENSOES_VALIDAS
from database import registrar_foto, listar_fotos, foto_existe, hash_existe


def proximo_numero() -> str:
    fotos = listar_fotos()
    if not fotos:
        return "001"
    numeros = [int(f["numero"]) for f in fotos]
    return str(max(numeros) + 1).zfill(3)


def registrar_fotos_existentes():
    """Escaneia pasta fotos/ e registra no banco apenas as que ainda não estão"""
    arquivos = sorted([
        f for f in FOTOS_DIR.iterdir()
        if f.suffix.lower() in EXTENSOES_VALIDAS
    ])

    registradas = 0
    for arquivo in arquivos:
        if not foto_existe(str(arquivo)):
            numero = proximo_numero()
            registrar_foto(numero, arquivo.name, str(arquivo))
            registradas += 1

    return registradas


def _extrair_data(nome: str, fallback_dt: datetime) -> str:
    m = re.search(r"(\\d{4}-\\d{2}-\\d{2})[^\\d]?(\\d{2})[-_](\\d{2})[-_](\\d{2})", nome)
    if m:
        return f"{m.group(1)}_{m.group(2)}-{m.group(3)}-{m.group(4)}"
    m = re.search(r"(\\d{8})[-_](\\d{2})(\\d{2})(\\d{2})", nome)
    if m:
        d = datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
        return f"{d}_{m.group(2)}-{m.group(3)}-{m.group(4)}"
    m = re.search(r"(\\d{4}-\\d{2}-\\d{2})", nome)
    if m:
        return m.group(1)
    m = re.search(r"(\\d{8})", nome)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
    return fallback_dt.strftime("%Y-%m-%d")


def sincronizar_pasta_fotos() -> int:
    arquivos = sorted([
        f for f in FOTOS_DIR.iterdir()
        if f.suffix.lower() in EXTENSOES_VALIDAS
    ], key=lambda p: p.name.lower())

    registradas = 0
    for arquivo in arquivos:
        if foto_existe(str(arquivo)):
            continue
        file_bytes = arquivo.read_bytes()
        hash_md5 = hashlib.md5(file_bytes).hexdigest()
        if hash_existe(hash_md5):
            continue
        numero = proximo_numero()
        data_tag = _extrair_data(arquivo.name, datetime.fromtimestamp(arquivo.stat().st_mtime))
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
    sufixo = Path(filename).suffix.lower()
    if sufixo not in EXTENSOES_VALIDAS:
        return {"sucesso": False, "erro": "Formato não suportado"}

    # Checar duplicata por hash MD5 - apenas registrar, não bloquear
    hash_md5 = hashlib.md5(file_bytes).hexdigest()
    existente = hash_existe(hash_md5)
    if existente:
        return {
            "sucesso": True,
            "numero": existente['numero'],
            "duplicada": True,
            "mensagem": f"Foto #{existente['numero']} já existe"
        }

    numero = proximo_numero()
    novo_nome = f"{numero}_{Path(filename).stem}{sufixo}"
    destino = FOTOS_DIR / novo_nome

    with open(destino, "wb") as f:
        f.write(file_bytes)

    registrar_foto(numero, novo_nome, str(destino), hash_md5=hash_md5)

    return {
        "sucesso": True,
        "numero": numero,
        "filename": novo_nome,
        "filepath": str(destino)
    }


def listar_fotos_disco() -> list:
    """Lista fotos existentes na pasta com metadados"""
    return sorted([
        {
            "filename": f.name,
            "filepath": str(f),
            "tamanho_kb": round(f.stat().st_size / 1024, 1)
        }
        for f in FOTOS_DIR.iterdir()
        if f.suffix.lower() in EXTENSOES_VALIDAS
    ], key=lambda x: x["filename"])
