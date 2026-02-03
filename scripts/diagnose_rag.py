#!/usr/bin/env python3
"""
RAG System Diagnostics Script

This script analyzes potential issues with the RAG system response quality by:
1. Checking vector database collection metadata
2. Examining document content quality and retrieval
3. Testing query relevance with sample questions
4. Verifying embedding quality

Usage:
    python scripts/diagnose_rag.py
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from langchain_openai import AzureOpenAIEmbeddings
from backend.config import get_first_env

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
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
SAMPLE_QUERIES = [
    "What are the energy requirements?",
    "Tell me about the water systems",
    "What are the key requirements for HEA_01?",
    "Explain the transport regulations in the documents"
]

def initialize_qdrant() -> QdrantClient:
    """Initialize Qdrant client."""
    try:
        qdrant_url = get_first_env("QDRANT_URL")
        qdrant_api_key = get_first_env("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is required")
        
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        
        try:
            client.get_collection(COLLECTION_NAME)
            logger.info(f"Connected to Qdrant collection: {COLLECTION_NAME}")
        except Exception as e:
            logger.warning(f"Collection '{COLLECTION_NAME}' not found: {e}")
            logger.warning("Run enhanced ingestion script to create the collection")
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise

def initialize_embeddings() -> AzureOpenAIEmbeddings:
    """Initialize Azure OpenAI embeddings."""
    try:
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=get_first_env("AZURE_OPENAI_ENDPOINT"),
            api_key=get_first_env("AZURE_OPENAI_API_KEY"),
            api_version=get_first_env("OPENAI_API_VERSION"),
            azure_deployment=get_first_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME"),
            model=EMBEDDING_MODEL_NAME
        )
        logger.info(f"Initialized Azure OpenAI embeddings: {EMBEDDING_MODEL_NAME}")
        return embeddings
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        raise

def get_collection_stats(qdrant_client: QdrantClient) -> Dict[str, Any]:
    """Get detailed collection statistics."""
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    
    # Get collection info
    stats = {
        "collection_name": COLLECTION_NAME,
        "points_count": collection_info.points_count,
        "vectors_config": collection_info.config.params.vectors,
        "status": "healthy"
    }
    
    # Sample some points to check content
    try:
        # Get 5 random points
        scroll_results = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        points = scroll_results[0]
        content_samples = []
        content_length_stats = {"min": float('inf'), "max": 0, "total": 0}
        
        for point in points:
            payload = point.payload
            content = payload.get("content", "")
            content_length = len(content)
            
            # Update content length statistics
            content_length_stats["min"] = min(content_length_stats["min"], content_length)
            content_length_stats["max"] = max(content_length_stats["max"], content_length)
            content_length_stats["total"] += content_length
            
            # Add truncated content sample
            content_samples.append({
                "file_name": payload.get("file_name", "Unknown"),
                "content_length": content_length,
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            })
        
        if points:
            content_length_stats["avg"] = content_length_stats["total"] / len(points)
        else:
            content_length_stats["min"] = 0
            content_length_stats["avg"] = 0
        
        stats["content_samples"] = content_samples
        stats["content_length_stats"] = content_length_stats
        
    except Exception as e:
        logger.error(f"Error sampling points: {e}")
        stats["content_samples"] = []
        stats["content_length_stats"] = {"error": str(e)}
    
    return stats

def test_retrieval_quality(qdrant_client: QdrantClient, embeddings: AzureOpenAIEmbeddings) -> Dict[str, Any]:
    """Test retrieval quality with sample queries."""
    results = {}
    
    for query in SAMPLE_QUERIES:
        try:
            # Generate embedding for the query
            query_embedding = embeddings.embed_query(query)
            
            # Search for relevant documents
            search_results = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                limit=3,
                with_payload=True,
                score_threshold=0.6
            )
            
            # Process results
            query_results = []
            for result in search_results:
                payload = result.payload or {}
                query_results.append({
                    "score": float(result.score),
                    "file_name": payload.get("file_name", "Unknown"),
                    "content_preview": payload.get("content", "")[:200] + "..." 
                        if len(payload.get("content", "")) > 200 else payload.get("content", "")
                })
            
            results[query] = {
                "results_count": len(query_results),
                "top_results": query_results
            }
            
        except Exception as e:
            logger.error(f"Error testing query '{query}': {e}")
            results[query] = {"error": str(e)}
    
    return results

def diagnose_document_issues() -> Dict[str, Any]:
    """Run diagnostics on the RAG system."""
    diagnosis = {
        "timestamp": Path(__file__).stat().st_mtime,
        "vector_db": {},
        "retrieval_quality": {},
        "potential_issues": []
    }
    
    # Check if we're using fake services
    use_fake_services = os.environ.get("USE_FAKE_SERVICES", "").lower() == "true"
    if use_fake_services:
        logger.info("⚠️ Running in FAKE SERVICES mode")
        diagnosis["potential_issues"].append("System is running in FAKE SERVICES mode")
        return diagnosis
    
    try:
        # Initialize services
        qdrant_client = initialize_qdrant()
        embeddings = initialize_embeddings()
        
        # Get collection statistics
        diagnosis["vector_db"] = get_collection_stats(qdrant_client)
        
        # Test retrieval quality
        diagnosis["retrieval_quality"] = test_retrieval_quality(qdrant_client, embeddings)
        
        # Analyze potential issues
        points_count = diagnosis["vector_db"]["points_count"]
        
        # Check document count
        if points_count == 0:
            diagnosis["potential_issues"].append("No documents in vector database")
        elif points_count < 10:
            diagnosis["potential_issues"].append(f"Very few documents ({points_count}) in vector database")
            
        # Check content length
        if "content_length_stats" in diagnosis["vector_db"]:
            stats = diagnosis["vector_db"]["content_length_stats"]
            if stats.get("avg", 0) < 100:
                diagnosis["potential_issues"].append("Document chunks are very short (avg < 100 chars)")
            elif stats.get("max", 0) < 500:
                diagnosis["potential_issues"].append("Document chunks may be too small (max < 500 chars)")
        
        # Check retrieval quality
        low_result_queries = []
        for query, results in diagnosis["retrieval_quality"].items():
            if results.get("results_count", 0) == 0:
                low_result_queries.append(query)
                
        if low_result_queries:
            diagnosis["potential_issues"].append(
                f"No results found for {len(low_result_queries)}/{len(SAMPLE_QUERIES)} sample queries"
            )
            
        # If no specific issues found, add general suggestions
        if not diagnosis["potential_issues"]:
            diagnosis["potential_issues"] = [
                "No obvious database issues detected. Consider:",
                "- Checking embedding model settings",
                "- Reviewing query processor settings",
                "- Ensuring document chunking is appropriate",
                "- Verifying prompt engineering in enhanced_rag_service.py"
            ]
            
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        diagnosis["error"] = str(e)
        diagnosis["potential_issues"].append(f"Diagnostic error: {e}")
    
    return diagnosis

def main():
    """Main function to run diagnostics."""
    logger.info("🔍 Running RAG system diagnostics...")
    
    try:
        diagnosis = diagnose_document_issues()
        
        print("\n======= RAG System Diagnosis =======")
        
        # Document stats
        if "vector_db" in diagnosis and "points_count" in diagnosis["vector_db"]:
            print(f"Document Count: {diagnosis['vector_db']['points_count']}")
            
            if "content_length_stats" in diagnosis["vector_db"]:
                stats = diagnosis["vector_db"]["content_length_stats"]
                print(f"Content Length: avg={stats.get('avg', 'N/A'):.1f}, min={stats.get('min', 'N/A')}, max={stats.get('max', 'N/A')}")
        
        # Sample content
        if "vector_db" in diagnosis and "content_samples" in diagnosis["vector_db"] and diagnosis["vector_db"]["content_samples"]:
            print("\n--- Content Sample ---")
            sample = diagnosis["vector_db"]["content_samples"][0]
            print(f"File: {sample.get('file_name', 'Unknown')}")
            print(f"Content ({sample.get('content_length', 0)} chars): {sample.get('content_preview', 'N/A')}")
            
        # Retrieval quality
        if "retrieval_quality" in diagnosis:
            print("\n--- Retrieval Test Results ---")
            for query, results in diagnosis["retrieval_quality"].items():
                result_count = results.get("results_count", 0)
                print(f"Query: '{query}'")
                print(f"Results: {result_count}")
                
                if result_count > 0 and "top_results" in results:
                    top = results["top_results"][0]
                    print(f"Top Match: {top.get('file_name', 'Unknown')} (score: {top.get('score', 0):.3f})")
                    print(f"Preview: {top.get('content_preview', 'N/A')[:100]}...")
                print()
            
        # Potential issues
        print("\n--- Potential Issues ---")
        for issue in diagnosis["potential_issues"]:
            print(f"• {issue}")
            
        print("\n--- Recommendations ---")
        print("1. Check data ingestion processes to ensure documents are properly indexed")
        print("2. Verify your embedding model setup in backend/config.py")
        print("3. Examine the enhanced_query_processor.py semantic_search method")
        print("4. Review document chunking settings in ingest_data.py")
        print("5. Consider adjusting similarity thresholds in the query processor")
        
        print("\n===============================")
        
        # Save detailed diagnosis to file
        with open("scripts/rag_diagnosis.json", "w") as f:
            json.dump(diagnosis, f, indent=2)
        logger.info("✅ Detailed diagnosis saved to scripts/rag_diagnosis.json")
        
    except Exception as e:
        logger.error(f"Error in diagnosis: {e}")
        print("\n⚠️ Error running diagnostics. See log for details.")

if __name__ == "__main__":
    main()
