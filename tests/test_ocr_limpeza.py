from dotenv import load_dotenv
from langwatch import trace
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

from ocr_engine import limpar_texto, extrair_usernames, extrair_repos_github


@trace(name="test_ocr_limpeza_basica")
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


@trace(name="test_extracao_users_repos")
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
