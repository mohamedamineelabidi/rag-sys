#!/usr/bin/env python3
"""
RAG Enhancement Recommendations

This script analyzes your RAG system and provides actionable recommendations for improving:
1. Document retrieval quality
2. Response accuracy and relevance
3. Vector database management

Usage:
    python scripts/enhance_rag_performance.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
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
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        return None

def get_recommendations(qdrant_client: QdrantClient = None) -> Dict[str, List[str]]:
    """Generate RAG system enhancement recommendations."""
    
    # Recommendations by category
    recommendations = {
        "retrieval_quality": [
            "Decrease chunk size from 1000 to 500-800 characters for more granular retrieval",
            "Increase chunk overlap from 200 to 100-200 to preserve context across chunks",
            "Update hybrid search implementation to combine semantic and keyword search",
            "Consider adding BM25 for keyword-based retrieval alongside vector search",
            "Add metadata filtering for category-specific searches (HEA, ENE, TRA, etc.)"
        ],
        "indexing": [
            "Re-index documents with enhanced metadata extraction",
            "Add technical term extraction during ingestion for better filtering",
            "Store document structure information (headings, sections) as metadata",
            "Consider hierarchical chunking (document → section → paragraph → sentence)",
            "Add document type classification during ingestion (technical, requirement, guide, etc.)"
        ],
        "prompting": [
            "Update system prompts to include more domain-specific context",
            "Implement multi-step reasoning in RAG service's response generation",
            "Add summarization step for each retrieved document before final answer generation",
            "Include explicit instructions for handling technical content in prompts",
            "Add grounding constraints to ensure responses are based only on retrieved context"
        ],
        "system_config": [
            "Update the similarity score threshold (currently 0.7) based on distribution analysis",
            "Consider reranking retrieved documents before response generation",
            "Implement query reformulation for better retrieval accuracy",
            "Add dynamic retrieval amount based on query complexity",
            "Implement caching for frequent queries to improve response time"
        ]
    }
    
    # Check if we have a database connection to provide targeted recommendations
    if qdrant_client:
        try:
            # Get collection info
            collection_info = qdrant_client.get_collection(COLLECTION_NAME)
            points_count = collection_info.points_count
            
            # Add specific recommendations based on collection size
            if points_count < 500:
                recommendations["critical"] = [
                    f"📉 Low document count ({points_count}) detected",
                    "Ensure all key documents are being indexed properly",
                    "Check ingestion logs for potential errors",
                    "Verify that all document types are being processed correctly"
                ]
            elif points_count > 5000:
                recommendations["critical"] = [
                    f"📈 Large collection size ({points_count} documents)",
                    "Consider semantic filtering before retrieval for performance",
                    "Implement pagination for document processing",
                    "Consider implementing vector indexes or approximate search for speed"
                ]
            
            # Get vector configuration
            vector_config = collection_info.config.params.vectors
            
            # Add recommendations based on vector configuration
            if vector_config:
                recommendations["vector_config"] = [
                    f"Current vector size: {vector_config.size}",
                    f"Current distance metric: {vector_config.distance}",
                    "Consider upgrading to text-embedding-3-large for improved accuracy",
                    "Experiment with different distance metrics (Cosine vs Dot Product)",
                    "Implement vector normalization if not already enabled"
                ]
        except Exception as e:
            logger.error(f"Error analyzing collection: {e}")
    
    return recommendations

def print_recommendation_checklist(recommendations: Dict[str, List[str]]):
    """Print recommendations in an actionable checklist format."""
    
    print("\n===== RAG Performance Enhancement Checklist =====\n")
    
    # Print critical recommendations first if they exist
    if "critical" in recommendations:
        print("🔴 CRITICAL RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations["critical"], 1):
            print(f"  {i}. {rec}")
        print()
        
    # Print other recommendation categories
    categories = {
        "retrieval_quality": "🔍 RETRIEVAL QUALITY IMPROVEMENTS:",
        "indexing": "📚 DOCUMENT INDEXING ENHANCEMENTS:",
        "prompting": "💬 PROMPT ENGINEERING UPDATES:",
        "system_config": "⚙️ SYSTEM CONFIGURATION CHANGES:",
        "vector_config": "🧮 VECTOR DATABASE CONFIGURATION:"
    }
    
    for category, title in categories.items():
        if category in recommendations and category != "critical":
            print(title)
            for i, rec in enumerate(recommendations[category], 1):
                print(f"  □ {i}. {rec}")
            print()
    
    print("======= Implementation Priority Order =======")
    print("1. First address any critical recommendations")
    print("2. Improve document indexing and chunking")
    print("3. Enhance retrieval quality settings")
    print("4. Update prompt engineering")
    print("5. Fine-tune system configuration")
    print("===========================================\n")

def main():
    """Main function to generate and display recommendations."""
    logger.info("🔍 Analyzing RAG system for enhancement opportunities...")
    
    # Check if we're using fake services
    use_fake_services = os.environ.get("USE_FAKE_SERVICES", "").lower() == "true"
    if use_fake_services:
        logger.info("⚠️ Running in FAKE SERVICES mode")
        print("\n⚠️ System is running in FAKE SERVICES mode. Turn off this mode for proper analysis.")
        qdrant_client = None
    else:
        # Initialize Qdrant client
        qdrant_client = initialize_qdrant()
    
    # Generate recommendations
    recommendations = get_recommendations(qdrant_client)
    
    # Print recommendations
    print_recommendation_checklist(recommendations)
    
    # Save recommendations to file
    with open("scripts/rag_recommendations.md", "w") as f:
        f.write("# RAG System Enhancement Recommendations\n\n")
        
        # Write critical recommendations first if they exist
        if "critical" in recommendations:
            f.write("## Critical Recommendations\n\n")
            for rec in recommendations["critical"]:
                f.write(f"- [ ] {rec}\n")
            f.write("\n")
            
        # Write other recommendation categories
        categories = {
            "retrieval_quality": "Retrieval Quality Improvements",
            "indexing": "Document Indexing Enhancements",
            "prompting": "Prompt Engineering Updates",
            "system_config": "System Configuration Changes",
            "vector_config": "Vector Database Configuration"
        }
        
        for category, title in categories.items():
            if category in recommendations and category != "critical":
                f.write(f"## {title}\n\n")
                for rec in recommendations[category]:
                    f.write(f"- [ ] {rec}\n")
                f.write("\n")
                
        f.write("## Implementation Priority\n\n")
        f.write("1. First address any critical recommendations\n")
        f.write("2. Improve document indexing and chunking\n")
        f.write("3. Enhance retrieval quality settings\n")
        f.write("4. Update prompt engineering\n")
        f.write("5. Fine-tune system configuration\n")
    
    logger.info("✅ Recommendations saved to scripts/rag_recommendations.md")
    
    # Provide immediate fix recommendations
    print("\n🔧 IMMEDIATE IMPROVEMENT STEPS:")
    print("1. Run diagnostics to identify specific issues:")
    print("   python scripts/diagnose_rag.py")
    print()
    print("2. Review and adjust chunk size and overlap in ingest_data.py:")
    print("   - Current: chunk_size=1000, chunk_overlap=200")
    print("   - Try: chunk_size=500, chunk_overlap=150")
    print()
    print("3. Lower the score threshold in enhanced_query_processor.py:")
    print("   - Current: score_threshold=0.7")
    print("   - Try: score_threshold=0.6")
    print()
    print("4. Adjust the number of results retrieved:")
    print("   - Current: limit=6")
    print("   - Try: limit=8 or 10")
    print()
    print("5. Re-index your documents after making changes:")
    print("   python scripts/ingest_data.py --rescan")

if __name__ == "__main__":
    main()
