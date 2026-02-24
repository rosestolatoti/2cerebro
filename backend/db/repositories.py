"""
2 Cerebro — Repositories (CRUD async puro)
Sem logica de negocio — apenas acesso ao banco.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from backend.db.database import get_db


# ─── Fotos ───────────────────────────────────────────────────────────────────


async def registrar_foto(
    numero: str,
    filename: str,
    filepath: str,
    hash_md5: Optional[str] = None,
    data_captura: Optional[str] = None,
) -> int:
    agora = datetime.now()
    dc = data_captura or agora.strftime("%Y-%m-%d")
    semana = agora.strftime("%Y-W%W")
    mes = agora.strftime("%Y-%m")
    async with get_db() as conn:
        cur = await conn.execute(
            """
            INSERT OR IGNORE INTO fotos
              (numero, filename, filepath, hash_md5, criado_em, data_captura, semana, mes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (numero, filename, filepath, hash_md5, agora.isoformat(), dc, semana, mes),
        )
        await conn.commit()
        return cur.lastrowid or 0


async def foto_existe(filepath: str) -> bool:
    async with get_db() as conn:
        cur = await conn.execute("SELECT id FROM fotos WHERE filepath=?", (filepath,))
        return await cur.fetchone() is not None


async def hash_existe(hash_md5: str) -> Optional[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT numero, filename FROM fotos WHERE hash_md5=?", (hash_md5,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def buscar_foto(numero: str) -> Optional[dict]:
    async with get_db() as conn:
        cur = await conn.execute("SELECT * FROM fotos WHERE numero=?", (numero,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def listar_fotos(limit: int = 500, offset: int = 0) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT * FROM fotos ORDER BY numero LIMIT ? OFFSET ?", (limit, offset)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def contar_fotos() -> int:
    async with get_db() as conn:
        cur = await conn.execute("SELECT COUNT(*) as n FROM fotos")
        row = await cur.fetchone()
        return row["n"] if row else 0


async def contar_fotos_com_ocr() -> int:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) as n FROM fotos WHERE ocr_limpo IS NOT NULL AND ocr_limpo != ''"
        )
        row = await cur.fetchone()
        return row["n"] if row else 0


async def atualizar_ocr(numero: str, ocr_texto: str, ocr_limpo: str) -> None:
    async with get_db() as conn:
        await conn.execute(
            """
            UPDATE fotos
            SET ocr_texto=?, ocr_limpo=?, status='ocr_feito', processado_em=?
            WHERE numero=?
            """,
            (ocr_texto, ocr_limpo, datetime.now().isoformat(), numero),
        )
        await conn.commit()


async def atualizar_classificacao(
    numero: str,
    fonte: str,
    tema: str,
    tipo: str,
    sentimento: str,
    entidades: list,
    resumo: str,
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """
            UPDATE fotos
            SET fonte=?, tema=?, tipo=?, sentimento=?, entidades=?, resumo=?, classificado=1
            WHERE numero=?
            """,
            (fonte, tema, tipo, sentimento, json.dumps(entidades), resumo, numero),
        )
        await conn.commit()


async def deletar_foto(numero: str) -> None:
    async with get_db() as conn:
        # limpar referencias em palavras
        cur = await conn.execute("SELECT id, fotos_ids, contagem FROM palavras")
        for p in await cur.fetchall():
            fotos = json.loads(p["fotos_ids"] or "[]")
            if numero in fotos:
                fotos.remove(numero)
                nc = max(0, p["contagem"] - 1)
                if nc == 0:
                    await conn.execute("DELETE FROM palavras WHERE id=?", (p["id"],))
                else:
                    await conn.execute(
                        "UPDATE palavras SET fotos_ids=?, contagem=? WHERE id=?",
                        (json.dumps(fotos), nc, p["id"]),
                    )
        # usuarios
        cur = await conn.execute("SELECT id, fotos_ids, contagem FROM usuarios")
        for u in await cur.fetchall():
            fotos = json.loads(u["fotos_ids"] or "[]")
            if numero in fotos:
                fotos.remove(numero)
                nc = max(0, u["contagem"] - 1)
                if nc == 0:
                    await conn.execute("DELETE FROM usuarios WHERE id=?", (u["id"],))
                else:
                    await conn.execute(
                        "UPDATE usuarios SET fotos_ids=?, contagem=? WHERE id=?",
                        (json.dumps(fotos), nc, u["id"]),
                    )
        # repos
        cur = await conn.execute("SELECT id, fotos_ids, contagem FROM repos")
        for r in await cur.fetchall():
            fotos = json.loads(r["fotos_ids"] or "[]")
            if numero in fotos:
                fotos.remove(numero)
                nc = max(0, r["contagem"] - 1)
                if nc == 0:
                    await conn.execute("DELETE FROM repos WHERE id=?", (r["id"],))
                else:
                    await conn.execute(
                        "UPDATE repos SET fotos_ids=?, contagem=? WHERE id=?",
                        (json.dumps(fotos), nc, r["id"]),
                    )
        await conn.execute("DELETE FROM fotos WHERE numero=?", (numero,))
        await conn.execute("DELETE FROM embeddings WHERE numero=?", (numero,))
        await conn.commit()


async def fotos_por_semana() -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT semana, COUNT(*) as total FROM fotos WHERE semana IS NOT NULL GROUP BY semana ORDER BY semana DESC LIMIT 20"
        )
        return [dict(r) for r in await cur.fetchall()]


