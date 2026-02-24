"""
2 Cerebro — Database Layer (aiosqlite async)
Connection pool via contextmanager, WAL mode, migracao automatica de schema.
"""

import json
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator

from backend.config import settings
from backend.utils.logger import get_logger

log = get_logger(__name__)

_DB_PATH = settings.db_path


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Abre conexao aiosqlite com WAL mode. Use como context manager."""
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        except Exception:
            await conn.rollback()
            raise


async def _ensure_columns(
    conn: aiosqlite.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    """Adiciona colunas que nao existem ainda (migracao incremental)."""
    cursor = await conn.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()
    existentes = {r["name"] for r in rows}
    for nome, definicao in columns:
        if nome not in existentes:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {definicao}")
            log.info("Schema migrado", extra={"table": table, "column": nome})


async def init_db() -> None:
    """Cria tabelas, indices e adiciona colunas novas (idempotente)."""
    async with get_db() as conn:
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS fotos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                numero        TEXT UNIQUE NOT NULL,
                filename      TEXT NOT NULL,
                filepath      TEXT NOT NULL,
                status        TEXT DEFAULT 'pendente',
                ocr_texto     TEXT,
                ocr_limpo     TEXT,
                criado_em     TEXT,
                processado_em TEXT,
                hash_md5      TEXT,
                hash_sha256   TEXT,
                data_captura  TEXT,
                semana        TEXT,
                mes           TEXT,
                motor_ocr     TEXT DEFAULT 'tesseract',
                fonte         TEXT,
                tema          TEXT,
                tipo          TEXT,
                sentimento    TEXT,
                entidades     TEXT,
                resumo        TEXT,
                classificado  INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS palavras (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                palavra   TEXT UNIQUE NOT NULL,
                contagem  INTEGER DEFAULT 0,
                fotos_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT UNIQUE NOT NULL,
                contagem  INTEGER DEFAULT 0,
                fotos_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS repos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                repo      TEXT UNIQUE NOT NULL,
                contagem  INTEGER DEFAULT 0,
                fotos_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS grupos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nome     TEXT UNIQUE NOT NULL,
                palavras TEXT DEFAULT '[]',
                cor      TEXT DEFAULT '#4f46e5'
            );

            CREATE TABLE IF NOT EXISTS blacklist (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                texto     TEXT UNIQUE NOT NULL,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                numero       TEXT UNIQUE NOT NULL,
                modelo       TEXT NOT NULL,
                vetor        TEXT NOT NULL,
                dimensao     INTEGER,
                atualizado_em TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_fotos_numero     ON fotos(numero);
            CREATE INDEX IF NOT EXISTS idx_fotos_hash       ON fotos(hash_md5);
            CREATE INDEX IF NOT EXISTS idx_fotos_semana     ON fotos(semana);
            CREATE INDEX IF NOT EXISTS idx_fotos_mes        ON fotos(mes);
            CREATE INDEX IF NOT EXISTS idx_palavras_palavra ON palavras(palavra);
            CREATE INDEX IF NOT EXISTS idx_usuarios_user    ON usuarios(username);
            CREATE INDEX IF NOT EXISTS idx_repos_repo       ON repos(repo);
            CREATE INDEX IF NOT EXISTS idx_embed_modelo_num ON embeddings(modelo, numero);
        """)

        # Migracao de colunas para banco existente
        await _ensure_columns(
            conn,
            "fotos",
            [
                ("hash_sha256", "hash_sha256 TEXT"),
                ("fonte", "fonte TEXT"),
                ("tema", "tema TEXT"),
                ("tipo", "tipo TEXT"),
                ("sentimento", "sentimento TEXT"),
                ("entidades", "entidades TEXT"),
                ("resumo", "resumo TEXT"),
                ("classificado", "classificado INTEGER DEFAULT 0"),
            ],
        )

        await conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_fotos_fonte      ON fotos(fonte);
            CREATE INDEX IF NOT EXISTS idx_fotos_tema       ON fotos(tema);
            CREATE INDEX IF NOT EXISTS idx_fotos_sentimento ON fotos(sentimento);
            CREATE INDEX IF NOT EXISTS idx_fotos_classif    ON fotos(classificado);
        """)

        # Grupos semanticos padrao
        grupos_padrao = [
            (
                "llm",
                [
                    "claude",
                    "gpt",
                    "ollama",
                    "gemini",
                    "kimi",
                    "qwen",
                    "llama",
                    "mistral",
                    "anthropic",
                    "openai",
                ],
                "#7c3aed",
            ),
            (
                "agentes",
                ["agent", "agente", "openclaw", "nanoclaw", "mcp", "skill", "workflow"],
                "#0891b2",
            ),
            (
                "github",
                [
                    "github",
                    "repo",
                    "repositorio",
                    "git",
                    "commit",
                    "pull",
                    "branch",
                    "open source",
                    "stars",
                ],
                "#16a34a",
            ),
            (
                "sql",
                [
                    "sql",
                    "query",
                    "select",
                    "join",
                    "index",
                    "banco",
                    "tabela",
                    "database",
                    "where",
                ],
                "#d97706",
            ),
            (
                "automacao",
                [
                    "automacao",
                    "automation",
                    "script",
                    "python",
                    "n8n",
                    "webhook",
                    "api",
                    "cron",
                    "pipeline",
                ],
                "#dc2626",
            ),
            (
                "produtividade",
                [
                    "obsidian",
                    "markdown",
                    "nota",
                    "memoria",
                    "context",
                    "token",
                    "prompt",
                ],
                "#059669",
            ),
            (
                "tendencia",
                ["launch", "novo", "release", "breaking", "2025", "2026", "viral"],
                "#db2777",
            ),
        ]
        for nome, palavras, cor in grupos_padrao:
            await conn.execute(
                "INSERT OR IGNORE INTO grupos (nome, palavras, cor) VALUES (?, ?, ?)",
                (nome, json.dumps(palavras), cor),
            )

        await conn.commit()
        log.info("DB inicializado", extra={"path": str(_DB_PATH)})
