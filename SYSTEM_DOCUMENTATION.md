# RAG System Documentation

## Overview
This document provides comprehensive information about the Retrieval-Augmented Generation (RAG) system that was successfully migrated from ChromaDB to Qdrant Cloud.

## System Architecture

### Technology Stack
- **Backend Framework**: FastAPI
- **Vector Database**: Qdrant Cloud (EU-West-2 region)
- **Embeddings Model**: Azure OpenAI text-embedding-3-small (1536 dimensions)
- **LLM**: Azure OpenAI GPT-4
- **Document Processing**: LangChain with custom processors
- **Frontend**: Streamlit
- **Environment**: Python 3.11 with virtual environment

### Core Components

#### 1. Document Processor (`backend/document_processor.py`)
**Classes**:
- `QdrantDocumentProcessor`: production implementation using Qdrant & Azure OpenAI.
- `InMemoryDocumentProcessor`: lightweight fake implementation used when `USE_FAKE_SERVICES=true` (for offline tests).

**Supported Formats**: PDF, XLSX, DOCX, TXT (images are skipped currently).

**Key Features** (current):
   - Configurable chunking via `CHUNK_SIZE` / `CHUNK_OVERLAP` (defaults 1000 / 200, overlap auto-adjusted if invalid)
   - Batch embedding (falls back to per-chunk) with retry logic for transient failures
   - Incremental indexing using a persistent shelve cache (`indexing_cache.py`) controlled by `USE_INDEXING_CACHE`
   - Optional deletion sync of removed files via `SYNC_DELETIONS_ON_STARTUP`
   - Targeted indexing of specific subdirectories using `INDEXING_INCLUDE_DIRS` (comma-separated)
   - Batch upserts (`QDRANT_UPSERT_BATCH`) & deletions (`QDRANT_DELETE_BATCH`)
   - Full rescan bypassing cache (`POST /rescan`)
   - Payload index on `file_path` for efficient deletions
   - Environment variable fallback for embedding deployment name (supports both plural & singular naming)

#### 2. RAG Service (`backend/rag_service.py`)
**Class**: `RAGService`

**Behavior**:
- Real mode: uses Azure Chat model (deployment from `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` or fallback variable `AZURE_OPENAI_GPT_DEPLOYMENT_NAME`).
- Fake mode (`USE_FAKE_SERVICES=true`): returns a deterministic placeholder answer concatenating source filenames (no external calls).

**Features**:
- Similarity search (Qdrant or in-memory) → top-k context assembly.
- Prompt template enforces grounding; declines if no supporting context.
- Adjustable temperature & token limit (currently set low for factual answers).

#### 3. Data Models (`backend/models.py`)
- **Purpose**: Defines data structures for sources and responses
- **Classes**: `Source`, response models for API consistency

#### 4. Main API (`backend/main.py`)
**Framework**: FastAPI with lifespan startup tasks and permissive CORS.

**Endpoints (current)**:
| Method | Path | Description |
|--------|------|-------------|
| GET | /healthcheck | Basic service & index summary |
| GET | /runtime-config | Returns safe runtime configuration snapshot |
| GET | /collection-status | Detailed Qdrant collection info |
| POST | /ask | Ask a question (RAG pipeline) |
| GET | /search?q=... | Raw similarity search (debug) |
| POST | /rescan | Force full re-index (ignores cache) |
| POST | /upload | Upload & background process documents |

## Migration Details

### From ChromaDB to Qdrant Cloud

#### Previous Setup (ChromaDB)
- Local vector database storage
- Embedding dimension mismatch issues
- Limited scalability and cloud integration

#### Current Setup (Qdrant Cloud)
- **Cloud Provider**: Qdrant Cloud
- **Region**: EU-West-2
- **Collection Name**: "documents"
- **Vector Size**: 1536 dimensions
- **Distance Metric**: Cosine similarity
- **API Authentication**: Secured with API key

