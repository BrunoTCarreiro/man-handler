import logging
import os
from pathlib import Path


# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
)

# Create a logger for this module
logger = logging.getLogger("backend")


# =============================================================================
# Base Paths
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"

MANUALS_DIR = DATA_DIR / "manuals"
VECTORDB_DIR = DATA_DIR / "vectordb"
CATALOG_DIR = DATA_DIR / "catalog"
DEVICE_CATALOG_PATH = CATALOG_DIR / "devices.json"


# =============================================================================
# Network Exposure Configuration
# =============================================================================
# Set EXPOSE_NETWORK=1 to allow access from local network (default: localhost only)
EXPOSE_NETWORK = os.getenv("EXPOSE_NETWORK", "0").strip() in ("1", "true", "yes", "on")

# =============================================================================
# CORS Configuration
# =============================================================================
# Comma-separated list of allowed origins, e.g., "http://localhost:3000,http://localhost:5173"
# If EXPOSE_NETWORK is enabled, defaults to "*" to allow all origins
# For production, specify exact origins for security
_cors_origins_env = os.getenv("CORS_ORIGINS", "*" if EXPOSE_NETWORK else "http://localhost:3000,http://localhost:5173")
if _cors_origins_env.strip() == "*":
    CORS_ORIGINS: list[str] = ["*"]  # Allow all origins (for local network access)
else:
    CORS_ORIGINS: list[str] = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]


# =============================================================================
# Model Configuration
# =============================================================================
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "bge-m3")
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "mistral:instruct")  # Mistral 7B - good multilingual support
TRANSLATION_MODEL_NAME = os.getenv("TRANSLATION_MODEL", "mistral:instruct")  # Same model for translation


# =============================================================================
# Retrieval Parameters
# =============================================================================
TOP_K = int(os.getenv("TOP_K", "5"))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.3"))  # Minimum similarity score (0-1)


# =============================================================================
# Chunking Configuration
# =============================================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))


# =============================================================================
# Initialization
# =============================================================================
def ensure_directories() -> None:
    """Create data directories if they do not exist."""
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()
