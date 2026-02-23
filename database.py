"""
GigU Brain — Database Layer
SQLite para memória persistente do sistema
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "gigu_brain.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns(conn, table: str, columns: list[tuple[str, str]]):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existentes = {r["name"] for r in rows}
    for nome, definicao in columns:
        if nome not in existentes:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {definicao}")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS fotos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            filename    TEXT NOT NULL,
            filepath    TEXT NOT NULL,
            status      TEXT DEFAULT 'pendente',
            ocr_texto   TEXT,
            ocr_limpo   TEXT,
            criado_em   TEXT,
            processado_em TEXT,
            hash_md5    TEXT,
            data_captura TEXT,
            semana      TEXT,
            mes         TEXT,
            motor_ocr   TEXT DEFAULT 'tesseract'
        );

        CREATE TABLE IF NOT EXISTS palavras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            palavra     TEXT UNIQUE NOT NULL,
            contagem    INTEGER DEFAULT 0,
            fotos_ids   TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            contagem    INTEGER DEFAULT 0,
            fotos_ids   TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS repos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            repo        TEXT UNIQUE NOT NULL,
            contagem    INTEGER DEFAULT 0,
            fotos_ids   TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS grupos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT UNIQUE NOT NULL,
            palavras    TEXT DEFAULT '[]',
            cor         TEXT DEFAULT '#4f46e5'
        );
        CREATE TABLE IF NOT EXISTS blacklist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            texto       TEXT UNIQUE NOT NULL,
            criado_em   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS embeddings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            modelo      TEXT NOT NULL,
            vetor       TEXT NOT NULL,
            dimensao    INTEGER,
            atualizado_em TEXT
        );
    """)

    colunas_fotos = [
        ("hash_md5", "hash_md5 TEXT"),
        ("data_captura", "data_captura TEXT"),
        ("semana", "semana TEXT"),
        ("mes", "mes TEXT"),
        ("motor_ocr", "motor_ocr TEXT DEFAULT 'tesseract'")
    ]
    ensure_columns(conn, "fotos", colunas_fotos)

    conn.commit()

    # Grupos semânticos padrão
    import json
    grupos_padrao = [
        (
            "llm",
            [
                "claude", "gpt", "ollama", "gemini", "kimi", "qwen", "llama", "mistral", "anthropic", "openai"
            ],
            "#7c3aed",
        ),
        (
            "agentes",
            ["agent", "agente", "openclaw", "nanoclaw", "clawwork", "mcp", "skill", "workflow"],
            "#0891b2",
        ),
        (
            "github",
            ["github", "repo", "repositorio", "git", "commit", "pull", "branch", "open source", "stars"],
            "#16a34a",
        ),
        (
            "sql",
            ["sql", "query", "select", "join", "index", "banco", "tabela", "database", "where", "group"],
            "#d97706",
        ),
        (
            "automacao",
            ["automacao", "automation", "script", "python", "n8n", "webhook", "api", "cron", "pipeline"],
            "#dc2626",
        ),
        (
            "produtividade",
            ["obsidian", "markdown", "nota", "memoria", "context", "token", "prompt", "agents.md"],
            "#059669",
        ),
        (
            "tendencia",
            ["launch", "novo", "release", "breaking", "ultima hora", "2025", "2026", "viral"],
            "#db2777",
        ),
    ]

    for nome, palavras, cor in grupos_padrao:
        cur.execute("""
            INSERT OR IGNORE INTO grupos (nome, palavras, cor)
            VALUES (?, ?, ?)
        """, (nome, json.dumps(palavras), cor))

    conn.commit()
    conn.close()
    print("DB inicializado com sucesso")


# --- FOTOS ---

def registrar_foto(numero: str, filename: str, filepath: str, hash_md5: str = None) -> int:
    agora = datetime.now()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO fotos
        (numero, filename, filepath, hash_md5, criado_em, data_captura, semana, mes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        numero, filename, filepath, hash_md5,
        agora.isoformat(),
        agora.strftime("%Y-%m-%d"),
        agora.strftime("%Y-W%W"),
        agora.strftime("%Y-%m")
    ))
    conn.commit()
    id_ = cur.lastrowid
    conn.close()
    return id_


