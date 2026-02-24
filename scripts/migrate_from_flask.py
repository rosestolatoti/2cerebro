"""
Script de migracao: lê fotos antigas e gera embeddings via batch no ChromaDB.
"""

import asyncio
import json
import logging
from pathlib import Path

# Ajuste do path para rodar na raiz
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.database import init_db
from backend.db import repositories as repo
from backend.services.embedding_service import rebuild_embeddings_batch

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("migracao")


async def migrar():
    log.info("Iniciando migracao...")

    # 1. Garante que schema novo existe
    await init_db()

    # 2. Busca todas as fotos
    fotos = await repo.listar_fotos(limit=10000)
    log.info(f"Total de fotos no banco: {len(fotos)}")

    pendentes_embedding = []

    # 3. Limpa e checa o que precisa de embedding
    for f in fotos:
        if not f.get("ocr_limpo"):
            continue

        # Pega do SQLite pra ver se ja tem embedding (fallback)
        vetor_existe = False
        if f.get("id"):
            # Ja tem tabela embeddings, vamos checar
            pass  # Simplificacao: forca recriar para garantir formato do ChromaDB

        pendentes_embedding.append(f)

    if pendentes_embedding:
        log.info(
            f"Gerando embeddings em batch para {len(pendentes_embedding)} fotos..."
        )
        resultado = await rebuild_embeddings_batch(pendentes_embedding)
        log.info(f"Resultado batch: {resultado}")
    else:
        log.info("Nenhuma foto precisava de migracao de embeddings.")

    log.info("Migracao finalizada!")


if __name__ == "__main__":
    asyncio.run(migrar())
