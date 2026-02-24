"""
GigU Brain — Configurações Globais
"""

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).parent

# Diretórios
FOTOS_DIR = BASE_DIR / "fotos"
OCR_DIR = BASE_DIR / "ocr_bruto"
NOTAS_DIR = BASE_DIR / "obsidian_notas"
LOGS_DIR = BASE_DIR / "logs"
CHROMA_DIR = BASE_DIR / "chroma_data"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Garantir que existem
for d in [FOTOS_DIR, OCR_DIR, NOTAS_DIR, LOGS_DIR, CHROMA_DIR, MODELS_DIR]:
    d.mkdir(exist_ok=True)

# Formatos aceitos
EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# OCR
TESSERACT_LANG = "por+eng"
TESSERACT_CONFIG = "--psm 6 --oem 3"

# Palavras ignoradas no contador (stopwords)
STOPWORDS = {
    "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos",
    "um", "uma", "uns", "umas", "ou", "se", "ao", "as", "os", "que",
    "por", "para", "com", "the", "and", "for", "you", "are", "this",
    "that", "have", "from", "not", "but", "all", "can", "your", "it",
    "is", "in", "to", "of", "a", "an", "be", "at", "we", "they",
    "was", "has", "its", "our", "will", "with", "use", "via", "just",
    "more", "like", "also", "when", "than", "then", "what", "how",
    "eu", "vc", "ele", "ela", "nos", "eles", "mais", "mas", "pra",
    "pelo", "pela", "pelo", "sobre", "como", "cada", "sua", "seu",
    "isso", "esse", "esta", "este", "foi", "sao", "tem", "ter",
    "uma", "todo", "toda", "muito", "voce", "para", "isso"
}

# Flask
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "20"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "12"))
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "5"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", str(18_000_000)))
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "4200"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "auto")
SEMANTIC_MODEL_NAME = os.getenv("SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")

EMBEDDING_DIM = 48
EMBEDDING_THRESHOLD = 0.35
EMBEDDING_MAX_LINKS = 4
