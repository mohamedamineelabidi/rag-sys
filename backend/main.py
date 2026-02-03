import asyncio
import os
import logging
import time
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.models import (
    QuestionRequest, RAGResponse, HealthCheckResponse, SearchResult,
    Source, SourceType, ConfidenceLevel, AnswerMetadata, FollowUpQuestion
)
from backend.enhanced_rag_service import AdvancedRAGService
from backend.enhanced_query_processor import EnhancedQdrantQueryProcessor, InMemoryDocumentProcessor
from backend.intelligent_query_processor import EnhancedQueryProcessor
from backend.config import validate_required_env, get_runtime_config

# --- App State and Services ---
app_state = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On Startup
    logger.info("=== RAG Document Assistant Starting Up ===")
    
    # Validate environment early
    try:
        validate_required_env()
    except EnvironmentError as e:
        logger.error(f"Environment validation failed: {e}")
        raise

    # Initialize services first, so they are available immediately
    logger.info("Initializing Document Processor and RAG Service...")
    if os.environ.get("USE_FAKE_SERVICES", "false").lower() == "true":
        logger.info("Using InMemoryDocumentProcessor (fake services mode)")
        doc_processor = InMemoryDocumentProcessor()
    else:
        doc_processor = EnhancedQdrantQueryProcessor()
    app_state["rag_service"] = AdvancedRAGService(doc_processor)
    app_state["doc_processor"] = doc_processor
    
    # Get collection info
    try:
        collection_info = doc_processor.get_collection_info()
        logger.info(f"Qdrant Collection Status: {collection_info.get('points_count', 0)} documents indexed")
    except Exception as e:
        logger.warning(f"Could not get collection info: {e}")
    
    # Note: Document ingestion is now handled separately by scripts/ingest_data.py
    # The backend server only handles search and retrieval operations
    logger.info("Document ingestion is handled separately by 'python scripts/ingest_data.py'")
    logger.info("This server handles only search and retrieval operations")
    
    logger.info("=== Server Ready - API endpoints available ===")
    yield
    
    # On Shutdown
    logger.info("=== Server shutting down ===")
    app_state.clear()


