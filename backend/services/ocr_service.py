"""
2 Cerebro — OCR Service
Migrado de ocr_engine.py com suporte a async via run_in_executor.
"""

from __future__ import annotations
import asyncio
import re
from datetime import datetime
from functools import partial
from pathlib import Path

import pytesseract
from pytesseract import Output
from PIL import Image, ImageEnhance

from backend.config import settings
from backend.utils.logger import get_logger

log = get_logger(__name__)

try:
    import numpy as np

    _NP = True
except ImportError:
    np = None  # type: ignore
    _NP = False

# Configura path do tesseract se necessario
if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

# Padroes de lixo de UI mobile
_LIXO = [
    r"^\d{1,2}:\d{2}.*$",
    r"^.*\d+%.*$",
    r"^[<>|©®°•·\-_=]{2,}$",
    r"^\s*[<O|]\s*[IO|<>]\s*$",
    r"^\s*\(\s*\d*\s*\)\s*$",
    r"^Publicar sua resposta.*$",
    r"^Traduzido do ingl[eê]s.*$",
    r"^Ver tradu[cç][aã]o.*$",
    r"^Acessar o perfil.*$",
    r"^Abrir aplicativo.*$",
    r"^\s*[←€]\s*Postar\s*$",
    r"^\s*Posts\s*$",
    r"^\s*Postar\s*$",
    r"^.*Republicações.*Comentários.*$",
    r"^.*Curtidas.*Salvos.*$",
    r"^.*Visualizações.*$",
    r"^Translated from English.*$",
    r"^See translation.*$",
    r"^Ver mais.*$",
    r"^Responder.*$",
    r"^Curtir.*$",
    r"^Compartilhar.*$",
    r"^Retweet.*$",
    r"^Repostar.*$",
    r"^Seguir.*$",
    r"^Seguindo.*$",
    r"^X.*com.*$",
    r"^Postado por.*$",
]


# ─── Pre-processamento ────────────────────────────────────────────────────────


def _recortar_area_texto(img: Image.Image) -> Image.Image:
    if not _NP:
        return img
    gray = img.convert("L")
    arr = np.array(gray)
    h, w = arr.shape
    if h < 50 or w < 50:
        return img
    mask = arr < 230
    row_ratio = mask.mean(axis=1)
    col_ratio = mask.mean(axis=0)
    rows = np.where(row_ratio > 0.01)[0]
    cols = np.where(col_ratio > 0.01)[0]
    if rows.size == 0 or cols.size == 0:
        return img
    top = max(int(rows[0] - h * 0.02), 0)
    bottom = min(int(rows[-1] + h * 0.02), h - 1)
    left = max(int(cols[0] - w * 0.02), 0)
    right = min(int(cols[-1] + w * 0.02), w - 1)
    if bottom <= top or right <= left:
        return img
    return img.crop((left, top, right, bottom))


