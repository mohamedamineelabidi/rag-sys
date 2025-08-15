"""
Enhanced Query Processor for RAG Backend

This module provides advanced document retrieval capabilities with:
- Multi-strategy search (semantic, keyword, hybrid)
- Context-aware ranking
- Smart result filtering and reranking
- Query expansion and preprocessing
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchRequest
from langchain_openai import AzureOpenAIEmbeddings
from backend.config import get_first_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "documents")
EMBEDDING_MODEL_NAME = "text-embedding-3-small"


class QueryPreprocessor:
    """Enhanced query preprocessing for better retrieval."""
    
    @staticmethod
    def preprocess_query(query: str) -> Dict[str, Any]:
        """Preprocess and analyze the query for better retrieval."""
        query_lower = query.lower().strip()
        
        # Extract key information from query
        analysis = {
            'original_query': query,
            'cleaned_query': query_lower,
            'query_type': 'general',
            'key_terms': [],
            'filters': {},
            'expansion_terms': []
        }
        
        # Detect query type
        if any(term in query_lower for term in ['requirement', 'standard', 'norm', 'regulation']):
            analysis['query_type'] = 'requirement'
        elif any(term in query_lower for term in ['calculation', 'analysis', 'assess', 'evaluate']):
            analysis['query_type'] = 'calculation'
        elif any(term in query_lower for term in ['energy', 'thermal', 'hvac', 'heating', 'cooling']):
            analysis['query_type'] = 'energy'
        elif any(term in query_lower for term in ['water', 'plumbing', 'drainage']):
            analysis['query_type'] = 'water'
        elif any(term in query_lower for term in ['transport', 'access', 'mobility']):
            analysis['query_type'] = 'transport'
        
        # Extract key technical terms
        technical_patterns = [
            r'\b\d+\s*(kW|MW|kWh|MWh|°C|°F|%|m²|m³)\b',  # Units with values
            r'\b(energy|thermal|efficiency|consumption|performance)\b',  # Energy terms
            r'\b(HEA|ENE|TRA|WAT|RSC|RSL|LUE|POL)[\s_-]*\d+\b',  # Category references
            r'\b(requirement|standard|regulation|compliance|audit)\b'   # Regulatory terms
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            analysis['key_terms'].extend(matches)
        
        # Extract category filters
        category_match = re.search(r'\b(HEA|ENE|TRA|WAT|RSC|RSL|LUE|POL)\b', query.upper())
        if category_match:
            category_code = category_match.group(1)
            analysis['filters']['category'] = f"{category_code.lower()}_*"
        
        # Query expansion based on type
        expansion_map = {
            'energy': ['thermal', 'heating', 'cooling', 'efficiency', 'consumption', 'performance'],
            'requirement': ['standard', 'regulation', 'compliance', 'norm', 'criterion'],
            'calculation': ['analysis', 'assessment', 'evaluation', 'computation', 'estimate'],
            'water': ['plumbing', 'drainage', 'sanitary', 'hydraulic'],
            'transport': ['access', 'mobility', 'circulation', 'traffic']
        }
        
        if analysis['query_type'] in expansion_map:
            analysis['expansion_terms'] = expansion_map[analysis['query_type']]
        
        return analysis


class EnhancedQdrantQueryProcessor:
    """
    Enhanced query processor with multiple search strategies and smart ranking.
    """

    def __init__(self):
        """Initialize the enhanced query processor."""
        self.qdrant_client = self._initialize_qdrant()
        self.embeddings = self._initialize_embeddings()
        self.query_preprocessor = QueryPreprocessor()
        logger.info("✅ EnhancedQdrantQueryProcessor initialized")

    def _initialize_qdrant(self) -> QdrantClient:
        """Initialize Qdrant client."""
        try:
            qdrant_url = get_first_env("QDRANT_URL")
            qdrant_api_key = get_first_env("QDRANT_API_KEY")
            
            if not qdrant_url:
                raise ValueError("QDRANT_URL environment variable is required")
            
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            
            try:
                client.get_collection(COLLECTION_NAME)
                logger.info(f"✅ Connected to Qdrant collection: {COLLECTION_NAME}")
            except Exception as e:
                logger.warning(f"⚠️  Collection '{COLLECTION_NAME}' not found: {e}")
                logger.warning("🔧 Run enhanced ingestion script to create the collection")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    def _initialize_embeddings(self) -> AzureOpenAIEmbeddings:
        """Initialize Azure OpenAI embeddings."""
        try:
            embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=get_first_env("AZURE_OPENAI_ENDPOINT"),
                api_key=get_first_env("AZURE_OPENAI_API_KEY"),
                api_version=get_first_env("OPENAI_API_VERSION"),
                azure_deployment=get_first_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME"),
                model=EMBEDDING_MODEL_NAME
            )
            logger.info(f"✅ Initialized Azure OpenAI embeddings: {EMBEDDING_MODEL_NAME}")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for given text."""
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            raise

    def _build_query_filter(self, query_analysis: Dict[str, Any]) -> Optional[Filter]:
        """Build Qdrant filter based on query analysis."""
        conditions = []
        
        # Add category filter if detected
        if 'category' in query_analysis['filters']:
            conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(value=query_analysis['filters']['category'])
                )
            )
        
        # Filter by content type for specific query types
        if query_analysis['query_type'] == 'requirement':
            conditions.append(
                FieldCondition(
                    key="section_type",
                    match=MatchValue(value="requirement_section")
                )
            )
        elif query_analysis['query_type'] == 'calculation':
            conditions.append(
                FieldCondition(
                    key="section_type",
                    match=MatchValue(value="calculation_section")
                )
            )
        
        # Prefer technical content for technical queries
        if query_analysis['query_type'] in ['energy', 'calculation']:
            conditions.append(
                FieldCondition(
                    key="technical_content",
                    match=MatchValue(value=True)
                )
            )
        
        return Filter(must=conditions) if conditions else None

    def semantic_search(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Perform enhanced semantic search with query preprocessing."""
        try:
            # Preprocess and analyze query
            query_analysis = self.query_preprocessor.preprocess_query(query)
            logger.info(f"Query analysis: type={query_analysis['query_type']}, terms={query_analysis['key_terms']}")
            
            # Create embedding for the original query
            query_embedding = self._create_embedding(query_analysis['original_query'])
            
            # Build filter based on query analysis
            query_filter = self._build_query_filter(query_analysis)
            
            # Perform semantic search
            search_results = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit * 2,  # Get more results for reranking
                with_payload=True,
                score_threshold=0.3  # Minimum relevance threshold
            )
            
            # Process and rerank results
            results = []
            for result in search_results:
                payload = result.payload or {}
                
                # Calculate enhanced relevance score
                enhanced_score = self._calculate_enhanced_score(
                    result.score, 
                    payload, 
                    query_analysis
                )
                
                results.append({
                    "content": payload.get("content", ""),
                    "enhanced_content": payload.get("enhanced_content", payload.get("content", "")),
                    "file_name": payload.get("file_name", "Unknown"),
                    "category": payload.get("category", "Unknown"),
                    "document_type": payload.get("document_type", "general"),
                    "section_type": payload.get("section_type", "content_section"),
                    "technical_content": payload.get("technical_content", False),
                    "original_score": float(result.score),
                    "enhanced_score": enhanced_score,
                    "metadata": {
                        k: v for k, v in payload.items() 
                        if k not in ["content", "enhanced_content"]
                    }
                })
            
            # Sort by enhanced score and limit results
            results.sort(key=lambda x: x["enhanced_score"], reverse=True)
            final_results = results[:limit]
            
            logger.info(f"Enhanced semantic search found {len(final_results)} relevant documents")
            return final_results
            
        except Exception as e:
            logger.error(f"Failed to perform enhanced semantic search: {e}")
            return []

    def _calculate_enhanced_score(self, base_score: float, payload: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
        """Calculate enhanced relevance score based on multiple factors."""
        score = base_score
        
        # Boost for matching query type
        query_type = query_analysis['query_type']
        section_type = payload.get('section_type', '')
        
        if query_type == 'requirement' and 'requirement' in section_type:
            score += 0.2
        elif query_type == 'calculation' and 'calculation' in section_type:
            score += 0.2
        elif query_type in ['energy', 'water', 'transport'] and payload.get('technical_content', False):
            score += 0.15
        
        # Boost for document type relevance
        doc_type = payload.get('document_type', '')
        if query_type == 'calculation' and doc_type in ['calculation', 'audit']:
            score += 0.1
        elif doc_type == 'report' and any(term in query_analysis['cleaned_query'] for term in ['summary', 'overview']):
            score += 0.1
        
        # Boost for category match
        if 'category' in query_analysis['filters']:
            expected_category = query_analysis['filters']['category'].replace('_*', '')
            if payload.get('category', '').startswith(expected_category):
                score += 0.3
        
        # Boost for content with units and numbers (technical queries)
        if query_type in ['energy', 'calculation'] and payload.get('contains_units', False):
            score += 0.1
        
        # Slight penalty for very short chunks (less context)
        chunk_length = payload.get('chunk_length', 0)
        if chunk_length < 200:
            score -= 0.05
        elif chunk_length > 800:  # Boost for longer, more detailed chunks
            score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0

    def hybrid_search(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword approaches."""
        try:
            # Get semantic results
            semantic_results = self.semantic_search(query, limit=limit)
            
            # For now, return semantic results (can be extended with keyword search)
            # Future enhancement: implement BM25 or similar keyword search and combine scores
            
            return semantic_results
            
        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            return []

    def similarity_search(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Main search interface - uses enhanced semantic search."""
        return self.semantic_search(query, limit)

    def get_collection_info(self) -> Dict[str, Any]:
        """Get enhanced information about the Qdrant collection."""
        try:
            collection_info = self.qdrant_client.get_collection(COLLECTION_NAME)
            points_count = collection_info.points_count
            
            # Get sample of points to analyze content distribution
            sample_points = self.qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=50,
                with_payload=True
            )[0]
            
            # Analyze content distribution
            stats = {
                'categories': {},
                'document_types': {},
                'section_types': {},
                'technical_content_ratio': 0,
                'avg_chunk_length': 0
            }
            
            total_length = 0
            technical_count = 0
            
            for point in sample_points:
                if point.payload:
                    # Count categories
                    category = point.payload.get('category', 'unknown')
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
                    
                    # Count document types
                    doc_type = point.payload.get('document_type', 'unknown')
                    stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1
                    
                    # Count section types
                    section_type = point.payload.get('section_type', 'unknown')
                    stats['section_types'][section_type] = stats['section_types'].get(section_type, 0) + 1
                    
                    # Technical content
                    if point.payload.get('technical_content', False):
                        technical_count += 1
                    
                    # Chunk length
                    chunk_length = point.payload.get('chunk_length', 0)
                    total_length += chunk_length
            
            if sample_points:
                stats['technical_content_ratio'] = technical_count / len(sample_points)
                stats['avg_chunk_length'] = total_length / len(sample_points)
            
            return {
                "collection_name": COLLECTION_NAME,
                "points_count": points_count,
                "status": "healthy",
                "sample_size": len(sample_points),
                "content_distribution": stats,
                "vectors_config": {
                    "size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get enhanced collection info: {e}")
            return {
                "collection_name": COLLECTION_NAME,
                "points_count": 0,
                "status": "error",
                "error": str(e)
            }


class InMemoryDocumentProcessor:
    """Enhanced fake processor for testing with better mock data."""
    
    def __init__(self):
        # Create more realistic test data
        self.docs = [
            {
                "content": "Energy efficiency requirements for buildings must meet the HEA-01 standards with thermal performance of 25 kWh/m² annually.",
                "file_name": "HEA_01_requirements.pdf",
                "category": "1_hea",
                "document_type": "audit",
                "section_type": "requirement_section",
                "technical_content": True,
                "contains_units": True
            },
            {
                "content": "Water system calculations show consumption of 150 L/day per person for the building complex according to WAT-02 analysis.",
                "file_name": "WAT_02_calculations.xlsx",
                "category": "4_wat",
                "document_type": "calculation",
                "section_type": "calculation_section",
                "technical_content": True,
                "contains_units": True
            },
            {
                "content": "Transport accessibility assessment indicates compliance with local regulations for public access and mobility standards.",
                "file_name": "TRA_01_assessment.docx",
                "category": "3_tra",
                "document_type": "assessment",
                "section_type": "content_section",
                "technical_content": False,
                "contains_units": False
            }
        ]
        logger.info("✅ Enhanced InMemoryDocumentProcessor initialized with realistic test data")

    def similarity_search(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Enhanced mock search with better scoring."""
        query_lower = query.lower()
        scored = []
        
        for doc in self.docs:
            score = 0.5  # Base score
            
            # Simple keyword matching
            content_lower = doc["content"].lower()
            for word in query_lower.split():
                if word in content_lower:
                    score += 0.1
            
            # Category matching
            if any(cat in query_lower for cat in ['hea', 'wat', 'tra', 'ene']):
                for cat in ['hea', 'wat', 'tra', 'ene']:
                    if cat in query_lower and cat in doc.get("category", ""):
                        score += 0.3
            
            # Technical content boost
            if any(term in query_lower for term in ['energy', 'calculation', 'requirement']) and doc.get("technical_content", False):
                score += 0.2
            
            if score > 0.5:  # Only return relevant results
                result_doc = dict(doc)
                result_doc["score"] = score
                result_doc["enhanced_score"] = score
                result_doc["original_score"] = score
                scored.append(result_doc)
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def get_collection_info(self) -> Dict[str, Any]:
        """Mock collection info."""
        return {
            "collection_name": COLLECTION_NAME,
            "points_count": len(self.docs),
            "status": "fake_service",
            "content_distribution": {
                "categories": {"1_hea": 1, "4_wat": 1, "3_tra": 1},
                "document_types": {"audit": 1, "calculation": 1, "assessment": 1}
            }
        }
