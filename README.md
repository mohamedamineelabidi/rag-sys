# RAG Document Assistant

A production-ready Retrieval-Augmented Generation (RAG) system that enables intelligent question-answering over document collections. Built with FastAPI, Streamlit, Azure OpenAI, and Qdrant vector database.

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Development](#development)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)
- [License](#license)

## Overview

The RAG Document Assistant is an enterprise-grade system designed to extract knowledge from document repositories and provide accurate, context-aware responses to user queries. The system leverages advanced natural language processing to understand questions, retrieve relevant document passages, and generate comprehensive answers grounded in the source material.

## Problem Statement

Organizations accumulate vast amounts of knowledge in documents (PDFs, Word documents, spreadsheets) that become difficult to search and utilize effectively. Traditional keyword search fails to capture semantic meaning, and manually reviewing documents is time-consuming and error-prone.

Key challenges addressed:
- **Information Retrieval**: Finding relevant information across heterogeneous document formats
- **Context Understanding**: Interpreting user intent and matching it to document content
- **Answer Generation**: Synthesizing coherent responses from multiple document sources
- **Source Attribution**: Maintaining traceability to original documents

## Solution

This system implements a RAG pipeline that:

1. **Ingests documents** from multiple formats (PDF, DOCX, TXT, XLSX)
2. **Chunks and embeds** content using Azure OpenAI embeddings
3. **Stores vectors** in Qdrant for efficient similarity search
4. **Retrieves context** using semantic search with intelligent filtering
5. **Generates answers** using Azure OpenAI GPT models with source attribution

The solution provides:
- High-accuracy semantic search across document collections
- Domain-aware query processing with automatic category detection
- Confidence scoring and source transparency
- Suggested follow-up questions for deeper exploration

## Architecture

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

### High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          RAG DOCUMENT ASSISTANT                             │
│                                                                             │
│   ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐     │
│   │           │     │           │     │           │     │           │     │
│   │ Document  │────▶│  Vector   │────▶│    RAG    │────▶│  Answer   │     │
│   │ Ingestion │     │  Storage  │     │ Pipeline  │     │Generation │     │
│   │           │     │           │     │           │     │           │     │
│   └───────────┘     └───────────┘     └───────────┘     └───────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Streamlit Web Application                         │  │
│  │                           (Port 8501)                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │  │
│  │  │    Chat     │  │   Search    │  │  Analytics  │                   │  │
│  │  │  Interface  │  │    Page     │  │  Dashboard  │                   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTP/REST
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLICATION LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Backend Server                            │  │
│  │                           (Port 8000)                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  /ask    /search    /intelligent-search    /healthcheck   /stats │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────┐  ┌────────────────┐  ┌────────────────────────┐   │  │
│  │  │ RAG Service  │  │ Query Processor│  │ Intelligent Processor  │   │  │
│  │  └──────────────┘  └────────────────┘  └────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ API Calls
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                     │
│  ┌───────────────────────────┐       ┌───────────────────────────────────┐  │
│  │      Qdrant Cloud         │       │        Azure OpenAI               │  │
│  │   (Vector Database)       │       │   (Embeddings & Chat)             │  │
│  │  ┌─────────────────────┐  │       │  ┌─────────────────────────────┐  │  │
│  │  │ documents collection│  │       │  │ text-embedding-3-small      │  │  │
│  │  │ - vectors (1536 dim)│  │       │  │ gpt-4 / gpt-35-turbo        │  │  │
│  │  │ - metadata payload  │  │       │  └─────────────────────────────┘  │  │
│  │  └─────────────────────┘  │       │                                   │  │
│  └───────────────────────────┘       └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Document Ingestion Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │
│   Documents  │───▶│   Document   │───▶│    Text      │───▶│   Chunk      │
│   (PDF/DOCX/ │    │   Loaders    │    │   Splitter   │    │  Processing  │
│   TXT/XLSX)  │    │              │    │              │    │              │
│              │    │              │    │  chunk_size: │    │  + metadata  │
└──────────────┘    └──────────────┘    │    1200      │    │  extraction  │
                                        └──────────────┘    └──────┬───────┘
                                                                   │
                    ┌──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │
│  Azure OpenAI│───▶│   Batch      │───▶│   Qdrant     │
│  Embeddings  │    │   Upsert     │    │   Storage    │
│              │    │              │    │              │
│  1536 dims   │    │  vectors +   │    │  documents   │
│              │    │  payload     │    │  collection  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Query Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY PROCESSING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

User Question: "What are the energy requirements?"
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Query        │    │ 2. Create       │    │ 3. Vector       │
│    Preprocessing│───▶│    Embedding    │───▶│    Search       │
│                 │    │                 │    │                 │
│ - Clean query   │    │ Azure OpenAI    │    │ Qdrant          │
│ - Detect intent │    │ text-embedding  │    │ similarity      │
│ - Extract terms │    │ -3-small        │    │ search          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
         ┌────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 4. Rerank &     │    │ 5. Context      │    │ 6. Answer       │
│    Filter       │───▶│    Assembly     │───▶│    Generation   │
│                 │    │                 │    │                 │
│ - Score boost   │    │ - Group by      │    │ Azure OpenAI    │
│ - Metadata      │    │   relevance     │    │ GPT-4           │
│   filtering     │    │ - Build context │    │ + sources       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                              ┌─────────────────┐
                                              │ 7. RAGResponse  │
                                              │                 │
                                              │ - answer        │
                                              │ - sources       │
                                              │ - confidence    │
                                              │ - follow-ups    │
                                              └─────────────────┘
```

### End-to-End Request Timeline

```
User                  Frontend              Backend               External Services
 │                       │                     │                         │
 │  Ask question         │                     │                         │
 │──────────────────────▶│                     │                         │
 │                       │  POST /ask          │                         │
 │                       │────────────────────▶│                         │
 │                       │                     │  Create embedding       │
 │                       │                     │────────────────────────▶│ Azure
 │                       │                     │  Vector (1536 dims)     │ OpenAI
 │                       │                     │◀────────────────────────│
 │                       │                     │  Search vectors         │
 │                       │                     │────────────────────────▶│ Qdrant
 │                       │                     │  Top-k matches          │ Cloud
 │                       │                     │◀────────────────────────│
 │                       │                     │  Generate answer        │
 │                       │                     │────────────────────────▶│ Azure
 │                       │                     │  Completion             │ OpenAI
 │                       │                     │◀────────────────────────│
 │                       │  RAGResponse        │                         │
 │                       │◀────────────────────│                         │
 │  Display answer       │                     │                         │
 │◀──────────────────────│                     │                         │
 │  + sources            │                     │                         │
 │  + follow-ups         │                     │                         │
 │                       │                     │                         │

Typical latency: 1-3 seconds
```

### Component Interaction Flow

1. **Document Ingestion**: The ingestion pipeline processes documents, generates embeddings, and stores them in Qdrant
2. **Query Processing**: User queries are analyzed for intent and domain classification
3. **Retrieval**: Semantic search retrieves relevant document chunks with metadata filtering
4. **Generation**: The RAG service consolidates context and generates grounded responses
5. **Response**: Answers are returned with source attribution and confidence scores

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend API | FastAPI | REST API server with async support |
| Frontend | Streamlit | Interactive web interface |
| Vector Database | Qdrant Cloud | Scalable vector similarity search |
| Embeddings | Azure OpenAI (text-embedding-3-small) | Document and query embeddings |
| LLM | Azure OpenAI (GPT-4) | Answer generation |
| Document Processing | LangChain | Document loading and chunking |
| Configuration | python-dotenv | Environment management |

## Project Structure

```
rag-sys/
├── backend/                          # FastAPI backend application
│   ├── main.py                       # API endpoints and server configuration
│   ├── config.py                     # Environment validation and configuration
│   ├── models.py                     # Pydantic data models
│   ├── enhanced_rag_service.py       # RAG pipeline and answer generation
│   ├── enhanced_query_processor.py   # Semantic search and retrieval
│   ├── intelligent_query_processor.py # Category-aware query processing
│   ├── indexing_cache.py             # Incremental indexing cache manager
│   └── requirements.txt              # Backend dependencies
│
├── frontend/                         # Streamlit frontend application
│   └── streamlit_app.py              # Main frontend application
│
├── scripts/                          # Utility scripts
│   ├── ingest_data.py                # Document ingestion pipeline
│   ├── check_document_count.py       # Database status utility
│   ├── diagnose_rag.py               # System diagnostics
│   ├── enhance_rag_performance.py    # Performance recommendations
│   ├── fix_rag_threshold.py          # Threshold adjustment utility
│   ├── requirements.txt              # Script dependencies
│   └── README.md                     # Script documentation
│
├── full-documentation/               # Detailed system documentation
│   ├── index.md                      # Documentation index
│   └── *.md                          # Component documentation
│
├── .env.example                      # Environment variable template
├── .gitignore                        # Git ignore patterns
├── README.md                         # This file
└── SYSTEM_DOCUMENTATION.md           # Technical system documentation
```

## Prerequisites

- Python 3.10 or higher
- Azure OpenAI account with:
  - Deployed chat model (GPT-4 or GPT-3.5-turbo)
  - Deployed embedding model (text-embedding-3-small recommended)
- Qdrant Cloud account (or self-hosted Qdrant instance)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mohamedamineelabidi/rag-sys.git
cd rag-sys
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell
```

### 3. Install Dependencies

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Install script dependencies (includes document processing libraries)
pip install -r scripts/requirements.txt
```

## Configuration

### 1. Environment Variables

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Azure OpenAI (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=text-embedding-3-small

# Qdrant (Required)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION_NAME=documents
```

### 2. Document Preparation

Create a `Data/` directory and add your documents:

```bash
mkdir -p Data
# Copy your PDF, DOCX, TXT, or XLSX files to Data/
```

Supported formats:
- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Plain text (`.txt`)
- Excel spreadsheets (`.xlsx`)

## Usage

### 1. Ingest Documents

Process and index your documents into the vector database:

```bash
python scripts/ingest_data.py
```

Options:
```bash
# Force full rescan (ignore cache)
python scripts/ingest_data.py --rescan

# Index specific directories only
python scripts/ingest_data.py --include-dirs "folder1,folder2"

# Use custom data path
python scripts/ingest_data.py --data-path "./CustomData"
```

### 2. Start the Backend Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start the Frontend Application

In a new terminal:
```bash
streamlit run frontend/streamlit_app.py
```

The application will be available at `http://localhost:8501`

### 4. Using the Application

1. **Chat Interface**: Ask natural language questions about your documents
2. **Search**: Perform semantic search with category filtering
3. **Analytics**: View system statistics and performance metrics

## API Reference

### Health Check

```http
GET /healthcheck
```

Returns system health status and document count.

### Ask Question

```http
POST /ask
Content-Type: application/json

{
  "question": "What are the energy requirements?",
  "max_sources": 4,
  "include_metadata": true
}
```

### Search Documents

```http
GET /search?q=energy+efficiency&limit=5
```

### Intelligent Search with Filtering

```http
GET /intelligent-search?q=requirements&categories=energy&auto_filter=true
```

### Collection Status

```http
GET /collection-status
```

For complete API documentation, visit `/docs` when the server is running.

## Development

### Running in Test Mode

```bash
# Enable fake services mode for testing without external APIs
export USE_FAKE_SERVICES=true
uvicorn backend.main:app --port 8000
```

### Code Quality

The project follows these conventions:
- Type hints for function signatures
- Pydantic models for data validation
- Comprehensive logging
- Error handling with appropriate HTTP status codes

### Diagnostics

```bash
# Check document count
python scripts/check_document_count.py

# Run system diagnostics
python scripts/diagnose_rag.py

# Get performance recommendations
python scripts/enhance_rag_performance.py
```

## Future Improvements

### Planned Enhancements

- [ ] **Authentication**: Add OAuth2/JWT authentication for API security
- [ ] **Monitoring**: Integrate Prometheus metrics and Grafana dashboards
- [ ] **Caching**: Implement Redis caching for frequent queries
- [ ] **Hybrid Search**: Combine BM25 keyword search with semantic search
- [ ] **Multi-tenancy**: Support for multiple users and document collections
- [ ] **Streaming Responses**: WebSocket support for streaming LLM responses
- [ ] **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- [ ] **Docker Support**: Containerized deployment configuration
- [ ] **Conversation Memory**: Persistent conversation history with summarization

### Known Limitations

- Image content within documents is not currently processed
- Large documents may require increased chunking parameters
- Response latency depends on Azure OpenAI API performance

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes with appropriate tests
4. Ensure code follows existing style conventions
5. Submit a pull request with a clear description

### Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Relevant error messages and logs
- Steps to reproduce the issue

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

For detailed technical documentation, see [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) and the [full-documentation](full-documentation/) directory.
