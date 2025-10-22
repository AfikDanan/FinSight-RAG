"""
Tests for repository classes and database operations.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

from app.repositories import CompanyRepository, DocumentRepository, DocumentChunkRepository


class TestCompanyRepository:
    """Test CompanyRepository functionality."""
    
    def test_create_company(self, repo_manager, sample_company_data):
        """Test creating a company through repository."""
        company = repo_manager.company.create(sample_company_data)
        
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
        assert company.cik_str == 320193
        assert company.is_active is True
    
    def test_get_by_ticker(self, repo_manager, created_company):
        """Test getting company by ticker."""
        company = repo_manager.company.get_by_ticker("AAPL")
        
        assert company is not None
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
    
    def test_get_by_ticker_case_insensitive(self, repo_manager, created_company):
        """Test getting company by ticker is case insensitive."""
        company = repo_manager.company.get_by_ticker("aapl")
        
        assert company is not None
        assert company.ticker == "AAPL"
    
    def test_get_by_cik(self, repo_manager, created_company):
        """Test getting company by CIK."""
        company = repo_manager.company.get_by_cik(320193)
        
        assert company is not None
        assert company.ticker == "AAPL"
        assert company.cik_str == 320193
    
    def test_search_by_name(self, repo_manager, created_company):
        """Test searching companies by name."""
        companies = repo_manager.company.search_by_name("Apple")
        
        assert len(companies) == 1
        assert companies[0].ticker == "AAPL"
        
        # Test partial match
        companies = repo_manager.company.search_by_name("App")
        assert len(companies) == 1
    
    def test_search_by_ticker(self, repo_manager, created_company):
        """Test searching companies by ticker."""
        companies = repo_manager.company.search_by_name("AAPL")
        
        assert len(companies) == 1
        assert companies[0].ticker == "AAPL"
    
    def test_get_by_sector(self, repo_manager, created_company):
        """Test getting companies by sector."""
        companies = repo_manager.company.get_by_sector("Technology")
        
        assert len(companies) == 1
        assert companies[0].sector == "Technology"
    
    def test_get_by_industry(self, repo_manager, created_company):
        """Test getting companies by industry."""
        companies = repo_manager.company.get_by_industry("Consumer Electronics")
        
        assert len(companies) == 1
        assert companies[0].industry == "Consumer Electronics"
    
    def test_update_market_cap(self, repo_manager, created_company):
        """Test updating market capitalization."""
        new_market_cap = 3500000000000.0
        updated_company = repo_manager.company.update_market_cap("AAPL", new_market_cap)
        
        assert updated_company is not None
        assert updated_company.market_cap == new_market_cap
    
    def test_deactivate_company(self, repo_manager, created_company):
        """Test deactivating a company."""
        result = repo_manager.company.deactivate_company("AAPL")
        
        assert result is True
        
        # Verify company is deactivated
        company = repo_manager.company.get_by_ticker("AAPL")
        assert company.is_active is False
    
    def test_get_active_companies(self, repo_manager, created_company):
        """Test getting only active companies."""
        # Initially should have 1 active company
        active_companies = repo_manager.company.get_active_companies()
        assert len(active_companies) == 1
        
        # Deactivate company
        repo_manager.company.deactivate_company("AAPL")
        
        # Should have 0 active companies
        active_companies = repo_manager.company.get_active_companies()
        assert len(active_companies) == 0
    
    def test_get_similar_companies(self, repo_manager, test_db):
        """Test getting similar companies."""
        # Create multiple companies in same sector
        companies_data = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "cik_str": 320193,
                "sector": "Technology",
                "industry": "Consumer Electronics"
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corporation", 
                "cik_str": 789019,
                "sector": "Technology",
                "industry": "Software"
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "cik_str": 1652044,
                "sector": "Technology",
                "industry": "Internet Services"
            }
        ]
        
        for company_data in companies_data:
            repo_manager.company.create(company_data)
        
        # Get similar companies to AAPL
        similar = repo_manager.company.get_similar_companies("AAPL")
        
        assert len(similar) == 2  # MSFT and GOOGL
        tickers = [company.ticker for company in similar]
        assert "MSFT" in tickers
        assert "GOOGL" in tickers
        assert "AAPL" not in tickers  # Should not include itself


class TestDocumentRepository:
    """Test DocumentRepository functionality."""
    
    def test_create_document(self, repo_manager, created_company, sample_document_data):
        """Test creating a document through repository."""
        document = repo_manager.document.create(sample_document_data)
        
        assert document.ticker == "AAPL"
        assert document.filing_type == "10-K"
        assert document.processing_status == "pending"
    
    def test_get_by_accession_number(self, repo_manager, created_document):
        """Test getting document by accession number."""
        document = repo_manager.document.get_by_accession_number("0000320193-23-000006")
        
        assert document is not None
        assert document.ticker == "AAPL"
        assert document.filing_type == "10-K"
    
    def test_get_by_ticker(self, repo_manager, created_document):
        """Test getting documents by ticker."""
        documents = repo_manager.document.get_by_ticker("AAPL")
        
        assert len(documents) == 1
        assert documents[0].ticker == "AAPL"
    
    def test_get_by_ticker_with_filing_type(self, repo_manager, created_document):
        """Test getting documents by ticker and filing type."""
        documents = repo_manager.document.get_by_ticker("AAPL", filing_type="10-K")
        
        assert len(documents) == 1
        assert documents[0].filing_type == "10-K"
        
        # Test with non-matching filing type
        documents = repo_manager.document.get_by_ticker("AAPL", filing_type="10-Q")
        assert len(documents) == 0
    
    def test_get_recent_documents(self, repo_manager, created_document):
        """Test getting recent documents."""
        documents = repo_manager.document.get_recent_documents(days=30)
        
        assert len(documents) == 1
        assert documents[0].ticker == "AAPL"
    
    def test_get_processed_documents(self, repo_manager, created_document):
        """Test getting processed documents."""
        # Initially no processed documents
        processed = repo_manager.document.get_processed_documents()
        assert len(processed) == 0
        
        # Update status to completed
        repo_manager.document.update_processing_status(created_document.id, "completed")
        
        # Should now have 1 processed document
        processed = repo_manager.document.get_processed_documents()
        assert len(processed) == 1
    
    def test_get_pending_documents(self, repo_manager, created_document):
        """Test getting pending documents."""
        pending = repo_manager.document.get_pending_documents()
        
        assert len(pending) == 1
        assert pending[0].processing_status == "pending"
    
    def test_update_processing_status(self, repo_manager, created_document):
        """Test updating document processing status."""
        updated_doc = repo_manager.document.update_processing_status(
            created_document.id, 
            "completed"
        )
        
        assert updated_doc is not None
        assert updated_doc.processing_status == "completed"
        assert updated_doc.processed_at is not None
    
    def test_update_processing_status_with_error(self, repo_manager, created_document):
        """Test updating processing status with error message."""
        error_msg = "Failed to parse document"
        updated_doc = repo_manager.document.update_processing_status(
            created_document.id,
            "failed",
            error_message=error_msg
        )
        
        assert updated_doc is not None
        assert updated_doc.processing_status == "failed"
        assert updated_doc.processing_error == error_msg
    
    def test_get_latest_filing(self, repo_manager, test_db, created_company):
        """Test getting latest filing of specific type."""
        # Create multiple 10-K filings
        doc_data_1 = {
            "ticker": "AAPL",
            "filing_type": "10-K",
            "accession_number": "0000320193-22-000006",
            "filed_date": datetime(2022, 11, 3),
            "processing_status": "completed"
        }
        
        doc_data_2 = {
            "ticker": "AAPL",
            "filing_type": "10-K", 
            "accession_number": "0000320193-23-000006",
            "filed_date": datetime(2023, 11, 3),
            "processing_status": "completed"
        }
        
        repo_manager.document.create(doc_data_1)
        repo_manager.document.create(doc_data_2)
        
        # Get latest 10-K
        latest = repo_manager.document.get_latest_filing("AAPL", "10-K")
        
        assert latest is not None
        assert latest.filed_date.year == 2023
        assert latest.accession_number == "0000320193-23-000006"


class TestDocumentChunkRepository:
    """Test DocumentChunkRepository functionality."""
    
    def test_create_chunk(self, repo_manager, created_document, sample_chunk_data):
        """Test creating a document chunk through repository."""
        sample_chunk_data["document_id"] = created_document.id
        chunk = repo_manager.document_chunk.create(sample_chunk_data)
        
        assert chunk.document_id == created_document.id
        assert chunk.section == "Financial Statements"
        assert chunk.chunk_index == 1
        assert chunk.is_financial_data is True
    
    def test_get_by_document_id(self, repo_manager, created_chunk):
        """Test getting chunks by document ID."""
        chunks = repo_manager.document_chunk.get_by_document_id(created_chunk.document_id)
        
        assert len(chunks) == 1
        assert chunks[0].id == created_chunk.id
    
    def test_get_by_content_hash(self, repo_manager, created_chunk):
        """Test getting chunk by content hash."""
        chunk = repo_manager.document_chunk.get_by_content_hash("abc123def456")
        
        assert chunk is not None
        assert chunk.id == created_chunk.id
    
    def test_get_chunks_by_section(self, repo_manager, created_chunk):
        """Test getting chunks by section."""
        chunks = repo_manager.document_chunk.get_chunks_by_section(
            created_chunk.document_id,
            "Financial Statements"
        )
        
        assert len(chunks) == 1
        assert chunks[0].section == "Financial Statements"
    
    def test_get_chunks_by_section_with_subsection(self, repo_manager, created_chunk):
        """Test getting chunks by section and subsection."""
        chunks = repo_manager.document_chunk.get_chunks_by_section(
            created_chunk.document_id,
            "Financial Statements",
            subsection="Income Statement"
        )
        
        assert len(chunks) == 1
        assert chunks[0].subsection == "Income Statement"
    
    def test_get_financial_data_chunks(self, repo_manager, created_chunk):
        """Test getting financial data chunks."""
        chunks = repo_manager.document_chunk.get_financial_data_chunks()
        
        assert len(chunks) == 1
        assert chunks[0].is_financial_data is True
    
    def test_get_table_chunks(self, repo_manager, test_db, created_document):
        """Test getting table chunks."""
        # Create a table chunk
        table_chunk_data = {
            "document_id": created_document.id,
            "content": "Revenue | 2023 | $383.3B",
            "section": "Financial Statements",
            "chunk_index": 2,
            "word_count": 5,
            "character_count": 20,
            "confidence_score": 0.9,
            "is_table": True
        }
        
        repo_manager.document_chunk.create(table_chunk_data)
        
        # Get table chunks
        table_chunks = repo_manager.document_chunk.get_table_chunks()
        
        assert len(table_chunks) == 1
        assert table_chunks[0].is_table is True
    
    def test_search_chunks_by_content(self, repo_manager, created_chunk):
        """Test searching chunks by content."""
        chunks = repo_manager.document_chunk.search_chunks_by_content("revenue")
        
        assert len(chunks) == 1
        assert "revenue" in chunks[0].content.lower()
    
    def test_get_high_confidence_chunks(self, repo_manager, created_chunk):
        """Test getting high confidence chunks."""
        chunks = repo_manager.document_chunk.get_high_confidence_chunks(min_confidence=0.9)
        
        assert len(chunks) == 1
        assert chunks[0].confidence_score >= 0.9
    
    def test_update_pinecone_id(self, repo_manager, created_chunk):
        """Test updating Pinecone vector ID."""
        pinecone_id = "vector-123-abc"
        updated_chunk = repo_manager.document_chunk.update_pinecone_id(
            created_chunk.id,
            pinecone_id
        )
        
        assert updated_chunk is not None
        assert updated_chunk.pinecone_id == pinecone_id
    
    def test_get_chunks_without_embeddings(self, repo_manager, created_chunk):
        """Test getting chunks without embeddings."""
        chunks = repo_manager.document_chunk.get_chunks_without_embeddings()
        
        assert len(chunks) == 1
        assert chunks[0].pinecone_id is None
        
        # Update with Pinecone ID
        repo_manager.document_chunk.update_pinecone_id(created_chunk.id, "vector-123")
        
        # Should now have 0 chunks without embeddings
        chunks = repo_manager.document_chunk.get_chunks_without_embeddings()
        assert len(chunks) == 0
    
    def test_delete_chunks_by_document(self, repo_manager, created_chunk):
        """Test deleting all chunks for a document."""
        document_id = created_chunk.document_id
        
        # Verify chunk exists
        chunks = repo_manager.document_chunk.get_by_document_id(document_id)
        assert len(chunks) == 1
        
        # Delete chunks
        deleted_count = repo_manager.document_chunk.delete_chunks_by_document(document_id)
        
        assert deleted_count == 1
        
        # Verify chunks are deleted
        chunks = repo_manager.document_chunk.get_by_document_id(document_id)
        assert len(chunks) == 0


class TestRepositoryTransactions:
    """Test repository transaction handling."""
    
    def test_transaction_rollback_on_error(self, repo_manager, sample_company_data):
        """Test transaction rollback on database error."""
        # Create a company
        company = repo_manager.company.create(sample_company_data)
        assert company.ticker == "AAPL"
        
        # Try to create duplicate (should fail and rollback)
        with pytest.raises(SQLAlchemyError):
            repo_manager.company.create(sample_company_data)
        
        # Original company should still exist
        existing_company = repo_manager.company.get_by_ticker("AAPL")
        assert existing_company is not None
    
    def test_bulk_create(self, repo_manager):
        """Test bulk creation of records."""
        companies_data = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "cik_str": 320193,
                "sector": "Technology"
            },
            {
                "ticker": "MSFT", 
                "name": "Microsoft Corporation",
                "cik_str": 789019,
                "sector": "Technology"
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "cik_str": 1652044,
                "sector": "Technology"
            }
        ]
        
        created_companies = repo_manager.company.bulk_create(companies_data)
        
        assert len(created_companies) == 3
        tickers = [company.ticker for company in created_companies]
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "GOOGL" in tickers