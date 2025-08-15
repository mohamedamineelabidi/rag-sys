import os
import time
import requests
import streamlit as st
from typing import Optional, Dict, Any, List
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# === PAGE CONFIGURATION ===
st.set_page_config(
    page_title="RAG Document Assistant - Enhanced",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === ENHANCED STYLING ===
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(45deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-weight: bold;
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background: linear-gradient(135deg, #f8d7da, #f5c6cb);
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        background: linear-gradient(135deg, #d1ecf1, #bee5eb);
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 1rem;
        max-width: 80%;
    }
    .user-message {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        margin-left: auto;
        text-align: right;
    }
    .assistant-message {
        background: linear-gradient(135deg, #f3e5f5, #e1bee7);
        margin-right: auto;
    }
    .source-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stats-container {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 1rem;
        border-radius: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# === CONFIGURATION ===
DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# === SESSION STATE INITIALIZATION ===
def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        "conversation_history": [],
        "backend_status": None,
        "last_health_check": 0,
        "collection_info": None,
        "search_history": [],
        "favorite_questions": [],
        "response_times": [],
        "current_page": "chat",
        "advanced_mode": False,
        "conversation_context": {},
        "system_stats": None,
        "last_stats_update": 0
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_session_state()

# === UTILITY FUNCTIONS ===
def check_backend_health(backend_url: str) -> Dict[str, Any]:
    """Enhanced backend health check with more details"""
    try:
        start_time = time.time()
        
        # Health check
        health_response = requests.get(f"{backend_url}/healthcheck", timeout=10)
        health_time = round((time.time() - start_time) * 1000, 2)
        
        # Collection status
        try:
            collection_response = requests.get(f"{backend_url}/collection-status", timeout=10)
            collection_data = collection_response.json() if collection_response.ok else {}
        except:
            collection_data = {}
        
        if health_response.ok and health_response.json().get("status") == "ok":
            return {
                "status": "healthy",
                "response_time": health_time,
                "message": "✅ Backend is healthy",
                "collection_info": collection_data.get("collection_info", {}),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        else:
            return {
                "status": "unhealthy",
                "response_time": health_time,
                "message": "⚠️ Health check failed",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "response_time": None,
            "message": "🔴 Backend timeout (>10s)",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "connection_error", 
            "response_time": None,
            "message": "🔴 Cannot connect to backend",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time": None,
            "message": f"🔴 Error: {str(e)}",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

def search_documents(backend_url: str, query: str, limit: int = 5) -> Dict[str, Any]:
    """Search documents without generating an answer"""
    try:
        start_time = time.time()
        response = requests.get(
            f"{backend_url}/search",
            params={"q": query, "limit": limit},
            timeout=30
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if response.ok:
            data = response.json()
            return {
                "success": True,
                "results": data.get("results", []),
                "response_time": response_time,
                "query": query
            }
        else:
            return {
                "success": False,
                "message": f"Search failed: {response.text}",
                "response_time": response_time
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Search error: {str(e)}",
            "response_time": None
        }


def intelligent_search(backend_url: str, query: str, limit: int = 5, 
                      categories: List[str] = None, document_types: List[str] = None,
                      auto_filter: bool = True) -> Dict[str, Any]:
    """Enhanced intelligent search with category filtering and metadata awareness"""
    try:
        start_time = time.time()
        params = {
            "q": query,
            "limit": limit,
            "auto_filter": auto_filter
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        if document_types:
            params["document_types"] = ",".join(document_types)
        
        response = requests.get(
            f"{backend_url}/intelligent-search",
            params=params,
            timeout=30
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if response.ok:
            result_data = response.json()
            return {
                "success": True,
                "results": result_data.get("results", []),
                "metadata": result_data.get("metadata", {}),
                "response_time": response_time,
                "message": "Intelligent search completed successfully"
            }
        else:
            return {
                "success": False,
                "results": [],
                "metadata": {},
                "response_time": response_time,
                "message": f"Search failed: {response.text}",
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "results": [],
            "metadata": {},
            "response_time": 0,
            "message": f"Search error: {str(e)}",
        }


def get_available_categories(backend_url: str) -> Dict[str, Any]:
    """Get available document categories from the backend"""
    try:
        response = requests.get(f"{backend_url}/categories", timeout=10)
        if response.ok:
            return response.json()
        else:
            return {"categories": {}, "total_categories": 0, "available_filters": []}
    except Exception as e:
        return {"categories": {}, "total_categories": 0, "available_filters": []}

def ask_question(backend_url: str, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Enhanced question asking with better error handling and support for new response format"""
    try:
        start_time = time.time()
        
        # Prepare request payload with enhanced structure
        payload = {
            "question": question,
            "max_sources": 4,
            "include_metadata": True
        }
        
        # Add conversation context if available
        if context:
            payload["context"] = {
                "conversation_id": context.get("conversation_id"),
                "previous_questions": context.get("previous_questions", [])[-3:],  # Last 3 questions for context
                "user_preferences": context.get("user_preferences")
            }
        
        response = requests.post(
            f"{backend_url}/ask", 
            json=payload, 
            timeout=120
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Store response time for analytics
        st.session_state.response_times.append({
            "timestamp": datetime.now(),
            "response_time": response_time,
            "question_length": len(question)
        })
        
        if response.ok:
            data = response.json()
            
            # Handle new enhanced response structure
            if "metadata" in data:
                # New enhanced response format
                return {
                    "success": True,
                    "answer": data.get("answer", "No answer provided"),
                    "sources": data.get("sources", []),
                    "metadata": data.get("metadata", {}),
                    "follow_up_questions": data.get("follow_up_questions", []),
                    "conversation_id": data.get("conversation_id"),
                    "response_time": response_time,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
            else:
                # Legacy response format
                return {
                    "success": True,
                    "answer": data.get("answer", "No answer provided"),
                    "sources": data.get("sources", []),
                    "metadata": {
                        "confidence_level": "medium",
                        "processing_time_ms": response_time,
                        "retrieval_count": len(data.get("sources", []))
                    },
                    "follow_up_questions": [],
                    "response_time": response_time,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
        else:
            return {
                "success": False,
                "message": f"Query failed: {response.text}",
                "response_time": response_time,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Query timeout - try a simpler question",
            "response_time": None,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Query error: {str(e)}",
            "response_time": None,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

def get_system_stats(backend_url: str) -> Dict[str, Any]:
    """Get system statistics from backend"""
    try:
        response = requests.get(f"{backend_url}/stats", timeout=10)
        if response.ok:
            return {
                "success": True,
                "stats": response.json(),
                "timestamp": datetime.now()
            }
        else:
            return {"success": False, "message": "Failed to fetch stats"}
    except Exception as e:
        return {"success": False, "message": f"Stats error: {str(e)}"}


def display_confidence_indicator(confidence_level: str, reasoning: str = ""):
    """Display confidence level with visual indicator"""
    confidence_colors = {
        "high": "🟢",
        "medium": "🟡", 
        "low": "🟠",
        "uncertain": "🔴"
    }
    
    confidence_text = {
        "high": "High Confidence",
        "medium": "Medium Confidence",
        "low": "Low Confidence", 
        "uncertain": "Uncertain"
    }
    
    icon = confidence_colors.get(confidence_level.lower(), "⚪")
    text = confidence_text.get(confidence_level.lower(), confidence_level.title())
    
    st.markdown(f"""
    <div style="
        display: inline-flex; 
        align-items: center; 
        background: rgba(255,255,255,0.1); 
        padding: 0.25rem 0.5rem; 
        border-radius: 1rem; 
        font-size: 0.85rem;
        margin: 0.25rem 0;
    ">
        {icon} <strong>{text}</strong>
        {f" - {reasoning}" if reasoning else ""}
    </div>
    """, unsafe_allow_html=True)


def display_follow_up_questions(follow_ups: List[Dict], backend_url: str):
    """Display and handle follow-up questions"""
    if not follow_ups:
        return
        
    st.markdown("### 💡 Suggested Follow-up Questions")
    
    for i, follow_up in enumerate(follow_ups):
        question = follow_up.get("question", "")
        category = follow_up.get("category", "General")
        relevance = follow_up.get("relevance_score", 0.5)
        
        col1, col2 = st.columns([0.8, 0.2])
        
        with col1:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                padding: 0.75rem;
                border-radius: 0.5rem;
                border-left: 3px solid #007bff;
                margin: 0.25rem 0;
            ">
                <div style="font-size: 0.75rem; color: #6c757d; margin-bottom: 0.25rem;">
                    📂 {category} • ⭐ {relevance:.1f}
                </div>
                <div style="font-size: 0.9rem;">
                    {question}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("Ask", key=f"followup_{i}", use_container_width=True):
                # Add the follow-up question to the chat
                result = ask_question(backend_url, question, st.session_state.conversation_context)
                
                # Update conversation history
                history_entry = {
                    "question": question,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "result": result
                }
                st.session_state.conversation_history.append(history_entry)
                st.rerun()


def update_conversation_context(question: str, result: Dict[str, Any]):
    """Update conversation context for better continuity"""
    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = {}
    
    context = st.session_state.conversation_context
    
    # Update conversation ID if available
    if result.get("conversation_id"):
        context["conversation_id"] = result["conversation_id"]
    
    # Maintain list of recent questions
    if "previous_questions" not in context:
        context["previous_questions"] = []
    
    context["previous_questions"].append(question)
    if len(context["previous_questions"]) > 5:
        context["previous_questions"] = context["previous_questions"][-5:]  # Keep last 5
    
    # Track user preferences (simple example)
    if "user_preferences" not in context:
        context["user_preferences"] = {"detailed_responses": True}


def format_answer_text(text: str) -> str:
    """Format answer text to improve readability"""
    # Clean up common formatting issues
    text = text.replace("**", "**")  # Ensure consistent bold formatting
    text = text.replace("*", "*")    # Ensure consistent italic formatting
    
    # Add proper spacing around numbered lists
    import re
    text = re.sub(r'(\d+\.)\s*([A-Z])', r'\n\1 **\2', text)
    
    # Improve bullet point formatting
    text = re.sub(r'([.:])\s*-\s*', r'\1\n\n- ', text)
    
    return text


def display_enhanced_answer(result: Dict[str, Any], show_metadata: bool = True):
    """Display answer with enhanced formatting and metadata"""
    if not result.get("success"):
        st.error(f"❌ {result.get('message', 'Unknown error occurred')}")
        return
    
    answer = result.get("answer", "")
    metadata = result.get("metadata", {})
    sources = result.get("sources", [])
    
    # Display main answer with proper markdown rendering
    st.markdown("**🤖 Assistant:**")
    
    # Format and render the answer as markdown for proper formatting
    formatted_answer = format_answer_text(answer)
    
    # Create a styled container for the answer
    with st.container():
        st.markdown(formatted_answer)
    
    # Display metadata if requested
    if show_metadata and metadata:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            confidence = metadata.get("confidence_level", "medium")
            reasoning = metadata.get("reasoning", "")
            display_confidence_indicator(confidence, reasoning)
        
        with col2:
            processing_time = metadata.get("processing_time_ms", 0)
            st.metric("⚡ Processing Time", f"{processing_time:.0f}ms")
        
        with col3:
            retrieval_count = metadata.get("retrieval_count", 0)
            st.metric("📄 Sources Used", retrieval_count)
        
        # Display limitations if any
        limitations = metadata.get("limitations", [])
        if limitations:
            with st.expander("⚠️ Response Limitations"):
                for limitation in limitations:
                    st.warning(limitation)
    
    # Display sources
    if sources:
        with st.expander(f"📚 Sources ({len(sources)} documents)", expanded=False):
            for i, source in enumerate(sources):
                source_type = source.get("source_type", "unknown")
                file_name = source.get("file_name", "Unknown file")
                score = source.get("score", 0)
                content = source.get("content", "")
                
                # Source type icons
                type_icons = {
                    "pdf": "📄",
                    "docx": "📝", 
                    "txt": "📄",
                    "xlsx": "📊",
                    "image": "🖼️",
                    "other": "📎"
                }
                
                icon = type_icons.get(source_type, "📎")
                
                st.markdown(f"""
                <div class="source-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <strong>{icon} {file_name}</strong>
                        <span style="font-size: 0.8rem; color: #6c757d;">
                            Score: {score:.3f}
                        </span>
                    </div>
                    <div style="font-size: 0.9rem; color: #495057; max-height: 100px; overflow-y: auto;">
                        {content[:300]}{"..." if len(content) > 300 else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def upload_documents_notice():
    """Show notice about deprecated upload functionality"""
    st.info("""
    📢 **Upload Method Changed**: 
    
    Document upload is now handled separately for better performance:
    
    1. 📁 Copy your files to the `Data/` directory 
    2. 🔄 Run: `python scripts/ingest_data.py`
    3. ✅ Documents will be indexed and available for queries
    
    This new method provides faster indexing and better resource management.
    """)

# === ENHANCED SIDEBAR ===
with st.sidebar:
    st.markdown("### 🧠 RAG Assistant Pro")
    st.markdown("**Enhanced Edition with Analytics**")
    
    # Page Navigation
    st.markdown("---")
    st.markdown("#### 📋 Navigation")
    page = st.selectbox(
        "Choose Page",
        ["💬 Chat", "🔍 Search", "📊 Analytics", "⚙️ Settings"],
        format_func=lambda x: x,
        key="page_selector"
    )
    
    st.session_state.current_page = page.split()[1].lower()
    
    # Backend Configuration
    st.markdown("---")
    st.markdown("#### 🔧 Backend Configuration")
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    
    # Enhanced Health Check
    st.markdown("#### 📊 System Health")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏥 Health Check", use_container_width=True):
            with st.spinner("Checking..."):
                st.session_state.backend_status = check_backend_health(backend_url)
                st.session_state.last_health_check = time.time()
    
    with col2:
        auto_check = st.checkbox("Auto-check", help="Automatically check health every 30s")
    
    # Auto health check
    if auto_check and (time.time() - st.session_state.last_health_check > 30):
        st.session_state.backend_status = check_backend_health(backend_url)
        st.session_state.last_health_check = time.time()
        st.rerun()
    
    # Enhanced status display
    if st.session_state.backend_status:
        status = st.session_state.backend_status
        if status["status"] == "healthy":
            st.success(f'{status["message"]} ({status["response_time"]}ms)')
            if "collection_info" in status and status["collection_info"]:
                collection = status["collection_info"]
                st.info(f"📚 Documents: {collection.get('points_count', 'N/A')}")
        elif status["status"] == "unhealthy":
            st.warning(status["message"])
        else:
            st.error(status["message"])
        
        st.caption(f"Last checked: {status.get('timestamp', 'Unknown')}")
    
    # Document Management Notice
    st.markdown("---")
    st.markdown("#### 📁 Document Management")
    if st.button("📋 Upload Instructions", use_container_width=True):
        st.session_state.show_upload_notice = True
    
    # Quick Actions
    st.markdown("---")
    st.markdown("#### ⚡ Quick Actions")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.conversation_history = []
        st.success("Chat history cleared!")
    
    if st.button("📊 Run System Test", use_container_width=True):
        with st.spinner("Testing system..."):
            # Test health
            health = check_backend_health(backend_url)
            if health["status"] == "healthy":
                # Test search
                search_result = search_documents(backend_url, "test", 1)
                if search_result["success"]:
                    st.success("✅ All systems operational!")
                else:
                    st.warning("⚠️ Search functionality issues")
            else:
                st.error("❌ Backend connection issues")
    
    # Advanced Mode Toggle
    st.markdown("---")
    st.session_state.advanced_mode = st.checkbox(
        "🔬 Advanced Mode", 
        value=st.session_state.advanced_mode,
        help="Show detailed technical information"
    )
    
    # System Information
    st.markdown("---")
    st.markdown("#### ℹ️ System Info")
    info_data = {
        "Vector DB": "Qdrant Cloud",
        "Region": "EU-West-2", 
        "Embeddings": "Azure OpenAI",
        "Model": "text-embedding-3-small",
        "LLM": "GPT-4/5",
        "Dimensions": "1536"
    }
    
    for key, value in info_data.items():
        st.markdown(f"**{key}:** {value}")

# === MAIN CONTENT BASED ON PAGE ===
st.markdown('<div class="main-header">🧠 RAG Document Assistant Pro</div>', unsafe_allow_html=True)
# Display upload notice if requested
if st.session_state.get("show_upload_notice", False):
    upload_documents_notice()
    if st.button("✅ Got it!"):
        st.session_state.show_upload_notice = False
        st.rerun()

# Enhanced metrics display
if st.session_state.backend_status and st.session_state.backend_status.get("collection_info"):
    collection = st.session_state.backend_status["collection_info"]
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📚 Documents", 
            collection.get("points_count", "N/A"),
            help="Total documents in the vector database"
        )
    with col2:
        st.metric(
            "🧠 Model", 
            "Azure OpenAI",
            "GPT-4/5",
            help="Language model for answer generation"
        )
    with col3:
        avg_response_time = "N/A"
        if st.session_state.response_times:
            avg_response_time = f"{sum(r['response_time'] for r in st.session_state.response_times[-10:]) / min(10, len(st.session_state.response_times)):.0f}ms"
        st.metric(
            "⚡ Avg Response", 
            avg_response_time,
            help="Average response time for last 10 queries"
        )
    with col4:
        st.metric(
            "🔄 Collection", 
            collection.get("collection_name", "documents"),
            collection.get("status", "unknown").title(),
            help="Vector database collection status"
        )
else:
    # Default metrics when backend info not available
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📚 Documents", "Check Status", help="Run health check to see document count")
    with col2:
        st.metric("🧠 Model", "Azure OpenAI", "GPT-4/5")
    with col3:
        st.metric("⚡ Response", "Ready", help="Query response times")
    with col4:
        st.metric("🔄 Status", "Unknown", help="Run health check for status")

st.markdown("---")

def handle_ask_question(question: str, backend_url: str):
    """Handles the logic for asking a question and updating the UI."""
    if not question.strip():
        return

    if not st.session_state.backend_status or st.session_state.backend_status["status"] != "healthy":
        st.warning("⚠️ Backend health unknown. Please run a health check first.")
        return

    with st.spinner("🤔 Analyzing documents and generating answer..."):
        result = ask_question(backend_url, question.strip(), st.session_state.conversation_context)
        
        update_conversation_context(question.strip(), result)
        
        history_entry = {
            "question": question.strip(),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "result": result
        }
        st.session_state.conversation_history.append(history_entry)
        
        # Clear the text input after submission
        if "chat_input" in st.session_state:
            st.session_state.chat_input = ""
        st.rerun()

# === PAGE ROUTING ===
if st.session_state.current_page == "chat":
    # === CHAT PAGE ===
    st.markdown("### 💬 Intelligent Document Chat")
    
    # Show suggested questions only if no conversation history exists
    if not st.session_state.conversation_history:
        st.markdown("#### 💡 Get Started with These Questions")
        st.markdown("*These suggestions will help you explore your documents. Click any question to get started!*")
        
        col1, col2, col3 = st.columns(3)
        
        suggestions = [
            "What are the main building requirements?",
            "Summarize the energy efficiency measures",
            "What safety protocols are mentioned?",
            "List all document categories",
            "What are the compliance requirements?",
            "Describe the project timeline"
        ]
        
        for i, suggestion in enumerate(suggestions):
            col = [col1, col2, col3][i % 3]
            with col:
                if st.button(f"💭 {suggestion}", key=f"suggest_{i}", use_container_width=True):
                    handle_ask_question(suggestion, backend_url)
        
        st.markdown("---")
    
    # Enhanced conversation history with better formatting
    if st.session_state.conversation_history:
        st.markdown("#### 📜 Conversation History")
        
        # Show conversation in enhanced format
        for i, entry in enumerate(st.session_state.conversation_history):
            
            # User message
            st.markdown("**🧑‍💼 You:**")
            st.markdown(f"> {entry['question']}")
            st.caption(f"🕒 {entry.get('timestamp', 'Unknown')}")
            
            # Assistant response using enhanced display
            if entry.get('result'):
                display_enhanced_answer(entry['result'], show_metadata=st.session_state.advanced_mode)
                
                # Display follow-up questions if available
                follow_ups = entry['result'].get('follow_up_questions', [])
                if follow_ups and i == len(st.session_state.conversation_history) - 1:  # Only for latest response
                    display_follow_up_questions(follow_ups, backend_url)
            else:
                # Legacy format fallback
                if entry.get('success'):
                    answer = entry.get('answer', 'No answer')
                    response_time = entry.get('response_time', 'N/A')
                    sources_count = len(entry.get('sources', []))
                    
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <div style="font-size: 1.05em; line-height: 1.6;">
                            {answer}
                        </div>
                        <div style="margin-top: 8px; font-size: 0.8em; color: #666;">
                            ⚡ {response_time}ms • 📚 {sources_count} sources
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")  # Separator between conversations
            
        st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
    
    # Question input
    question = st.text_area(
        "💬 Enter your question:",
        placeholder="Ask something about your documents... (e.g., 'What are the energy requirements for building HEA 01?')",
        help="Ask questions about the content in your indexed documents",
        height=100,
        key="chat_input"
    )
    
    # Enhanced control buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔍 Ask Question", use_container_width=True, type="primary"):
            handle_ask_question(st.session_state.chat_input, backend_url)
    with col2:
        search_button = st.button("🔎 Search Only", use_container_width=True)
    with col3:
        favorite_button = st.button("⭐ Add to Favorites", use_container_width=True, disabled=not question.strip())
    with col4:
        clear_button = st.button("🗑️ Clear All", use_container_width=True)
    
    # Handle favorite questions
    if favorite_button and question.strip():
        if question.strip() not in st.session_state.favorite_questions:
            st.session_state.favorite_questions.append(question.strip())
            st.success("Added to favorites! ⭐")
        else:
            st.info("Already in favorites!")
    
    if clear_button:
        st.session_state.conversation_history = []
        st.success("History cleared!")
        st.rerun()
    
    # Process search only
    if search_button and question.strip():
        with st.spinner("🔍 Searching documents..."):
            search_result = search_documents(backend_url, question.strip(), 10)
            
            if search_result["success"]:
                st.markdown("### 🔍 Search Results")
                st.caption(f"Found {len(search_result['results'])} results in {search_result['response_time']}ms")
                
                for i, result in enumerate(search_result["results"], 1):
                    with st.expander(f"{i}. {result.get('file_name', 'Unknown')} (Score: {result.get('score', 0):.3f})"):
                        st.text(result.get('content', 'No content'))
            else:
                st.error(f"Search failed: {search_result['message']}")

elif st.session_state.current_page == "search":
    # === ENHANCED SEARCH PAGE ===
    st.markdown("### 🔍 Intelligent Document Search")
    st.markdown("*Use our advanced search to find specific information with category filtering and smart metadata*")
    
    # Get available categories for filtering
    categories_data = get_available_categories(backend_url)
    available_categories = categories_data.get("available_filters", [])
    
    # Search Configuration
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("🔎 Search Query", placeholder="Enter keywords to search in documents...")
    with col2:
        search_limit = st.selectbox("📊 Results", [5, 10, 20, 50], index=1)
    with col3:
        use_intelligent = st.checkbox("🧠 Smart Search", value=True, help="Use AI-powered category detection and filtering")
    
    # Advanced Filters (collapsible)
    with st.expander("🎛️ Advanced Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Category filter
            selected_categories = st.multiselect(
                "📁 Filter by Categories",
                options=available_categories,
                help="Select specific document categories to search within"
            )
            
        with col2:
            # Document type filter
            doc_types = ["PDF", "DOCX", "XLSX", "TXT"]
            selected_doc_types = st.multiselect(
                "📄 Document Types",
                options=doc_types,
                help="Filter by document file types"
            )
            
        with col3:
            auto_filter = st.checkbox(
                "🎯 Auto-detect Categories",
                value=True,
                help="Automatically detect relevant categories from your query"
            )
    
    # Display available categories summary
    if available_categories:
        st.markdown("#### 📂 Available Document Categories")
        cols = st.columns(min(len(available_categories), 4))
        for i, category in enumerate(available_categories):
            with cols[i % 4]:
                count = categories_data.get("categories", {}).get(category, 0)
                st.metric(category.replace(" & ", " &\n"), count, help=f"Documents in {category}")
    
    # Search Buttons
    col1, col2 = st.columns(2)
    with col1:
        intelligent_search_btn = st.button(
            "🧠 Intelligent Search", 
            use_container_width=True, 
            type="primary",
            disabled=not use_intelligent
        )
    with col2:
        basic_search_btn = st.button(
            "🔍 Basic Search", 
            use_container_width=True,
            help="Traditional vector similarity search"
        )
    
    # Process searches
    search_result = None
    search_type = None
    
    if (intelligent_search_btn or basic_search_btn) and search_query.strip():
        if intelligent_search_btn and use_intelligent:
            # Intelligent Search
            search_type = "intelligent"
            with st.spinner("🧠 Running intelligent search..."):
                search_result = intelligent_search(
                    backend_url=backend_url,
                    query=search_query,
                    limit=search_limit,
                    categories=selected_categories if selected_categories else None,
                    document_types=selected_doc_types if selected_doc_types else None,
                    auto_filter=auto_filter
                )
        else:
            # Basic Search
            search_type = "basic"
            with st.spinner("🔍 Searching documents..."):
                search_result = search_documents(backend_url, search_query, search_limit)
    
    # Display Results
    if search_result:
        if search_result["success"]:
            results = search_result["results"]
            metadata = search_result.get("metadata", {})
            
            # Add to search history
            st.session_state.search_history.append({
                "query": search_query,
                "results_count": len(results),
                "timestamp": datetime.now(),
                "response_time": search_result["response_time"],
                "search_type": search_type
            })
            
            # Search Results Header
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Results Found", len(results))
            with col2:
                st.metric("⚡ Response Time", f"{search_result['response_time']}ms")
            with col3:
                st.metric("🔍 Search Type", search_type.title())
            with col4:
                if search_type == "intelligent" and metadata.get("auto_filter_applied"):
                    st.metric("🎯 Auto-Filter", "Applied")
                else:
                    st.metric("🎯 Auto-Filter", "None")
            
            # Display intelligent search metadata
            if search_type == "intelligent" and metadata:
                st.markdown("#### 🧠 Intelligent Search Insights")
                col1, col2 = st.columns(2)
                
                with col1:
                    if metadata.get("filtered_categories"):
                        st.info(f"🎯 **Categories Detected:** {', '.join(metadata['filtered_categories'])}")
                    
                with col2:
                    if metadata.get("filtered_document_types"):
                        st.info(f"📄 **Document Types:** {', '.join(metadata['filtered_document_types'])}")
            
            # Results Visualization (for advanced mode)
            if results and st.session_state.advanced_mode:
                if search_type == "intelligent":
                    scores = [r.get('relevance_score', 0) for r in results]
                    vector_scores = [r.get('vector_score', 0) for r in results]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name='Relevance Score', x=list(range(1, len(scores) + 1)), y=scores))
                    fig.add_trace(go.Bar(name='Vector Score', x=list(range(1, len(vector_scores) + 1)), y=vector_scores))
                    fig.update_layout(
                        title="Intelligent Search Scoring",
                        xaxis_title="Result #",
                        yaxis_title="Score",
                        barmode='group'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    scores = [r.get('score', 0) for r in results]
                    fig = px.bar(
                        x=list(range(1, len(scores) + 1)),
                        y=scores,
                        title="Basic Search Relevance Scores",
                        labels={"x": "Result #", "y": "Relevance Score"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # Display Results
            st.markdown("#### 📋 Search Results")
            for i, result in enumerate(results, 1):
                if search_type == "intelligent":
                    # Enhanced display for intelligent search
                    relevance_score = result.get('relevance_score', 0)
                    vector_score = result.get('vector_score', 0)
                    category_match = result.get('category_match', False)
                    
                    relevance_color = "🟢" if relevance_score > 0.8 else "🟡" if relevance_score > 0.5 else "🔴"
                    match_indicator = "🎯" if category_match else ""
                    
                    with st.expander(f"{relevance_color} {match_indicator} {i}. {result.get('metadata', {}).get('file_name', 'Unknown')} (Relevance: {relevance_score:.3f})"):
                        # Metadata display
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown("**Content:**")
                            st.text_area("", result.get('content', 'No content available'), height=150, disabled=True, key=f"intelligent_result_{i}")
                            
                        with col2:
                            st.markdown("**📊 Scores:**")
                            st.metric("Relevance", f"{relevance_score:.3f}")
                            st.metric("Vector", f"{vector_score:.3f}")
                            
                            st.markdown("**📁 Metadata:**")
                            metadata_info = result.get('metadata', {})
                            for key, value in metadata_info.items():
                                if value and key != 'technical_keywords':
                                    st.text(f"{key}: {value}")
                            
                            # Technical keywords
                            keywords = metadata_info.get('technical_keywords', [])
                            if keywords:
                                st.markdown("**🔬 Keywords:**")
                                for keyword in keywords[:5]:  # Show first 5
                                    st.code(keyword)
                else:
                    # Basic display for traditional search
                    relevance_color = "🟢" if result.get('score', 0) > 0.8 else "🟡" if result.get('score', 0) > 0.5 else "🔴"
                    
                    with st.expander(f"{relevance_color} {i}. {result.get('file_name', 'Unknown')} (Score: {result.get('score', 0):.3f})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown("**Content:**")
                            st.text(result.get('content', 'No content available'))
                        with col2:
                            st.markdown("**Metadata:**")
                            metadata_info = result.get('metadata', {})
                            for key, value in metadata_info.items():
                                st.text(f"{key}: {value}")
        else:
            st.error(f"❌ Search failed: {search_result['message']}")
    elif search_query.strip() and (intelligent_search_btn or basic_search_btn):
        st.warning("Please enter a search query")
    
    # Search history
    if st.session_state.search_history:
        st.markdown("---")
        st.markdown("### 📋 Recent Searches")
        
        for search in st.session_state.search_history[-5:]:  # Show last 5
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.text(search["query"])
            with col2:
                st.text(f"{search['results_count']} results")
            with col3:
                st.text(f"{search['response_time']}ms")
            with col4:
                st.text(search["timestamp"].strftime("%H:%M"))

elif st.session_state.current_page == "analytics":
    # === ANALYTICS PAGE ===
    st.markdown("### 📊 System Analytics & Performance")
    
    # Performance metrics
    if st.session_state.response_times:
        st.markdown("#### ⚡ Response Time Analytics")
        
        df = pd.DataFrame(st.session_state.response_times)
        
        col1, col2 = st.columns(2)
        with col1:
            # Response time trend
            fig = px.line(
                df, 
                x="timestamp", 
                y="response_time",
                title="Response Time Trend",
                labels={"response_time": "Response Time (ms)", "timestamp": "Time"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Response time distribution
            fig = px.histogram(
                df,
                x="response_time",
                title="Response Time Distribution",
                labels={"response_time": "Response Time (ms)", "count": "Frequency"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Statistics
        st.markdown("#### 📈 Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        response_times = [r["response_time"] for r in st.session_state.response_times]
        with col1:
            st.metric("Average", f"{sum(response_times) / len(response_times):.0f}ms")
        with col2:
            st.metric("Minimum", f"{min(response_times):.0f}ms")
        with col3:
            st.metric("Maximum", f"{max(response_times):.0f}ms")
        with col4:
            st.metric("Total Queries", len(st.session_state.response_times))
    
    # Usage analytics
    st.markdown("---")
    st.markdown("#### 📊 Usage Analytics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💬 Chat Sessions", len(st.session_state.conversation_history))
        st.metric("🔍 Searches", len(st.session_state.search_history))
    with col2:
        st.metric("⭐ Favorite Questions", len(st.session_state.favorite_questions))
        health_checks = 1 if st.session_state.backend_status else 0
        st.metric("🏥 Health Checks", health_checks)
    
    # Question analytics
    if st.session_state.conversation_history:
        st.markdown("---")
        st.markdown("#### ❓ Question Analytics")
        
        questions = [entry["question"] for entry in st.session_state.conversation_history]
        question_lengths = [len(q.split()) for q in questions]
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(
                x=question_lengths,
                title="Question Length Distribution",
                labels={"x": "Words per Question", "y": "Frequency"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            success_rate = sum(1 for entry in st.session_state.conversation_history if entry.get("success", False))
            success_percentage = (success_rate / len(st.session_state.conversation_history)) * 100
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=["Successful", "Failed"],
                    values=[success_rate, len(st.session_state.conversation_history) - success_rate],
                    title="Query Success Rate"
                )
            ])
            st.plotly_chart(fig, use_container_width=True)

elif st.session_state.current_page == "settings":
    # === SETTINGS PAGE ===
    st.markdown("### ⚙️ Settings & Configuration")
    
    # Export/Import functionality
    st.markdown("#### 💾 Data Management")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Export Chat History", use_container_width=True):
            if st.session_state.conversation_history:
                export_data = {
                    "conversation_history": st.session_state.conversation_history,
                    "search_history": st.session_state.search_history,
                    "favorite_questions": st.session_state.favorite_questions,
                    "export_timestamp": datetime.now().isoformat()
                }
                st.download_button(
                    "💾 Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"rag_chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.info("No data to export")
    
    with col2:
        if st.button("🗑️ Reset All Data", use_container_width=True):
            if st.button("⚠️ Confirm Reset", type="secondary"):
                st.session_state.conversation_history = []
                st.session_state.search_history = []
                st.session_state.favorite_questions = []
                st.session_state.response_times = []
                st.success("All data reset!")
                st.rerun()
    
    # Favorite questions management
    if st.session_state.favorite_questions:
        st.markdown("---")
        st.markdown("#### ⭐ Favorite Questions")
        
        for i, fav in enumerate(st.session_state.favorite_questions):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(fav)
            with col2:
                if st.button("🗑️", key=f"del_fav_{i}", help="Remove from favorites"):
                    st.session_state.favorite_questions.pop(i)
                    st.rerun()
    
    # Advanced settings
    st.markdown("---")
    st.markdown("#### 🔬 Advanced Settings")
    
    # Theme customization (placeholder for future enhancement)
    theme = st.selectbox("🎨 Theme", ["Default", "Dark", "Light", "Custom"])
    auto_scroll = st.checkbox("📜 Auto-scroll to new messages", value=True)
    show_timestamps = st.checkbox("🕒 Show detailed timestamps", value=True)
    enable_notifications = st.checkbox("🔔 Enable notifications", value=False)
    
    st.info("💡 More advanced settings coming soon!")

# === FOOTER ===
st.markdown("---")

# Enhanced footer with system status
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.session_state.backend_status:
        status_emoji = {"healthy": "🟢", "unhealthy": "🟡", "timeout": "🔴", "connection_error": "🔴", "error": "🔴"}
        emoji = status_emoji.get(st.session_state.backend_status["status"], "⚪")
        st.markdown(f"**System Status:** {emoji} {st.session_state.backend_status['status'].title()}")
    else:
        st.markdown("**System Status:** ⚪ Unknown")

with footer_col2:
    st.markdown(f"**Active Page:** 📋 {st.session_state.current_page.title()}")

with footer_col3:
    st.markdown(f"**Session:** 💬 {len(st.session_state.conversation_history)} chats")

st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem; margin-top: 2rem; border-top: 1px solid #eee;'>
    <p>🧠 <strong>RAG Document Assistant Pro v3.0</strong> | Powered by Qdrant Cloud & Azure OpenAI</p>
    <p>💡 Enhanced with multi-page navigation, analytics, and advanced search capabilities!</p>
</div>
""", unsafe_allow_html=True)