#### Migration Process
1. **Environment Setup**: Updated `.env` with Qdrant Cloud credentials
2. **Code Refactoring**: Complete rewrite of document processor
3. **Collection Configuration**: Proper vector size matching Azure OpenAI embeddings
4. **Testing**: Comprehensive validation with real document data

## Configuration

### Environment Variables (Key Set)
The system supports backward compatibility for some variable names.

```bash
# Qdrant
QDRANT_URL=...                # Required (unless USE_FAKE_SERVICES=true)
QDRANT_API_KEY=...            # Required
QDRANT_COLLECTION_NAME=documents

# Azure OpenAI (real mode)
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
# Embeddings deployment (either name accepted)
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=text-embedding-3-small
# Fallback legacy name supported automatically:
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small

# Chat deployment (either name accepted)
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt4-chat
# Fallback legacy alternative:
# AZURE_OPENAI_GPT_DEPLOYMENT_NAME=gpt4-chat

OPENAI_API_VERSION=2025-01-01-preview

# Indexing behavior
USE_INDEXING_CACHE=true
SYNC_DELETIONS_ON_STARTUP=true
SKIP_STARTUP_SCAN=false
INDEXING_INCLUDE_DIRS=
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
QDRANT_UPSERT_BATCH=256
QDRANT_DELETE_BATCH=100

# Local / test mode
USE_FAKE_SERVICES=false  # When true: skips external calls & uses in-memory index/answers
```

### Dependencies (Pinned)
See `backend/requirements.txt` for authoritative list (includes batch processing & testing libs).

## Testing Results

### Test Data Location
- **Primary Test Folder**: `Data/1_HEA/HEA_01`
- **Document Types**: PDF, XLSX, images (images skipped)
- **Total Files Processed**: 13 documents
- **Total Chunks Generated**: 423 chunks

### Document Processing Results
```
✅ HEA 01 audit secotherm page 55-1708072.pdf → 411 chunks
✅ HEA 01_Daylighting Boulevard Haussman.xlsx → 6 chunks
✅ HEA 01_Plan de surfaces.pdf → 3 chunks
✅ HEA 01_Plan R0.pdf → 1 chunk
✅ HEA 01_Plan R6.pdf → 1 chunk
✅ HEA 01_Plan R7.pdf → 1 chunk
⚠️ Several elevation/plan PDFs → 0 chunks (no extractable text)
```

### RAG Query Testing (Sample Historical)
**Test Query**: "What is the building design and layout for HEA 01?"

**Results**:
- **Retrieved Documents**: 4 relevant chunks
- **Similarity Scores**: 0.528 - 0.432 (high relevance)
- **Answer Quality**: Comprehensive building information including:
  - Latitude and sunlight requirements (48.8°, 8% minimum)
  - Glazing percentages by façade orientation
  - Detailed surface measurements
  - Total building metrics

**Source Attribution**:
1. HEA 01_Daylighting Boulevard Haussman.xlsx (Score: 0.528)
2. HEA 01 audit secotherm page 55-1708072.pdf (Score: 0.436)

### Current Database Status (Example Snapshot)
- **Total Documents in Qdrant**: 834 chunks
- **Storage Location**: Qdrant Cloud (confirmed)
- **Collection Health**: ✅ Active and responsive
- **API Connectivity**: ✅ Functional

## Usage Instructions

### Starting the System (Real Mode)

1. **Activate Virtual Environment**:
   ```bash
   .\venv\Scripts\Activate.ps1
   ```

2. **Start Backend API**:
   ```bash
   cd rag-project
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start Frontend** (if needed):
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

### Document Processing

#### Single File Processing
```python
from backend.document_processor import QdrantDocumentProcessor
processor = QdrantDocumentProcessor()
processor.process_and_index_documents(["path/to/document.pdf"])
```

#### Batch Processing
```python
files_to_process = []
for file in os.listdir("Data/folder"):
    if file.lower().endswith(('.pdf', '.xlsx', '.docx', '.txt')):
        files_to_process.append(os.path.join("Data/folder", file))
