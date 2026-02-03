# RAG Document Assistant - Architecture Documentation

Comprehensive architecture documentation covering system design, component interactions, and end-to-end data flows.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Architecture](#component-architecture)
3. [Data Flow Architecture](#data-flow-architecture)
4. [End-to-End Request Flow](#end-to-end-request-flow)
5. [Infrastructure Architecture](#infrastructure-architecture)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)

---

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                              RAG DOCUMENT ASSISTANT                             │
│                                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │             │     │             │     │             │     │             │  │
│  │  Document   │────▶│   Vector    │────▶│     RAG     │────▶│   Answer    │  │
│  │  Ingestion  │     │   Storage   │     │   Pipeline  │     │  Generation │  │
│  │             │     │             │     │             │     │             │  │
│  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION LAYER                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         Streamlit Web Application                          │  │
│  │                              (Port 8501)                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │    Chat     │  │   Search    │  │  Analytics  │  │  Document View  │  │  │
│  │  │  Interface  │  │    Page     │  │  Dashboard  │  │                 │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │ HTTP/REST
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Backend Server                             │  │
│  │                              (Port 8000)                                   │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                          API Endpoints                                │ │  │
│  │  │  /ask  /search  /intelligent-search  /healthcheck  /stats  /categories│ │  │
│  │  └──────────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐  │  │
│  │  │  RAG Service   │  │ Query Processor│  │ Intelligent Query Processor│  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │ API Calls
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 DATA LAYER                                       │
│  ┌─────────────────────────────┐       ┌─────────────────────────────────────┐  │
│  │       Qdrant Cloud          │       │         Azure OpenAI                │  │
│  │    (Vector Database)        │       │    (Embeddings & Chat)              │  │
│  │  ┌───────────────────────┐  │       │  ┌─────────────────────────────┐   │  │
│  │  │  documents collection │  │       │  │ text-embedding-3-small      │   │  │
│  │  │  - vectors (1536 dim) │  │       │  │ gpt-4 / gpt-35-turbo        │   │  │
│  │  │  - metadata payload   │  │       │  └─────────────────────────────┘   │  │
│  │  └───────────────────────┘  │       │                                     │  │
│  └─────────────────────────────┘       └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Backend Components

```
backend/
│
├── main.py                          ◄─── FastAPI Application Entry Point
│   │
│   ├── Lifespan Management          ◄─── Service initialization/cleanup
│   ├── CORS Middleware              ◄─── Cross-origin request handling
│   └── API Endpoints                ◄─── Route handlers
│
├── enhanced_rag_service.py          ◄─── Core RAG Pipeline
│   │
│   ├── AdvancedRAGService           ◄─── Main RAG orchestrator
│   │   ├── ask_question()           ◄─── Full RAG pipeline
│   │   ├── search_documents()       ◄─── Document retrieval only
│   │   └── _assess_confidence()     ◄─── Confidence scoring
│   │
│   └── ContextProcessor             ◄─── Context consolidation
│       ├── consolidate_context()    ◄─── Merge search results
│       └── detect_query_intent()    ◄─── Query analysis
│
├── enhanced_query_processor.py      ◄─── Document Retrieval
│   │
│   ├── EnhancedQdrantQueryProcessor ◄─── Production implementation
│   │   ├── semantic_search()        ◄─── Vector similarity search
│   │   ├── hybrid_search()          ◄─── Combined search strategies
│   │   └── _calculate_enhanced_score() ◄─── Relevance scoring
│   │
│   ├── QueryPreprocessor            ◄─── Query analysis
│   │   └── preprocess_query()       ◄─── Clean and analyze queries
│   │
│   └── InMemoryDocumentProcessor    ◄─── Test/fake implementation
│
├── intelligent_query_processor.py   ◄─── Advanced Query Processing
│   │
│   └── EnhancedQueryProcessor       ◄─── Category-aware retrieval
│       ├── search_with_filters()    ◄─── Metadata-filtered search
│       └── get_available_categories() ◄─── Category enumeration
│
├── models.py                        ◄─── Data Models (Pydantic)
│   │
│   ├── Request Models
│   │   └── QuestionRequest          ◄─── Input validation
│   │
│   ├── Response Models
│   │   ├── RAGResponse              ◄─── Full response structure
│   │   ├── Source                   ◄─── Document source info
│   │   ├── AnswerMetadata           ◄─── Response metadata
│   │   └── FollowUpQuestion         ◄─── Suggested questions
│   │
│   └── Enums
│       ├── SourceType               ◄─── PDF, DOCX, TXT, XLSX
│       └── ConfidenceLevel          ◄─── HIGH, MEDIUM, LOW
│
├── config.py                        ◄─── Configuration Management
│   │
│   ├── validate_required_env()      ◄─── Environment validation
│   ├── get_runtime_config()         ◄─── Safe config exposure
│   └── get_first_env()              ◄─── Multi-key env lookup
│
└── indexing_cache.py                ◄─── Indexing Cache Manager
    │
    └── IndexingCacheManager         ◄─── Persistent file tracking
        ├── get_file_hash()          ◄─── Content hashing
        ├── is_file_indexed()        ◄─── Cache lookup
        └── mark_file_indexed()      ◄─── Cache update
```

### Frontend Components

```
frontend/
│
└── streamlit_app.py                 ◄─── Streamlit Application
    │
    ├── Page Configuration           ◄─── Layout, title, icons
    │
    ├── Session State                ◄─── User session management
    │   ├── conversation_history     ◄─── Chat messages
    │   └── search_results           ◄─── Last search results
    │
    ├── Sidebar Navigation           ◄─── Page selection
    │   ├── Chat                     ◄─── Main conversation interface
    │   ├── Search                   ◄─── Document search
    │   └── Analytics                ◄─── System statistics
    │
    ├── Chat Interface               ◄─── Question/Answer UI
    │   ├── Message Display          ◄─── Chat bubbles
    │   ├── Source Attribution       ◄─── Document references
    │   └── Follow-up Questions      ◄─── Suggested queries
    │
    └── API Integration              ◄─── Backend communication
        ├── ask_question()           ◄─── POST /ask
        ├── search_documents()       ◄─── GET /search
        └── get_stats()              ◄─── GET /stats
```

### Scripts Components

```
scripts/
│
├── ingest_data.py                   ◄─── Primary Ingestion Script
│   │
│   └── DataIngestionProcessor       ◄─── Document processing pipeline
│       ├── _initialize_qdrant()     ◄─── Vector DB setup
│       ├── _initialize_embeddings() ◄─── Azure OpenAI setup
│       ├── _get_loader()            ◄─── Document loader factory
│       ├── _extract_metadata()      ◄─── Metadata extraction
│       ├── _analyze_chunk_content() ◄─── Content analysis
│       ├── process_and_index()      ◄─── Main processing
│       └── scan_and_process()       ◄─── Directory scanning
│
├── check_document_count.py          ◄─── Collection Status Check
│
├── diagnose_rag.py                  ◄─── System Diagnostics
│   ├── get_collection_stats()       ◄─── Vector DB analysis
│   ├── test_retrieval_quality()     ◄─── Query testing
│   └── diagnose_document_issues()   ◄─── Issue identification
│
├── enhance_rag_performance.py       ◄─── Performance Recommendations
│   └── get_recommendations()        ◄─── Optimization suggestions
│
└── fix_rag_threshold.py             ◄─── Threshold Adjustment
```

---

## Data Flow Architecture

### Document Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DOCUMENT INGESTION PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

    Data/                                                              Qdrant Cloud
    ├── folder1/            ┌───────────────┐                         ┌──────────┐
    │   ├── doc1.pdf   ────▶│               │                         │          │
    │   └── doc2.docx  ────▶│   Document    │    ┌──────────────┐    │  Vector  │
    ├── folder2/            │   Scanning    │───▶│   Loader     │    │  Storage │
    │   └── data.xlsx  ────▶│               │    │   Factory    │    │          │
    └── notes.txt      ────▶│               │    └──────┬───────┘    │ documents│
                            └───────────────┘           │             │collection│
                                                        ▼             │          │
                            ┌───────────────┐    ┌──────────────┐    │  1536    │
                            │               │    │              │    │dimensions│
                            │   Indexing    │◀───│  Document    │    │          │
                            │    Cache      │    │  Loaders     │    └────▲─────┘
                            │               │    │              │         │
                            │ (skip if      │    │ PDF/DOCX/    │         │
                            │  unchanged)   │    │ TXT/XLSX     │         │
                            │               │    │              │         │
                            └───────────────┘    └──────┬───────┘         │
                                                        │                 │
                                                        ▼                 │
                                                 ┌──────────────┐         │
                                                 │              │         │
                                                 │    Text      │         │
                                                 │   Splitter   │         │
                                                 │              │         │
                                                 │ chunk_size:  │         │
                                                 │   1200       │         │
                                                 │ overlap: 250 │         │
                                                 │              │         │
                                                 └──────┬───────┘         │
                                                        │                 │
                                                        ▼                 │
                            ┌───────────────┐    ┌──────────────┐         │
                            │               │    │              │         │
                            │  Azure OpenAI │◀───│   Chunk      │         │
                            │  Embeddings   │    │  Processing  │         │
                            │               │    │              │         │
                            │ text-embedding│    │ + metadata   │         │
                            │ -3-small      │    │ extraction   │         │
                            │               │    │              │         │
                            └───────┬───────┘    └──────────────┘         │
                                    │                                     │
                                    │         ┌──────────────────┐        │
                                    └────────▶│                  │────────┘
                                              │  Batch Upsert    │
                                              │                  │
                                              │  vectors +       │
                                              │  payload         │
                                              │                  │
                                              └──────────────────┘
```

### Query Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           QUERY PROCESSING PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

User Query: "What are the energy requirements?"
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Query Preprocessing                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  QueryPreprocessor.preprocess_query()                                    │  │
│  │                                                                          │  │
│  │  Input:  "What are the energy requirements?"                             │  │
│  │                                                                          │  │
│  │  Output: {                                                               │  │
│  │    "cleaned_query": "energy requirements",                               │  │
│  │    "query_type": "energy",                                               │  │
│  │    "filters": {"category": "energy"},                                    │  │
│  │    "keywords": ["energy", "requirements"]                                │  │
│  │  }                                                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Query Embedding                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Azure OpenAI Embeddings                                                 │  │
│  │                                                                          │  │
│  │  Input:  "energy requirements"                                           │  │
│  │  Model:  text-embedding-3-small                                          │  │
│  │  Output: [0.012, -0.034, 0.056, ... ] (1536 dimensions)                  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Vector Search                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Qdrant Similarity Search                                                │  │
│  │                                                                          │  │
│  │  Collection: "documents"                                                 │  │
│  │  Vector:     query_embedding                                             │  │
│  │  Limit:      6 results                                                   │  │
│  │  Filter:     category == "energy" (if auto_filter enabled)               │  │
│  │  Distance:   Cosine similarity                                           │  │
│  │                                                                          │  │
│  │  Returns: [                                                              │  │
│  │    {score: 0.85, content: "...", metadata: {...}},                       │  │
│  │    {score: 0.78, content: "...", metadata: {...}},                       │  │
│  │    ...                                                                   │  │
│  │  ]                                                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Score Enhancement & Reranking                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  _calculate_enhanced_score()                                             │  │
│  │                                                                          │  │
│  │  Factors:                                                                │  │
│  │  + Query type match bonus        (+0.05 for matching section_type)       │  │
│  │  + Document type relevance       (+0.03 for technical docs)              │  │
│  │  + Category match bonus          (+0.02 for category alignment)          │  │
│  │  + Technical content bonus       (+0.02 for units/numbers)               │  │
│  │  - Short chunk penalty           (-0.05 for <200 chars)                  │  │
│  │                                                                          │  │
│  │  Result: Reordered list by enhanced scores                               │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Context Consolidation                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  ContextProcessor.consolidate_context()                                  │  │
│  │                                                                          │  │
│  │  Groups results by:                                                      │  │
│  │  - Relevance tier (high: >0.7, medium: >0.5, low: <0.5)                  │  │
│  │  - Source document                                                       │  │
│  │  - Content type                                                          │  │
│  │                                                                          │  │
│  │  Output: {                                                               │  │
│  │    "context_text": "Document 1: ... Document 2: ...",                    │  │
│  │    "source_count": 4,                                                    │  │
│  │    "domain": "energy",                                                   │  │
│  │    "avg_score": 0.72                                                     │  │
│  │  }                                                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Answer Generation                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Azure OpenAI Chat Completion                                            │  │
│  │                                                                          │  │
│  │  Model:       GPT-4 / GPT-3.5-turbo                                      │  │
│  │  Temperature: 0.1 (low for factual responses)                            │  │
│  │  Max Tokens:  2000                                                       │  │
│  │                                                                          │  │
│  │  Prompt Template (domain-specific):                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────────┐ │  │
│  │  │ You are an expert building energy consultant...                    │ │  │
│  │  │                                                                    │ │  │
│  │  │ Context Information:                                               │ │  │
│  │  │ {consolidated_context}                                             │ │  │
│  │  │                                                                    │ │  │
│  │  │ Question: {user_question}                                          │ │  │
│  │  │                                                                    │ │  │
│  │  │ Instructions:                                                      │ │  │
│  │  │ 1. Focus on energy-related requirements...                         │ │  │
│  │  │ 2. Include units (kWh, MW, etc.)...                                │ │  │
│  │  │ ...                                                                │ │  │
│  │  └────────────────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: Response Assembly                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  RAGResponse Construction                                                │  │
│  │                                                                          │  │
│  │  {                                                                       │  │
│  │    "answer": "Based on the documents, the energy requirements...",       │  │
│  │    "sources": [                                                          │  │
│  │      {"file_name": "energy_audit.pdf", "score": 0.85, ...},              │  │
│  │      {"file_name": "requirements.docx", "score": 0.78, ...}              │  │
│  │    ],                                                                    │  │
│  │    "metadata": {                                                         │  │
│  │      "processing_time": 1.23,                                            │  │
│  │      "sources_count": 4,                                                 │  │
│  │      "confidence_level": "high",                                         │  │
│  │      "reasoning": "Multiple primary sources with high relevance"         │  │
│  │    },                                                                    │  │
│  │    "follow_up_questions": [                                              │  │
│  │      {"question": "What are the specific efficiency targets?", ...}      │  │
│  │    ]                                                                     │  │
│  │  }                                                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## End-to-End Request Flow

### Complete Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         END-TO-END REQUEST FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

USER                    FRONTEND                BACKEND                 EXTERNAL
 │                         │                       │                        │
 │  1. Type question       │                       │                        │
 │ ─────────────────────▶  │                       │                        │
 │                         │                       │                        │
 │                         │  2. POST /ask         │                        │
 │                         │  {question: "..."}    │                        │
 │                         │ ─────────────────────▶│                        │
 │                         │                       │                        │
 │                         │                       │  3. Create embedding   │
 │                         │                       │ ──────────────────────▶│
 │                         │                       │                        │ Azure
 │                         │                       │  4. Return vector      │ OpenAI
 │                         │                       │ ◀──────────────────────│
 │                         │                       │                        │
 │                         │                       │  5. Search vectors     │
 │                         │                       │ ──────────────────────▶│
 │                         │                       │                        │ Qdrant
 │                         │                       │  6. Return matches     │ Cloud
 │                         │                       │ ◀──────────────────────│
 │                         │                       │                        │
 │                         │                       │  7. Generate answer    │
 │                         │                       │ ──────────────────────▶│
 │                         │                       │                        │ Azure
 │                         │                       │  8. Return completion  │ OpenAI
 │                         │                       │ ◀──────────────────────│
 │                         │                       │                        │
 │                         │  9. RAGResponse       │                        │
 │                         │ ◀─────────────────────│                        │
 │                         │                       │                        │
 │  10. Display answer     │                       │                        │
 │ ◀─────────────────────  │                       │                        │
 │      + sources          │                       │                        │
 │      + follow-ups       │                       │                        │
 │                         │                       │                        │

Timeline (typical):
─────────────────────────────────────────────────────────────────────────────────
0ms        100ms       300ms       500ms       800ms      1200ms     1500ms
│           │           │           │           │           │           │
├───────────┼───────────┼───────────┼───────────┼───────────┼───────────┤
│  Request  │  Embed    │  Vector   │  Rerank   │  Generate │  Response │
│  Parse    │  Query    │  Search   │  Results  │  Answer   │  Build    │
```

### API Endpoint Details

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            API ENDPOINT ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

                              FastAPI Application
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   HEALTH      │          │     RAG       │          │   ANALYTICS   │
│   ENDPOINTS   │          │   ENDPOINTS   │          │   ENDPOINTS   │
└───────────────┘          └───────────────┘          └───────────────┘
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│               │          │               │          │               │
│ GET           │          │ POST /ask     │          │ GET /stats    │
│ /healthcheck  │          │               │          │               │
│               │          │ Request:      │          │ Response:     │
│ Response:     │          │ {             │          │ {             │
│ {             │          │   question,   │          │   total_docs, │
│   status,     │          │   max_sources,│          │   categories, │
│   doc_count   │          │   session_id  │          │   queries     │
│ }             │          │ }             │          │ }             │
│               │          │               │          │               │
│ GET           │          │ Response:     │          │ GET           │
│ /collection   │          │   RAGResponse │          │ /categories   │
│ -status       │          │               │          │               │
│               │          │ GET /search   │          │               │
│ GET           │          │ ?q=...&limit= │          │               │
│ /runtime      │          │               │          │               │
│ -config       │          │ GET           │          │               │
│               │          │ /intelligent  │          │               │
│               │          │ -search       │          │               │
│               │          │ ?q=...&       │          │               │
│               │          │  categories=  │          │               │
│               │          │  &auto_filter │          │               │
└───────────────┘          └───────────────┘          └───────────────┘
```

---

## Infrastructure Architecture

### Deployment Options

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT ARCHITECTURE OPTIONS                           │
└─────────────────────────────────────────────────────────────────────────────────┘

OPTION 1: Docker Compose (Development/Small Scale)
───────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Docker Host                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  docker-compose.yml                                                      │   │
│  │  ┌─────────────────────┐     ┌─────────────────────┐                    │   │
│  │  │  rag-backend        │     │  rag-frontend       │                    │   │
│  │  │  (Port 8000)        │◀────│  (Port 8501)        │                    │   │
│  │  │                     │     │                     │                    │   │
│  │  │  FastAPI + Uvicorn  │     │  Streamlit          │                    │   │
│  │  └─────────────────────┘     └─────────────────────┘                    │   │
│  │            │                                                             │   │
│  │            │ (Optional local Qdrant)                                     │   │
│  │            ▼                                                             │   │
│  │  ┌─────────────────────┐                                                 │   │
│  │  │  qdrant (optional)  │                                                 │   │
│  │  │  (Port 6333/6334)   │                                                 │   │
│  │  └─────────────────────┘                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
           ┌───────────────┐           ┌───────────────┐
           │  Qdrant Cloud │           │  Azure OpenAI │
           │  (External)   │           │  (External)   │
           └───────────────┘           └───────────────┘


OPTION 2: Kubernetes (Production/Scale)
───────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Kubernetes Cluster                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Namespace: rag-system                                                  │    │
│  │                                                                         │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │    │
│  │  │  Ingress        │  │  Service:       │  │  Service:       │        │    │
│  │  │  Controller     │──│  backend-svc    │  │  frontend-svc   │        │    │
│  │  │                 │  │  (ClusterIP)    │  │  (ClusterIP)    │        │    │
│  │  └─────────────────┘  └────────┬────────┘  └────────┬────────┘        │    │
│  │                                │                    │                  │    │
│  │                                ▼                    ▼                  │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │  Deployment: backend          Deployment: frontend              │  │    │
│  │  │  ┌─────┐ ┌─────┐ ┌─────┐     ┌─────┐ ┌─────┐                   │  │    │
│  │  │  │ Pod │ │ Pod │ │ Pod │     │ Pod │ │ Pod │                   │  │    │
│  │  │  └─────┘ └─────┘ └─────┘     └─────┘ └─────┘                   │  │    │
│  │  │  replicas: 3                  replicas: 2                       │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────┐  ┌─────────────────┐                              │    │
│  │  │  ConfigMap      │  │  Secret         │                              │    │
│  │  │  (non-secret    │  │  (API keys,     │                              │    │
│  │  │   config)       │  │   credentials)  │                              │    │
│  │  └─────────────────┘  └─────────────────┘                              │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘


OPTION 3: Cloud Native (Azure)
─────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Azure Cloud                                         │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐        │
│  │  Azure           │     │  Azure           │     │  Azure           │        │
│  │  Front Door      │────▶│  Container Apps  │────▶│  OpenAI          │        │
│  │  (CDN + WAF)     │     │  (Backend)       │     │  Service         │        │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘        │
│           │                        │                                            │
│           │               ┌────────┴────────┐                                   │
│           │               │                 │                                   │
│           ▼               ▼                 ▼                                   │
│  ┌──────────────────┐   ┌──────────────────┐                                   │
│  │  Azure           │   │  Azure Key       │                                   │
│  │  Container Apps  │   │  Vault           │                                   │
│  │  (Frontend)      │   │  (Secrets)       │                                   │
│  └──────────────────┘   └──────────────────┘                                   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Monitoring: Azure Monitor + Application Insights                         │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                            ┌───────────────┐
                            │  Qdrant Cloud │
                            │  (External)   │
                            └───────────────┘
```

---

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: Network Security                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • HTTPS/TLS encryption for all external traffic                         │   │
│  │  • CORS configuration (configurable allowed origins)                     │   │
│  │  • Rate limiting (to be implemented)                                     │   │
│  │  • IP allowlisting (optional)                                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: Application Security                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Input validation via Pydantic models                                  │   │
│  │  • Request body size limits                                              │   │
│  │  • SQL injection prevention (N/A - no SQL)                               │   │
│  │  • XSS prevention (Streamlit handles)                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: Secrets Management                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Environment variables for credentials                                 │   │
│  │  • .env file excluded from version control                               │   │
│  │  • .env.example template for safe sharing                                │   │
│  │  • get_runtime_config() exposes only safe values                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: Container Security                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Non-root user in Docker containers                                    │   │
│  │  • Minimal base images (python:3.11-slim)                                │   │
│  │  • No unnecessary packages installed                                     │   │
│  │  • Health checks for container orchestration                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: Data Security                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Qdrant Cloud API key authentication                                   │   │
│  │  • Azure OpenAI API key authentication                                   │   │
│  │  • No user data persistence (stateless API)                              │   │
│  │  • Document data stored only in Qdrant (encrypted at rest)               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

CREDENTIALS FLOW:
─────────────────

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│              │     │              │     │              │
│  .env file   │────▶│  python-     │────▶│  Application │
│  (local)     │     │  dotenv      │     │  Code        │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       │ NOT committed to git
       │
       ▼
┌──────────────┐
│              │
│  .gitignore  │
│  excludes    │
│  .env        │
│              │
└──────────────┘
```

---

## Deployment Architecture

### CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CI/CD PIPELINE                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│   Developer │────▶│   GitHub    │────▶│   GitHub    │────▶│  Container  │
│   Push      │     │   Repo      │     │   Actions   │     │  Registry   │
│             │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘     └──────┬──────┘
                                               │                    │
                                               ▼                    │
                                    ┌──────────────────┐           │
                                    │  CI Pipeline     │           │
                                    │                  │           │
                                    │  1. Checkout     │           │
                                    │  2. Setup Python │           │
                                    │  3. Install deps │           │
                                    │  4. Run linter   │           │
                                    │  5. Check imports│           │
                                    │  6. Build Docker │───────────┘
                                    │                  │
                                    └──────────────────┘

GitHub Actions Workflow (ci.yml):
─────────────────────────────────

┌─────────────────────────────────────────────────────────────────────────────────┐
│  on: push/pull_request to main                                                   │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Job: lint-and-test                                                     │    │
│  │                                                                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │ Checkout │─▶│  Setup   │─▶│ Install  │─▶│   Ruff   │─▶│  Verify  │ │    │
│  │  │   code   │  │ Python   │  │   deps   │  │  linter  │  │ imports  │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                      │
│                                          ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  Job: docker-build (needs: lint-and-test)                               │    │
│  │                                                                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │    │
│  │  │ Checkout │─▶│  Setup   │─▶│  Build   │─▶│  Build   │              │    │
│  │  │   code   │  │ Buildx   │  │ Backend  │  │ Frontend │              │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### File Structure Summary

```
rag-sys/
│
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions CI pipeline
│
├── backend/
│   ├── main.py                       # FastAPI application
│   ├── config.py                     # Configuration management
│   ├── models.py                     # Pydantic data models
│   ├── enhanced_rag_service.py       # RAG pipeline
│   ├── enhanced_query_processor.py   # Document retrieval
│   ├── intelligent_query_processor.py# Advanced query processing
│   ├── indexing_cache.py             # File caching
│   └── requirements.txt              # Backend dependencies
│
├── frontend/
│   ├── streamlit_app.py              # Streamlit UI
│   └── requirements.txt              # Frontend dependencies
│
├── scripts/
│   ├── ingest_data.py                # Document ingestion
│   ├── check_document_count.py       # Collection status
│   ├── diagnose_rag.py               # System diagnostics
│   ├── enhance_rag_performance.py    # Performance recommendations
│   ├── fix_rag_threshold.py          # Threshold adjustment
│   ├── requirements.txt              # Script dependencies
│   └── README.md                     # Script documentation
│
├── full-documentation/               # Detailed documentation
│   ├── index.md
│   └── *.md
│
├── Data/                             # Document storage (gitignored)
│
├── .env                              # Environment variables (gitignored)
├── .env.example                      # Environment template
├── .gitignore                        # Git ignore patterns
├── Dockerfile                        # Backend container
├── Dockerfile.frontend               # Frontend container
├── docker-compose.yml                # Multi-service orchestration
├── LICENSE                           # MIT License
├── README.md                         # Project README
├── SYSTEM_DOCUMENTATION.md           # Technical documentation
└── ARCHITECTURE.md                   # This file
```

---

## Summary

This RAG Document Assistant implements a modern, scalable architecture with:

1. **Clean Separation of Concerns**: Frontend, Backend, and Data layers are clearly separated
2. **Stateless API Design**: Enables horizontal scaling
3. **External Service Integration**: Azure OpenAI for AI, Qdrant Cloud for vectors
4. **Container-Ready**: Docker and Docker Compose support
5. **CI/CD Pipeline**: GitHub Actions for automated testing
6. **Security Best Practices**: Secrets management, non-root containers, input validation

The architecture supports evolution from single-developer deployment to enterprise-scale production environments.
