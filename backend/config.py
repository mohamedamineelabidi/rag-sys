"""Configuration and environment validation utilities for the RAG backend.

Centralizes access to required environment variables and provides helpful
error messages early in the startup phase instead of failing deep inside
service logic.
"""
from __future__ import annotations
import os
from typing import List, Dict, Iterable, Optional

REQUIRED_ENV_VARS: List[str] = [
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    # We now support both EMBEDDINGS and EMBEDDING naming. Keep canonical plural.
    "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    "OPENAI_API_VERSION",
]

def validate_required_env() -> None:
    """Validate required environment variables unless fake services are enabled."""
    if os.environ.get("USE_FAKE_SERVICES", "false").lower() == "true":
        # Skip strict validation in fake mode
        return
    missing = [k for k in REQUIRED_ENV_VARS if not os.environ.get(k)]
    if missing:
        raise EnvironmentError("Missing required environment variables: " + ", ".join(missing))


def get_first_env(*names: str, default: Optional[str] = None) -> Optional[str]:
    """Return first existing environment variable among provided names.

    Example: get_first_env("A", "B") returns value of A if set else B.
    """
    for n in names:
        val = os.environ.get(n)
        if val is not None:
            return val
    return default

def get_runtime_config() -> Dict[str, str]:
    """Return a snapshot of key runtime configuration values (non-secret)."""
    keys_to_expose = [
        "QDRANT_URL",
        "QDRANT_COLLECTION_NAME",
        "OPENAI_API_VERSION",
        "INDEXING_INCLUDE_DIRS",
        "USE_INDEXING_CACHE",
        "SYNC_DELETIONS_ON_STARTUP",
        "SKIP_STARTUP_SCAN",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP",
    ]
    out: Dict[str, str] = {}
    for k in keys_to_expose:
        if k in os.environ:
            out[k] = os.environ[k]
    return out
