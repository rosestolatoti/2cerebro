"""
GigU Brain — OCR Engine
Extração e limpeza de texto de imagens via Tesseract
"""

import re
import pytesseract
from pytesseract import Output
from PIL import Image, ImageEnhance
from pathlib import Path
from config import TESSERACT_LANG, TESSERACT_CONFIG, STOPWORDS, OCR_DIR
from datetime import datetime
import os
try:
    import numpy as np
except Exception:
    np = None


# Padrões de lixo para remover
LIXO = [
    r'^\d{1,2}:\d{2}.*$',           # barra de status: 21:50 ...
    r'^.*\d+%.*$',                   # bateria: 95%
    r'^[<>|©®°•·\-_=]{2,}$',        # linhas de símbolos
    r'^\s*[<O|]\s*[IO|<>]\s*$',      # botões navegação < O IO
    r'^\s*\(\s*\d*\s*\)\s*$',        # (0)
    r'^Publicar sua resposta.*$',     # rodapé twitter
    r'^Traduzido do inglês.*$',       # label google translate
    r'^Ver tradução.*$',
    r'^Acessar o perfil.*$',
    r'^Abrir aplicativo.*$',
    r'^\s*€\s*Postar\s*$',
    r'^\s*←\s*Postar\s*$',
    r'^Seguir.*$',
    r'^Seguindo.*$',
    r'^\s*Posts\s*$',
    r'^\s*Postar\s*$',
    r'^.*Republicações.*Comentários.*$',
    r'^.*Curtidas.*Salvos.*$',
    r'^.*Visualizações.*$',
    r'^Traduzido do inglês.*Google.*$',
    r'^Traduzido do ingles.*Google.*$',
    r'^Traduzido do inglês por Google.*$',
    r'^Traduzido do ingles por Google.*$',
    r'^Translated from English.*$',
    r'^See translation.*$',
    r'^Ver mais.*$',
    r'^Responder.*$',
    r'^Responder a.*$',
    r'^Curtir.*$',
    r'^Compartilhar.*$',
    r'^Retweet.*$',
    r'^Repostar.*$',
    r'^Seguir.*Twitter.*$',
    r'^X.*com.*$',
    r'^Postado por.*$',
]

TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
if not TESSERACT_CMD:
    default_cmd = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if default_cmd.exists():
        TESSERACT_CMD = str(default_cmd)
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def preprocessar(image_path: str) -> Image.Image:
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    topo = int(h * (0.10 if h > 1600 else 0.07))
    base = int(h * (0.06 if h > 1600 else 0.04))
    esquerda = int(w * 0.01)
    direita = int(w * 0.99)
    img = img.crop((esquerda, topo, direita, h - base))
    img = _recortar_area_texto(img)

    # Upscale se necessário
    w, h = img.size
    if w < 1000:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)

    img = ImageEnhance.Contrast(img).enhance(2.1)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.convert("L")
    if np is None:
        img = img.point(lambda x: 0 if x < 145 else 255)
    else:
        img = _threshold_adaptativo(img)
    return img.convert("RGB")


def _recortar_area_texto(img: Image.Image) -> Image.Image:
    if np is None:
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
    if np is None:
        return img
    w, h = img.size
    small = img.resize((max(1, w // 8), max(1, h // 8)), Image.BILINEAR)
    mean_up = small.resize((w, h), Image.BILINEAR)
    base = np.array(img).astype("float32")
    mean = np.array(mean_up).astype("float32")
    bin_arr = (base < (mean - 10)).astype("uint8") * 255
    return Image.fromarray(bin_arr)


def _linha_util(linha: str) -> bool:
    total = len(linha)
    if total < 4:
        return False
    letras = len(re.findall(r"[a-zA-ZÀ-ÿ]", linha))
    digitos = len(re.findall(r"\d", linha))
    if letras == 0:
        return False
    if letras / total < 0.35:
        return False
    if digitos / total > 0.6 and letras / total < 0.45:
        return False
    return True


def limpar_texto(texto: str) -> str:
    linhas = texto.split('\n')
    limpas = []
    vistos = set()

    for linha in linhas:
        linha = linha.strip()
        if not linha or len(linha) < 3:
            continue
        if not _linha_util(linha):
            continue
        ignorar = any(re.match(p, linha, re.IGNORECASE) for p in LIXO)
        if not ignorar and linha.lower() not in vistos:
            limpas.append(linha)
            vistos.add(linha.lower())

    return '\n'.join(limpas)


def extrair_palavras(texto: str) -> list:
    palavras = re.findall(r'\b[a-zA-ZÀ-ÿ]{2,}\b', texto.lower())
    return [p for p in palavras if p not in STOPWORDS]


def extrair_usernames(texto: str) -> list[str]:
    encontrados = re.findall(r"@([a-zA-Z0-9_]{2,30})", texto)
    return list(dict.fromkeys([e.lower() for e in encontrados]))


def extrair_repos_github(texto: str) -> list[str]:
    texto = _reconstruir_urls_github(texto)
    repos = []
    for m in re.findall(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", texto):
        owner, repo = m
        repo = repo.replace(".git", "").strip(". ,;:()[]{}<>")
        owner = owner.strip(". ,;:()[]{}<>")
        if owner and repo:
            repos.append(f"{owner}/{repo}".lower())
    return list(dict.fromkeys(repos))


def _reconstruir_urls_github(texto: str) -> str:
    linhas = [linha.strip() for linha in texto.splitlines()]
    saida = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if "github.com" in linha and not re.search(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", linha):
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


def _config_por_imagem(img: Image.Image) -> str:
    w, h = img.size
    if w > h:
        return "--psm 3 --oem 3"
    return TESSERACT_CONFIG


def _texto_por_confianca(img: Image.Image, config: str) -> str:
    data = pytesseract.image_to_data(img, lang=TESSERACT_LANG, config=config, output_type=Output.DICT)
    linhas = {}
    n = len(data["text"])
    for i in range(n):
        texto = data["text"][i].strip()
        conf = int(float(data["conf"][i]))
        if conf < 60 or not texto:
            continue
        chave = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        linhas.setdefault(chave, []).append(texto)
    ordenadas = [linhas[k] for k in sorted(linhas.keys())]
    return "\n".join(" ".join(p) for p in ordenadas)


def salvar_ocr_bruto(numero: str, filename: str, texto: str) -> Path:
    arquivo = OCR_DIR / f"{numero}_{Path(filename).stem}.md"
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
    with open(arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return arquivo


def processar_imagem(image_path: str, numero: str, filename: str) -> dict:
    try:
        img = preprocessar(image_path)
        config = _config_por_imagem(img)
        texto_bruto = pytesseract.image_to_string(
            img,
            lang=TESSERACT_LANG,
            config=config
        ).strip()
        texto_conf = _texto_por_confianca(img, config)
        texto_base = texto_conf if len(texto_conf) >= 30 else texto_bruto
        texto_limpo = limpar_texto(texto_base)
        palavras = extrair_palavras(texto_limpo)
        salvar_ocr_bruto(numero, filename, texto_bruto)

        return {
            "sucesso": True,
            "texto_bruto": texto_bruto,
            "texto_limpo": texto_limpo,
            "palavras": palavras,
            "caracteres": len(texto_limpo)
        }

    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "texto_bruto": "",
            "texto_limpo": "",
            "palavras": [],
            "caracteres": 0
        }
