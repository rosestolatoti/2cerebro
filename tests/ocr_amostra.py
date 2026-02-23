"""
Executa OCR em todas as fotos e imprime análise de dados.
"""
from pathlib import Path
from statistics import mean
from collections import Counter, defaultdict
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from ocr_engine import processar_imagem, extrair_usernames, extrair_repos_github
from database import init_db, atualizar_ocr, atualizar_ocr_limpo, atualizar_palavras, atualizar_usuarios, atualizar_repos

FOTOS_DIR = BASE_DIR / "fotos"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main():
    init_db()
    arquivos = [f for f in FOTOS_DIR.iterdir() if f.suffix.lower() in EXTS]
    arquivos.sort(key=lambda p: p.name.lower())
    if not arquivos:
        print("Nenhuma foto encontrada")
        return

    resultados = []
    palavras_contagem = Counter()
    palavras_fotos = defaultdict(set)
    usuarios_contagem = Counter()
    repos_contagem = Counter()

    for f in arquivos:
        numero = f.name.split("_")[0]
        r = processar_imagem(str(f), numero, f.name)
        texto = r.get("texto_limpo", "")
        palavras = r.get("palavras", [])
        usernames = extrair_usernames(texto)
        repos = extrair_repos_github(texto)

        if r.get("sucesso"):
            atualizar_ocr(numero, r.get("texto_bruto", ""))
            atualizar_ocr_limpo(numero, texto)
            atualizar_palavras(numero, palavras)
            if usernames:
                atualizar_usuarios(numero, usernames)
            if repos:
                atualizar_repos(numero, repos)

        for p in palavras:
            palavras_contagem[p] += 1
            palavras_fotos[p].add(numero)
        for u in usernames:
            usuarios_contagem[u] += 1
        for repo in repos:
            repos_contagem[repo] += 1

        resultados.append({
            "arquivo": f.name,
            "sucesso": r.get("sucesso", False),
            "caracteres": r.get("caracteres", 0),
            "palavras": len(palavras),
            "usuarios": len(usernames),
            "repos": len(repos),
            "erro": r.get("erro", "")
        })

    sucessos = [r for r in resultados if r["sucesso"]]
    medias = {
        "caracteres": mean([r["caracteres"] for r in sucessos]) if sucessos else 0,
        "palavras": mean([r["palavras"] for r in sucessos]) if sucessos else 0
    }

    total = len(resultados)
    sucesso = sum(1 for r in resultados if r["sucesso"])
    falhas = total - sucesso
    fotos_com_usuarios = sum(1 for r in resultados if r["usuarios"] > 0)
    fotos_com_repos = sum(1 for r in resultados if r["repos"] > 0)

    print("ANALISE OCR (TODAS AS FOTOS)")
    print(f"total_fotos: {total}")
    print(f"sucesso: {sucesso}")
    print(f"falhas: {falhas}")
    print(f"media_caracteres: {medias['caracteres']:.1f}")
    print(f"media_palavras: {medias['palavras']:.1f}")
    print(f"fotos_com_usuarios: {fotos_com_usuarios}")
    print(f"fotos_com_repos: {fotos_com_repos}")
    print("top_palavras:")
    for p, c in palavras_contagem.most_common(20):
        print(f"{p} {c} fotos:{len(palavras_fotos[p])}")
    print("top_usuarios:")
    for u, c in usuarios_contagem.most_common(20):
        print(f"@{u} {c}")
    print("top_repos:")
    for repo, c in repos_contagem.most_common(20):
        print(f"{repo} {c}")


if __name__ == "__main__":
    main()
