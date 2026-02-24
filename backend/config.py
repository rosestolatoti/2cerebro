"""
2 Cerebro — Configuracao Global
Pydantic BaseSettings com suporte a .env
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # --- Diretorios ---
    base_dir: Path = BASE_DIR
    fotos_dir: Path = BASE_DIR / "fotos"
    ocr_dir: Path = BASE_DIR / "ocr_bruto"
    notas_dir: Path = BASE_DIR / "obsidian_notas"
    logs_dir: Path = BASE_DIR / "logs"
    chroma_dir: Path = BASE_DIR / "chroma_data"
    models_dir: Path = BASE_DIR / "models"

    # --- Banco de dados ---
    db_path: Path = BASE_DIR / "gigu_brain.db"

    # --- Servidor ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # --- Seguranca ---
    api_token: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- OCR ---
    tesseract_lang: str = "por+eng"
    tesseract_config: str = "--psm 6 --oem 3"
    tesseract_cmd: str = ""
    max_upload_mb: int = 12
    max_upload_files: int = 5
    max_image_pixels: int = 18_000_000
    max_image_side: int = 4200

    # --- Embeddings ---
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_threshold: float = 0.35
    embedding_max_links: int = 4

    # --- Ollama ---
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_num_thread: int = 6

    # --- Groq ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # --- Performance ---
    sync_interval: int = 20

    # --- Formatos aceitos ---
    extensoes_validas: set = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    # --- Stopwords (PT + EN) ---
    stopwords: set = {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "em",
        "na",
        "no",
        "nas",
        "nos",
        "um",
        "uma",
        "uns",
        "umas",
        "ou",
        "se",
        "ao",
        "as",
        "os",
        "que",
        "por",
        "para",
        "com",
        "the",
        "and",
        "for",
        "you",
        "are",
        "this",
        "that",
        "have",
        "from",
        "not",
        "but",
        "all",
        "can",
        "your",
        "it",
        "is",
        "in",
        "to",
        "of",
        "a",
        "an",
        "be",
        "at",
        "we",
        "they",
        "was",
        "has",
        "its",
        "our",
        "will",
        "with",
        "use",
        "via",
        "just",
        "more",
        "like",
        "also",
        "when",
        "than",
        "then",
        "what",
        "how",
        "eu",
        "vc",
        "ele",
        "ela",
        "nos",
        "eles",
        "mais",
        "mas",
        "pra",
        "pelo",
        "pela",
        "sobre",
        "como",
        "cada",
        "sua",
        "seu",
        "isso",
        "esse",
        "esta",
        "este",
        "foi",
        "sao",
        "tem",
        "ter",
        "todo",
        "toda",
        "muito",
        "voce",
        "para",
    }

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def model_post_init(self, __context) -> None:
        """Garante que os diretorios existem ao inicializar."""
        for d in [
            self.fotos_dir,
            self.ocr_dir,
            self.notas_dir,
            self.logs_dir,
            self.chroma_dir,
            self.models_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def embedding_model_path(self) -> Path:
        local = self.models_dir / self.embedding_model_name
        if local.exists():
            return local
        return Path(self.embedding_model_name)


# Instancia global — importar de qualquer modulo
settings = Settings()