def foto_existe(filepath: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT id FROM fotos WHERE filepath=?", (filepath,)).fetchone()
    conn.close()
    return row is not None


def hash_existe(hash_md5: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT numero, filename FROM fotos WHERE hash_md5=?", (hash_md5,)).fetchone()
    conn.close()
    return dict(row) if row else None


def deletar_foto_db(numero: str):
    import json
    conn = get_conn()

    # Remover referência da tabela de palavras
    palavras = conn.execute("SELECT id, fotos_ids, contagem FROM palavras").fetchall()
    for p in palavras:
        fotos = json.loads(p["fotos_ids"] or "[]")
        if numero in fotos:
            fotos.remove(numero)
            nova_contagem = max(0, p["contagem"] - 1)
            if nova_contagem == 0:
                conn.execute("DELETE FROM palavras WHERE id=?", (p["id"],))
            else:
                conn.execute(
                    "UPDATE palavras SET fotos_ids=?, contagem=? WHERE id=?",
                    (json.dumps(fotos), nova_contagem, p["id"])
                )

    usuarios = conn.execute("SELECT id, fotos_ids, contagem FROM usuarios").fetchall()
    for u in usuarios:
        fotos = json.loads(u["fotos_ids"] or "[]")
        if numero in fotos:
            fotos.remove(numero)
            nova_contagem = max(0, u["contagem"] - 1)
            if nova_contagem == 0:
                conn.execute("DELETE FROM usuarios WHERE id=?", (u["id"],))
            else:
                conn.execute(
                    "UPDATE usuarios SET fotos_ids=?, contagem=? WHERE id=?",
                    (json.dumps(fotos), nova_contagem, u["id"])
                )

    repos = conn.execute("SELECT id, fotos_ids, contagem FROM repos").fetchall()
    for r in repos:
        fotos = json.loads(r["fotos_ids"] or "[]")
        if numero in fotos:
            fotos.remove(numero)
            nova_contagem = max(0, r["contagem"] - 1)
            if nova_contagem == 0:
                conn.execute("DELETE FROM repos WHERE id=?", (r["id"],))
            else:
                conn.execute(
                    "UPDATE repos SET fotos_ids=?, contagem=? WHERE id=?",
                    (json.dumps(fotos), nova_contagem, r["id"])
                )

    conn.execute("DELETE FROM fotos WHERE numero=?", (numero,))
    conn.commit()
    conn.close()


def atualizar_ocr(numero: str, ocr_texto: str):
    conn = get_conn()
    conn.execute("""
        UPDATE fotos SET ocr_texto=?, status='ocr_feito', processado_em=?
        WHERE numero=?
    """, (ocr_texto, datetime.now().isoformat(), numero))
    conn.commit()
    conn.close()


def atualizar_ocr_limpo(numero: str, ocr_limpo: str):
    conn = get_conn()
    conn.execute("""
        UPDATE fotos SET ocr_limpo=? WHERE numero=?
    """, (ocr_limpo, numero))
    conn.commit()
    conn.close()


def listar_fotos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM fotos ORDER BY numero").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_foto(numero: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM fotos WHERE numero=?", (numero,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- PALAVRAS ---

def atualizar_palavras(numero_foto: str, palavras: list):
    import json
    conn = get_conn()
    cur = conn.cursor()

    for palavra in palavras:
        palavra = palavra.lower().strip()
        if len(palavra) < 2:
            continue

        row = cur.execute(
            "SELECT id, contagem, fotos_ids FROM palavras WHERE palavra=?",
            (palavra,)
        ).fetchone()

        if row:
            fotos = json.loads(row["fotos_ids"])
            if numero_foto not in fotos:
                fotos.append(numero_foto)
            cur.execute("""
                UPDATE palavras SET contagem=?, fotos_ids=? WHERE palavra=?
            """, (row["contagem"] + 1, json.dumps(fotos), palavra))
        else:
            cur.execute("""
                INSERT INTO palavras (palavra, contagem, fotos_ids)
                VALUES (?, 1, ?)
            """, (palavra, json.dumps([numero_foto])))

    conn.commit()
    conn.close()


def top_palavras(limit: int = 100):
    conn = get_conn()
    rows = conn.execute("""
        SELECT palavra, contagem, fotos_ids
        FROM palavras
        ORDER BY contagem DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- GRUPOS ---

def listar_grupos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM grupos ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- USUARIOS (@mentions) ---

def atualizar_usuarios(numero_foto: str, usernames: list):
    import json
    conn = get_conn()
    cur = conn.cursor()

    for username in usernames:
        username = username.lower().strip()
        if len(username) < 2:
            continue

        row = cur.execute(
            "SELECT id, contagem, fotos_ids FROM usuarios WHERE username=?",
            (username,)
        ).fetchone()

        if row:
            fotos = json.loads(row["fotos_ids"])
            if numero_foto not in fotos:
                fotos.append(numero_foto)
            cur.execute(
                "UPDATE usuarios SET contagem=?, fotos_ids=? WHERE username=?",
                (row["contagem"] + 1, json.dumps(fotos), username)
            )
        else:
            cur.execute(
                "INSERT INTO usuarios (username, contagem, fotos_ids) VALUES (?, 1, ?)",
                (username, json.dumps([numero_foto]))
            )

    conn.commit()
    conn.close()


def top_usuarios(limit: int = 20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT username, contagem, fotos_ids
        FROM usuarios
        ORDER BY contagem DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def atualizar_repos(numero_foto: str, repos: list):
    import json
    conn = get_conn()
    cur = conn.cursor()

    for repo in repos:
        repo = repo.lower().strip()
        if len(repo) < 3:
            continue

        row = cur.execute(
            "SELECT id, contagem, fotos_ids FROM repos WHERE repo=?",
            (repo,)
        ).fetchone()

        if row:
            fotos = json.loads(row["fotos_ids"])
            if numero_foto not in fotos:
                fotos.append(numero_foto)
            cur.execute(
                "UPDATE repos SET contagem=?, fotos_ids=? WHERE repo=?",
                (row["contagem"] + 1, json.dumps(fotos), repo)
            )
        else:
            cur.execute(
                "INSERT INTO repos (repo, contagem, fotos_ids) VALUES (?, 1, ?)",
                (repo, json.dumps([numero_foto]))
            )

    conn.commit()
    conn.close()


def top_repos(limit: int = 20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT repo, contagem, fotos_ids
        FROM repos
        ORDER BY contagem DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- BLACKLIST ---

def adicionar_blacklist(texto: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO blacklist (texto) VALUES (?)",
            (texto.strip(),)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def listar_blacklist():
    conn = get_conn()
    rows = conn.execute("SELECT id, texto, criado_em FROM blacklist ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remover_blacklist(texto_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM blacklist WHERE id=?", (texto_id,))
        conn.commit()
    finally:
        conn.close()


def salvar_embedding(numero: str, modelo: str, vetor: list[float], dimensao: int):
    import json
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO embeddings (numero, modelo, vetor, dimensao, atualizado_em)
        VALUES (?, ?, ?, ?, ?)
    """, (numero, modelo, json.dumps(vetor), dimensao, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def listar_embeddings(modelo: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT numero, modelo, vetor, dimensao, atualizado_em
        FROM embeddings
        WHERE modelo=?
    """, (modelo,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
