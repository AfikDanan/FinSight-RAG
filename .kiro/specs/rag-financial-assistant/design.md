# RAG-Based Financial Analysis Assistant - Design Document

## Overview

The RAG-Based Financial Analysis Assistant is built using a modern React frontend and FastAPI backend architecture with an on-demand document processing workflow. The system starts with an empty database and dynamically scrapes, processes, and vectorizes SEC EDGAR filings based on user requests. Users select a company ticker and time range (1, 3, or 5 years), triggering a pipeline that scrapes documents, chunks them, stores them locally, vectorizes them in Pinecone, and then enables a chat interface for querying the processed company data.

## Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer - React"
        TICKER[Ticker Input]
        TIMERANGE[Time Range Selector]
        PROGRESS[Processing Status]
        CHAT[Chat Interface]
        STATE[Zustand State Management]
    end
    
    subgraph "Backend API Layer - FastAPI"
        FASTAPI[FastAPI Server]
        SCRAPE_API[Scraping Endpoints]
        CHAT_API[Chat Endpoints]
        STATUS_API[Status Endpoints]
    end
    
    subgraph "Document Processing Pipeline"
        SCRAPER[SEC EDGAR Scraper]
        PARSER[Document Parser]
        CHUNKER[Document Chunker]
        EMBEDDER[Embedding Generator]
        VECTORIZER[Vector Store Manager]
    end
    
    subgraph "Chat Processing Pipeline"
        QP[Query Processor]
        RETRIEVER[Vector Retriever]
        RAG[RAG Engine]
        LLM[OpenAI Integration]
    end
    
    subgraph "Storage Layer"
        PG[PostgreSQL Database]
        PINECONE[Pinecone Vector DB]
        REDIS[Redis Cache/Status]
    end
    
    subgraph "External Sources"
        SEC[SEC EDGAR API]
        OPENAI[OpenAI API]
    end
    
    %% User workflow
    TICKER --> SCRAPE_API
    TIMERANGE --> SCRAPE_API
    SCRAPE_API --> SCRAPER
    
    %% Processing pipeline
    SCRAPER --> SEC
    SCRAPER --> PARSER
    PARSER --> PG
    PARSER --> CHUNKER
    CHUNKER --> PG
    CHUNKER --> EMBEDDER
    EMBEDDER --> OPENAI
    EMBEDDER --> VECTORIZER
    VECTORIZER --> PINECONE
    
    %% Status updates
    SCRAPER --> REDIS
    PARSER --> REDIS
    CHUNKER --> REDIS
    EMBEDDER --> REDIS
    STATUS_API --> REDIS
    STATUS_API --> PROGRESS
    
    %% Chat workflow
    CHAT --> CHAT_API
    CHAT_API --> QP
    QP --> RETRIEVER
    RETRIEVER --> PINECONE
    RETRIEVER --> RAG
    RAG --> LLM
    LLM --> OPENAI
    RAG --> CHAT
```

### Technology Stack

**Frontend (React)**
- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Material-UI (MUI)** for consistent UI components
- **Zustand** for lightweight state management
- **React Query** for server state management and caching
- **Axios** for HTTP client with interceptors

**Backend (FastAPI)**
- **FastAPI** with Python 3.11+ for high-performance API
- **Pydantic** for data validation and serialization
- **SQLAlchemy** for database ORM
- **Alembic** for database migrations
- **Celery** with Redis for background task processing
- **JWT** for authentication and authorization

**Data & AI**
- **LangChain** for RAG pipeline orchestration and document processing
- **Pinecone** for vector database and semantic search (via LangChain)
- **OpenAI API** for embeddings and language model (via LangChain)
- **PostgreSQL** for metadata and structured data
- **Redis** for caching and session management

## Components and Interfaces

### 1. React Frontend Components

**Multi-Phase Interface Structure:**
```typescript
// Main application component managing workflow phases
interface App {
  currentPhase: 'input' | 'processing' | 'chat'
  selectedTicker: string
  selectedTimeRange: 1 | 3 | 5
  processingStatus: ProcessingStatus
  chatSession: ChatSession
}

// Company ticker input and time range selection
interface CompanyInputForm {
  ticker: string
  timeRange: 1 | 3 | 5
  onSubmit: (ticker: string, timeRange: number) => void
  isValidating: boolean
  suggestions: string[]
}

// Processing status display
interface ProcessingStatusPanel {
  status: ProcessingStatus
  progress: number
  currentStep: string
  estimatedTimeRemaining: number
  onCancel?: () => void
}

