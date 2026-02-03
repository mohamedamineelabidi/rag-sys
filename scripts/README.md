# Scripts Directory

Utility scripts for data ingestion, diagnostics, and system management.

## Available Scripts

### ingest_data.py

Primary data ingestion script for processing and indexing documents into Qdrant.

```bash
# Basic usage - incremental indexing
python scripts/ingest_data.py

# Force full rescan (ignore cache)
python scripts/ingest_data.py --rescan

# Index specific directories only
python scripts/ingest_data.py --include-dirs "folder1,folder2"

# Use custom data path
python scripts/ingest_data.py --data-path "./CustomData"
```

**Features:**
- Incremental indexing with persistent cache
- Multi-format support: PDF, DOCX, TXT, XLSX
- Automatic metadata extraction
- Batch embedding generation

### check_document_count.py

Quick utility to verify the number of documents indexed in Qdrant.

```bash
python scripts/check_document_count.py
```

### diagnose_rag.py

Comprehensive diagnostic tool for analyzing RAG system health.

```bash
python scripts/diagnose_rag.py
```

**Checks performed:**
- Collection metadata and statistics
- Document content quality analysis
- Query relevance testing
- Embedding quality verification

### enhance_rag_performance.py

Generates performance improvement recommendations based on current system state.

```bash
python scripts/enhance_rag_performance.py
```

### fix_rag_threshold.py

Utility to adjust the similarity score threshold for document retrieval.

```bash
python scripts/fix_rag_threshold.py
```

## Configuration

Scripts use the same environment variables as the main application. Ensure your `.env` file is configured properly before running.

Required variables:
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`

## Logging

Scripts log to both console and `scripts/ingestion.log` (for ingest_data.py).

## Dependencies

Install script dependencies:

```bash
pip install -r scripts/requirements.txt
```
