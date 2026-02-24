"""
2 Cerebro — LLM Service
Ollama (local) -> Groq -> Gemini. Fallback automatico.
"""

from __future__ import annotations
import json
from typing import Optional

import httpx

from backend.config import settings
from backend.utils.logger import get_logger

log = get_logger(__name__)

_TIMEOUT = 60.0
_TIMEOUT_CLASSIF = 30.0


# ─── Ollama ───────────────────────────────────────────────────────────────────


async def _ollama(
    prompt: str, model: Optional[str] = None, timeout: float = _TIMEOUT
) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": model or settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_thread": settings.ollama_num_thread},
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except Exception as e:
        log.warning("Ollama indisponivel", extra={"erro": str(e)})
        return None


# ─── Groq ─────────────────────────────────────────────────────────────────────


async def _groq(prompt: str) -> Optional[str]:
    if not settings.groq_api_key or settings.groq_api_key.startswith("gsk_..."):
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("Groq indisponivel", extra={"erro": str(e)})
        return None


# ─── Gemini ───────────────────────────────────────────────────────────────────


async def _gemini(prompt: str) -> Optional[str]:
    if not settings.gemini_api_key or settings.gemini_api_key.startswith("AIza..."):
        return None
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
    except Exception as e:
        log.warning("Gemini indisponivel", extra={"erro": str(e)})
        return None


# ─── Fallback chain ───────────────────────────────────────────────────────────


async def completar(prompt: str, preferir_local: bool = True) -> tuple[str, str]:
    """
    Retorna (resposta, provider_usado).
    Ordem: Ollama -> Groq -> Gemini.
    """
    providers = [
        ("ollama", _ollama(prompt, timeout=_TIMEOUT_CLASSIF)),
        ("groq", _groq(prompt)),
        ("gemini", _gemini(prompt)),
    ]
    if not preferir_local:
        providers = providers[1:] + [providers[0]]

    for nome, coro in providers:
        resultado = await coro
        if resultado:
            log.info("LLM respondeu", extra={"provider": nome, "chars": len(resultado)})
            return resultado, nome

    return "", "nenhum"


# ─── Classificacao estruturada ────────────────────────────────────────────────

_PROMPT_CLASSIF = """Analise o texto extraido de um print de tela e classifique:

TEXTO:
{texto}

Responda APENAS em JSON valido (sem markdown, sem explicacoes):
{{
    "fonte": "twitter|instagram|github|site|reddit|youtube|outro",
    "tema": "llm|agentes|automacao|dados|web|devops|outro",
    "tipo": "tutorial|opiniao|lancamento|caso_de_uso|ferramenta|debate|outro",
    "sentimento": "positivo|neutro|negativo",
    "entidades": ["lista", "de", "nomes"],
    "resumo": "Duas frases resumindo o conteudo."
}}"""


async def classificar_foto(texto: str) -> Optional[dict]:
    """Classifica foto usando LLM. Retorna dict ou None se falhar."""
    if not texto or len(texto.strip()) < 20:
        return None
    prompt = _PROMPT_CLASSIF.format(texto=texto[:3000])
    resposta, provider = await completar(prompt, preferir_local=True)
    if not resposta:
        return None
    # Extrai JSON da resposta
    try:
        # Remove markdown caso o modelo insista em usar
        clean = resposta.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
            clean = clean.split("```")[0]
        data = json.loads(clean)
        data["_provider"] = provider
        return data
    except json.JSONDecodeError as e:
        log.warning(
            "JSON invalido na resposta LLM",
            extra={"erro": str(e), "resposta": resposta[:200]},
        )
        return None


# ─── Analise livre ────────────────────────────────────────────────────────────


async def analisar_texto(texto: str, instrucao: str = "") -> tuple[str, str]:
    prompt = f"{instrucao}\n\nTEXTO:\n{texto[:4000]}" if instrucao else texto[:4000]
    return await completar(prompt)


# ─── Verificar disponibilidade ────────────────────────────────────────────────


async def ollama_disponivel() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