async def fotos_por_mes() -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT mes, COUNT(*) as total FROM fotos WHERE mes IS NOT NULL GROUP BY mes ORDER BY mes DESC LIMIT 12"
        )
        return [dict(r) for r in await cur.fetchall()]


async def busca_textual(query: str, limit: int = 20) -> list[dict]:
    """Busca LIKE no ocr_limpo — O(n), aceita para volumes pequenos."""
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT * FROM fotos WHERE ocr_limpo LIKE ? ORDER BY numero DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        return [dict(r) for r in await cur.fetchall()]


# ─── Palavras ─────────────────────────────────────────────────────────────────


async def atualizar_palavras(numero_foto: str, palavras: list[str]) -> None:
    async with get_db() as conn:
        for palavra in palavras:
            palavra = palavra.lower().strip()
            if len(palavra) < 2:
                continue
            cur = await conn.execute(
                "SELECT id, contagem, fotos_ids FROM palavras WHERE palavra=?",
                (palavra,),
            )
            row = await cur.fetchone()
            if row:
                fotos = json.loads(row["fotos_ids"])
                if numero_foto not in fotos:
                    fotos.append(numero_foto)
                await conn.execute(
                    "UPDATE palavras SET contagem=?, fotos_ids=? WHERE palavra=?",
                    (row["contagem"] + 1, json.dumps(fotos), palavra),
                )
            else:
                await conn.execute(
                    "INSERT INTO palavras (palavra, contagem, fotos_ids) VALUES (?, 1, ?)",
                    (palavra, json.dumps([numero_foto])),
                )
        await conn.commit()


async def top_palavras(limit: int = 100) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT palavra, contagem, fotos_ids FROM palavras ORDER BY contagem DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]


# ─── Usuarios ─────────────────────────────────────────────────────────────────


async def atualizar_usuarios(numero_foto: str, usernames: list[str]) -> None:
    async with get_db() as conn:
        for username in usernames:
            username = username.lower().strip()
            if len(username) < 2:
                continue
            cur = await conn.execute(
                "SELECT id, contagem, fotos_ids FROM usuarios WHERE username=?",
                (username,),
            )
            row = await cur.fetchone()
            if row:
                fotos = json.loads(row["fotos_ids"])
                if numero_foto not in fotos:
                    fotos.append(numero_foto)
                await conn.execute(
                    "UPDATE usuarios SET contagem=?, fotos_ids=? WHERE username=?",
                    (row["contagem"] + 1, json.dumps(fotos), username),
                )
            else:
                await conn.execute(
                    "INSERT INTO usuarios (username, contagem, fotos_ids) VALUES (?, 1, ?)",
                    (username, json.dumps([numero_foto])),
                )
        await conn.commit()


async def top_usuarios(limit: int = 20) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT username, contagem, fotos_ids FROM usuarios ORDER BY contagem DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]


# ─── Repos ────────────────────────────────────────────────────────────────────


async def atualizar_repos(numero_foto: str, repos: list[str]) -> None:
    async with get_db() as conn:
        for repo in repos:
            repo = repo.lower().strip()
            if len(repo) < 3:
                continue
            cur = await conn.execute(
                "SELECT id, contagem, fotos_ids FROM repos WHERE repo=?", (repo,)
            )
            row = await cur.fetchone()
            if row:
                fotos = json.loads(row["fotos_ids"])
                if numero_foto not in fotos:
                    fotos.append(numero_foto)
                await conn.execute(
                    "UPDATE repos SET contagem=?, fotos_ids=? WHERE repo=?",
                    (row["contagem"] + 1, json.dumps(fotos), repo),
                )
            else:
                await conn.execute(
                    "INSERT INTO repos (repo, contagem, fotos_ids) VALUES (?, 1, ?)",
                    (repo, json.dumps([numero_foto])),
                )
        await conn.commit()


async def top_repos(limit: int = 20) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT repo, contagem, fotos_ids FROM repos ORDER BY contagem DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]


# ─── Embeddings ───────────────────────────────────────────────────────────────


async def salvar_embedding(
    numero: str, modelo: str, vetor: list[float], dimensao: int
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO embeddings (numero, modelo, vetor, dimensao, atualizado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (numero, modelo, json.dumps(vetor), dimensao, datetime.now().isoformat()),
        )
        await conn.commit()


async def listar_embeddings(modelo: str) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT numero, modelo, vetor, dimensao, atualizado_em FROM embeddings WHERE modelo=?",
            (modelo,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def contar_embeddings() -> int:
    async with get_db() as conn:
        cur = await conn.execute("SELECT COUNT(*) as n FROM embeddings")
        row = await cur.fetchone()
        return row["n"] if row else 0


# ─── Grupos ───────────────────────────────────────────────────────────────────


async def listar_grupos() -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute("SELECT * FROM grupos ORDER BY nome")
        return [dict(r) for r in await cur.fetchall()]


# ─── Blacklist ────────────────────────────────────────────────────────────────


async def adicionar_blacklist(texto: str) -> None:
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO blacklist (texto) VALUES (?)", (texto.strip(),)
        )
        await conn.commit()


async def listar_blacklist() -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT id, texto, criado_em FROM blacklist ORDER BY id DESC"
        )
        return [dict(r) for r in await cur.fetchall()]