processor.process_and_index_documents(files_to_process)
```

### Querying the System

#### Direct RAG Service Usage
```python
from backend.rag_service import RAGService
from backend.document_processor import QdrantDocumentProcessor

processor = QdrantDocumentProcessor()
rag = RAGService(processor)
answer, sources = rag.get_answer("Your question here")
```

#### API Endpoint Usage
```bash
curl -X POST "http://localhost:8000/ask" \
-H "Content-Type: application/json" \
-d '{"question": "Your question here"}'
```

## Performance & Behavior Notes

### Processing Performance (Indicative)
- Startup skip of unchanged files via cache (O(number of new/modified files)).
- Batch embeddings reduce round trips; fallback increases resilience.
- Deletion batches prevent large filter overloads.

### Accuracy Metrics
- **Retrieval Relevance**: High (scores > 0.4 for relevant content)
- **Answer Quality**: Comprehensive and factually accurate
- **Source Attribution**: Precise file and content mapping

## Data Structure

### Supported Document Types
- **PDF**: Text extraction with metadata preservation
- **XLSX**: Cell content and sheet structure
- **DOCX**: Text content with formatting
- **TXT**: Direct text processing

### Metadata Schema
```json
{
  "source": "filename.pdf",
  "file_name": "filename.pdf",
  "chunk_index": 0,
  "total_chunks": 100
}
```

### Vector Storage Schema
- **Vector Dimension**: 1536
- **Payload**: Document content + metadata
- **ID**: UUID for each chunk
- **Collection**: "documents"

## Troubleshooting

### Common Issues

1. **Connection Issues**:
   - Verify Qdrant Cloud API key and URL
   - Check network connectivity to EU-West-2 region

2. **Embedding Dimension Mismatch**:
   - Ensure collection configured for 1536 dimensions
   - Verify Azure OpenAI embedding model compatibility

3. **Document Processing Failures**:
   - Check file format support
   - Verify file accessibility and permissions
   - Monitor memory usage for large documents

### Monitoring and Health Checks

#### Collection Status
```python
processor = QdrantDocumentProcessor()
info = processor.get_collection_info()
print(f"Total documents: {info['points_count']}")
```

#### API Health Check
```bash
curl http://localhost:8000/health
```

## Future Enhancements

### Planned Improvements
1. Multi-language embeddings & detection.
2. Semantic-aware or layout-aware chunk splitting.
3. Query result caching (Redis) with TTL.
4. Structured logging & metrics (Prometheus exporter + Grafana dashboard).
5. Fine-grained reindex endpoint (specific files path parameter).
6. Role-based auth / API keys for endpoints.
7. Rate limiting and request body size enforcement.
8. Embedding store compaction / orphan cleanup job.

### Scalability Considerations
- **Horizontal Scaling**: Multiple API instances with load balancing
- **Database Sharding**: Collection partitioning for large datasets
- **Caching Strategy**: Query result caching for performance
- **Monitoring**: Comprehensive logging and metrics collection

## Security Notes

### Data Protection
- API keys stored in environment variables only
- No credentials in source code
- Secure HTTPS connections to Qdrant Cloud
- Input validation for all API endpoints

### Access Control
- Qdrant Cloud API key authentication
- CORS configuration for frontend access
- Rate limiting considerations for production

## Support and Maintenance

### Regular Maintenance Tasks
1. **Database Cleanup**: Remove obsolete document chunks
2. **Performance Monitoring**: Query response times and accuracy
3. **Security Updates**: Keep dependencies current
4. **Backup Strategy**: Document metadata and configuration

### Contact Information
- **System Administrator**: [Your contact information]
- **Last Updated**: August 13, 2025
- **Version**: 2.0 (Qdrant Cloud Migration)

---

## Summary

The system now includes incremental indexing, batch operations, environment fallback, fake-service test mode, and new operational endpoints improving reliability, observability, and local developer experience.

The system is fully operational and ready for production use with your document corpus.
