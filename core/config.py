# core/config.py
from pathlib import Path

# --- المسارات ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "geant.db"

# --- Ollama ---
OLLAMA_HOST = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:3b"
OLLAMA_TIMEOUT_SECONDS = 60

# --- الاسترجاع (RAG) ---
TOP_K = 4
MIN_SIMILARITY = 0.5   # قيمة مبدئية مفترضة، سنضبطها بالتجربة لاحقًا

# --- التوليد ---
TEMPERATURE = 0.2
NUM_PREDICT = 400

# --- البحث عن المنتجات ---
MAX_PRODUCT_RESULTS = 10
DEFAULT_CURRENCY = "DZD"

# --- إدخال المعرفة (ingestion) ---
MAX_CHUNK_CHARS = 800
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