# --- App Initialization ---
app = FastAPI(
    title="RAG Document Assistant API",
    description="API for a Retrieval-Augmented Generation system.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "./Data"  # Updated to match our project structure


# --- API Endpoints ---
@app.get("/healthcheck", response_model=HealthCheckResponse, tags=["Health"])
def healthcheck():
    try:
        doc_processor = app_state["doc_processor"]
        collection_info = doc_processor.get_collection_info()
        return HealthCheckResponse(
            status="ok",
            message=f"API healthy. {collection_info.get('points_count', 0)} documents indexed."
        )
    except Exception as e:
        logger.error(f"Healthcheck failed: {e}")
        return HealthCheckResponse(status="ok", message="API healthy but collection info unavailable")


@app.get("/runtime-config", tags=["Health"])
def runtime_config():
    return {"config": get_runtime_config()}


@app.get("/collection-status", tags=["Health"])
def get_collection_status():
    """Get detailed information about the Qdrant collection."""
    try:
        doc_processor = app_state["doc_processor"]
        collection_info = doc_processor.get_collection_info()
        return {
            "status": "success",
            "collection_info": collection_info,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection status: {str(e)}")


@app.post("/ask", response_model=RAGResponse, tags=["RAG"])
def ask_question(request: QuestionRequest):
    try:
        rag_service: AdvancedRAGService = app_state["rag_service"]
        response = rag_service.ask_question(request)
        return response
    except Exception as e:
        logger.error(f"Error during question answering: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@app.post("/rescan", tags=["Documents"])
def force_rescan():
    """Note: Rescan functionality is now handled by scripts/ingest_data.py"""
    return {
        "status": "deprecated", 
        "message": "Document ingestion is now handled separately. Use 'python scripts/ingest_data.py --rescan' to reindex documents."
    }


@app.get("/search", response_model=SearchResult, tags=["RAG"])
def raw_search(q: str, limit: int = 5):
    try:
        start_time = time.time()
        rag_service: AdvancedRAGService = app_state["rag_service"]
        results = rag_service.search_documents(q, limit=limit)
        
        # Convert to Source objects
        from backend.models import Source, SourceType
        enhanced_sources = []
        for result in results:
            # Detect source type
            extension = result["file_name"].lower().split('.')[-1] if '.' in result["file_name"] else ''
            type_mapping = {
                'pdf': SourceType.PDF,
                'docx': SourceType.DOCX,
                'txt': SourceType.TXT,
                'xlsx': SourceType.XLSX,
                'jpg': SourceType.IMAGE,
                'png': SourceType.IMAGE
            }
            source_type = type_mapping.get(extension, SourceType.OTHER)
            
            enhanced_sources.append(Source(
                file_name=result["file_name"],
                content=result["content"],
                score=result.get("score", 0.0),  # Use .get for safety
                source_type=source_type
            ))
        
        search_time = round((time.time() - start_time) * 1000, 2)
        
        return SearchResult(
            query=q,
            results=enhanced_sources,
            total_found=len(results),
            search_time_ms=search_time
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/upload", tags=["Documents"])
async def upload_documents(files: List[UploadFile] = File(...)):
    """Note: Document upload and indexing is now handled by scripts/ingest_data.py"""
    return {
        "status": "deprecated",
        "message": "Document upload is now handled separately. Copy files to the Data directory and run 'python scripts/ingest_data.py' to index them."
    }


@app.get("/models-test", tags=["Debug"])
def test_models():
    """Test endpoint to validate model compatibility"""
    try:
        # Create a sample request
        request = QuestionRequest(
            question="Test question",
            session_id="test-session",
            max_sources=3
        )
        
        # Create a sample response
        source = Source(
            file_name="test.pdf",
            content="Test content",
            score=0.95,
            source_type=SourceType.PDF
        )
        
        follow_up = FollowUpQuestion(
            question="Follow-up question?",
            reasoning="Test reasoning"
        )
        
        metadata = AnswerMetadata(
            processing_time=0.5,
            sources_count=1,
            reasoning="Test reasoning",
            confidence_level=ConfidenceLevel.HIGH
        )
        
        response = RAGResponse(
            answer="Test answer",
            sources=[source],
            confidence=ConfidenceLevel.HIGH,
            metadata=metadata,
            follow_up_questions=[follow_up],
            session_id="test-session"
        )
        
        return {
            "status": "ok",
            "message": "Models validated successfully",
            "request_sample": request,
            "response_sample": response
        }
        
    except Exception as e:
        logger.error(f"Models validation failed: {e}")
        return {
            "status": "error",
            "message": f"Models validation failed: {str(e)}"
        }


@app.get("/conversation/{conversation_id}", tags=["Chat"])
def get_conversation_history(conversation_id: str):
    """Get conversation history for a specific conversation ID"""
    # This would typically be stored in a database
    # For now, return a placeholder response
    return {
        "conversation_id": conversation_id,
        "messages": [],
        "created_at": time.time(),
        "last_updated": time.time()
    }


@app.post("/conversation/{conversation_id}/summarize", tags=["Chat"])
def summarize_conversation(conversation_id: str):
    """Generate a summary of the conversation"""
    from backend.models import ConversationSummary
    # This would typically analyze stored conversation data
    return ConversationSummary(
        main_topics=["Energy efficiency", "Building analysis"],
        key_findings=["No specific findings available"],
        document_coverage={},
        total_messages=0
    )


@app.get("/intelligent-search", tags=["RAG"])
def intelligent_search(
    q: str, 
    limit: int = 5,
    categories: str = None,
    document_types: str = None,
    auto_filter: bool = True
):
    """
    Enhanced search with intelligent category filtering and metadata awareness.
    
    Args:
        q: Search query
        limit: Maximum number of results
        categories: Comma-separated list of categories to filter by
        document_types: Comma-separated list of document types (PDF, DOCX, etc.)
        auto_filter: Whether to automatically detect and filter by categories
    """
    try:
        start_time = time.time()
        
        # Initialize the intelligent query processor if not already done
        if "intelligent_processor" not in app_state:
            from openai import AzureOpenAI
            from qdrant_client import QdrantClient
            
            openai_client = AzureOpenAI(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_version=os.environ["OPENAI_API_VERSION"],
            )
            
            qdrant_client = QdrantClient(
                url=os.environ["QDRANT_URL"],
                api_key=os.environ.get("QDRANT_API_KEY"),
            )
            
            app_state["intelligent_processor"] = EnhancedQueryProcessor(
                qdrant_client=qdrant_client,
                collection_name=os.environ["QDRANT_COLLECTION_NAME"],
                openai_client=openai_client,
                embedding_model=os.environ["AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME"]
            )
        
        intelligent_processor = app_state["intelligent_processor"]
        
        # Parse categories and document types
        category_list = [c.strip() for c in categories.split(",")] if categories else None
        doc_type_list = [d.strip() for d in document_types.split(",")] if document_types else None
        
        # Perform intelligent search
        results = intelligent_processor.search_with_metadata(
            query=q,
            limit=limit,
            auto_filter=auto_filter,
            categories=category_list,
            document_types=doc_type_list
        )
        
        processing_time = time.time() - start_time
        
        return {
            "query": q,
            "results": results,
            "metadata": {
                "total_results": len(results),
                "processing_time_ms": round(processing_time * 1000, 2),
                "auto_filter_applied": auto_filter,
                "filtered_categories": category_list,
                "filtered_document_types": doc_type_list
            }
        }
        
    except Exception as e:
        logger.error(f"Error in intelligent search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/categories", tags=["Analytics"])  
def get_available_categories():
    """Get a summary of available document categories."""
    try:
        if "intelligent_processor" not in app_state:
            # Initialize if needed
            intelligent_search("test", limit=1)  # This will initialize the processor
        
        intelligent_processor = app_state["intelligent_processor"]
        category_summary = intelligent_processor.get_category_summary()
        
        return {
            "categories": category_summary,
            "total_categories": len(category_summary),
            "available_filters": list(category_summary.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return {
            "categories": {},
            "total_categories": 0,
            "available_filters": []
        }


@app.get("/stats", tags=["Analytics"])
def get_system_stats():
    """Get system usage statistics"""
    from backend.models import SystemStats
    try:
        doc_processor = app_state["doc_processor"]
        collection_info = doc_processor.get_collection_info()
        
        return SystemStats(
            total_documents=collection_info.get('points_count', 0),
            total_queries_today=0,  # Would track in production
            avg_response_time_ms=500.0,  # Would calculate from stored data
            most_common_topics=[],
            system_health="healthy"
        )
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return SystemStats(
            total_documents=0,
            total_queries_today=0,
            avg_response_time_ms=0.0,
            most_common_topics=[],
            system_health="unknown"
        )
