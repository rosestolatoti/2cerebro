from dotenv import load_dotenv
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

from ocr_engine import limpar_texto, extrair_usernames, extrair_repos_github
from file_manager import salvar_upload
from config import FOTOS_DIR


def test_ocr_limpeza_basica() -> None:
    """
    Garante que a limpeza remove ruído e mantém conteúdo útil.
    """
    texto = """
    21:50
    Traduzido do inglês por Google
    Ver tradução
    @OpenClaw nova release
    github.com/owner/repo
    Curtir
    """
    limpo = limpar_texto(texto)
    assert "Traduzido" not in limpo
    assert "Ver tradução" not in limpo
    assert "@OpenClaw" in limpo
    assert "github.com/owner/repo" in limpo


def test_extracao_users_repos() -> None:
    """
    Extrai @users e repos de texto com variações de URL.
    """
    texto = "Veja @User_01 e https://github.com/Owner/Repo.git agora"
    users = extrair_usernames(texto)
    repos = extrair_repos_github(texto)
    assert users == ["user_01"]
    assert repos == ["owner/repo"]

    texto_quebrado = "github.com/OpenClaw\nProjetoX"
    repos_quebrados = extrair_repos_github(texto_quebrado)
    assert repos_quebrados == ["openclaw/projetox"]


def test_upload_validacao_basica() -> None:
    """
    Garante que upload rejeita vazio e aceita formato válido.
    """
    vazio = salvar_upload(b"", "vazio.png")
    assert vazio["sucesso"] is False

    png_min = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    resultado = salvar_upload(png_min, "teste_upload.png")
    assert resultado["sucesso"] is True
    destino = FOTOS_DIR / resultado["filename"]
    assert destino.exists()
    destino.unlink(missing_ok=True)
