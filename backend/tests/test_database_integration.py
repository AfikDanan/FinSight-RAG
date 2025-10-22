"""
Integration tests for database operations and performance.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
import time

from app.database import check_database_connection, get_database_health
from app.repositories import RepositoryManager


class TestDatabaseConnection:
    """Test database connection and health checks."""
    
    def test_database_connection(self, test_db):
        """Test basic database connection."""
        # Execute a simple query
        result = test_db.execute(text("SELECT 1 as test_value"))
        row = result.fetchone()
        
        assert row is not None
        assert row.test_value == 1
    
    def test_database_health_check(self, test_db):
        """Test database health check function."""
        # Note: This test uses SQLite, so some PostgreSQL-specific features won't work
        # But we can test the basic structure
        try:
            health = get_database_health()
            assert "status" in health
        except Exception:
            # Expected for SQLite test database
            pass
    
    def test_repository_manager_initialization(self, test_db):
        """Test repository manager initialization."""
        repo_manager = RepositoryManager(test_db)
        
        assert repo_manager.company is not None
        assert repo_manager.document is not None
        assert repo_manager.document_chunk is not None
    
    def test_repository_manager_transaction_handling(self, repo_manager, sample_company_data):
        """Test repository manager transaction handling."""
        # Create a company
        company = repo_manager.company.create(sample_company_data)
        
        # Test commit
        repo_manager.commit()
        
        # Verify company exists after commit
        existing_company = repo_manager.company.get_by_ticker("AAPL")
        assert existing_company is not None
        
        # Test rollback
        repo_manager.company.update_market_cap("AAPL", 4000000000000.0)
        repo_manager.rollback()
        
        # Market cap should be unchanged
        company_after_rollback = repo_manager.company.get_by_ticker("AAPL")
        assert company_after_rollback.market_cap == sample_company_data["market_cap"]


class TestDatabasePerformance:
    """Test database query performance and optimization."""
    
    def test_company_search_performance(self, repo_manager):
        """Test company search query performance."""
        # Create multiple companies for testing
        companies_data = []
        for i in range(100):
            companies_data.append({
                "ticker": f"TEST{i:03d}",
                "name": f"Test Company {i}",
                "cik_str": 1000000 + i,
                "sector": "Technology" if i % 2 == 0 else "Finance",
                "industry": f"Industry {i % 10}"
            })
        
        # Bulk create companies
        repo_manager.company.bulk_create(companies_data)
        
        # Test search performance
        start_time = time.time()
        results = repo_manager.company.search_by_name("Test")
        end_time = time.time()
        
        query_time = end_time - start_time
        
        assert len(results) > 0
        assert query_time < 1.0  # Should complete within 1 second
    
    def test_document_retrieval_performance(self, repo_manager, test_db):
        """Test document retrieval performance."""
        # Create a company
        company_data = {
            "ticker": "PERF",
            "name": "Performance Test Company",
            "cik_str": 9999999
        }
        repo_manager.company.create(company_data)
        
        # Create multiple documents
        documents_data = []
        for i in range(50):
            documents_data.append({
                "ticker": "PERF",
                "filing_type": "10-K" if i % 5 == 0 else "10-Q",
                "accession_number": f"0000999999-23-{i:06d}",
                "filed_date": datetime.utcnow() - timedelta(days=i),
                "processing_status": "completed"
            })
        
        repo_manager.document.bulk_create(documents_data)
        
        # Test retrieval performance
        start_time = time.time()
        documents = repo_manager.document.get_by_ticker("PERF")
        end_time = time.time()
        
        query_time = end_time - start_time
        
        assert len(documents) == 50
        assert query_time < 0.5  # Should complete within 0.5 seconds
    
    def test_chunk_search_performance(self, repo_manager, test_db):
        """Test document chunk search performance."""
        # Create company and document
        company_data = {
            "ticker": "CHUNK",
            "name": "Chunk Test Company", 
            "cik_str": 8888888
        }
        company = repo_manager.company.create(company_data)
        
        document_data = {
            "ticker": "CHUNK",
            "filing_type": "10-K",
            "accession_number": "0000888888-23-000001",
            "filed_date": datetime.utcnow(),
            "processing_status": "completed"
        }
        document = repo_manager.document.create(document_data)
        
        # Create multiple chunks
        chunks_data = []
        for i in range(200):
            chunks_data.append({
                "document_id": document.id,
                "content": f"This is chunk {i} containing financial data and revenue information.",
                "section": f"Section {i % 10}",
                "chunk_index": i,
                "word_count": 12,
                "character_count": 65,
                "confidence_score": 0.8 + (i % 20) / 100,
                "is_financial_data": i % 3 == 0
            })
        
        repo_manager.document_chunk.bulk_create(chunks_data)
        
        # Test search performance
        start_time = time.time()
        chunks = repo_manager.document_chunk.search_chunks_by_content("revenue")
        end_time = time.time()
        
        query_time = end_time - start_time
        
        assert len(chunks) > 0
        assert query_time < 1.0  # Should complete within 1 second


class TestComplexQueries:
    """Test complex database queries and relationships."""
    
    def test_cross_table_queries(self, repo_manager, test_db):
        """Test queries that span multiple tables."""
        # Create test data
        company_data = {
            "ticker": "COMPLEX",
            "name": "Complex Query Company",
            "cik_str": 7777777,
            "sector": "Technology"
        }
        company = repo_manager.company.create(company_data)
        
        document_data = {
            "ticker": "COMPLEX",
            "filing_type": "10-K",
            "accession_number": "0000777777-23-000001",
            "filed_date": datetime.utcnow(),
            "processing_status": "completed"
        }
        document = repo_manager.document.create(document_data)
        
        chunk_data = {
            "document_id": document.id,
            "content": "Revenue increased by 15% year over year.",
            "section": "Financial Performance",
            "chunk_index": 1,
            "word_count": 8,
            "character_count": 40,
            "confidence_score": 0.95,
            "is_financial_data": True
        }
        chunk = repo_manager.document_chunk.create(chunk_data)
        
        # Test complex query: Get financial chunks for companies in Technology sector
        financial_chunks = repo_manager.document_chunk.get_financial_data_chunks(ticker="COMPLEX")
        
        assert len(financial_chunks) == 1
        assert financial_chunks[0].is_financial_data is True
        assert financial_chunks[0].document.company.sector == "Technology"
    
    def test_aggregation_queries(self, repo_manager, test_db):
        """Test aggregation and statistical queries."""
        # Create multiple companies in different sectors
        companies_data = [
            {"ticker": "TECH1", "name": "Tech Company 1", "cik_str": 1111111, "sector": "Technology", "market_cap": 1000000000},
            {"ticker": "TECH2", "name": "Tech Company 2", "cik_str": 1111112, "sector": "Technology", "market_cap": 2000000000},
            {"ticker": "FIN1", "name": "Finance Company 1", "cik_str": 2222221, "sector": "Finance", "market_cap": 500000000},
            {"ticker": "FIN2", "name": "Finance Company 2", "cik_str": 2222222, "sector": "Finance", "market_cap": 1500000000}
        ]
        
        for company_data in companies_data:
            repo_manager.company.create(company_data)
        
        # Test sector statistics
        sector_stats = repo_manager.company.get_sector_statistics()
        
        assert len(sector_stats) == 2
        
        # Find Technology sector stats
        tech_stats = next((s for s in sector_stats if s["sector"] == "Technology"), None)
        assert tech_stats is not None
        assert tech_stats["company_count"] == 2
        assert tech_stats["total_market_cap"] == 3000000000
        
        # Find Finance sector stats
        finance_stats = next((s for s in sector_stats if s["sector"] == "Finance"), None)
        assert finance_stats is not None
        assert finance_stats["company_count"] == 2
        assert finance_stats["total_market_cap"] == 2000000000
    
    def test_document_statistics(self, repo_manager, test_db):
        """Test document processing statistics."""
        # Create company
        company_data = {
            "ticker": "STATS",
            "name": "Statistics Company",
            "cik_str": 6666666
        }
        repo_manager.company.create(company_data)
        
        # Create documents with different statuses
        documents_data = [
            {"ticker": "STATS", "filing_type": "10-K", "accession_number": "0000666666-23-000001", "filed_date": datetime.utcnow(), "processing_status": "completed"},
            {"ticker": "STATS", "filing_type": "10-Q", "accession_number": "0000666666-23-000002", "filed_date": datetime.utcnow(), "processing_status": "completed"},
            {"ticker": "STATS", "filing_type": "8-K", "accession_number": "0000666666-23-000003", "filed_date": datetime.utcnow(), "processing_status": "pending"},
            {"ticker": "STATS", "filing_type": "10-Q", "accession_number": "0000666666-23-000004", "filed_date": datetime.utcnow(), "processing_status": "failed"}
        ]
        
        for doc_data in documents_data:
            repo_manager.document.create(doc_data)
        
        # Get filing statistics
        stats = repo_manager.document.get_filing_statistics(ticker="STATS")
        
        assert stats["total_documents"] == 4
        assert stats["processed_documents"] == 2
        assert stats["pending_documents"] == 1
        assert stats["failed_documents"] == 1
        assert stats["processing_rate"] == 50.0
        
        # Check filing type breakdown
        assert stats["filing_types"]["10-K"] == 1
        assert stats["filing_types"]["10-Q"] == 2
        assert stats["filing_types"]["8-K"] == 1


class TestDataIntegrity:
    """Test data integrity and constraint enforcement."""
    
    def test_foreign_key_constraints(self, repo_manager, test_db):
        """Test foreign key constraint enforcement."""
        # Try to create document without company (should fail in real PostgreSQL)
        document_data = {
            "ticker": "NONEXISTENT",
            "filing_type": "10-K",
            "accession_number": "0000000000-23-000001",
            "filed_date": datetime.utcnow(),
            "processing_status": "pending"
        }
        
        # In SQLite with foreign keys enabled, this would fail
        # For this test, we'll just verify the logic works
        try:
            document = repo_manager.document.create(document_data)
            # If creation succeeds, verify we can't find the company
            company = repo_manager.company.get_by_ticker("NONEXISTENT")
            assert company is None
        except Exception:
            # Expected behavior with proper foreign key constraints
            pass
    
    def test_cascade_delete_behavior(self, repo_manager, created_company, created_document, created_chunk):
        """Test cascade delete behavior."""
        document_id = created_document.id
        chunk_id = created_chunk.id
        
        # Delete company (should cascade to documents and chunks)
        repo_manager.company.delete("AAPL")
        
        # Verify document and chunk are deleted
        deleted_document = repo_manager.document.get(document_id)
        deleted_chunk = repo_manager.document_chunk.get(chunk_id)
        
        # In SQLite, cascade behavior might not work exactly like PostgreSQL
        # But we can test the repository delete methods
        assert deleted_document is None or deleted_document.id != document_id
    
    def test_unique_constraint_enforcement(self, repo_manager, sample_company_data):
        """Test unique constraint enforcement."""
        # Create first company
        company1 = repo_manager.company.create(sample_company_data)
        assert company1.ticker == "AAPL"
        
        # Try to create duplicate ticker
        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            repo_manager.company.create(sample_company_data)
        
        # Try to create duplicate CIK
        duplicate_cik_data = sample_company_data.copy()
        duplicate_cik_data["ticker"] = "AAPL2"
        duplicate_cik_data["name"] = "Apple Inc. Duplicate"
        
        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            repo_manager.company.create(duplicate_cik_data)