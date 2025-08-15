"""
Enhanced RAG Service with Advanced Context Processing

This module provides improved RAG capabilities with:
- Context-aware prompt engineering
- Multi-layered response generation
- Enhanced confidence assessment
- Smart context consolidation
"""

import os
import logging
import time
import uuid
import re
from typing import List, Tuple, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from backend.enhanced_query_processor import EnhancedQdrantQueryProcessor, InMemoryDocumentProcessor
from backend.config import get_first_env
from backend.models import (
    Source, SourceType, ConfidenceLevel, AnswerMetadata, 
    FollowUpQuestion, RAGResponse, QuestionRequest
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextProcessor:
    """Advanced context processing and consolidation."""
    
    @staticmethod
    def consolidate_context(search_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Consolidate and organize search results for better context."""
        if not search_results:
            return {"consolidated_text": "", "context_info": {}}
        
        # Group results by category and document type
        context_groups = {
            'primary': [],    # High relevance results
            'supporting': [], # Medium relevance results
            'reference': []   # Lower relevance results
        }
        
        # Categorize results by enhanced score
        for result in search_results:
            score = result.get('enhanced_score', result.get('score', 0))
            if score >= 0.8:
                context_groups['primary'].append(result)
            elif score >= 0.6:
                context_groups['supporting'].append(result)
            else:
                context_groups['reference'].append(result)
        
        # Build consolidated context
        consolidated_parts = []
        
        # Add primary context first
        if context_groups['primary']:
            consolidated_parts.append("=== PRIMARY INFORMATION ===")
            for i, result in enumerate(context_groups['primary'], 1):
                content = result.get('enhanced_content', result.get('content', ''))
                file_info = f"[Source {i}: {result.get('file_name', 'Unknown')} - {result.get('category', 'Unknown')}]"
                consolidated_parts.append(f"{file_info}\n{content}\n")
        
        # Add supporting context
        if context_groups['supporting']:
            consolidated_parts.append("=== SUPPORTING INFORMATION ===")
            for i, result in enumerate(context_groups['supporting'], len(context_groups['primary']) + 1):
                content = result.get('enhanced_content', result.get('content', ''))
                file_info = f"[Source {i}: {result.get('file_name', 'Unknown')} - {result.get('category', 'Unknown')}]"
                consolidated_parts.append(f"{file_info}\n{content}\n")
        
        # Add reference context if needed and space allows
        if context_groups['reference'] and len(consolidated_parts) < 3000:  # Token management
            consolidated_parts.append("=== REFERENCE INFORMATION ===")
            for i, result in enumerate(context_groups['reference'][:2], len(context_groups['primary']) + len(context_groups['supporting']) + 1):
                content = result.get('content', '')[:300] + "..." if len(result.get('content', '')) > 300 else result.get('content', '')
                file_info = f"[Source {i}: {result.get('file_name', 'Unknown')}]"
                consolidated_parts.append(f"{file_info}\n{content}\n")
        
        consolidated_text = "\n".join(consolidated_parts)
        
        # Generate context metadata
        context_info = {
            'total_sources': len(search_results),
            'primary_sources': len(context_groups['primary']),
            'supporting_sources': len(context_groups['supporting']),
            'reference_sources': len(context_groups['reference']),
            'categories_covered': list(set(r.get('category', 'Unknown') for r in search_results)),
            'document_types': list(set(r.get('document_type', 'general') for r in search_results)),
            'has_technical_content': any(r.get('technical_content', False) for r in search_results),
            'avg_relevance_score': sum(r.get('enhanced_score', r.get('score', 0)) for r in search_results) / len(search_results),
            'context_length': len(consolidated_text)
        }
        
        return {
            'consolidated_text': consolidated_text,
            'context_info': context_info
        }

    @staticmethod
    def detect_query_intent(query: str) -> Dict[str, Any]:
        """Detect the intent and requirements of the query."""
        try:
            query_lower = query.lower()
            
            intent = {
                'type': 'general',
                'requires_calculation': False,
                'requires_specific_values': False,
                'requires_comparison': False,
                'domain': 'general',
                'complexity': 'medium'
            }
            
            # Detect question type
            if any(word in query_lower for word in ['what', 'which', 'define', 'explain']):
                intent['type'] = 'definition'
            elif any(word in query_lower for word in ['how', 'calculate', 'compute', 'determine']):
                intent['type'] = 'procedure'
                intent['requires_calculation'] = True
            elif any(word in query_lower for word in ['why', 'reason', 'cause']):
                intent['type'] = 'explanation'
            elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
                intent['type'] = 'comparison'
                intent['requires_comparison'] = True
            
            # Detect domain
            domain_keywords = {
                'energy': ['energy', 'thermal', 'heating', 'cooling', 'efficiency', 'kwh', 'consumption'],
                'water': ['water', 'plumbing', 'drainage', 'sanitary', 'hydraulic'],
                'transport': ['transport', 'access', 'mobility', 'traffic', 'parking'],
                'regulatory': ['requirement', 'standard', 'regulation', 'compliance', 'norm'],
                'technical': ['calculation', 'analysis', 'assessment', 'audit', 'evaluation']
            }
            
            for domain, keywords in domain_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    intent['domain'] = domain
                    break
            
            # Detect complexity
            if len(query.split()) > 15 or intent['requires_calculation'] or intent['requires_comparison']:
                intent['complexity'] = 'high'
            elif len(query.split()) < 8 and intent['type'] == 'definition':
                intent['complexity'] = 'low'
            
            # Detect if specific values are requested
            if any(term in query_lower for term in ['value', 'number', 'amount', 'quantity', 'rate', 'percentage']):
                intent['requires_specific_values'] = True
            
            return intent
        except Exception as e:
            logger.error(f"Error detecting query intent: {e}")
            # Return default intent if there's an error
            return {
                'type': 'general',
                'requires_calculation': False,
                'requires_specific_values': False,
                'requires_comparison': False,
                'domain': 'general',
                'complexity': 'medium'
            }
# Enhanced prompt templates for different query types and domains
DOMAIN_PROMPTS = {
    'energy': """
You are an expert building energy consultant analyzing energy evaluation documents.

Context Information:
{context}

---

Question: {question}

Instructions:
1. Focus on energy-related requirements, calculations, and performance metrics
2. When providing values, always include units (kWh, MW, °C, etc.)
3. Reference specific standards or regulations mentioned in the context
4. If calculations are mentioned, explain the methodology
5. Highlight any energy efficiency requirements or targets

Provide a comprehensive answer that addresses the energy aspects of the question based solely on the provided context.
""",

    'regulatory': """
You are a building compliance expert analyzing regulatory and standard documents.

Context Information:
{context}

---

Question: {question}

Instructions:
1. Focus on requirements, standards, regulations, and compliance aspects
2. Clearly state what is required vs. what is recommended
3. Reference specific standard numbers or regulation names when mentioned
4. Explain compliance procedures if described in the context
5. Highlight any mandatory vs. optional requirements

Provide a detailed answer focusing on regulatory and compliance aspects based solely on the provided context.
""",

    'technical': """
You are a technical building consultant analyzing technical documentation and calculations.

Context Information:
{context}

---

Question: {question}

Instructions:
1. Focus on technical calculations, methodologies, and analytical procedures
2. Explain calculation methods and assumptions when present
3. Provide technical values with appropriate units and precision
4. Reference technical standards or methodologies mentioned
5. Highlight any technical limitations or assumptions

Provide a technical analysis based solely on the provided context.
""",

    'general': """
You are an expert building consultant analyzing building evaluation documents.

Context Information:
{context}

---

Question: {question}

Instructions:
1. Provide a comprehensive answer based solely on the provided context
2. Include specific values, requirements, or procedures when mentioned
3. Reference source documents when providing information
4. Explain technical terms if they appear in the context
5. Be precise and factual, avoiding speculation

Answer the question thoroughly using only the information provided in the context.
"""
}

# Follow-up question templates by domain
FOLLOWUP_TEMPLATES = {
    'general': [
        "What additional information can you provide about this topic?",
        "Are there any related documents I should be aware of?",
        "What are the key points to understand about this subject?",
        "Can you explain how this information is typically applied?"
    ],
    'energy': [
        "What are the specific energy efficiency targets mentioned?",
        "How is energy performance calculated or measured?",
        "What energy standards or regulations apply?",
        "Are there any energy consumption limits specified?"
    ],
    'regulatory': [
        "What specific standards or regulations are referenced?",
        "What are the compliance verification procedures?",
        "Are there any exceptions or special conditions mentioned?",
        "What documentation is required for compliance?"
    ],
    'technical': [
        "What calculation methodologies are used?",
        "What are the key technical parameters or assumptions?",
        "How are the results validated or verified?",
        "What technical standards guide these procedures?"
    ],
    'water': [
        "What are the water consumption requirements?",
        "How is water system performance evaluated?",
        "What water quality standards apply?",
        "Are there water efficiency targets specified?"
    ],
    'transport': [
        "What accessibility requirements are specified?",
        "How is transport impact assessed?",
        "What parking or access standards apply?",
        "Are there mobility or circulation requirements?"
    ]
}


class AdvancedRAGService:
    """Enhanced RAG service with advanced context processing and domain-aware responses."""
    
    def __init__(self, doc_processor):
        self.doc_processor = doc_processor
        self.context_processor = ContextProcessor()
        self.conversation_context = {}
        
        if os.environ.get("USE_FAKE_SERVICES", "false").lower() == "true":
            self.llm = None
            logger.info("✅ Advanced RAG Service initialized in fake mode")
        else:
            chat_deployment = get_first_env("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "AZURE_OPENAI_GPT_DEPLOYMENT_NAME")
            if not chat_deployment:
                raise EnvironmentError("Chat deployment env var not found")
            
            self.llm = AzureChatOpenAI(
                azure_deployment=chat_deployment,
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_version=os.environ["OPENAI_API_VERSION"],
                temperature=0.1,  # Low temperature for factual responses
                max_tokens=2000   # Increased for detailed responses
            )
            logger.info("✅ Advanced RAG Service initialized with Azure OpenAI")

    def _detect_source_type(self, filename: str) -> SourceType:
        """Detect source type from filename."""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        type_mapping = {
            'pdf': SourceType.PDF,
            'docx': SourceType.DOCX,
            'doc': SourceType.DOCX,
            'txt': SourceType.TXT,
            'xlsx': SourceType.XLSX,
            'xls': SourceType.XLSX,
            'jpg': SourceType.IMAGE,
            'jpeg': SourceType.IMAGE,
            'png': SourceType.IMAGE
        }
        return type_mapping.get(extension, SourceType.OTHER)

    def _assess_response_confidence(self, query: str, context_info: Dict[str, Any], response_text: str) -> Tuple[ConfidenceLevel, str]:
        """Assess confidence level based on context quality and response characteristics."""
        
        # Base confidence assessment
        confidence_score = 0.5
        reasoning_parts = []
        
        # Context quality factors
        if context_info['primary_sources'] >= 2:
            confidence_score += 0.2
            reasoning_parts.append("multiple primary sources")
        elif context_info['primary_sources'] == 1:
            confidence_score += 0.1
            reasoning_parts.append("one primary source")
        
        if context_info['avg_relevance_score'] >= 0.8:
            confidence_score += 0.15
            reasoning_parts.append("high relevance scores")
        elif context_info['avg_relevance_score'] >= 0.6:
            confidence_score += 0.1
            reasoning_parts.append("good relevance scores")
        
        # Technical content boost for technical queries
        query_intent = self.context_processor.detect_query_intent(query)
        if query_intent['domain'] in ['energy', 'technical'] and context_info['has_technical_content']:
            confidence_score += 0.1
            reasoning_parts.append("technical content available")
        
        # Response quality indicators
        if len(response_text) > 500 and 'specific' in response_text.lower():
            confidence_score += 0.05
            reasoning_parts.append("detailed response")
        
        # Check for uncertainty indicators in response
        uncertainty_indicators = ['may', 'might', 'possibly', 'unclear', 'insufficient information']
        if any(indicator in response_text.lower() for indicator in uncertainty_indicators):
            confidence_score -= 0.15
            reasoning_parts.append("some uncertainty expressed")
        
        # Determine confidence level
        if confidence_score >= 0.8:
            level = ConfidenceLevel.HIGH
        elif confidence_score >= 0.6:
            level = ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.4:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.UNCERTAIN
        
        reasoning = f"Based on {', '.join(reasoning_parts)}" if reasoning_parts else "Standard assessment"
        
        return level, reasoning

    def _generate_followup_questions(self, query: str, context_info: Dict[str, Any]) -> List[FollowUpQuestion]:
        """Generate relevant follow-up questions based on context and domain."""
        try:
            query_intent = self.context_processor.detect_query_intent(query)
            domain = query_intent.get('domain', 'general')
            
            # Get domain-specific templates with fallback to general
            if domain in FOLLOWUP_TEMPLATES:
                templates = FOLLOWUP_TEMPLATES[domain]
            else:
                logger.warning(f"Domain '{domain}' not found in FOLLOWUP_TEMPLATES. Using 'general' domain.")
                templates = FOLLOWUP_TEMPLATES.get('general', [
                    "What additional information can you provide about this topic?",
                    "Are there any related documents I should be aware of?"
                ])
            
            # Select most relevant follow-ups based on available context
            followups = []
            
            # Always include a general exploration question
            followups.append(FollowUpQuestion(
                question=f"What additional details are available about {domain} aspects in these documents?",
                reasoning="Explore additional information in the same domain"
            ))
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}")
            # Fallback to basic follow-up questions
            return [
                FollowUpQuestion(
                    question="What additional information can you provide about this topic?",
                    reasoning="Basic follow-up due to error"
                ),
                FollowUpQuestion(
                    question="Are there any related documents I should be aware of?",
                    reasoning="Basic follow-up due to error"
                )
            ]
        
        # Add domain-specific questions
        if len(templates) >= 2:
            followups.extend([
                FollowUpQuestion(question=templates[0], reasoning="Domain-specific inquiry"),
                FollowUpQuestion(question=templates[1], reasoning="Further domain exploration")
            ])
        
        # Add context-specific question based on available categories
        if len(context_info['categories_covered']) > 1:
            categories = ', '.join(context_info['categories_covered'])
            followups.append(FollowUpQuestion(
                question=f"How do the requirements compare across different categories ({categories})?",
                reasoning="Cross-category comparison"
            ))
        
        return followups[:4]  # Limit to 4 follow-ups

    def ask_question(self, request: QuestionRequest) -> RAGResponse:
        """Process question with enhanced RAG capabilities."""
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        
        try:
            logger.info(f"Processing enhanced question: {request.question[:100]}...")
            
            # Detect query intent
            query_intent = self.context_processor.detect_query_intent(request.question)
            # Ensure the domain key exists
            if 'domain' not in query_intent:
                query_intent['domain'] = 'general'
            logger.info(f"Query intent: {query_intent}")
            
            # Retrieve relevant documents with enhanced search
            search_results = self.doc_processor.similarity_search(request.question, limit=6)
            
            if not search_results:
                return RAGResponse(
                    answer="I could not find relevant information in the documents to answer your question.",
                    sources=[],
                    confidence=ConfidenceLevel.UNCERTAIN,
                    metadata=AnswerMetadata(
                        processing_time=time.time() - start_time,
                        sources_count=0,
                        reasoning="No relevant documents found",
                        confidence_level=ConfidenceLevel.UNCERTAIN
                    ),
                    follow_up_questions=[],
                    session_id=session_id
                )
            
            # Consolidate context
            context_data = self.context_processor.consolidate_context(search_results, request.question)
            consolidated_context = context_data['consolidated_text']
            context_info = context_data['context_info']
            
            logger.info(f"Context consolidated: {context_info['total_sources']} sources, {context_info['context_length']} chars")
            
            # Prepare sources
            sources = []
            for i, result in enumerate(search_results, 1):
                sources.append(Source(
                    content=result.get("content", ""),
                    file_name=result.get("file_name", "Unknown"),
                    source_type=self._detect_source_type(result.get("file_name", "")),
                    score=result.get("enhanced_score", result.get("score", 0.0)),
                    metadata=result.get("metadata", {})
                ))
            
            # Generate response
            if self.llm is None:
                # Fake service response
                answer = f"[FAKE SERVICE] Based on the analysis of {len(search_results)} documents, here's what I found regarding your question about {request.question}. The context includes information from {', '.join(context_info['categories_covered'])} categories."
                confidence_level = ConfidenceLevel.MEDIUM
                reasoning = "Fake service simulation"
            else:
                # Select appropriate prompt based on domain
                domain = query_intent['domain']
                if domain in DOMAIN_PROMPTS:
                    prompt_template = DOMAIN_PROMPTS[domain]
                else:
                    logger.warning(f"Domain '{domain}' not found in DOMAIN_PROMPTS. Using 'general' domain.")
                    prompt_template = DOMAIN_PROMPTS.get('general', DOMAIN_PROMPTS['general'])
                    
                prompt = ChatPromptTemplate.from_template(prompt_template)
                
                # Generate response
                response = self.llm.invoke(prompt.format(
                    context=consolidated_context,
                    question=request.question
                ))
                answer = response.content
                
                # Assess confidence
                confidence_level, reasoning = self._assess_response_confidence(
                    request.question, context_info, answer
                )
            
            # Generate follow-up questions
            follow_up_questions = self._generate_followup_questions(request.question, context_info)
            
            processing_time = time.time() - start_time
            
            response = RAGResponse(
                answer=answer,
                sources=sources,
                confidence=confidence_level,
                metadata=AnswerMetadata(
                    processing_time=processing_time,
                    sources_count=len(sources),
                    reasoning=reasoning,
                    query_intent=query_intent,
                    context_info=context_info,
                    confidence_level=confidence_level
                ),
                follow_up_questions=follow_up_questions,
                session_id=session_id
            )
            
            logger.info(f"Enhanced response generated in {processing_time:.2f}s with {confidence_level.value} confidence")
            return response
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in enhanced ask_question: {str(e)}")
            logger.error(f"Traceback: {error_details}")
            return RAGResponse(
                answer=f"I encountered an error while processing your question. Please try again or contact support.",
                sources=[],
                confidence=ConfidenceLevel.UNCERTAIN,
                metadata=AnswerMetadata(
                    processing_time=time.time() - start_time,
                    sources_count=0,
                    reasoning=f"Error: {str(e)}",
                    confidence_level=ConfidenceLevel.UNCERTAIN
                ),
                follow_up_questions=[],
                session_id=session_id
            )

    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Enhanced document search with better result formatting."""
        try:
            results = self.doc_processor.similarity_search(query, limit=limit)
            
            # Format results for API response
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "file_name": result.get("file_name", "Unknown"),
                    "category": result.get("category", "Unknown"),
                    "document_type": result.get("document_type", "general"),
                    "score": result.get("enhanced_score", result.get("score", 0.0)),
                    "technical_content": result.get("technical_content", False),
                    "metadata": result.get("metadata", {})
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in enhanced search_documents: {e}")
            return []


# Alias for backward compatibility
EnhancedRAGService = AdvancedRAGService
