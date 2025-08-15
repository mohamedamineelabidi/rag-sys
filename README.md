# RAG Document Assistant

This project is a Retrieval-Augmented Generation (RAG) application that allows you to chat with your documents. It uses a Streamlit frontend, a FastAPI backend, and Qdrant for vector storage.

## Features

- **Intelligent Document Chat:** Ask questions in natural language and get answers based on your documents.
- **Advanced Search:** Perform intelligent searches with category filtering and metadata awareness.
- **Analytics Dashboard:** View system analytics and performance metrics.
- **Easy Data Ingestion:** A simple script to ingest your documents into the vector database.

## Project Structure

```
rag-project/
├── backend/         # FastAPI backend application
├── frontend/        # Streamlit frontend application
├── scripts/         # Data ingestion and utility scripts
├── Data/            # Directory for your documents
├── .env             # Environment variables
└── README.md
```

## Setup and Installation

### Prerequisites

- Python 3.8+
- An Azure account with access to OpenAI services
- A Qdrant Cloud account

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rag-project
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

Install the required Python packages for the backend, frontend, and scripts:

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
pip install -r scripts/requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `rag-project` directory and add the following environment variables with your credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT="<your-azure-openai-endpoint>"
AZURE_OPENAI_API_KEY="<your-azure-openai-api-key>"
OPENAI_API_VERSION="2023-12-01-preview"
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="<your-chat-deployment-name>"
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME="<your-embeddings-deployment-name>"

# Qdrant Configuration
QDRANT_URL="<your-qdrant-cloud-url>"
QDRANT_API_KEY="<your-qdrant-api-key>"
QDRANT_COLLECTION_NAME="documents"
```

## How to Use

### 1. Add Your Documents

Place the documents you want to chat with inside the `rag-project/Data` directory. The application supports PDF, DOCX, TXT, and XLSX files.

### 2. Ingest Your Data

Run the data ingestion script to process and index your documents. This will create the necessary vector embeddings in your Qdrant collection.

```bash
python scripts/ingest_data.py
```

To force a full rescan of all documents, use the `--rescan` flag:

```bash
python scripts/ingest_data.py --rescan
```

### 3. Run the Backend Server

Start the FastAPI backend server:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4. Run the Frontend Application

In a new terminal, start the Streamlit frontend application:

```bash
streamlit run frontend/streamlit_app.py
```

The application will open in your browser, and you can start asking questions about your documents.

## Usage

- **Chat:** Ask questions in the chat interface to get answers from your documents.
- **Search:** Use the search page to find specific information with advanced filtering options.
- **Analytics:** Monitor system performance and usage statistics on the analytics page.

---

This project is ready to be shared. Enjoy!