// Chat interface (enabled after processing)
interface ChatInterface {
  messages: Message[]
  currentQuery: string
  isLoading: boolean
  companyContext: CompanyContext
  onSendMessage: (message: string) => void
}

// Citation display component
interface CitationPanel {
  citation: Citation
  documentExcerpt: string
  onClose: () => void
}
```

**State Management (Zustand):**
```typescript
interface AppState {
  // Workflow state
  currentPhase: 'input' | 'processing' | 'chat'
  selectedTicker: string
  selectedTimeRange: 1 | 3 | 5
  
  // Processing state
  processingStatus: ProcessingStatus
  processingProgress: number
  currentStep: string
  
  // Chat state
  messages: Message[]
  currentSession: string
  isTyping: boolean
  companyContext: CompanyContext
  
  // UI state
  citationPanelOpen: boolean
  currentCitation: Citation | null
  
  // Actions
  startProcessing: (ticker: string, timeRange: number) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  openCitation: (citation: Citation) => void
  resetWorkflow: () => void
}

interface ProcessingStatus {
  phase: 'scraping' | 'parsing' | 'chunking' | 'vectorizing' | 'complete' | 'error'
  documentsFound: number
  documentsProcessed: number
  chunksCreated: number
  chunksVectorized: number
  error?: string
}
```

### 2. FastAPI Backend Structure

**Main Application Setup:**
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn

app = FastAPI(
    title="RAG Financial Assistant API",
    description="API for financial document analysis and chat",
    version="1.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
```

**API Route Structure:**
```python
# Company validation and processing endpoints
@app.get("/api/companies/validate/{ticker}")
async def validate_ticker(ticker: str) -> TickerValidationResponse:
    pass

@app.post("/api/companies/process")
async def start_company_processing(request: ProcessingRequest) -> ProcessingResponse:
    pass

@app.get("/api/companies/{ticker}/status")
async def get_processing_status(ticker: str) -> ProcessingStatusResponse:
    pass

# Document scraping and processing endpoints
@app.post("/api/scraping/start")
async def start_scraping(ticker: str, years: int) -> ScrapeJobResponse:
    pass

@app.get("/api/scraping/{job_id}/status")
async def get_scraping_status(job_id: str) -> ScrapeStatusResponse:
    pass

# Chat endpoints (available after processing)
@app.post("/api/chat/query")
async def process_query(request: QueryRequest) -> QueryResponse:
    pass

@app.get("/api/chat/sessions/{session_id}")
async def get_chat_history(session_id: str) -> ChatHistoryResponse:
    pass

# Document and citation endpoints
@app.get("/api/documents/{document_id}")
async def get_document(document_id: str) -> DocumentResponse:
    pass

@app.get("/api/citations/{citation_id}")
async def get_citation_details(citation_id: str) -> CitationResponse:
    pass
```

### 3. Document Processing Pipeline

**SEC EDGAR Scraping and Processing:**
```python
class DocumentProcessingPipeline:
    def __init__(self, 
                 edgar_scraper: SECEdgarScraper,
                 document_parser: DocumentParser,
                 chunker: DocumentChunker,
                 vector_store: Pinecone,  # LangChain Pinecone vector store
                 embeddings: OpenAIEmbeddings):
        self.edgar_scraper = edgar_scraper
        self.document_parser = document_parser
        self.chunker = chunker
        self.vector_store = vector_store  # LangChain Pinecone vector store
        self.embeddings = embeddings
    
    async def process_company(self, 
                            ticker: str, 
                            years: int,
                            status_callback: Callable = None) -> ProcessingResult:
        
        # 1. Scrape SEC EDGAR filings
        if status_callback:
            await status_callback("scraping", 0)
        
        filings = await self.edgar_scraper.scrape_filings(ticker, years)
        
        # 2. Parse and store documents
        if status_callback:
            await status_callback("parsing", 25)
            
        documents = []
        for filing in filings:
            doc = await self.document_parser.parse_filing(filing)
            await self.store_document(doc)
            documents.append(doc)
        
        # 3. Create document chunks
        if status_callback:
            await status_callback("chunking", 50)
            
        all_chunks = []
        for doc in documents:
            chunks = await self.chunker.create_chunks(doc)
            await self.store_chunks(chunks)
            all_chunks.extend(chunks)
        
        # 4. Generate embeddings and store in Pinecone using LangChain
        if status_callback:
            await status_callback("vectorizing", 75)
            
        # Convert chunks to LangChain Documents
        langchain_docs = await self.convert_chunks_to_langchain_docs(all_chunks, ticker)
        
        # Store in Pinecone using LangChain vector store
        await self.vector_store.aadd_documents(langchain_docs)
        
        if status_callback:
            await status_callback("complete", 100)
        
        return ProcessingResult(
            ticker=ticker,
            documents_processed=len(documents),
            chunks_created=len(all_chunks),
            status="complete"
        )
    
    async def convert_chunks_to_langchain_docs(self, 
                                             chunks: List[DocumentChunk], 
                                             ticker: str) -> List[Document]:
        """Convert internal document chunks to LangChain Document format"""
        langchain_docs = []
        
        for chunk in chunks:
            doc = Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "ticker": ticker,
                    "section": chunk.section,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "filing_type": chunk.document.filing_type,
                    "filing_date": chunk.document.filed_date.isoformat()
                }
            )
            langchain_docs.append(doc)
        
        return langchain_docs
```

