"""
Tests for document storage service.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.document_storage import DocumentStorageService
from app.services.sec_edgar_scraper import Filing
from app.models.database import Document, Company
from app.repositories.document import DocumentRepository
from app.repositories.company import CompanyRepository


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_filing():
    """Create sample filing for tests"""
    return Filing(
        accession_number="0000320193-23-000006",
        filing_type="10-K",
        filing_date=datetime(2023, 1, 15),
        period_end=datetime(2022, 12, 31),
        document_url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000006/aapl-20221231.htm",
        ticker="AAPL",
        company_name="Apple Inc.",
        cik="0000320193",
        file_size=1024000,
        document_format="HTML"
    )


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def document_storage_service(mock_db_session, temp_storage_dir):
    """Create document storage service with mocked dependencies"""
    return DocumentStorageService(
        db=mock_db_session,
        storage_path=temp_storage_dir,
        max_concurrent_downloads=2,
        retry_attempts=2,
        retry_delay=0.1
    )


class TestDocumentStorageService:
    """Test cases for DocumentStorageService"""
    
    def test_init(self, document_storage_service, temp_storage_dir):
        """Test service initialization"""
        assert document_storage_service.storage_path == Path(temp_storage_dir)
        assert document_storage_service.max_concurrent_downloads == 2
        assert document_storage_service.retry_attempts == 2
        assert document_storage_service.retry_delay == 0.1
    
    def test_generate_file_path(self, document_storage_service, sample_filing):
        """Test file path generation"""
        file_path = document_storage_service._generate_file_path(sample_filing)
        
        expected_path = (
            document_storage_service.storage_path / 
            "AAPL" / "2023" / "10-K" / "aapl-20221231.htm"
        )
        
        assert file_path == expected_path
    
    def test_calculate_content_hash(self, document_storage_service):
        """Test content hash calculation"""
        content = b"test content"
        hash_value = document_storage_service._calculate_content_hash(content)
        
        # SHA-256 hash of "test content"
        expected_hash = "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
        assert hash_value == expected_hash
    
    def test_detect_document_format(self, document_storage_service):
        """Test document format detection"""
        # Test HTML content type
        format_html = document_storage_service._detect_document_format(
            "text/html", Path("test.html")
        )
        assert format_html == "HTML"
        
        # Test PDF content type
        format_pdf = document_storage_service._detect_document_format(
            "application/pdf", Path("test.pdf")
        )
        assert format_pdf == "PDF"
        
        # Test XBRL content type
        format_xbrl = document_storage_service._detect_document_format(
            "application/xml", Path("test.xml")
        )
        assert format_xbrl == "XBRL"
        
        # Test file extension fallback
        format_ext = document_storage_service._detect_document_format(
            "application/octet-stream", Path("test.pdf")
        )
        assert format_ext == "PDF"
    
    @pytest.mark.asyncio
    async def test_download_document_content_success(self, document_storage_service):
        """Test successful document download"""
        mock_response = MagicMock()
        mock_response.content = b"test document content"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(document_storage_service.client, 'get', return_value=mock_response):
            content, content_type = await document_storage_service._download_document_content(
                "https://example.com/test.html"
            )
            
            assert content == b"test document content"
            assert content_type == "text/html"
    
    @pytest.mark.asyncio
    async def test_download_document_content_retry(self, document_storage_service):
        """Test document download with retry logic"""
        # First call fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
        
        mock_response_success = MagicMock()
        mock_response_success.content = b"test content"
        mock_response_success.headers = {"content-type": "text/html"}
        mock_response_success.raise_for_status = MagicMock()
        
        with patch.object(document_storage_service.client, 'get', 
                         side_effect=[mock_response_fail, mock_response_success]):
            content, content_type = await document_storage_service._download_document_content(
                "https://example.com/test.html"
            )
            
            assert content == b"test content"
            assert content_type == "text/html"
    
    @pytest.mark.asyncio
    async def test_save_document_to_disk(self, document_storage_service, temp_storage_dir):
        """Test saving document to disk"""
        content = b"test document content"
        file_path = Path(temp_storage_dir) / "test.html"
        
        file_size = await document_storage_service._save_document_to_disk(content, file_path)
        
        assert file_size == len(content)
        assert file_path.exists()
        assert file_path.read_bytes() == content
    
    @pytest.mark.asyncio
    async def test_check_document_exists(self, document_storage_service, sample_filing):
        """Test checking if document exists"""
        # Mock document repository
        mock_doc_repo = MagicMock()
        mock_doc_repo.get_by_accession_number.return_value = None
        document_storage_service.document_repo = mock_doc_repo
        
        result = await document_storage_service._check_document_exists(sample_filing)
        
        assert result is None
        mock_doc_repo.get_by_accession_number.assert_called_once_with(
            sample_filing.accession_number
        )
    
    @pytest.mark.asyncio
    async def test_create_document_record(self, document_storage_service, sample_filing, temp_storage_dir):
        """Test creating document record"""
        # Mock repositories
        mock_company_repo = MagicMock()
        mock_doc_repo = MagicMock()
        
        # Mock company exists
        mock_company = Company(
            ticker=sample_filing.ticker,
            name=sample_filing.company_name,
            cik_str=int(sample_filing.cik)
        )
        mock_company_repo.get.return_value = mock_company
        
        # Mock document creation
        mock_document = Document(
            ticker=sample_filing.ticker,
            filing_type=sample_filing.filing_type,
            accession_number=sample_filing.accession_number
        )
        mock_doc_repo.create.return_value = mock_document
        
        document_storage_service.company_repo = mock_company_repo
        document_storage_service.document_repo = mock_doc_repo
        
        file_path = Path(temp_storage_dir) / "test.html"
        result = await document_storage_service._create_document_record(
            sample_filing, file_path, 1024, "HTML"
        )
        
        assert result == mock_document
        mock_company_repo.get.assert_called_once_with(sample_filing.ticker)
        mock_doc_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_and_store_filing_success(self, document_storage_service, sample_filing):
        """Test successful filing download and storage"""
        # Mock all dependencies
        document_storage_service._check_document_exists = AsyncMock(return_value=None)
        document_storage_service._download_document_content = AsyncMock(
            return_value=(b"test content", "text/html")
        )
        document_storage_service._save_document_to_disk = AsyncMock(return_value=1024)
        
        mock_document = Document(id="test-doc-id")
        document_storage_service._create_document_record = AsyncMock(return_value=mock_document)
        
        result = await document_storage_service.download_and_store_filing(sample_filing)
        
        assert result == mock_document
        document_storage_service._check_document_exists.assert_called_once_with(sample_filing)
        document_storage_service._download_document_content.assert_called_once_with(
            sample_filing.document_url
        )
    
    @pytest.mark.asyncio
    async def test_download_and_store_filing_already_exists(self, document_storage_service, sample_filing):
        """Test filing download when document already exists"""
        existing_doc = Document(id="existing-doc-id")
        document_storage_service._check_document_exists = AsyncMock(return_value=existing_doc)
        
        result = await document_storage_service.download_and_store_filing(sample_filing)
        
        assert result == existing_doc
        document_storage_service._check_document_exists.assert_called_once_with(sample_filing)
    
    @pytest.mark.asyncio
    async def test_download_and_store_filings_multiple(self, document_storage_service):
        """Test downloading multiple filings"""
        # Create sample filings
        filings = [
            Filing(
                accession_number=f"test-{i}",
                filing_type="10-K",
                filing_date=datetime(2023, 1, i+1),
                period_end=None,
                document_url=f"https://example.com/doc{i}.html",
                ticker="TEST",
                company_name="Test Company",
                cik="0000123456"
            )
            for i in range(3)
        ]
        
        # Mock successful downloads
        mock_documents = [Document(id=f"doc-{i}") for i in range(3)]
        document_storage_service.download_and_store_filing = AsyncMock(
            side_effect=mock_documents
        )
        
        # Track progress calls
        progress_calls = []
        async def progress_callback(status, current, total):
            progress_calls.append((status, current, total))
        
        result = await document_storage_service.download_and_store_filings(
            filings, progress_callback
        )
        
        assert len(result) == 3
        assert all(doc in mock_documents for doc in result)
        
        # Check progress was tracked
        assert len(progress_calls) > 0
        assert progress_calls[0] == ("downloading", 0, 3)
        assert progress_calls[-1] == ("completed", 3, 3)
    
    @pytest.mark.asyncio
    async def test_process_company_filings_success(self, document_storage_service):
        """Test complete company filing processing workflow"""
        ticker = "AAPL"
        years = 1
        
        # Mock SEC scraper
        mock_filings = [
            Filing(
                accession_number="test-filing",
                filing_type="10-K",
                filing_date=datetime(2023, 1, 15),
                period_end=None,
                document_url="https://example.com/test.html",
                ticker=ticker,
                company_name="Apple Inc.",
                cik="0000320193"
            )
        ]
        
        mock_documents = [Document(id="test-doc")]
        
        with patch('app.services.document_storage.SECEdgarScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_filings.return_value = mock_filings
            mock_scraper_class.return_value.__aenter__.return_value = mock_scraper
            
            document_storage_service.download_and_store_filings = AsyncMock(
                return_value=mock_documents
            )
            
            # Track progress calls
            progress_calls = []
            async def progress_callback(status, current, total):
                progress_calls.append((status, current, total))
            
            result = await document_storage_service.process_company_filings(
                ticker, years, progress_callback=progress_callback
            )
            
            assert result["ticker"] == ticker
            assert result["status"] == "completed"
            assert result["filings_found"] == 1
            assert result["documents_stored"] == 1
            assert result["error"] is None
            
            # Check progress was tracked
            assert len(progress_calls) >= 3  # scraping, downloading, completed
    
    def test_get_storage_statistics(self, document_storage_service, temp_storage_dir):
        """Test storage statistics calculation"""
        # Create some test files
        test_file = Path(temp_storage_dir) / "test.txt"
        test_file.write_text("test content")
        
        # Mock database statistics
        mock_db_stats = {"total_documents": 5, "processed_documents": 3}
        document_storage_service.document_repo.get_filing_statistics = MagicMock(
            return_value=mock_db_stats
        )
        
        stats = document_storage_service.get_storage_statistics()
        
        assert stats["storage_path"] == str(document_storage_service.storage_path)
        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] > 0
        assert stats["database_stats"] == mock_db_stats
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files(self, document_storage_service, temp_storage_dir):
        """Test cleanup of orphaned files"""
        # Create test file
        test_file = Path(temp_storage_dir) / "orphaned.txt"
        test_file.write_text("orphaned content")
        
        # Mock database query to return no matching document
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        document_storage_service.db.query.return_value = mock_query
        
        cleaned_count = await document_storage_service.cleanup_orphaned_files()
        
        assert cleaned_count == 1
        assert not test_file.exists()