"""
GigU Brain — Flask Server
API e servidor principal
"""

from flask import Flask, jsonify, render_template, request, send_from_directory
from pathlib import Path
from config import SYNC_INTERVAL
from database import (
    adicionar_blacklist,
    atualizar_ocr,
    atualizar_ocr_limpo,
    atualizar_palavras,
    atualizar_repos,
    atualizar_usuarios,
    buscar_foto,
    deletar_foto_db,
    get_conn,
    init_db,
    listar_blacklist,
    listar_embeddings,
    listar_fotos,
    listar_grupos,
    remover_blacklist,
    salvar_embedding,
    top_palavras,
    top_repos,
    top_usuarios,
)
from file_manager import registrar_fotos_existentes, salvar_upload, sincronizar_pasta_fotos
from ocr_engine import extrair_repos_github, extrair_usernames, processar_imagem
from embeddings import construir_clusters, construir_grafo, gerar_embeddings, similaridades, termos_por_cluster
from datetime import datetime
from threading import Thread
import time
import json
import urllib.error
import urllib.request

app = Flask(__name__)
init_db()
registrar_fotos_existentes()
sincronizar_pasta_fotos()


def _loop_sync():
    while True:
        try:
            sincronizar_pasta_fotos()
        except Exception as exc:
            print(exc)
        time.sleep(SYNC_INTERVAL)


Thread(target=_loop_sync, daemon=True).start()


# ─── PÁGINAS ────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── FOTOS ──────────────────────────────────────────────

@app.route("/api/fotos", methods=["GET"])
def api_fotos():
    sincronizar_pasta_fotos()
    fotos = listar_fotos()
    return jsonify(fotos)


@app.route("/api/foto/<numero>", methods=["GET"])
def api_foto(numero):
    foto = buscar_foto(numero)
    if not foto:
        return jsonify({"erro": "Foto não encontrada"}), 404
    return jsonify(foto)


@app.route("/api/foto/imagem/<numero>")
def api_imagem(numero):
    foto = buscar_foto(numero)
    if not foto:
        return jsonify({"erro": "Não encontrada"}), 404
    path = Path(foto["filepath"])
    return send_from_directory(path.parent, path.name)


# ─── UPLOAD ─────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("fotos")
    if not files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    if len(files) > 5:
        return jsonify({"erro": "Máximo 5 fotos por vez"}), 400

    resultados = []
    for file in files:
        resultado = salvar_upload(file.read(), file.filename)
        resultados.append(resultado)

    return jsonify({"resultados": resultados})


# ─── OCR ────────────────────────────────────────────────

@app.route("/api/ocr/<numero>", methods=["POST"])
def api_ocr(numero):
    foto = buscar_foto(numero)
    if not foto:
        return jsonify({"erro": "Foto não encontrada"}), 404

    resultado = processar_imagem(foto["filepath"], numero, foto["filename"])

    if resultado["sucesso"]:
        atualizar_ocr(numero, resultado["texto_bruto"])
        atualizar_ocr_limpo(numero, resultado["texto_limpo"])
        atualizar_palavras(numero, resultado["palavras"])
        usernames = extrair_usernames(resultado["texto_limpo"])
        if usernames:
            atualizar_usuarios(numero, usernames)
        repos = extrair_repos_github(resultado["texto_limpo"])
        if repos:
            atualizar_repos(numero, repos)

    return jsonify(resultado)


@app.route("/api/ocr/<numero>/salvar", methods=["POST"])
def api_salvar_ocr(numero):
    data = request.get_json()
    texto = data.get("texto", "")

    usernames = extrair_usernames(texto)
    if usernames:
        atualizar_usuarios(numero, usernames)
    repos = extrair_repos_github(texto)
    if repos:
        atualizar_repos(numero, repos)

    atualizar_ocr_limpo(numero, texto)
    return jsonify({"sucesso": True})


# ─── PALAVRAS ───────────────────────────────────────────

