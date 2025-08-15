from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types of document sources"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    XLSX = "xlsx"
    IMAGE = "image"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence levels for answers"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class Source(BaseModel):
    file_name: str
    content: str
    score: float
    source_type: Optional[SourceType] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    excerpt_start: Optional[int] = None
    excerpt_end: Optional[int] = None


class QuestionContext(BaseModel):
    """Context for the current question"""
    conversation_id: Optional[str] = None
    previous_questions: Optional[List[str]] = Field(default=None, max_items=5)
    user_preferences: Optional[Dict[str, Any]] = None


class QuestionRequest(BaseModel):
    question: str
    context: Optional[QuestionContext] = None
    max_sources: Optional[int] = Field(default=4, ge=1, le=10)
    include_metadata: Optional[bool] = True
    session_id: Optional[str] = None


class AnswerMetadata(BaseModel):
    """Metadata about the generated answer"""
    processing_time: float
    sources_count: int
    reasoning: Optional[str] = None
    limitations: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    model_used: Optional[str] = None
    query_intent: Optional[Dict[str, Any]] = None
    context_info: Optional[Dict[str, Any]] = None
    confidence_level: Optional[ConfidenceLevel] = None
    
    
class FollowUpQuestion(BaseModel):
    """Suggested follow-up questions"""
    question: str
    reasoning: str
    category: Optional[str] = None
    relevance_score: Optional[float] = 0.8


class RAGResponse(BaseModel):
    answer: str
    sources: List[Source]
    metadata: AnswerMetadata
    follow_up_questions: Optional[List[FollowUpQuestion]] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    """Individual chat message"""
    id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ConversationSummary(BaseModel):
    """Summary of conversation topics and key points"""
    main_topics: List[str]
    key_findings: List[str]
    document_coverage: Dict[str, int]  # file_name -> times_referenced
    total_messages: int
    duration_minutes: Optional[float] = None


class HealthCheckResponse(BaseModel):
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Enhanced search result structure"""
    query: str
    results: List[Source]
    total_found: int
    search_time_ms: float
    filters_applied: Optional[Dict[str, Any]] = None


class SystemStats(BaseModel):
    """System performance and usage statistics"""
    total_documents: int
    total_queries_today: int
    avg_response_time_ms: float
    most_common_topics: List[Dict[str, Any]]
    system_health: str
