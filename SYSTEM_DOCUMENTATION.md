# System Documentation

Technical documentation for the RAG Document Assistant system architecture, components, and implementation details.

## Table of Contents

- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Configuration](#configuration)
- [Data Flow](#data-flow)
- [API Endpoints](#api-endpoints)
- [Data Structures](#data-structures)
- [Troubleshooting](#troubleshooting)
- [Performance Considerations](#performance-considerations)

## System Architecture

### Technology Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Frontend | Streamlit | Interactive web interface |
| Backend | FastAPI | Async REST API server |
| Vector Database | Qdrant Cloud | Scalable vector similarity search |
| Embeddings | Azure OpenAI | text-embedding-3-small (1536 dimensions) |
| LLM | Azure OpenAI | GPT-4 for answer generation |
| Document Processing | LangChain | Document loaders and text splitters |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                    ┌─────────────────────────┐ │
│  │   Streamlit UI      │                    │    Direct API Calls     │ │
│  │   (Port 8501)       │                    │    (curl, SDK, etc.)    │ │
│  └──────────┬──────────┘                    └────────────┬────────────┘ │
└─────────────┼──────────────────────────────────────────────┼────────────┘
              │                                              │
              └────────────────────┬─────────────────────────┘
                                   │ HTTP/REST
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                           │   │
│  │                    (backend/main.py)                             │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │/ask     │  │/search  │  │/health  │  │/stats   │            │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │   │
│  └───────┼────────────┼────────────┼────────────┼──────────────────┘   │
└──────────┼────────────┼────────────┼────────────┼───────────────────────┘
           │            │            │            │
           └────────────┴─────┬──────┴────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐        ┌────────────────────────────────┐  │
│  │  AdvancedRAGService    │        │  EnhancedQdrantQueryProcessor  │  │
│  │  - Context processing  │        │  - Semantic search             │  │
│  │  - Answer generation   │───────▶│  - Query preprocessing         │  │
│  │  - Confidence scoring  │        │  - Result reranking            │  │
│  └───────────┬────────────┘        └───────────────┬────────────────┘  │
│              │                                      │                   │
└──────────────┼──────────────────────────────────────┼───────────────────┘
               │                                      │
               ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Services                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐        ┌────────────────────────────────┐  │
│  │    Azure OpenAI        │        │        Qdrant Cloud            │  │
│  │  - Chat completions    │        │  - Vector storage              │  │
│  │  - Text embeddings     │        │  - Similarity search           │  │
│  └────────────────────────┘        └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Backend Application (`backend/main.py`)

The FastAPI application that handles all API requests.

**Key Features:**
- Lifespan management for service initialization
- CORS middleware for cross-origin requests
- Error handling and logging
- Health monitoring endpoints

**Startup Sequence:**
1. Validate environment variables
2. Initialize document processor
3. Initialize RAG service
4. Verify Qdrant connection
5. Start accepting requests

### 2. RAG Service (`backend/enhanced_rag_service.py`)

The core RAG pipeline that processes questions and generates answers.

**Classes:**

| Class | Purpose |
|-------|---------|
| `ContextProcessor` | Consolidates search results into structured context |
| `AdvancedRAGService` | Main RAG orchestration and answer generation |

**Key Methods:**
- `ask_question()`: Process a question through the full RAG pipeline
- `search_documents()`: Perform document search without answer generation
- `_assess_response_confidence()`: Calculate confidence scores

### 3. Query Processor (`backend/enhanced_query_processor.py`)

Handles document retrieval with advanced search capabilities.

**Features:**
- Query preprocessing and analysis
- Semantic search with Qdrant
- Score-based reranking
- Category-aware filtering

### 4. Intelligent Query Processor (`backend/intelligent_query_processor.py`)

Advanced query processing with metadata-aware retrieval.

**Features:**
- Query intent detection
- Automatic category filtering
- Query expansion for better recall

### 5. Data Models (`backend/models.py`)

Pydantic models for request/response validation.

**Key Models:**

| Model | Purpose |
|-------|---------|
| `QuestionRequest` | Incoming question with context |
| `RAGResponse` | Complete response with answer and metadata |
| `Source` | Document source information |
| `AnswerMetadata` | Response metadata including confidence |

### 6. Data Ingestion (`scripts/ingest_data.py`)

Standalone script for document processing and indexing.

**Features:**
- Incremental indexing with cache
- Multi-format document support
- Metadata extraction
- Batch processing for efficiency

## Configuration

### Environment Variables

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | `https://xxx.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `sk-...` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | Chat model deployment name | `gpt-4` |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME` | Embedding model deployment | `text-embedding-3-small` |
| `OPENAI_API_VERSION` | API version | `2024-02-15-preview` |
| `QDRANT_URL` | Qdrant Cloud URL | `https://xxx.qdrant.io` |
| `QDRANT_API_KEY` | Qdrant API key | `...` |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_COLLECTION_NAME` | `documents` | Vector collection name |
| `USE_INDEXING_CACHE` | `true` | Enable incremental indexing |
| `SYNC_DELETIONS_ON_STARTUP` | `true` | Remove deleted files from index |
| `CHUNK_SIZE` | `1000` | Document chunk size |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `EMBEDDING_SIZE` | `1536` | Embedding vector dimensions |
| `USE_FAKE_SERVICES` | `false` | Enable test mode |

### Configuration Validation

The `backend/config.py` module validates configuration at startup:

```python
from backend.config import validate_required_env, get_runtime_config

# Validates all required environment variables
validate_required_env()

# Returns non-secret configuration for debugging
config = get_runtime_config()
```

## Data Flow

### Question Answering Flow

```
1. User submits question
   │
   ▼
2. Query preprocessing
   - Clean and normalize query
   - Detect query type/domain
   - Extract key terms
   │
   ▼
3. Document retrieval
   - Generate query embedding
   - Search Qdrant for similar vectors
   - Apply metadata filters
   - Rerank results by relevance
   │
   ▼
4. Context consolidation
   - Group results by relevance tier
   - Build structured context
   - Calculate context statistics
   │
   ▼
5. Answer generation
   - Select domain-appropriate prompt
   - Send context + question to LLM
   - Generate response
   │
   ▼
6. Response enrichment
   - Assess confidence level
   - Generate follow-up questions
   - Compile source attribution
   │
   ▼
7. Return RAGResponse
```

### Document Ingestion Flow

```
1. Scan data directory
   │
   ▼
2. Check indexing cache
   - Identify new/modified files
   - Identify deleted files
   │
   ▼
3. Process new documents
   - Load with appropriate loader
   - Extract text content
   - Split into chunks
   │
   ▼
4. Generate embeddings
   - Batch embedding calls
   - Fallback to per-chunk on failure
   │
   ▼
5. Store in Qdrant
   - Generate UUIDs
   - Attach metadata
   - Batch upsert
   │
   ▼
6. Update cache
   - Record processed files
   - Remove deleted entries
```

## API Endpoints

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthcheck` | Service health status |
| `GET` | `/collection-status` | Qdrant collection information |
| `GET` | `/runtime-config` | Non-secret configuration values |
| `POST` | `/ask` | Submit question for RAG processing |
| `GET` | `/search` | Raw semantic search |
| `GET` | `/intelligent-search` | Search with category filtering |
| `GET` | `/categories` | Available document categories |
| `GET` | `/stats` | System statistics |

### Request/Response Examples

**Ask Question:**
```json
// POST /ask
{
  "question": "What are the energy efficiency requirements?",
  "max_sources": 4,
  "include_metadata": true,
  "session_id": "optional-session-id"
}

// Response
{
  "answer": "Based on the documents...",
  "sources": [
    {
      "file_name": "energy_requirements.pdf",
      "content": "...",
      "score": 0.85,
      "source_type": "pdf"
    }
  ],
  "metadata": {
    "processing_time": 1.23,
    "sources_count": 4,
    "confidence_level": "high",
    "reasoning": "Based on multiple primary sources"
  },
  "follow_up_questions": [
    {
      "question": "What are the specific efficiency targets?",
      "reasoning": "Domain-specific inquiry"
    }
  ]
}
```

## Data Structures

### Vector Storage Schema

Each document chunk is stored with:

```json
{
  "id": "uuid-v4",
  "vector": [0.1, 0.2, ...],  // 1536 dimensions
  "payload": {
    "content": "Document text...",
    "file_name": "document.pdf",
    "category": "energy",
    "document_type": "requirement",
    "section_type": "content_section",
    "technical_content": true,
    "chunk_length": 850
  }
}
```

### Supported Document Formats

| Format | Extension | Loader |
|--------|-----------|--------|
| PDF | `.pdf` | PyMuPDFLoader / UnstructuredPDFLoader |
| Word | `.docx` | Docx2txtLoader |
| Text | `.txt` | TextLoader |
| Excel | `.xlsx` | UnstructuredExcelLoader |

## Troubleshooting

### Common Issues

#### 1. Connection Errors

**Symptom:** `Failed to initialize Qdrant client`

**Solutions:**
- Verify `QDRANT_URL` format (include `https://`)
- Check `QDRANT_API_KEY` validity
- Ensure network connectivity to Qdrant Cloud

#### 2. Embedding Errors

**Symptom:** `Failed to create embedding`

**Solutions:**
- Verify Azure OpenAI credentials
- Check deployment name matches Azure portal
- Ensure API version is correct

#### 3. No Search Results

**Symptom:** Queries return empty results

**Solutions:**
- Run `python scripts/check_document_count.py` to verify data
- Check score threshold (default 0.3)
- Re-index documents with `--rescan` flag

#### 4. Slow Performance

**Symptom:** High response latency

**Solutions:**
- Reduce `max_sources` in requests
- Check network latency to cloud services
- Consider implementing query caching

### Diagnostic Commands

```bash
# Check document count in Qdrant
python scripts/check_document_count.py

# Run comprehensive diagnostics
python scripts/diagnose_rag.py

# Get performance recommendations
python scripts/enhance_rag_performance.py
```

## Performance Considerations

### Optimization Strategies

1. **Chunking Parameters**
   - Smaller chunks (500-800 chars) for precise retrieval
   - Larger overlap (150-250 chars) for context preservation

2. **Batch Operations**
   - Embeddings generated in batches
   - Qdrant upserts batched for efficiency

3. **Caching**
   - Incremental indexing cache prevents reprocessing
   - Consider Redis for query result caching

4. **Retrieval Tuning**
   - Adjust `score_threshold` based on data distribution
   - Use category filters to narrow search scope

### Scalability Notes

- **Horizontal Scaling**: Deploy multiple API instances behind load balancer
- **Database Sharding**: Qdrant supports distributed deployments
- **Async Processing**: FastAPI handles concurrent requests efficiently

---

For user-facing documentation, see [README.md](README.md).