@app.route("/api/palavras", methods=["GET"])
def api_palavras():
    limit = request.args.get("limit", 100, type=int)
    palavras = top_palavras(limit)
    return jsonify(palavras)


@app.route("/api/grupos", methods=["GET"])
def api_grupos():
    grupos = listar_grupos()
    return jsonify(grupos)


@app.route("/api/buscar", methods=["GET"])
def api_buscar():
    termo = request.args.get("q", "").strip()
    if not termo or len(termo) < 2:
        return jsonify([])
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM fotos
        WHERE ocr_limpo LIKE ? OR ocr_texto LIKE ?
        ORDER BY numero
    """, (f"%{termo}%", f"%{termo}%")).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/foto/<numero>", methods=["DELETE"])
def api_deletar_foto(numero):
    foto = buscar_foto(numero)
    if not foto:
        return jsonify({"erro": "Não encontrada"}), 404
    try:
        Path(foto["filepath"]).unlink(missing_ok=True)
    except Exception:
        pass
    deletar_foto_db(numero)
    return jsonify({"sucesso": True})


# --- OCR COMPARACAO ---

@app.route("/api/ocr/<numero>/comparar", methods=["POST"])
def api_comparar_ocr(numero):
    foto = buscar_foto(numero)
    if not foto:
        return jsonify({"erro": "Foto não encontrada"}), 404
    return jsonify({"erro": "Comparação PaddleOCR desativada"}), 400


@app.route("/api/ocr/<numero>/salvar-motor", methods=["POST"])
def api_salvar_motor(numero):
    from ocr_engine import extrair_palavras

    dados = request.json
    motor = dados.get("motor")
    texto = dados.get("texto", "")

    palavras = extrair_palavras(texto)

    atualizar_ocr_limpo(numero, texto)
    atualizar_palavras(numero, palavras)

    conn = get_conn()
    try:
        conn.execute(
            "UPDATE fotos SET motor_ocr=?, status='ocr_feito', processado_em=? WHERE numero=?",
            (motor, datetime.now().isoformat(), numero)
        )
        conn.commit()
    except Exception as exc:
        print(exc)
    conn.close()

    return jsonify({"sucesso": True, "palavras": len(palavras), "motor": motor})


# --- TIMELINE ---

@app.route("/api/fotos/por-semana", methods=["GET"])
def api_fotos_por_semana():
    conn = get_conn()
    rows = conn.execute("""
        SELECT semana, COUNT(*) as total,
               SUM(CASE WHEN status='ocr_feito' THEN 1 ELSE 0 END) as processadas
        FROM fotos
        GROUP BY semana
        ORDER BY semana DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/fotos/por-mes", methods=["GET"])