### 4. LangChain RAG Engine Implementation

**LangChain-Based Query Processing Pipeline:**
```python
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.callbacks import AsyncCallbackHandler

class FinancialRAGEngine:
    def __init__(self, 
                 pinecone_index: str,
                 openai_api_key: str,
                 db_manager: DatabaseManager):
        
        # Initialize LangChain components
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.llm = OpenAI(
            temperature=0.1,
            openai_api_key=openai_api_key,
            model_name="gpt-4o-mini"
        )
        
        # Initialize Pinecone vector store
        self.vector_store = Pinecone.from_existing_index(
            index_name=pinecone_index,
            embedding=self.embeddings
        )
        
        self.db_manager = db_manager
        self.setup_rag_chain()
    
    def setup_rag_chain(self):
        """Setup the LangChain RAG pipeline with custom prompt"""
        
        # Custom prompt template for financial analysis
        prompt_template = """
        You are a financial analysis assistant. Use the following pieces of context from SEC filings 
        to answer the question about {company_ticker}. Always cite your sources with specific 
        document references.

        Context from SEC filings:
        {context}

        Question: {question}

        Instructions:
        1. Provide accurate information based only on the provided context
        2. Include specific citations with document names and sections
        3. If information is not available in the context, clearly state this
        4. Focus on factual financial data and avoid speculation
        5. Format numerical data clearly with proper units

        Answer:
        """
        
        self.prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question", "company_ticker"]
        )
        
        # Create retrieval QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "score_threshold": 0.7,
                    "k": 8
                }
            ),
            chain_type_kwargs={"prompt": self.prompt},
            return_source_documents=True
        )
    
    async def process_query(self, 
                          query: str, 
                          ticker: str,
                          session_id: str = None) -> RAGResponse:
        
        # 1. Verify company data is available
        company_data = await self.db_manager.get_company_processing_status(ticker)
        if company_data.status != "complete":
            raise CompanyNotProcessedError(f"Company {ticker} not fully processed")
        
        # 2. Create company-specific retriever
        company_retriever = self.vector_store.as_retriever(
            search_kwargs={
                "filter": {"ticker": ticker},
                "k": 8
            }
        )
        
        # 3. Update chain with company-specific retriever
        self.qa_chain.retriever = company_retriever
        
        # 4. Process query through LangChain
        result = await self.qa_chain.acall({
            "query": query,
            "company_ticker": ticker
        })
        
        # 5. Extract citations from source documents
        citations = await self.extract_citations_from_sources(
            result["source_documents"]
        )
        
        # 6. Generate related questions
        related_questions = await self.generate_related_questions(
            query, ticker, result["source_documents"]
        )
        
        return RAGResponse(
            answer=result["result"],
            citations=citations,
            related_questions=related_questions,
            sources=result["source_documents"],
            company_context=ticker,
            session_id=session_id
        )
    
    async def extract_citations_from_sources(self, 
                                           source_docs: List[Document]) -> List[Citation]:
        """Extract citation information from LangChain source documents"""
        citations = []
        
        for doc in source_docs:
            # Get additional metadata from database
            chunk_metadata = await self.db_manager.get_chunk_metadata(
                doc.metadata.get("chunk_id")
            )
            
            citation = Citation(
                id=doc.metadata.get("chunk_id"),
                document_title=chunk_metadata.document_title,
                filing_type=chunk_metadata.filing_type,
                filing_date=chunk_metadata.filing_date,
                section=doc.metadata.get("section", ""),
                page_number=doc.metadata.get("page_number"),
                excerpt=doc.page_content[:200] + "...",
                confidence=doc.metadata.get("score", 0.0),
                chunk_id=doc.metadata.get("chunk_id")
            )
            citations.append(citation)
        
        return citations
    
    async def generate_related_questions(self, 
                                       original_query: str,
                                       ticker: str,
                                       source_docs: List[Document]) -> List[str]:
        """Generate related questions based on available context"""
        
        context_summary = "\n".join([doc.page_content[:100] for doc in source_docs[:3]])
        
        related_prompt = f"""
        Based on the user's question about {ticker}: "{original_query}"
        And the available context: {context_summary}
        
        Generate 3 related questions that the user might want to ask about this company.
        Focus on financial metrics, business performance, and regulatory information.
        
        Related questions:
        """
        
        response = await self.llm.agenerate([related_prompt])
        questions = response.generations[0][0].text.strip().split('\n')
        
        return [q.strip('- ').strip() for q in questions if q.strip()]

class LangChainCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for monitoring LangChain operations"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    async def on_chain_start(self, serialized, inputs, **kwargs):
        # Log chain start
        pass
    
    async def on_chain_end(self, outputs, **kwargs):
        # Log successful completion
        pass
    
    async def on_chain_error(self, error, **kwargs):
        # Log errors for debugging
        pass
```

