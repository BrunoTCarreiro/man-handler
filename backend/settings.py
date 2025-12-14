from pathlib import Path


# Base paths (relative to backend/)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"

MANUALS_DIR = DATA_DIR / "manuals"
VECTORDB_DIR = DATA_DIR / "vectordb"
CATALOG_DIR = DATA_DIR / "catalog"
DEVICE_CATALOG_PATH = CATALOG_DIR / "devices.json"


# Models
EMBED_MODEL_NAME = "bge-m3"
LLM_MODEL_NAME = "mistral:instruct"  # Mistral 7B - good multilingual support
TRANSLATION_MODEL_NAME = "mistral:instruct"  # Same model for translation


# Retrieval parameters
TOP_K = 5
RELEVANCE_THRESHOLD = 0.3  # Minimum similarity score (0-1, lower = more strict)


# Chunking
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


def ensure_directories() -> None:
    """Create data directories if they do not exist."""
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()


