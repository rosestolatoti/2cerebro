"""
Renomeia fotos com sequência e data e sincroniza o banco.
"""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
FOTOS_DIR = BASE_DIR / "fotos"
DB_PATH = BASE_DIR / "gigu_brain.db"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def extrair_data(nome: str, fallback_dt: datetime) -> str:
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


def renomear_fotos():
    arquivos = [f for f in FOTOS_DIR.iterdir() if f.suffix.lower() in EXTS]
    arquivos.sort(key=lambda p: p.name.lower())
    if not arquivos:
        raise SystemExit("Nenhuma foto encontrada")

    renomes = []
    for idx, f in enumerate(arquivos, start=1):
        dt = datetime.fromtimestamp(f.stat().st_mtime)
        data_tag = extrair_data(f.name, dt)
        ext = f.suffix.lower()
        novo_nome = f"{idx:03d}_{data_tag}{ext}"
        tmp_nome = f"__tmp__{idx:03d}_{f.name}"
        tmp_path = f.with_name(tmp_nome)
        f.rename(tmp_path)
        renomes.append((tmp_path, f.name, novo_nome))

    final_paths = []
    for tmp_path, old_name, new_name in renomes:
        new_path = tmp_path.with_name(new_name)
        tmp_path.rename(new_path)
        final_paths.append((old_name, new_name, new_path))

    return final_paths


def atualizar_banco(final_paths):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM fotos").fetchall()
    rows_by_filename = {r["filename"]: r for r in rows}
    rows_by_filepath = {r["filepath"]: r for r in rows}

    updates = []
    map_numero = {}
    filepaths_set = {str(p) for _, _, p in final_paths}
    numeros_set = {n.split("_")[0] for _, n, _ in final_paths}

    for old_name, new_name, new_path in final_paths:
        row = rows_by_filename.get(old_name) or rows_by_filepath.get(str(FOTOS_DIR / old_name))
        new_num = new_name.split("_")[0]
        if row:
            old_num = row["numero"]
            updates.append((row["id"], new_num, new_name, str(new_path)))
            map_numero[old_num] = new_num
        else:
            agora = datetime.now().isoformat()
            data_captura = datetime.now().strftime("%Y-%m-%d")
            semana = datetime.now().strftime("%Y-W%W")
            mes = datetime.now().strftime("%Y-%m")
            cur.execute(
                "INSERT OR IGNORE INTO fotos (numero, filename, filepath, criado_em, data_captura, semana, mes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_num, new_name, str(new_path), agora, data_captura, semana, mes)
            )

    for row_id, new_num, new_name, new_path in updates:
        cur.execute(
            "UPDATE fotos SET numero=?, filename=?, filepath=? WHERE id=?",
            (f"TMP_{row_id}", new_name, new_path, row_id)
        )
    for row_id, new_num, _, _ in updates:
        cur.execute("UPDATE fotos SET numero=? WHERE id=?", (new_num, row_id))

    rows = cur.execute("SELECT id, numero, filepath FROM fotos").fetchall()
    removidos = [r["numero"] for r in rows if r["filepath"] not in filepaths_set]
    for n in removidos:
        cur.execute("DELETE FROM fotos WHERE numero=?", (n,))

    def atualizar_lista(tabela):
        rows = cur.execute(f"SELECT id, fotos_ids FROM {tabela}").fetchall()
        for r in rows:
            fotos = json.loads(r["fotos_ids"] or "[]")
            novos = []
            for num in fotos:
                if num in map_numero:
                    novos.append(map_numero[num])
                elif num in numeros_set:
                    novos.append(num)
            novos = list(dict.fromkeys(novos))
            if not novos:
                cur.execute(f"DELETE FROM {tabela} WHERE id=?", (r["id"],))
            else:
                cur.execute(
                    f"UPDATE {tabela} SET fotos_ids=?, contagem=? WHERE id=?",
                    (json.dumps(novos), len(novos), r["id"])
                )

    atualizar_lista("palavras")
    atualizar_lista("usuarios")

    tabela = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
    ).fetchone()
    if tabela:
        emb_rows = cur.execute("SELECT id, numero FROM embeddings").fetchall()
        for r in emb_rows:
            if r["numero"] in map_numero:
                cur.execute("UPDATE embeddings SET numero=? WHERE id=?", (f"TMP_{r['id']}", r["id"]))
        for r in emb_rows:
            if r["numero"] in map_numero:
                cur.execute("UPDATE embeddings SET numero=? WHERE id=?", (map_numero[r["numero"]], r["id"]))
        emb_rows = cur.execute("SELECT id, numero FROM embeddings").fetchall()
        for r in emb_rows:
            if r["numero"] not in numeros_set:
                cur.execute("DELETE FROM embeddings WHERE id=?", (r["id"],))

    conn.commit()
    conn.close()
    return len(final_paths), len(removidos)


def main():
    final_paths = renomear_fotos()
    total, removidos = atualizar_banco(final_paths)
    print(f"Renomeadas: {total} | Removidas do DB: {removidos}")


if __name__ == "__main__":
    main()
