"""
Test configuration and fixtures for database integration tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import tempfile
import os

from app.database import Base, get_db
from app.main import app
from app.models.database import Company, Document, DocumentChunk
from app.repositories import RepositoryManager


# Test database URL (SQLite in-memory for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create test session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db(test_engine, test_session_factory):
    """Create test database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = test_session_factory()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_client(test_db):
    """Create test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def repo_manager(test_db):
    """Create repository manager for tests."""
    return RepositoryManager(test_db)


@pytest.fixture(scope="function")
def sample_company_data():
    """Sample company data for tests."""
    return {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "cik_str": 320193,
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3000000000000.0
    }


@pytest.fixture(scope="function")
def sample_document_data():
    """Sample document data for tests."""
    return {
        "ticker": "AAPL",
        "filing_type": "10-K",
        "accession_number": "0000320193-23-000006",
        "period_end": "2023-09-30T00:00:00",
        "filed_date": "2023-11-03T00:00:00",
        "document_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000006/aapl-20230930.htm",
        "document_format": "HTML",
        "processing_status": "pending"
    }


@pytest.fixture(scope="function")
def sample_chunk_data():
    """Sample document chunk data for tests."""
    return {
        "content": "Apple Inc. reported revenue of $383.3 billion for fiscal year 2023.",
        "content_hash": "abc123def456",
        "section": "Financial Statements",
        "subsection": "Income Statement",
        "page_number": 45,
        "chunk_index": 1,
        "word_count": 12,
        "character_count": 67,
        "confidence_score": 0.95,
        "is_financial_data": True,
        "is_table": False
    }


@pytest.fixture(scope="function")
def created_company(repo_manager, sample_company_data):
    """Create a company in the test database."""
    return repo_manager.company.create(sample_company_data)


@pytest.fixture(scope="function")
def created_document(repo_manager, created_company, sample_document_data):
    """Create a document in the test database."""
    return repo_manager.document.create(sample_document_data)


@pytest.fixture(scope="function")
def created_chunk(repo_manager, created_document, sample_chunk_data):
    """Create a document chunk in the test database."""
    sample_chunk_data["document_id"] = created_document.id
    return repo_manager.document_chunk.create(sample_chunk_data)