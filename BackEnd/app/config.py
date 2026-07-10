import os
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Rutas base del proyecto
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "Documentacion"
FAISS_INDEX_PATH = BASE_DIR / "faiss_index"
HISTORY_FILE_PATH = BASE_DIR / "chat_history.json"
ENV_FILE = BASE_DIR / "static" / ".env"

# ─────────────────────────────────────────────
# Carga de variables de entorno
# ─────────────────────────────────────────────
load_dotenv(dotenv_path=ENV_FILE)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "No se encontró GEMINI_API_KEY en el archivo .env\n"
        f"   Ruta esperada: {ENV_FILE}\n"
        "   Obtén tu clave gratuita en: https://aistudio.google.com/app/apikey"
    )

# ─────────────────────────────────────────────
# Modelos de Google Gemini
# ─────────────────────────────────────────────

LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# ─────────────────────────────────────────────
# Parámetros del chunking de documentos
# ─────────────────────────────────────────────
CHUNK_SIZE = 800        
CHUNK_OVERLAP = 100    

TOP_K_RESULTS = 5

# ─────────────────────────────────────────────
# Configuración del LLM
# ─────────────────────────────────────────────
LLM_TEMPERATURE = 0.2   
LLM_MAX_TOKENS = 2048
