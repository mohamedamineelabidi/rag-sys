#!/usr/bin/env python3
"""
Document Count Check Script

This script checks the number of documents in the Qdrant vector database.
It provides a quick way to verify the state of your vector database.

Usage:
    python scripts/check_document_count.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "documents")

def initialize_qdrant() -> QdrantClient:
    """Initialize Qdrant client."""
    try:
        from backend.config import get_first_env
        
        qdrant_url = get_first_env("QDRANT_URL")
        qdrant_api_key = get_first_env("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is required")
        
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        
        try:
            client.get_collection(COLLECTION_NAME)
            logger.info(f"✅ Connected to Qdrant collection: {COLLECTION_NAME}")
        except Exception as e:
            logger.warning(f"⚠️ Collection '{COLLECTION_NAME}' not found: {e}")
            logger.warning("🔧 Run enhanced ingestion script to create the collection")
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise

def get_collection_info(qdrant_client: QdrantClient) -> Dict[str, Any]:
    """Get information about the Qdrant collection."""
    try:
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count
        
        return {
            "collection_name": COLLECTION_NAME,
            "points_count": points_count,
            "vectors_config": collection_info.config.params.vectors,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        return {
            "collection_name": COLLECTION_NAME,
            "points_count": 0,
            "status": "error",
            "error": str(e)
        }

def main():
    """Main function to check document count."""
    
    # Check if we're using fake services
    use_fake_services = os.environ.get("USE_FAKE_SERVICES", "").lower() == "true"
    if use_fake_services:
        logger.info("⚠️ Running in FAKE SERVICES mode")
        logger.info("📊 Document count information not available in this mode")
        return
    
    try:
        qdrant_client = initialize_qdrant()
        info = get_collection_info(qdrant_client)
        
        print("\n======= Vector Database Document Count =======")
        print(f"Collection: {info['collection_name']}")
        print(f"Document Count: {info['points_count']}")
        print(f"Status: {info['status']}")
        
        if info['status'] == 'error':
            print(f"Error: {info.get('error', 'Unknown error')}")
        elif 'vectors_config' in info:
            print(f"Vector Configuration: {info['vectors_config']}")
        
        print("=============================================\n")
        
        logger.info(f"📊 Total documents in vector database: {info['points_count']}")
    except Exception as e:
        logger.error(f"Error checking document count: {e}")
        print("\n⚠️ Error checking document count. See log for details.")

if __name__ == "__main__":
    main()