### 5. SEC EDGAR Scraper Implementation

**SEC Filing Scraper:**
```python
class SECEdgarScraper:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.base_url = "https://www.sec.gov/Archives/edgar"
        
    async def scrape_filings(self, ticker: str, years: int) -> List[Filing]:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        # Get company CIK
        cik = await self.get_company_cik(ticker)
        
        # Scrape different filing types
        filing_types = ['10-K', '10-Q', '8-K', 'DEF 14A']
        all_filings = []
        
        for filing_type in filing_types:
            filings = await self.scrape_filing_type(
                cik, filing_type, start_date, end_date
            )
            all_filings.extend(filings)
        
        return all_filings
    
    async def scrape_filing_type(self, 
                               cik: str, 
                               filing_type: str, 
                               start_date: datetime, 
                               end_date: datetime) -> List[Filing]:
        
        # Respect SEC rate limits
        await self.rate_limiter.wait()
        
        # Query SEC EDGAR database
        search_url = f"{self.base_url}/search"
        params = {
            'cik': cik,
            'type': filing_type,
            'dateb': end_date.strftime('%Y%m%d'),
            'datea': start_date.strftime('%Y%m%d'),
            'count': 100
        }
        
        # Parse search results and download documents
        filings = []
        # Implementation details for parsing SEC responses
        
        return filings

class DocumentParser:
    def __init__(self):
        self.parsers = {
            'html': HTMLParser(),
            'xbrl': XBRLParser(),
            'txt': TextParser()
        }
    
    async def parse_filing(self, filing: Filing) -> Document:
        # Download filing content
        content = await self.download_filing_content(filing.url)
        
        # Detect format and parse
        format_type = self.detect_format(content)
        parser = self.parsers[format_type]
        
        # Extract structured content
        parsed_content = await parser.parse(content)
        
        return Document(
            id=filing.accession_number,
            ticker=filing.ticker,
            filing_type=filing.type,
            content=parsed_content,
            metadata=filing.metadata
        )
```

## Data Models

### Frontend TypeScript Models

```typescript
interface CompanyProcessingRequest {
  ticker: string
  timeRange: 1 | 3 | 5
}

interface ProcessingStatus {
  ticker: string
  phase: 'scraping' | 'parsing' | 'chunking' | 'vectorizing' | 'complete' | 'error'
  progress: number
  documentsFound: number
  documentsProcessed: number
  chunksCreated: number
  chunksVectorized: number
  estimatedTimeRemaining?: number
  error?: string
  startedAt: Date
  completedAt?: Date
}

interface CompanyContext {
  ticker: string
  name: string
  processingStatus: ProcessingStatus
  documentsAvailable: number
  timeRangeProcessed: number
}

interface Message {
  id: string
  content: string
  type: 'user' | 'assistant'
  timestamp: Date
  citations?: Citation[]
  isLoading?: boolean
}

interface Citation {
  id: string
  documentTitle: string
  filingType: string
  filingDate: Date
  section: string
  pageNumber?: number
  excerpt: string
  confidence: number
  chunkId: string
}

interface QueryResponse {
  answer: string
  citations: Citation[]
  relatedQuestions: string[]
  processingTime: number
  companyContext: string
}
```

