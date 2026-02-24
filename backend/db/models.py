"""
2 Cerebro — Pydantic Schemas (request / response)
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ─── Foto ────────────────────────────────────────────────────────────────────


class FotoBase(BaseModel):
    numero: str
    filename: str
    filepath: str
    status: str = "pendente"
    ocr_texto: Optional[str] = None
    ocr_limpo: Optional[str] = None
    criado_em: Optional[str] = None
    processado_em: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    data_captura: Optional[str] = None
    semana: Optional[str] = None
    mes: Optional[str] = None
    motor_ocr: str = "tesseract"
    # Cerebro 1
    fonte: Optional[str] = None
    tema: Optional[str] = None
    tipo: Optional[str] = None
    sentimento: Optional[str] = None
    entidades: Optional[str] = None  # JSON array serializado
    resumo: Optional[str] = None
    classificado: int = 0


class FotoResponse(FotoBase):
    id: int

    model_config = {"from_attributes": True}


class FotoListResponse(BaseModel):
    fotos: List[FotoResponse]
    total: int


# ─── OCR ─────────────────────────────────────────────────────────────────────


class OcrRequest(BaseModel):
    numero: str


class OcrResponse(BaseModel):
    sucesso: bool
    numero: str
    texto_bruto: str = ""
    texto_limpo: str = ""
    palavras: List[str] = []
    caracteres: int = 0
    erro: Optional[str] = None


# ─── Upload ───────────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    sucesso: bool
    numero: str = ""
    filename: str = ""
    filepath: str = ""
    duplicada: bool = False
    mensagem: Optional[str] = None
    erro: Optional[str] = None


# ─── Busca ────────────────────────────────────────────────────────────────────


class BuscaRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    semantica: bool = True


class ResultadoBusca(BaseModel):
    numero: str
    filename: str
    score: float
    trecho: Optional[str] = None


class BuscaResponse(BaseModel):
    query: str
    resultados: List[ResultadoBusca]
    total: int
    modo: str  # "semantica" | "textual" | "misto"


# ─── Embeddings ───────────────────────────────────────────────────────────────


class EmbeddingResponse(BaseModel):
    sucesso: bool
    processados: int = 0
    modelo: str = ""
    erro: Optional[str] = None


class SimilaresResponse(BaseModel):
    numero: str
    similares: List[dict]


# ─── Insights / Grafo ─────────────────────────────────────────────────────────


class GraphNode(BaseModel):
    id: str
    label: str
    contagem: int = 0
    grupo: Optional[str] = None
    cor: Optional[str] = None


class GraphLink(BaseModel):
    source: str
    target: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


class ClusterItem(BaseModel):
    numero: str
    cluster: int


class ClusterResponse(BaseModel):
    clusters: dict[int, List[str]]
    total_clusters: int


class DossieResponse(BaseModel):
    termo: str
    contagem: int
    fotos: List[str]
    coocorrencias: List[dict]
    timeline: List[dict]
    ancoras: List[str]


# ─── LLM ─────────────────────────────────────────────────────────────────────


class LlmRequest(BaseModel):
    numero: str
    prompt_extra: Optional[str] = None


class LlmResponse(BaseModel):
    sucesso: bool
    numero: str
    resposta: str = ""
    provider: str = ""
    erro: Optional[str] = None


class PostRequest(BaseModel):
    tema: Optional[str] = None
    numeros: Optional[List[str]] = None
    estilo: str = "thread"  # "thread" | "linkedin" | "curto"


class PostResponse(BaseModel):
    sucesso: bool
    post: str = ""
    fontes: List[str] = []
    erro: Optional[str] = None


# ─── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    db: bool
    chroma: bool
    ollama: bool
    fotos_total: int
    embeddings_total: int
    version: str = "1.0.0"


# ─── Stats / Top ─────────────────────────────────────────────────────────────


class PalavraItem(BaseModel):
    palavra: str
    contagem: int
    fotos_ids: List[str] = []


class UsuarioItem(BaseModel):
    username: str
    contagem: int
    fotos_ids: List[str] = []


class RepoItem(BaseModel):
    repo: str
    contagem: int
    fotos_ids: List[str] = []


class StatsResponse(BaseModel):
    total_fotos: int
    fotos_com_ocr: int
    top_palavras: List[PalavraItem]
    top_usuarios: List[UsuarioItem]
    top_repos: List[RepoItem]
    por_semana: List[dict]
    por_mes: List[dict]
