# Scripts Directory

This directory contains utility scripts for the RAG project, focusing on data ingestion and management tasks.

## Scripts

### `ingest_data.py`

The main data ingestion script for processing and indexing documents into the Qdrant vector database.

#### Features
- **Incremental indexing** using persistent cache to only process new/modified files
- **Selective directory indexing** to target specific folders
- **Document type support**: PDF, DOCX, TXT, XLSX files
- **Automatic deletion sync** to remove indexed documents when files are deleted
- **Comprehensive logging** with both console and file output

#### Usage

```bash
# Basic usage - incremental indexing of all documents
python scripts/ingest_data.py

# Force full rescan (ignore cache, reindex everything)
python scripts/ingest_data.py --rescan

# Index only specific directories
python scripts/ingest_data.py --include-dirs "1_HEA,2_ENE"

# Use custom data path
python scripts/ingest_data.py --data-path "./CustomData"

# Show collection information
python scripts/ingest_data.py --info
```

#### Configuration

The script uses the same environment variables as the main application:

- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant API key
- `QDRANT_COLLECTION_NAME` - Collection name (default: "documents")
- `AZURE_OPENAI_*` - Azure OpenAI configuration for embeddings
- `USE_INDEXING_CACHE` - Enable/disable persistent cache (default: "true")
- `SYNC_DELETIONS_ON_STARTUP` - Enable/disable deletion sync (default: "true")
- `INDEXING_INCLUDE_DIRS` - Comma-separated directories to index

#### Logging

The script logs to both console and `scripts/ingestion.log` file.

#### Examples

1. **Initial setup** - Index all documents:
   ```bash
   python scripts/ingest_data.py
   ```

2. **Update index** after adding new files:
   ```bash
   python scripts/ingest_data.py
   ```

3. **Rebuild entire index**:
   ```bash
   python scripts/ingest_data.py --rescan
   ```

4. **Index only energy-related documents**:
   ```bash
   python scripts/ingest_data.py --include-dirs "2_ENE"
   ```

## Integration with Backend

The backend server (`backend/main.py`) has been updated to focus solely on serving queries and does not perform document ingestion. This separation provides:

- **Faster server startup** - No need to wait for document processing
- **Better resource management** - Ingestion can run separately on different schedules
- **Cleaner architecture** - Clear separation of concerns
- **Flexible deployment** - Can run ingestion as batch jobs or scheduled tasks

## Migration from Old System

If you're migrating from the previous integrated system:

1. The backend server no longer performs automatic document scanning on startup
2. Run `python scripts/ingest_data.py` to index your documents
3. The `/rescan` and `/upload` endpoints now return deprecation notices
4. Use the standalone ingestion script for all document management

## Troubleshooting

- **Connection errors**: Check your Qdrant configuration and network connectivity
- **Embedding errors**: Verify Azure OpenAI credentials and deployment names
- **File processing errors**: Check file permissions and supported formats
- **Cache issues**: Delete `backend/.rag_cache.db` to reset the cache