def api_fotos_por_mes():
    conn = get_conn()
    rows = conn.execute("""
        SELECT mes, COUNT(*) as total,
               SUM(CASE WHEN status='ocr_feito' THEN 1 ELSE 0 END) as processadas
        FROM fotos
        GROUP BY mes
        ORDER BY mes DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/palavras/por-semana", methods=["GET"])
def api_palavras_por_semana():
    semana = request.args.get("semana", "")
    conn = get_conn()

    if not semana:
        conn.close()
        return jsonify({"erro": "Informe ?semana=2026-W08"})

    fotos_semana = conn.execute(
        "SELECT numero FROM fotos WHERE semana=?", (semana,)
    ).fetchall()
    numeros = [str(f["numero"]) for f in fotos_semana]

    if not numeros:
        conn.close()
        return jsonify([])

    todas_palavras = conn.execute(
        "SELECT palavra, contagem, fotos_ids FROM palavras ORDER BY contagem DESC"
    ).fetchall()

    resultado = []
    for p in todas_palavras:
        fotos_ids = json.loads(p["fotos_ids"] or "[]")
        intersecao = [f for f in fotos_ids if f in numeros]
        if intersecao:
            resultado.append({
                "palavra": p["palavra"],
                "contagem_semana": len(intersecao),
                "fotos": intersecao
            })

    resultado.sort(key=lambda x: x["contagem_semana"], reverse=True)
    conn.close()
    return jsonify(resultado[:50])


# --- USUARIOS (@mentions) ---

@app.route("/api/usuarios", methods=["GET"])
def api_usuarios():
    limit = request.args.get("limit", 20, type=int)
    usuarios = top_usuarios(limit)
    return jsonify(usuarios)


@app.route("/api/repos", methods=["GET"])
def api_repos():
    limit = request.args.get("limit", 20, type=int)
    repos = top_repos(limit)
    return jsonify(repos)


def _trecho(texto: str, termo: str, max_len: int = 240) -> str:
    if not texto:
        return ""
    texto = texto.replace("\n", " ").strip()
    termo = termo.strip()
    if not termo:
        return texto[:max_len]
    idx = texto.lower().find(termo.lower())
    if idx == -1:
        return texto[:max_len]
    inicio = max(0, idx - int(max_len * 0.35))
    fim = min(len(texto), inicio + max_len)
    return texto[inicio:fim].strip()


def _contar_ocorrencias(texto: str, termo: str) -> int:
    if not texto or not termo:
        return 0
    return texto.lower().count(termo.lower())


def _intersecao_ids(fotos_ids: list, numeros_set: set[str]) -> list:
    return [f for f in fotos_ids if f in numeros_set]


def _carregar_dossie(termo: str) -> dict:
    termo = termo.strip()
    conn = get_conn()
    like = f"%{termo}%"
    rows = conn.execute("""
        SELECT numero, filename, ocr_limpo, ocr_texto, semana, mes, motor_ocr
        FROM fotos
        WHERE ocr_limpo LIKE ? OR ocr_texto LIKE ?
        ORDER BY numero
    """, (like, like)).fetchall()

    fotos = []
    numeros = []
    anchors = []
    timeline_semana = {}
    timeline_mes = {}

    for r in rows:
        texto = r["ocr_limpo"] or r["ocr_texto"] or ""
        numero = str(r["numero"])
        numeros.append(numero)
        fotos.append({
            "numero": numero,
            "filename": r["filename"],
            "semana": r["semana"],
            "mes": r["mes"],
            "motor_ocr": r["motor_ocr"],
            "trecho": _trecho(texto, termo),
            "tamanho": len(texto),
        })
        ocorrencias = _contar_ocorrencias(texto, termo)
        score = (ocorrencias * 2) + (len(texto) / 120)
        anchors.append({
            "numero": numero,
            "score": round(score, 2),
            "filename": r["filename"],
            "ocorrencias": ocorrencias,
        })
        if r["semana"]:
            timeline_semana[r["semana"]] = timeline_semana.get(r["semana"], 0) + 1
        if r["mes"]:
            timeline_mes[r["mes"]] = timeline_mes.get(r["mes"], 0) + 1

    numeros_set = set(numeros)
    termo_lower = termo.lower()

    palavras_rows = conn.execute(
        "SELECT palavra, fotos_ids FROM palavras ORDER BY contagem DESC"
    ).fetchall()
    coocorrencias = []
    for p in palavras_rows:
        palavra = p["palavra"]
        if palavra == termo_lower:
            continue
        fotos_ids = json.loads(p["fotos_ids"] or "[]")
        intersecao = _intersecao_ids(fotos_ids, numeros_set)
        if intersecao:
            coocorrencias.append({
                "palavra": palavra,
                "contagem": len(intersecao),
                "fotos": intersecao[:30],
            })
    coocorrencias.sort(key=lambda x: x["contagem"], reverse=True)

    usuarios_rows = conn.execute(
        "SELECT username, fotos_ids FROM usuarios ORDER BY contagem DESC"
    ).fetchall()
    usuarios = []
    for u in usuarios_rows:
        fotos_ids = json.loads(u["fotos_ids"] or "[]")
        intersecao = _intersecao_ids(fotos_ids, numeros_set)
        if intersecao:
            usuarios.append({
                "username": u["username"],
                "contagem": len(intersecao),
                "fotos": intersecao[:30],
            })
    usuarios.sort(key=lambda x: x["contagem"], reverse=True)

    repos_rows = conn.execute(
        "SELECT repo, fotos_ids FROM repos ORDER BY contagem DESC"
    ).fetchall()
    repos = []
    for r in repos_rows:
        fotos_ids = json.loads(r["fotos_ids"] or "[]")
        intersecao = _intersecao_ids(fotos_ids, numeros_set)
        if intersecao:
            repos.append({
                "repo": r["repo"],
                "contagem": len(intersecao),
                "fotos": intersecao[:30],
            })
    repos.sort(key=lambda x: x["contagem"], reverse=True)

    conn.close()

    anchors.sort(key=lambda x: (x["ocorrencias"], x["score"]), reverse=True)
    timeline_semana_lista = [
        {"semana": s, "total": timeline_semana[s]}
        for s in sorted(timeline_semana.keys(), reverse=True)
    ]
    timeline_mes_lista = [
        {"mes": m, "total": timeline_mes[m]}
        for m in sorted(timeline_mes.keys(), reverse=True)
    ]

    return {
        "termo": termo,
        "total_fotos": len(fotos),
        "fotos": fotos[:200],
        "coocorrencias": coocorrencias[:30],
        "usuarios": usuarios[:20],
        "repos": repos[:20],
        "anchors": anchors[:5],
        "timeline": {
            "por_semana": timeline_semana_lista,
            "por_mes": timeline_mes_lista,
        },
    }


def _http_post_json(url: str, headers: dict, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return {"_erro": f"HTTP {exc.code}", "_raw": body}
    except urllib.error.URLError as exc:
        return {"_erro": str(exc.reason)}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_erro": "Resposta inválida", "_raw": body}


def _montar_prompt_dossie(dados: dict) -> tuple[str, str]:
    sistema = (
        "Você é um analista sênior de dados de OCR. Responda em português. "
        "Use bullets claros, destaque padrões, anomalias, hipóteses e próximos passos. "
        "Não invente fatos além dos dados."
    )
    dados_json = json.dumps(dados, ensure_ascii=False)
    prompt = (
        "Analise o dossiê a seguir e gere insights úteis para produto e pesquisa.\n"
        "Estruture a resposta com:\n"
        "1) Resumo em 3 bullets\n"
        "2) Padrões e coocorrências mais relevantes\n"
        "3) Usuários e repositórios que parecem centrais\n"
        "4) Linha do tempo e mudanças\n"
        "5) Ações recomendadas\n\n"
        f"DADOS:\n{dados_json}"
    )
    return sistema, prompt


def _chamar_llm(provider: str, model: str, api_key: str, base_url: str, dados: dict) -> dict:
    sistema, prompt = _montar_prompt_dossie(dados)
    provider = provider.lower()
    if provider == "ollama":
        url = (base_url or "http://localhost:11434").rstrip("/") + "/api/generate"
        payload = {"model": model, "prompt": f"{sistema}\n\n{prompt}", "stream": False}
        resp = _http_post_json(url, {"Content-Type": "application/json"}, payload)
        if resp.get("_erro"):
            return resp
        return {"texto": resp.get("response", "")}

    if provider == "gemini":
        url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{url}/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": f"{sistema}\n\n{prompt}"}]}]
        }
        resp = _http_post_json(
            url,
            {"Content-Type": "application/json", "x-goog-api-key": api_key},
            payload,
        )
        if resp.get("_erro"):
            return resp
        candidates = resp.get("candidates", [])
        if not candidates:
            return {"_erro": "Sem resposta do modelo", "_raw": json.dumps(resp, ensure_ascii=False)}
        parts = candidates[0].get("content", {}).get("parts", [])
        texto = parts[0].get("text", "") if parts else ""
        return {"texto": texto}

    if provider in {"groq", "mistral", "glm", "custom"}:
        if provider == "groq":
            base = base_url or "https://api.groq.com/openai/v1"
        elif provider == "mistral":
            base = base_url or "https://api.mistral.ai/v1"
        elif provider == "glm":
            base = base_url or "https://open.bigmodel.cn/api/paas/v4"
        else:
            base = base_url
        if not base:
            return {"_erro": "Base URL não informada"}
        url = base.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        resp = _http_post_json(
            url,
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            payload,
        )
        if resp.get("_erro"):
            return resp
        choices = resp.get("choices", [])
        texto = choices[0].get("message", {}).get("content", "") if choices else ""
        return {"texto": texto}

    return {"_erro": "Provider inválido"}


@app.route("/api/insights/dossie", methods=["GET"])
def api_insights_dossie():
    termo = request.args.get("termo", "").strip()
    if len(termo) < 2:
        return jsonify({"erro": "Informe um termo com 2+ caracteres"}), 400
    dados = _carregar_dossie(termo)
    return jsonify(dados)


@app.route("/api/llm/analisar", methods=["POST"])
def api_llm_analisar():
    data = request.get_json() or {}
    termo = data.get("termo", "").strip()
    provider = data.get("provider", "").strip().lower()
    model = data.get("model", "").strip()
    api_key = data.get("api_key", "").strip()
    base_url = data.get("base_url", "").strip()

    if len(termo) < 2:
        return jsonify({"sucesso": False, "erro": "Informe um termo com 2+ caracteres"}), 400
    if provider not in {"ollama", "gemini", "groq", "mistral", "glm", "custom"}:
        return jsonify({"sucesso": False, "erro": "Provider inválido"}), 400
    if provider != "ollama" and not api_key:
        return jsonify({"sucesso": False, "erro": "API key obrigatória"}), 400
    if not model:
        return jsonify({"sucesso": False, "erro": "Informe o modelo"}), 400

    dados = _carregar_dossie(termo)
    resposta = _chamar_llm(provider, model, api_key, base_url, dados)
    if resposta.get("_erro"):
        return jsonify({"sucesso": False, "erro": resposta.get("_erro"), "raw": resposta.get("_raw", "")}), 500
    return jsonify({"sucesso": True, "texto": resposta.get("texto", ""), "termo": termo})


# --- BLACKLIST ---

@app.route("/api/blacklist", methods=["GET"])
def api_blacklist():
    blacklist = listar_blacklist()
    return jsonify(blacklist)


@app.route("/api/blacklist", methods=["POST"])
def api_blacklist_add():
    data = request.get_json() or {}
    textos = data.get("textos")
    if textos is None:
        texto = data.get("texto", "")
        textos = [texto] if texto else []
    elif isinstance(textos, str):
        textos = [textos]

    for texto in textos:
        if texto and texto.strip():
            adicionar_blacklist(texto.strip())

    blacklist = listar_blacklist()
    return jsonify({"sucesso": True, "blacklist": blacklist})


@app.route("/api/blacklist/<int:texto_id>", methods=["DELETE"])
def api_blacklist_remove(texto_id):
    remover_blacklist(texto_id)
    return jsonify({"sucesso": True})


def _fotos_com_texto(semana: str | None = None):
    conn = get_conn()
    if semana:
        rows = conn.execute("""
            SELECT numero, filename, ocr_limpo, semana
            FROM fotos
            WHERE ocr_limpo IS NOT NULL AND ocr_limpo != '' AND semana=?
        """, (semana,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT numero, filename, ocr_limpo, semana
            FROM fotos
            WHERE ocr_limpo IS NOT NULL AND ocr_limpo != ''
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _rebuild_embeddings(fotos: list[dict]):
    resultado = gerar_embeddings(fotos)
    if not resultado.get("sucesso"):
        return resultado
    modelo = "tfidf_svd_v1"
    dimensao = resultado.get("dimensao", 0)
    for numero, vetor in resultado["vetores"].items():
        salvar_embedding(numero, modelo, vetor, dimensao)
    return resultado


@app.route("/api/embeddings/rebuild", methods=["POST"])
def api_embeddings_rebuild():
    fotos = _fotos_com_texto()
    if len(fotos) < 2:
        return jsonify({"sucesso": False, "erro": "Dados insuficientes"}), 400
    resultado = _rebuild_embeddings(fotos)
    if not resultado.get("sucesso"):
        return jsonify(resultado), 500
    return jsonify({"sucesso": True, "total": len(fotos), "dimensao": resultado.get("dimensao", 0)})


@app.route("/api/fotos/<numero>/similares", methods=["GET"])
def api_fotos_similares(numero):
    limit = request.args.get("limit", 6, type=int)
    modelo = "tfidf_svd_v1"
    registros = listar_embeddings(modelo)
    if not registros:
        fotos = _fotos_com_texto()
        if len(fotos) < 2:
            return jsonify([])
        resultado = _rebuild_embeddings(fotos)
        if not resultado.get("sucesso"):
            return jsonify([])
        registros = listar_embeddings(modelo)

    vetores = {r["numero"]: json.loads(r["vetor"]) for r in registros}
    sims = similaridades(vetores, numero)[:limit]
    if not sims:
        return jsonify([])

    numeros = [n for n, _ in sims]
    conn = get_conn()
    rows = conn.execute(
        f"SELECT numero, filename FROM fotos WHERE numero IN ({','.join(['?']*len(numeros))})",
        tuple(numeros)
    ).fetchall()
    conn.close()
    mapa = {r["numero"]: r["filename"] for r in rows}
    resultado = [{"numero": n, "score": s, "filename": mapa.get(n)} for n, s in sims]
    return jsonify(resultado)


@app.route("/api/clusters/semana", methods=["GET"])
def api_clusters_semana():
    semana = request.args.get("semana")
    if not semana:
        conn = get_conn()
        row = conn.execute("""
            SELECT semana FROM fotos
            WHERE semana IS NOT NULL AND semana != ''
            ORDER BY semana DESC
            LIMIT 1
        """).fetchone()
        conn.close()
        semana = row["semana"] if row else None

    fotos = _fotos_com_texto(semana) if semana else _fotos_com_texto()
    if len(fotos) < 2:
        return jsonify({"semana": semana, "clusters": []})

    resultado = gerar_embeddings(fotos)
    if not resultado.get("sucesso"):
        return jsonify({"semana": semana, "clusters": []})

    vetores = resultado["vetores"]
    cluster_map = construir_clusters(vetores)
    termos = termos_por_cluster(fotos, resultado["tokens"], cluster_map)
    clusters = {}
    for f in fotos:
        cid = cluster_map.get(f["numero"], -1)
        if cid not in clusters:
            clusters[cid] = {"id": cid, "total": 0, "fotos": [], "termos": termos.get(cid, [])}
        clusters[cid]["total"] += 1
        clusters[cid]["fotos"].append(f["numero"])

    lista = sorted(clusters.values(), key=lambda c: c["total"], reverse=True)
    return jsonify({"semana": semana, "clusters": lista})


@app.route("/api/grafo", methods=["GET"])
def api_grafo():
    fotos = _fotos_com_texto()
    if len(fotos) < 2:
        return jsonify({"nodes": [], "links": []})
    resultado = gerar_embeddings(fotos)
    if not resultado.get("sucesso"):
        return jsonify({"nodes": [], "links": []})
    vetores = resultado["vetores"]
    cluster_map = construir_clusters(vetores)
    grafo = construir_grafo(vetores)
    nodes = []
    for f in fotos:
        nodes.append({
            "id": f["numero"],
            "cluster": cluster_map.get(f["numero"], 0),
            "label": f["filename"],
            "imagem": f"/api/foto/imagem/{f['numero']}"
        })
    return jsonify({"nodes": nodes, "links": grafo["links"]})


# ─── START ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