### Backend Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class ProcessingRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    time_range: Literal[1, 3, 5] = Field(..., description="Years of historical data")

class ProcessingPhase(str, Enum):
    SCRAPING = "scraping"
    PARSING = "parsing"
    CHUNKING = "chunking"
    VECTORIZING = "vectorizing"
    COMPLETE = "complete"
    ERROR = "error"

class ProcessingStatusResponse(BaseModel):
    ticker: str
    phase: ProcessingPhase
    progress: float = Field(..., ge=0.0, le=100.0)
    documents_found: int
    documents_processed: int
    chunks_created: int
    chunks_vectorized: int
    estimated_time_remaining: Optional[int] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

class TickerValidationResponse(BaseModel):
    ticker: str
    is_valid: bool
    company_name: Optional[str] = None
    suggestions: List[str] = []

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    ticker: str = Field(..., min_length=1, max_length=10)
    session_id: Optional[str] = None

class CitationModel(BaseModel):
    id: str
    document_title: str
    filing_type: str
    filing_date: datetime
    section: str
    page_number: Optional[int] = None
    excerpt: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    chunk_id: str

class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationModel]
    related_questions: List[str]
    processing_time: float
    company_context: str
    session_id: str
```

### Database Models (SQLAlchemy)

```python
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    ticker = Column(String(10), primary_key=True)
    name = Column(String(255), nullable=False)
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="company")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    ticker = Column(String(10), ForeignKey("companies.ticker"))
    filing_type = Column(String(20))
    period_end = Column(DateTime)
    filed_date = Column(DateTime)
    document_url = Column(Text)
    processed_at = Column(DateTime)
    
    company = relationship("Company", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"))
    content = Column(Text)
    section = Column(String(100))
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    pinecone_id = Column(String(255))
    
    document = relationship("Document", back_populates="chunks")
```

## Error Handling

### Frontend Error Handling

```typescript
// Error boundary for React components
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Chat error:', error, errorInfo);
    // Send to error tracking service
  }
}

// API error handling with React Query
const useQuery = () => {
  return useReactQuery({
    queryKey: ['chat', query],
    queryFn: () => chatAPI.sendMessage(query),
    retry: (failureCount, error) => {
      if (error.status === 401) return false; // Don't retry auth errors
      return failureCount < 3;
    },
    onError: (error) => {
      toast.error(`Query failed: ${error.message}`);
    }
  });
};
```

### Backend Error Handling

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

class APIError(Exception):
    def __init__(self, status_code: int, message: str, details: dict = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url)
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "details": {}
            }
        }
    )
```

## Testing Strategy

### Frontend Testing (React)

```typescript
// Component testing with React Testing Library
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from './ChatInterface';

describe('ChatInterface', () => {
  test('sends message when form is submitted', async () => {
    const mockSendMessage = jest.fn();
    render(<ChatInterface onSendMessage={mockSendMessage} />);
    
    const input = screen.getByPlaceholderText('Ask about a company...');
    const button = screen.getByRole('button', { name: 'Send' });
    
    fireEvent.change(input, { target: { value: 'Tell me about AAPL' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Tell me about AAPL');
    });
  });
});

// Integration testing with MSW (Mock Service Worker)
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.post('/api/chat/query', (req, res, ctx) => {
    return res(ctx.json({
      answer: 'Apple Inc. is a technology company...',
      citations: [],
      related_questions: []
    }));
  })
);
```

### Backend Testing (FastAPI)

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_company_search():
    response = client.get("/api/companies/search?query=apple")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(company["ticker"] == "AAPL" for company in data)

def test_chat_query():
    response = client.post("/api/chat/query", json={
        "query": "What is Apple's revenue?",
        "session_id": "test-session"
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data

@pytest.fixture
def mock_vector_db():
    # Mock Pinecone responses for testing
    pass
```

## Deployment and Infrastructure

### Development Setup

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend setup
cd frontend
npm install
npm run dev  # Starts on port 3000
```

### Production Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ragdb
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ragdb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Security and Performance

### Security Measures

- **JWT Authentication** with refresh tokens
- **CORS** properly configured for production domains
- **Input validation** with Pydantic models
- **SQL injection protection** through SQLAlchemy ORM
- **Rate limiting** on API endpoints
- **HTTPS** enforcement in production

### Performance Optimizations

- **React Query** for client-side caching and background updates
- **Redis caching** for frequently accessed data
- **Database indexing** on commonly queried fields
- **Lazy loading** for large document content
- **Connection pooling** for database and external APIs
- **CDN** for static assets in production