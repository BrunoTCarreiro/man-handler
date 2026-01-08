"""
Configuration Manager for First-Time Setup

Handles:
- Setup completion tracking
- Ollama connection testing
- Model availability checking
- Configuration persistence
"""

import json
import logging
from pathlib import Path
from typing import Optional
import requests

from . import settings

logger = logging.getLogger("backend.config_manager")

CONFIG_FILE = settings.DATA_DIR / "config.json"
OLLAMA_BASE_URL = "http://localhost:11434"


class SetupConfig:
    """Manages setup configuration and persistence."""

    def __init__(self):
        self.config_path = CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.info("No config file found, returning default config")
            return self._default_config()
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info("Loaded configuration from %s", self.config_path)
                return config
        except Exception as e:
            logger.error("Failed to load config file: %s", e)
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            "setup_completed": False,
            "ollama_models": {
                "llm": settings.LLM_MODEL_NAME,
                "embedding": settings.EMBED_MODEL_NAME,
                "translation": settings.TRANSLATION_MODEL_NAME,
            },
            "rag_params": {
                "top_k": settings.TOP_K,
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
            },
        }

    def save_config(self) -> None:
        """Persist configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            logger.info("Saved configuration to %s", self.config_path)
        except Exception as e:
            logger.error("Failed to save config file: %s", e)
            raise

    def is_setup_completed(self) -> bool:
        """Check if first-time setup has been completed."""
        return self.config.get("setup_completed", False)

    def mark_setup_completed(self) -> None:
        """Mark setup as completed."""
        self.config["setup_completed"] = True
        self.save_config()

    def update_models(self, llm: Optional[str] = None, embedding: Optional[str] = None, translation: Optional[str] = None) -> None:
        """Update model configuration."""
        if llm:
            self.config["ollama_models"]["llm"] = llm
        if embedding:
            self.config["ollama_models"]["embedding"] = embedding
        if translation:
            self.config["ollama_models"]["translation"] = translation
        self.save_config()

    def update_rag_params(self, top_k: Optional[int] = None, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> None:
        """Update RAG parameters."""
        if top_k is not None:
            self.config["rag_params"]["top_k"] = top_k
        if chunk_size is not None:
            self.config["rag_params"]["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            self.config["rag_params"]["chunk_overlap"] = chunk_overlap
        self.save_config()

    def get_config_dict(self) -> dict:
        """Get the full configuration as a dictionary."""
        return self.config.copy()

    def get_llm_model(self) -> str:
        """Get configured LLM model."""
        return self.config.get("ollama_models", {}).get("llm", settings.LLM_MODEL_NAME)

    def get_embedding_model(self) -> str:
        """Get configured embedding model."""
        return self.config.get("ollama_models", {}).get("embedding", settings.EMBED_MODEL_NAME)

    def get_translation_model(self) -> str:
        """Get configured translation model."""
        return self.config.get("ollama_models", {}).get("translation", settings.TRANSLATION_MODEL_NAME)


# Global config instance
_config_instance: Optional[SetupConfig] = None


def get_config() -> SetupConfig:
    """Get or create the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = SetupConfig()
    return _config_instance


def check_ollama_connection() -> dict:
    """
    Check if Ollama is running and accessible.
    
    Returns:
        dict with status, message, and version (if available)
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            logger.info("Ollama is running: %s", version_info)
            return {
                "status": "connected",
                "message": "Ollama is running",
                "version": version_info.get("version", "unknown"),
            }
        else:
            logger.warning("Ollama responded with status %s", response.status_code)
            return {
                "status": "error",
                "message": f"Ollama responded with status {response.status_code}",
            }
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama at %s", OLLAMA_BASE_URL)
        return {
            "status": "disconnected",
            "message": "Cannot connect to Ollama. Is it running?",
        }
    except Exception as e:
        logger.error("Error checking Ollama connection: %s", e)
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
        }


def list_ollama_models() -> dict:
    """
    List all models available in Ollama.
    
    Returns:
        dict with models list and categorization
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        if response.status_code != 200:
            logger.error("Failed to list models, status: %s", response.status_code)
            return {
                "status": "error",
                "message": f"Failed to list models (status {response.status_code})",
                "models": [],
            }
        
        data = response.json()
        models = data.get("models", [])
        
        # Categorize models
        llm_models = []
        embedding_models = []
        
        for model in models:
            model_name = model.get("name", "")
            model_size = model.get("size", 0)
            
            # Categorize based on name patterns
            if any(emb in model_name.lower() for emb in ["embed", "bge", "nomic-embed"]):
                embedding_models.append({
                    "name": model_name,
                    "size": model_size,
                    "modified": model.get("modified_at", ""),
                })
            else:
                llm_models.append({
                    "name": model_name,
                    "size": model_size,
                    "modified": model.get("modified_at", ""),
                })
        
        logger.info("Found %d LLM models and %d embedding models", len(llm_models), len(embedding_models))
        
        return {
            "status": "success",
            "llm_models": llm_models,
            "embedding_models": embedding_models,
            "total": len(models),
        }
    
    except Exception as e:
        logger.error("Error listing Ollama models: %s", e)
        return {
            "status": "error",
            "message": str(e),
            "models": [],
        }


def test_model(model_name: str, model_type: str = "llm") -> dict:
    """
    Test if a specific model is working.
    
    Args:
        model_name: Name of the model to test
        model_type: Type of model ("llm" or "embedding")
    
    Returns:
        dict with test results
    """
    try:
        if model_type == "embedding":
            # Test embedding model
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": "test",
                },
                timeout=30,
            )
        else:
            # Test LLM model
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False,
                },
                timeout=30,
            )
        
        if response.status_code == 200:
            logger.info("Model %s tested successfully", model_name)
            return {
                "status": "success",
                "message": f"Model {model_name} is working correctly",
            }
        else:
            logger.error("Model test failed with status %s", response.status_code)
            return {
                "status": "error",
                "message": f"Model test failed (status {response.status_code})",
            }
    
    except Exception as e:
        logger.error("Error testing model %s: %s", model_name, e)
        return {
            "status": "error",
            "message": str(e),
        }

