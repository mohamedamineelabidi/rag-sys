#!/usr/bin/env python3
"""
Data Ingestion Script for RAG Project

This script handles the ingestion of documents into Qdrant vector database.
It can be run independently of the main server to populate or update the document index.

Usage:
    python scripts/ingest_data.py [--rescan] [--include-dirs DIR1,DIR2] [--data-path PATH]
    
Examples:
    python scripts/ingest_data.py                              # Normal incremental indexing
    python scripts/ingest_data.py --rescan                     # Force full rescan
    python scripts/ingest_data.py --include-dirs "1_HEA,2_ENE" # Index specific directories
    python scripts/ingest_data.py --data-path "./CustomData"   # Use custom data path
"""

import os
import sys
import argparse
import logging
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import time

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient, models
from langchain_community.document_loaders import UnstructuredPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings

from backend.indexing_cache import IndexingCacheManager
from backend.config import get_runtime_config, get_first_env

# Add openpyxl for Excel support
try:
    from langchain_community.document_loaders import UnstructuredExcelLoader
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    logging.warning("Excel support not available. Install 'openpyxl' for .xlsx support.")

# Configure logging
log_file_path = os.path.join(os.path.dirname(__file__), 'ingestion.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "Data")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "documents")
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
EMBEDDING_SIZE = int(os.environ.get("EMBEDDING_SIZE", 1536))
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".xlsx"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

# --- Behavior Configuration ---
USE_CACHE = os.environ.get("USE_INDEXING_CACHE", "true").lower() == "true"
SYNC_DELETIONS = os.environ.get("SYNC_DELETIONS_ON_STARTUP", "true").lower() == "true"


class DataIngestionProcessor:
    """
    Dedicated processor for data ingestion into Qdrant vector database.
    This is a streamlined version focused solely on document processing and indexing.
    """

    def __init__(self, data_path: str = DEFAULT_DATA_PATH, include_dirs: Optional[str] = None):
        self.data_path = data_path
        self.include_dirs = include_dirs or os.environ.get("INDEXING_INCLUDE_DIRS", "")
        
        # Initialize Qdrant client
        self.qdrant_client = self._initialize_qdrant()
        
        # Initialize embeddings
        self.embeddings = self._initialize_embeddings()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=250,
            length_function=len,
            separators=[
                "\n\n---", "\n\n", "\n", ". ", ", ", " ", ""
            ]
        )
        
        # Initialize cache manager
        self.cache_manager = IndexingCacheManager()
        
        logger.info(f"Data Ingestion Processor initialized")
        logger.info(f"Data path: {self.data_path}")
        logger.info(f"Include directories: {self.include_dirs if self.include_dirs else 'All directories'}")

    def _initialize_qdrant(self) -> QdrantClient:
        """Initialize Qdrant client and ensure collection exists."""
        try:
            qdrant_url = get_first_env("QDRANT_URL")
            qdrant_api_key = get_first_env("QDRANT_API_KEY")
            
            if not qdrant_url:
                raise ValueError("QDRANT_URL environment variable is required")
            
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            
            # Ensure collection exists
            try:
                client.get_collection(COLLECTION_NAME)
                logger.info(f"Connected to existing Qdrant collection: {COLLECTION_NAME}")
            except Exception:
                logger.info(f"Creating new Qdrant collection: {COLLECTION_NAME}")
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=EMBEDDING_SIZE,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")

            # Ensure payload index for 'section_type' exists for efficient filtering
            try:
                logger.info("Ensuring 'section_type' payload index exists...")
                client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="section_type",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                logger.info("'section_type' payload index is configured.")
            except Exception as e:
                logger.warning(f"Could not create payload index, it might already exist: {e}")
            
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
            logger.info(f"Initialized Azure OpenAI embeddings: {EMBEDDING_MODEL_NAME}")
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

    def _get_loader(self, file_path: str):
        """Get the appropriate document loader for the file type."""
        ext = Path(file_path).suffix.lower()
        try:
            if ext == ".pdf":
                # Try to use a simpler PDF loader that doesn't require pi_heif
                try:
                    from langchain_community.document_loaders import PyMuPDFLoader
                    return PyMuPDFLoader(file_path)
                except ImportError:
                    # Fallback to basic PDF loader with fewer dependencies
                    return UnstructuredPDFLoader(file_path, mode="elements", strategy="fast")
            elif ext == ".docx":
                return Docx2txtLoader(file_path)
            elif ext == ".txt":
                return TextLoader(file_path, encoding='utf-8')
            elif ext == ".xlsx":
                if EXCEL_SUPPORT:
                    return UnstructuredExcelLoader(file_path)
                else:
                    logger.warning(f"Skipping {file_path}. Install 'openpyxl' for .xlsx support.")
                    return None
            else:
                logger.warning(f"Unsupported file type: {ext} for file {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error creating loader for {file_path}: {e}")
            return None

    def _extract_metadata_from_path(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from the file path and name."""
        path = Path(file_path)
        parts = path.parts
        
        metadata = {
            'category': 'unknown',
            'document_type': 'general',
            'file_name': path.name
        }

        # Extract category (e.g., 1_HEA, 2_ENE)
        for part in parts:
            if re.match(r'^\d+_[A-Z]{3}$', part):
                metadata['category'] = part.lower()
                break
        
        # Infer document type from filename keywords
        filename_lower = path.name.lower()
        if any(k in filename_lower for k in ['requirement', 'standard', 'regulation']):
            metadata['document_type'] = 'requirement'
        elif any(k in filename_lower for k in ['calculation', 'calcul', 'analysis']):
            metadata['document_type'] = 'calculation'
        elif any(k in filename_lower for k in ['audit', 'assessment', 'evaluation']):
            metadata['document_type'] = 'audit'
        elif any(k in filename_lower for k in ['plan', 'drawing', 'schema']):
            metadata['document_type'] = 'plan'
        elif path.suffix == '.xlsx':
            metadata['document_type'] = 'spreadsheet'
            
        return metadata

    def _analyze_chunk_content(self, content: str) -> Dict[str, Any]:
        """Analyze chunk content to derive additional metadata."""
        content_lower = content.lower()
        analysis = {
            'section_type': 'content_section',
            'technical_content': False,
            'contains_units': False,
            'chunk_length': len(content)
        }

        # Detect section type
        if any(k in content_lower for k in ['requirement', 'standard', 'must comply', 'regulation']):
            analysis['section_type'] = 'requirement_section'
        elif any(k in content_lower for k in ['calculation', 'formula', 'analysis', 'results']):
            analysis['section_type'] = 'calculation_section'
        elif re.search(r'table\s+\d+', content_lower) or re.search(r'figure\s+\d+', content_lower):
            analysis['section_type'] = 'data_section'

        # Detect technical content and units
        technical_keywords = ['energy', 'thermal', 'hvac', 'kw', 'mw', 'kwh', 'mwh', '°c', 'efficiency']
        if any(keyword in content_lower for keyword in technical_keywords):
            analysis['technical_content'] = True
        
        if re.search(r'\b\d+\s*(kw|mw|kwh|mwh|°c|%|m²|m³|l/day)\b', content_lower):
            analysis['contains_units'] = True
            analysis['technical_content'] = True # If it has units, it's technical

        return analysis

    def process_and_index_documents(self, file_paths: List[str]):
        """Process and index a list of documents with rich metadata."""
        if not file_paths:
            logger.info("No files to process.")
            return

        logger.info(f"📚 Processing {len(file_paths)} documents...")
        
        total_chunks = 0
        processed_files = set()
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                logger.info(f"[{i}/{len(file_paths)}] Processing: {os.path.basename(file_path)}")
                
                # 1. Extract path-based metadata
                path_metadata = self._extract_metadata_from_path(file_path)

                # 2. Load document
                loader = self._get_loader(file_path)
                if not loader:
                    continue
                
                documents = loader.load()
                if not documents:
                    logger.warning(f"No content extracted from {file_path}")
                    continue
                
                # 3. Split into chunks
                chunks = self.text_splitter.split_documents(documents)
                if not chunks:
                    logger.warning(f"No chunks created from {file_path}")
                    continue
                
                # 4. Create embeddings and index with rich metadata
                points = []
                for chunk_idx, chunk in enumerate(chunks):
                    try:
                        # 5. Analyze chunk content for more metadata
                        content_analysis = self._analyze_chunk_content(chunk.page_content)
                        
                        # 6. Combine all metadata
                        final_payload = {
                            "content": chunk.page_content,
                            "file_name": path_metadata['file_name'],
                            "file_path": file_path,
                            "chunk_index": chunk_idx,
                            "total_chunks": len(chunks),
                            **path_metadata,
                            **content_analysis,
                            "original_metadata": chunk.metadata
                        }
                        
                        # 7. Create embedding
                        embedding = self._create_embedding(chunk.page_content)
                        
                        point = models.PointStruct(
                            id=str(uuid.uuid4()),
                            vector=embedding,
                            payload=final_payload
                        )
                        points.append(point)
                        
                    except Exception as e:
                        logger.error(f"Failed to process chunk {chunk_idx} of {file_path}: {e}")
                        continue
                
                # 8. Batch insert to Qdrant
                if points:
                    self.qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=points
                    )
                    total_chunks += len(points)
                    processed_files.add(file_path)
                    logger.info(f"✅ Indexed {len(points)} chunks from {os.path.basename(file_path)}")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        # Update cache
        if USE_CACHE:
            self.cache_manager.update_cache(processed_files=processed_files, deleted_files=set())
        
        logger.info(f"🎉 Completed! Processed {len(processed_files)} files, indexed {total_chunks} total chunks.")

    def scan_and_process(self, force_rescan: bool = False):
        """
        Scan the data directory and process documents based on cache.
        
        Args:
            force_rescan: If True, ignore cache and reprocess all files
        """
        if not os.path.exists(self.data_path):
            logger.error(f"Data path '{self.data_path}' not found!")
            return

        logger.info("🔍 Starting document scan...")
        
        # Determine which directories to scan
        include_dirs_str = self.include_dirs.strip()
        if include_dirs_str:
            target_dirs = [d.strip() for d in include_dirs_str.split(',')]
            scan_paths = [os.path.join(self.data_path, d) for d in target_dirs]
            logger.info(f"Targeted indexing enabled. Scanning only: {target_dirs}")
        else:
            scan_paths = [self.data_path]
            logger.info(f"Scanning all subdirectories in '{self.data_path}'")

        # Scan filesystem for supported files
        all_fs_files = set()
        image_files_found = []
        
        for scan_path in scan_paths:
            if not os.path.exists(scan_path):
                logger.warning(f"Directory does not exist, skipping: {scan_path}")
                continue
                
            for root, _, files in os.walk(scan_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()
                    
                    if file_ext in SUPPORTED_EXTENSIONS:
                        all_fs_files.add(file_path)
                    elif file_ext in IMAGE_EXTENSIONS:
                        image_files_found.append(file_path)

        logger.info(f"📊 Found {len(all_fs_files)} supported documents and {len(image_files_found)} images")

        # Determine what to process based on cache (unless force rescan)
        if force_rescan:
            files_to_index = all_fs_files
            files_to_delete = set()
            logger.info(f"🔄 Force rescan enabled - processing all {len(files_to_index)} files")
        else:
            files_to_index, files_to_delete = self.cache_manager.get_files_to_process(all_fs_files)
            
            # Handle deletions if enabled
            if SYNC_DELETIONS and files_to_delete:
                self.delete_documents_by_path(files_to_delete)

        if not files_to_index:
            logger.info("✅ Index is up-to-date. No new or modified files to process.")
            return

        logger.info(f"📁 Found {len(files_to_index)} files to index")
        self.process_and_index_documents(list(files_to_index))

    def delete_documents_by_path(self, file_paths: Set[str]):
        """Delete documents from Qdrant by their file paths."""
        if not file_paths:
            return
            
        logger.info(f"🗑️  Deleting {len(file_paths)} documents from index...")
        
        try:
            for file_path in file_paths:
                # Delete all points with this file_path
                self.qdrant_client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="file_path",
                                    match=models.MatchValue(value=file_path)
                                )
                            ]
                        )
                    )
                )
                logger.debug(f"Deleted documents for: {file_path}")
            
            # Update cache
            if USE_CACHE:
                self.cache_manager.update_cache(processed_files=set(), deleted_files=file_paths)
                
            logger.info(f"✅ Successfully deleted {len(file_paths)} documents from index")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the Qdrant collection."""
        try:
            collection_info = self.qdrant_client.get_collection(COLLECTION_NAME)
            points_count = collection_info.points_count
            
            return {
                "collection_name": COLLECTION_NAME,
                "points_count": points_count,
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
    """Main function to run data ingestion."""
    parser = argparse.ArgumentParser(
        description="RAG Data Ingestion Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--rescan", 
        action="store_true",
        help="Force full rescan ignoring cache (re-index all documents)"
    )
    
    parser.add_argument(
        "--include-dirs",
        type=str,
        help="Comma-separated list of subdirectories to index (e.g., '1_HEA,2_ENE')"
    )
    
    parser.add_argument(
        "--data-path",
        type=str,
        default=DEFAULT_DATA_PATH,
        help=f"Path to data directory (default: {DEFAULT_DATA_PATH})"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show collection information and exit"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = DataIngestionProcessor(
            data_path=args.data_path,
            include_dirs=args.include_dirs
        )
        
        if args.info:
            # Show collection info
            info = processor.get_collection_info()
            print(f"\nCollection Information:")
            print(f"  Name: {info['collection_name']}")
            print(f"  Documents: {info['points_count']}")
            print(f"  Status: {info['status']}")
            if 'error' in info:
                print(f"  Error: {info['error']}")
            return
        
        # Run ingestion
        logger.info("🚀 Starting data ingestion process...")
        start_time = time.time()
        
        processor.scan_and_process(force_rescan=args.rescan)
        
        duration = time.time() - start_time
        logger.info(f"✅ Data ingestion completed in {duration:.2f} seconds")
        
        # Show final stats
        info = processor.get_collection_info()
        logger.info(f"📊 Final collection stats: {info['points_count']} documents indexed")
        
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
