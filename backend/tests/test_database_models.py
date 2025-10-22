"""
Tests for SQLAlchemy database models and relationships.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.database import Company, Document, DocumentChunk, QueryLog


class TestCompanyModel:
    """Test Company model functionality."""
    
    def test_create_company(self, test_db, sample_company_data):
        """Test creating a company."""
        company = Company(**sample_company_data)
        test_db.add(company)
        test_db.commit()
        
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
        assert company.cik_str == 320193
        assert company.is_active is True
        assert company.created_at is not None
        assert company.updated_at is not None
    
    def test_company_unique_constraints(self, test_db, sample_company_data):
        """Test company unique constraints."""
        # Create first company
        company1 = Company(**sample_company_data)
        test_db.add(company1)
        test_db.commit()
        
        # Try to create duplicate ticker
        company2 = Company(**sample_company_data)
        test_db.add(company2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_company_cik_unique(self, test_db, sample_company_data):
        """Test CIK uniqueness constraint."""
        # Create first company
        company1 = Company(**sample_company_data)
        test_db.add(company1)
        test_db.commit()
        
        # Try to create company with same CIK but different ticker
        duplicate_cik_data = sample_company_data.copy()
        duplicate_cik_data["ticker"] = "MSFT"
        duplicate_cik_data["name"] = "Microsoft Corporation"
        
        company2 = Company(**duplicate_cik_data)
        test_db.add(company2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_company_repr(self, test_db, sample_company_data):
        """Test company string representation."""
        company = Company(**sample_company_data)
        test_db.add(company)
        test_db.commit()
        
        expected = "<Company(ticker='AAPL', name='Apple Inc.')>"
        assert repr(company) == expected


class TestDocumentModel:
    """Test Document model functionality."""
    
    def test_create_document(self, test_db, created_company, sample_document_data):
        """Test creating a document."""
        document = Document(**sample_document_data)
        test_db.add(document)
        test_db.commit()
        
        assert document.ticker == "AAPL"
        assert document.filing_type == "10-K"
        assert document.processing_status == "pending"
        assert document.created_at is not None
        assert document.id is not None
    
    def test_document_company_relationship(self, test_db, created_company, sample_document_data):
        """Test document-company relationship."""
        document = Document(**sample_document_data)
        test_db.add(document)
        test_db.commit()
        
        # Test relationship
        assert document.company is not None
        assert document.company.ticker == "AAPL"
        assert document.company.name == "Apple Inc."
        
        # Test reverse relationship
        assert len(created_company.documents) == 1
        assert created_company.documents[0].id == document.id
    
    def test_document_accession_unique(self, test_db, created_company, sample_document_data):
        """Test accession number uniqueness."""
        # Create first document
        document1 = Document(**sample_document_data)
        test_db.add(document1)
        test_db.commit()
        
        # Try to create duplicate accession number
        duplicate_data = sample_document_data.copy()
        duplicate_data["filing_type"] = "10-Q"
        
        document2 = Document(**duplicate_data)
        test_db.add(document2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_document_cascade_delete(self, test_db, created_company, sample_document_data):
        """Test cascade delete when company is deleted."""
        document = Document(**sample_document_data)
        test_db.add(document)
        test_db.commit()
        
        document_id = document.id
        
        # Delete company
        test_db.delete(created_company)
        test_db.commit()
        
        # Document should be deleted too
        deleted_document = test_db.query(Document).filter(Document.id == document_id).first()
        assert deleted_document is None


class TestDocumentChunkModel:
    """Test DocumentChunk model functionality."""
    
    def test_create_chunk(self, test_db, created_document, sample_chunk_data):
        """Test creating a document chunk."""
        sample_chunk_data["document_id"] = created_document.id
        chunk = DocumentChunk(**sample_chunk_data)
        test_db.add(chunk)
        test_db.commit()
        
        assert chunk.document_id == created_document.id
        assert chunk.content == "Apple Inc. reported revenue of $383.3 billion for fiscal year 2023."
        assert chunk.section == "Financial Statements"
        assert chunk.chunk_index == 1
        assert chunk.is_financial_data is True
        assert chunk.confidence_score == 0.95
    
    def test_chunk_document_relationship(self, test_db, created_document, sample_chunk_data):
        """Test chunk-document relationship."""
        sample_chunk_data["document_id"] = created_document.id
        chunk = DocumentChunk(**sample_chunk_data)
        test_db.add(chunk)
        test_db.commit()
        
        # Test relationship
        assert chunk.document is not None
        assert chunk.document.id == created_document.id
        assert chunk.document.ticker == "AAPL"
        
        # Test reverse relationship
        assert len(created_document.chunks) == 1
        assert created_document.chunks[0].id == chunk.id
    
    def test_chunk_pinecone_id_unique(self, test_db, created_document, sample_chunk_data):
        """Test Pinecone ID uniqueness."""
        sample_chunk_data["document_id"] = created_document.id
        sample_chunk_data["pinecone_id"] = "unique-vector-id-123"
        
        # Create first chunk
        chunk1 = DocumentChunk(**sample_chunk_data)
        test_db.add(chunk1)
        test_db.commit()
        
        # Try to create duplicate Pinecone ID
        duplicate_data = sample_chunk_data.copy()
        duplicate_data["chunk_index"] = 2
        duplicate_data["content"] = "Different content"
        
        chunk2 = DocumentChunk(**duplicate_data)
        test_db.add(chunk2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_chunk_cascade_delete(self, test_db, created_document, sample_chunk_data):
        """Test cascade delete when document is deleted."""
        sample_chunk_data["document_id"] = created_document.id
        chunk = DocumentChunk(**sample_chunk_data)
        test_db.add(chunk)
        test_db.commit()
        
        chunk_id = chunk.id
        
        # Delete document
        test_db.delete(created_document)
        test_db.commit()
        
        # Chunk should be deleted too
        deleted_chunk = test_db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
        assert deleted_chunk is None


class TestQueryLogModel:
    """Test QueryLog model functionality."""
    
    def test_create_query_log(self, test_db):
        """Test creating a query log entry."""
        query_log_data = {
            "query_text": "What is Apple's revenue?",
            "query_hash": "hash123",
            "session_id": "session-123",
            "query_type": "financial",
            "response_text": "Apple's revenue was $383.3 billion.",
            "response_time_ms": 1500,
            "chunks_retrieved": 5,
            "confidence_score": 0.92,
            "status": "completed"
        }
        
        query_log = QueryLog(**query_log_data)
        test_db.add(query_log)
        test_db.commit()
        
        assert query_log.query_text == "What is Apple's revenue?"
        assert query_log.query_type == "financial"
        assert query_log.status == "completed"
        assert query_log.confidence_score == 0.92
        assert query_log.created_at is not None


class TestModelRelationships:
    """Test complex model relationships and queries."""
    
    def test_full_relationship_chain(self, test_db, sample_company_data, sample_document_data, sample_chunk_data):
        """Test complete relationship chain: Company -> Document -> Chunk."""
        # Create company
        company = Company(**sample_company_data)
        test_db.add(company)
        test_db.commit()
        
        # Create document
        document = Document(**sample_document_data)
        test_db.add(document)
        test_db.commit()
        
        # Create chunk
        sample_chunk_data["document_id"] = document.id
        chunk = DocumentChunk(**sample_chunk_data)
        test_db.add(chunk)
        test_db.commit()
        
        # Test full chain
        assert company.documents[0].chunks[0].id == chunk.id
        assert chunk.document.company.ticker == "AAPL"
    
    def test_multiple_documents_per_company(self, test_db, created_company):
        """Test multiple documents for one company."""
        # Create multiple documents
        doc_data_1 = {
            "ticker": "AAPL",
            "filing_type": "10-K",
            "accession_number": "0000320193-23-000006",
            "filed_date": datetime.utcnow(),
            "processing_status": "completed"
        }
        
        doc_data_2 = {
            "ticker": "AAPL", 
            "filing_type": "10-Q",
            "accession_number": "0000320193-23-000007",
            "filed_date": datetime.utcnow(),
            "processing_status": "pending"
        }
        
        doc1 = Document(**doc_data_1)
        doc2 = Document(**doc_data_2)
        
        test_db.add_all([doc1, doc2])
        test_db.commit()
        
        # Test relationship
        assert len(created_company.documents) == 2
        filing_types = [doc.filing_type for doc in created_company.documents]
        assert "10-K" in filing_types
        assert "10-Q" in filing_types
    
    def test_multiple_chunks_per_document(self, test_db, created_document):
        """Test multiple chunks for one document."""
        # Create multiple chunks
        chunk_data_1 = {
            "document_id": created_document.id,
            "content": "First chunk content",
            "section": "Section 1",
            "chunk_index": 1,
            "word_count": 10,
            "character_count": 50,
            "confidence_score": 0.9
        }
        
        chunk_data_2 = {
            "document_id": created_document.id,
            "content": "Second chunk content", 
            "section": "Section 2",
            "chunk_index": 2,
            "word_count": 12,
            "character_count": 60,
            "confidence_score": 0.85
        }
        
        chunk1 = DocumentChunk(**chunk_data_1)
        chunk2 = DocumentChunk(**chunk_data_2)
        
        test_db.add_all([chunk1, chunk2])
        test_db.commit()
        
        # Test relationship
        assert len(created_document.chunks) == 2
        chunk_indices = [chunk.chunk_index for chunk in created_document.chunks]
        assert 1 in chunk_indices
        assert 2 in chunk_indices