"""
SQLAlchemy database models for the RAG Financial Assistant.
These models represent the database schema for companies, documents, and document chunks.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Float, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base


class Company(Base):
    """
    Company model representing public companies in the database.
    Stores basic company information and metadata.
    """
    __tablename__ = "companies"
    
    # Primary key
    ticker = Column(String(10), primary_key=True, index=True)
    
    # Basic company information
    name = Column(String(255), nullable=False, index=True)
    cik_str = Column(Integer, nullable=False, unique=True, index=True)
    exchange = Column(String(50), index=True)
    sector = Column(String(100), index=True)
    industry = Column(String(100), index=True)
    market_cap = Column(Float)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_companies_name_ticker', 'name', 'ticker'),
        Index('ix_companies_sector_industry', 'sector', 'industry'),
    )
    
    def __repr__(self):
        return f"<Company(ticker='{self.ticker}', name='{self.name}')>"


class Document(Base):
    """
    Document model representing SEC filings and other financial documents.
    Links to companies and contains document chunks.
    """
    __tablename__ = "documents"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Foreign key to company
    ticker = Column(String(10), ForeignKey("companies.ticker", ondelete="CASCADE"), nullable=False, index=True)
    
    # Document information
    filing_type = Column(String(20), nullable=False, index=True)  # 10-K, 10-Q, 8-K, etc.
    accession_number = Column(String(25), unique=True, index=True)  # SEC accession number
    period_end = Column(DateTime(timezone=True), index=True)
    filed_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Document metadata
    document_url = Column(Text)
    file_path = Column(Text)  # Local storage path
    file_size = Column(Integer)  # File size in bytes
    document_format = Column(String(10))  # PDF, HTML, XBRL, etc.
    
    # Processing status
    processed_at = Column(DateTime(timezone=True))
    processing_status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    processing_error = Column(Text)
    
    # Content metadata
    total_pages = Column(Integer)
    total_chunks = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_documents_ticker_filing_type', 'ticker', 'filing_type'),
        Index('ix_documents_filed_date_ticker', 'filed_date', 'ticker'),
        Index('ix_documents_period_end_ticker', 'period_end', 'ticker'),
    )
    
    def __repr__(self):
        return f"<Document(id='{self.id}', ticker='{self.ticker}', filing_type='{self.filing_type}')>"


class DocumentChunk(Base):
    """
    Document chunk model representing segmented portions of documents.
    Each chunk contains text content and metadata for vector search.
    """
    __tablename__ = "document_chunks"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Foreign key to document
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chunk content and metadata
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True)  # SHA-256 hash for deduplication
    section = Column(String(100), index=True)  # Section name (e.g., "Financial Statements", "Notes")
    subsection = Column(String(100))  # Subsection name
    page_number = Column(Integer, index=True)
    chunk_index = Column(Integer, nullable=False, index=True)  # Order within document
    
    # Vector database information
    pinecone_id = Column(String(255), unique=True, index=True)
    embedding_model = Column(String(50))  # Model used for embeddings
    
    # Content statistics
    word_count = Column(Integer)
    character_count = Column(Integer)
    
    # Chunk quality metrics
    confidence_score = Column(Float)  # Quality/confidence of extraction
    is_table = Column(Boolean, default=False)  # Whether chunk contains tabular data
    is_financial_data = Column(Boolean, default=False)  # Whether chunk contains financial numbers
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_chunks_document_chunk_index', 'document_id', 'chunk_index'),
        Index('ix_chunks_section_subsection', 'section', 'subsection'),
        Index('ix_chunks_financial_data', 'is_financial_data'),
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id='{self.id}', document_id='{self.document_id}', chunk_index={self.chunk_index})>"


class QueryLog(Base):
    """
    Query log model for tracking user queries and system performance.
    Used for analytics, debugging, and improving the RAG system.
    """
    __tablename__ = "query_logs"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Query information
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), index=True)  # Hash for deduplication
    session_id = Column(String(36), index=True)
    user_id = Column(String(36), index=True)  # For future user management
    
    # Context information
    company_context = Column(Text)  # JSON string of company tickers
    query_type = Column(String(50), index=True)  # financial, comparison, general, etc.
    
    # Response information
    response_text = Column(Text)
    response_time_ms = Column(Integer)  # Response time in milliseconds
    chunks_retrieved = Column(Integer)  # Number of chunks used
    confidence_score = Column(Float)  # Overall confidence in response
    
    # Status and error tracking
    status = Column(String(20), default="completed", index=True)  # completed, failed, timeout
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_query_logs_session_created', 'session_id', 'created_at'),
        Index('ix_query_logs_user_created', 'user_id', 'created_at'),
        Index('ix_query_logs_query_type_created', 'query_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<QueryLog(id='{self.id}', query_type='{self.query_type}', status='{self.status}')>"