def _threshold_adaptativo(img: Image.Image) -> Image.Image:
    if not _NP:
        return img
    w, h = img.size
    small = img.resize((max(1, w // 8), max(1, h // 8)), Image.Resampling.BILINEAR)
    mean_up = small.resize((w, h), Image.Resampling.BILINEAR)
    base = np.array(img).astype("float32")
    mean = np.array(mean_up).astype("float32")
    bin_arr = (base < (mean - 10)).astype("uint8") * 255
    return Image.fromarray(bin_arr)


def _preprocessar(image_path: str) -> Image.Image:
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    max_px = settings.max_image_pixels
    max_side = settings.max_image_side
    if w * h > max_px or max(w, h) > max_side:
        scale = min(max_side / max(w, h), (max_px / (w * h)) ** 0.5)
        img = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS
        )
        w, h = img.size

    topo = int(h * (0.10 if h > 1600 else 0.07))
    base = int(h * (0.06 if h > 1600 else 0.04))
    img = img.crop((int(w * 0.01), topo, int(w * 0.99), h - base))
    img = _recortar_area_texto(img)

    w, h = img.size
    if w < 1000:
        img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)

    img = ImageEnhance.Contrast(img).enhance(2.1)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.convert("L")
    img = (
        _threshold_adaptativo(img)
        if _NP
        else img.point(lambda x: 0 if x < 145 else 255)
    )
    return img.convert("RGB")


def _config_por_imagem(img: Image.Image) -> str:
    w, h = img.size
    return "--psm 3 --oem 3" if w > h else settings.tesseract_config


def _texto_por_confianca(img: Image.Image, config: str) -> str:
    data = pytesseract.image_to_data(
        img, lang=settings.tesseract_lang, config=config, output_type=Output.DICT
    )
    linhas: dict = {}
    for i in range(len(data["text"])):
        texto = data["text"][i].strip()
        conf = int(float(data["conf"][i]))
        if conf < 60 or not texto:
            continue
        chave = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        linhas.setdefault(chave, []).append(texto)
    return "\n".join(" ".join(p) for p in (linhas[k] for k in sorted(linhas)))


# ─── Limpeza e extracao ───────────────────────────────────────────────────────


def _linha_util(linha: str) -> bool:
    total = len(linha)
    if total < 4:
        return False
    letras = len(re.findall(r"[a-zA-ZÀ-ÿ]", linha))
    digitos = len(re.findall(r"\d", linha))
    if letras == 0 or letras / total < 0.35:
        return False
    if digitos / total > 0.6 and letras / total < 0.45:
        return False
    return True


def limpar_texto(texto: str) -> str:
    limpas = []
    vistos: set = set()
    for linha in texto.split("\n"):
        linha = linha.strip()
        if not linha or len(linha) < 3:
            continue
        if not _linha_util(linha):
            continue
        if any(re.match(p, linha, re.IGNORECASE) for p in _LIXO):
            continue
        if linha.lower() not in vistos:
            limpas.append(linha)
            vistos.add(linha.lower())
    return "\n".join(limpas)


def extrair_palavras(texto: str) -> list[str]:
    palavras = re.findall(r"\b[a-zA-ZÀ-ÿ]{2,}\b", texto.lower())
    return [p for p in palavras if p not in settings.stopwords]


def extrair_usernames(texto: str) -> list[str]:
    encontrados = re.findall(r"@([a-zA-Z0-9_]{2,30})", texto)
    return list(dict.fromkeys(e.lower() for e in encontrados))


def _reconstruir_urls_github(texto: str) -> str:
    linhas = [linha.strip() for linha in texto.splitlines()]
    saida = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if "github.com" in linha and not re.search(
            r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", linha
        ):
            owner = re.search(r"github\.com/([A-Za-z0-9_.-]+)", linha)
            if owner and i + 1 < len(linhas):
                prox = linhas[i + 1].strip()
                repo = re.search(r"([A-Za-z0-9_.-]+)", prox)
                if repo:
                    linha = f"{linha.rstrip('/')}/{repo.group(1)}"
                    i += 1
        saida.append(linha)
        i += 1
    return "\n".join(saida)


def extrair_repos_github(texto: str) -> list[str]:
    texto = _reconstruir_urls_github(texto)
    repos = []
    for m in re.findall(
        r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
        texto,
    ):
        owner, repo = m
        repo = repo.replace(".git", "").strip(". ,;:()[]{}<>")
        owner = owner.strip(". ,;:()[]{}<>")
        if owner and repo:
            repos.append(f"{owner}/{repo}".lower())
    return list(dict.fromkeys(repos))


def _salvar_ocr_bruto(numero: str, filename: str, texto: str) -> None:
    arquivo = settings.ocr_dir / f"{numero}_{Path(filename).stem}.md"
    conteudo = f"""---
foto: "{numero}"
arquivo: "{filename}"
data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
caracteres: {len(texto)}
---

# OCR Bruto — Foto {numero}
```
{texto}
```
"""
    arquivo.write_text(conteudo, encoding="utf-8")


# ─── Funcao principal (sync — chama via executor) ────────────────────────────


def _processar_sync(image_path: str, numero: str, filename: str) -> dict:
    try:
        if not Path(image_path).exists():
            return {
                "sucesso": False,
                "erro": "Arquivo nao encontrado",
                "texto_bruto": "",
                "texto_limpo": "",
                "palavras": [],
                "caracteres": 0,
            }

        img = _preprocessar(image_path)
        config = _config_por_imagem(img)
        texto_bruto = pytesseract.image_to_string(
            img, lang=settings.tesseract_lang, config=config
        ).strip()
        texto_conf = _texto_por_confianca(img, config)
        texto_base = texto_conf if len(texto_conf) >= 30 else texto_bruto
        texto_limpo = limpar_texto(texto_base)
        palavras = extrair_palavras(texto_limpo)
        _salvar_ocr_bruto(numero, filename, texto_bruto)

        return {
            "sucesso": True,
            "texto_bruto": texto_bruto,
            "texto_limpo": texto_limpo,
            "palavras": palavras,
            "caracteres": len(texto_limpo),
        }
    except Exception as e:
        log.exception("Erro no OCR", extra={"numero": numero, "erro": str(e)})
        return {
            "sucesso": False,
            "erro": str(e),
            "texto_bruto": "",
            "texto_limpo": "",
            "palavras": [],
            "caracteres": 0,
        }


async def processar_imagem(image_path: str, numero: str, filename: str) -> dict:
    """Executa OCR em thread pool para nao bloquear o event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_processar_sync, image_path, numero, filename)
    )
