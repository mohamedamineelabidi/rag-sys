"""
Enhanced Query Processor with Intelligent Filtering and Retrieval

This module implements advanced query processing that leverages the rich metadata
structure created by the intelligent ingestion pipeline.

Key Features:
- Category-aware filtering for precise retrieval
- Query intent detection and preprocessing
- Hybrid search combining vector similarity and metadata filtering
- Confidence scoring and result ranking
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny
import openai

logger = logging.getLogger(__name__)

class EnhancedQueryProcessor:
    """Advanced query processor with metadata-aware retrieval."""
    
    def __init__(self, qdrant_client: QdrantClient, collection_name: str, openai_client, embedding_model: str):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        
        # Category keywords for intent detection
        self.category_keywords = {
            "Health & Environmental Assessment": [
                "health", "environmental", "assessment", "impact", "risk", "safety", 
                "hazard", "exposure", "contamination", "air quality", "noise"
            ],
            "Energy & Efficiency": [
                "energy", "efficiency", "consumption", "power", "electricity", "heating",
                "cooling", "hvac", "renewable", "solar", "thermal", "insulation"
            ],
            "Transport & Accessibility": [
                "transport", "transportation", "accessibility", "traffic", "mobility",
                "parking", "public transport", "cycling", "walking", "infrastructure"
            ],
            "Water Management": [
                "water", "drainage", "plumbing", "sanitary", "sewage", "stormwater",
                "consumption", "supply", "treatment", "quality", "management"
            ],
            "Resource Scarcity & Management": [
                "resource", "scarcity", "management", "materials", "waste", "recycling",
                "circular economy", "consumption", "availability", "supply"
            ],
            "Resilience & Sustainability": [
                "resilience", "sustainability", "sustainable", "climate", "adaptation",
                "mitigation", "future", "long-term", "durable", "robust"
            ],
            "Land Use & Environment": [
                "land use", "environment", "landscape", "green space", "biodiversity",
                "ecology", "vegetation", "soil", "site", "planning"
            ],
            "Pollution & Environmental Impact": [
                "pollution", "environmental impact", "emissions", "carbon", "co2",
                "waste", "contamination", "environmental", "impact assessment"
            ]
        }
    
    def detect_query_intent(self, query: str) -> Tuple[List[str], float]:
        """
        Detect which categories the query might be related to.
        Returns a list of relevant categories and a confidence score.
        """
        query_lower = query.lower()
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    # Weight longer keywords higher
                    score += len(keyword.split())
            
            if score > 0:
                category_scores[category] = score
        
        # Sort by score and return top categories
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_categories:
            return [], 0.0
        
        # Return categories with highest scores
        max_score = sorted_categories[0][1]
        relevant_categories = [cat for cat, score in sorted_categories if score >= max_score * 0.7]
        confidence = min(max_score / 3.0, 1.0)  # Normalize confidence
        
        return relevant_categories, confidence
    
    def preprocess_query(self, query: str) -> str:
        """Preprocess the query to improve search performance."""
        # Expand common abbreviations
        abbreviations = {
            "hvac": "heating ventilation air conditioning",
            "co2": "carbon dioxide",
            "led": "light emitting diode",
            "kwh": "kilowatt hour",
            "m2": "square meter",
            "sq m": "square meter",
        }
        
        processed_query = query.lower()
        for abbr, expansion in abbreviations.items():
            processed_query = processed_query.replace(abbr, f"{abbr} {expansion}")
        
        return processed_query
    
    def create_metadata_filter(self, categories: List[str] = None, 
                             document_types: List[str] = None,
                             file_names: List[str] = None) -> Optional[Filter]:
        """Create a Qdrant filter based on metadata criteria."""
        conditions = []
        
        if categories:
            conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchAny(any=categories)
                )
            )
        
        if document_types:
            conditions.append(
                FieldCondition(
                    key="document_type", 
                    match=MatchAny(any=document_types)
                )
            )
        
        if file_names:
            conditions.append(
                FieldCondition(
                    key="file_name",
                    match=MatchAny(any=file_names)
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        
        return None
    
    def search_with_metadata(self, query: str, limit: int = 10, 
                           auto_filter: bool = True,
                           categories: List[str] = None,
                           document_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Perform enhanced search using both vector similarity and metadata filtering.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            auto_filter: Whether to automatically detect and filter by categories
            categories: Explicit categories to filter by
            document_types: Document types to filter by
            
        Returns:
            List of search results with enhanced metadata and scoring
        """
        try:
            # Preprocess the query
            processed_query = self.preprocess_query(query)
            
            # Detect query intent if auto-filtering is enabled
            detected_categories = []
            category_confidence = 0.0
            
            if auto_filter and not categories:
                detected_categories, category_confidence = self.detect_query_intent(query)
                if detected_categories and category_confidence > 0.3:
                    categories = detected_categories
                    logger.info(f"Auto-detected categories: {categories} (confidence: {category_confidence:.2f})")
            
            # Create metadata filter
            metadata_filter = self.create_metadata_filter(
                categories=categories,
                document_types=document_types
            )
            
            # Generate query embedding
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=processed_query
            )
            query_vector = response.data[0].embedding
            
            # Perform the search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=metadata_filter,
                limit=limit * 2,  # Get more results for post-processing
                with_payload=True,
                with_vectors=False,
                score_threshold=0.3  # Only return reasonably relevant results
            )
            
            # Enhance results with additional scoring
            enhanced_results = []
            for result in search_results:
                enhanced_result = {
                    "content": result.payload["content"],
                    "metadata": {
                        "file_name": result.payload.get("file_name", ""),
                        "category": result.payload.get("category", ""),
                        "document_type": result.payload.get("document_type", ""),
                        "page_number": result.payload.get("page_number"),
                        "technical_keywords": result.payload.get("technical_keywords", []),
                        "relative_path": result.payload.get("relative_path", ""),
                        "chunk_index": result.payload.get("chunk_index", 0),
                        "total_chunks": result.payload.get("total_chunks", 1),
                    },
                    "vector_score": result.score,
                    "category_match": result.payload.get("category") in (categories or []),
                    "category_confidence": category_confidence if auto_filter else 1.0,
                }
                
                # Calculate enhanced relevance score
                relevance_score = result.score
                
                # Boost score if category matches detected intent
                if enhanced_result["category_match"] and auto_filter:
                    relevance_score *= (1 + category_confidence * 0.5)
                
                # Boost score for technical keyword matches
                content_lower = result.payload["content"].lower()
                query_lower = query.lower()
                keyword_matches = sum(1 for word in query_lower.split() 
                                    if len(word) > 3 and word in content_lower)
                if keyword_matches > 0:
                    relevance_score *= (1 + keyword_matches * 0.1)
                
                enhanced_result["relevance_score"] = relevance_score
                enhanced_results.append(enhanced_result)
            
            # Sort by enhanced relevance score and return top results
            enhanced_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return enhanced_results[:limit]
            
        except Exception as e:
            logger.error(f"Error in enhanced search: {e}")
            return []
    
    def get_category_summary(self) -> Dict[str, int]:
        """Get a summary of available categories and document counts."""
        try:
            # Use Qdrant's scroll API to get a sample of documents
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Sample size
                with_payload=["category"]
            )
            
            category_counts = {}
            for point in scroll_result[0]:
                category = point.payload.get("category", "Unknown")
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return category_counts
            
        except Exception as e:
            logger.error(f"Error getting category summary: {e}")
            return {}
    
    def search_by_document(self, file_name: str, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Search within a specific document."""
        if query:
            return self.search_with_metadata(
                query=query,
                limit=limit,
                auto_filter=False,
                file_names=[file_name]
            )
        else:
            # Return all chunks from the document
            try:
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="file_name",
                            match=MatchValue(value=file_name)
                        )
                    ]
                )
                
                scroll_result = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter_condition,
                    limit=limit,
                    with_payload=True
                )
                
                results = []
                for point in scroll_result[0]:
                    results.append({
                        "content": point.payload["content"],
                        "metadata": {
                            "file_name": point.payload.get("file_name", ""),
                            "page_number": point.payload.get("page_number"),
                            "chunk_index": point.payload.get("chunk_index", 0),
                        },
                        "vector_score": 1.0,  # No vector search performed
                        "relevance_score": 1.0
                    })
                
                return results
                
            except Exception as e:
                logger.error(f"Error searching by document: {e}")
                return []
