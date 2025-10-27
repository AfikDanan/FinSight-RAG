"""
Tests for processing service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.processing_service import ProcessingService, ProcessingStatus, ProcessingPhase
from app.repositories.manager import RepositoryManager


@pytest.fixture
def mock_repo_manager():
    """Create mock repository manager"""
    return MagicMock(spec=RepositoryManager)


@pytest.fixture
def processing_service(mock_repo_manager):
    """Create processing service with mocked dependencies"""
    return ProcessingService(mock_repo_manager)


class TestProcessingStatus:
    """Test cases for ProcessingStatus"""
    
    def test_init(self):
        """Test ProcessingStatus initialization"""
        status = ProcessingStatus("AAPL", 3)
        
        assert status.ticker == "AAPL"
        assert status.time_range == 3
        assert status.phase == ProcessingPhase.PENDING
        assert status.progress == 0
        assert status.documents_found == 0
        assert status.documents_processed == 0
        assert status.chunks_created == 0
        assert status.chunks_vectorized == 0
        assert status.started_at is not None
        assert status.completed_at is None
        assert status.error_message is None
    
    def test_to_dict(self):
        """Test converting status to dictionary"""
        status = ProcessingStatus("AAPL", 3, "test-job-id")
        status.progress = 50
        status.documents_found = 10
        
        result = status.to_dict()
        
        assert result["jobId"] == "test-job-id"
        assert result["ticker"] == "AAPL"
        assert result["timeRange"] == 3
        assert result["phase"] == "pending"
        assert result["progress"] == 50
        assert result["documentsFound"] == 10
        assert "startedAt" in result
        assert result["completedAt"] is None


class TestProcessingService:
    """Test cases for ProcessingService"""
    
    def test_init(self, processing_service):
        """Test service initialization"""
        assert processing_service.repo_manager is not None
        assert processing_service.supported_filing_types == ["10-K", "10-Q", "8-K", "20-F", "4"]
        assert len(processing_service._processing_jobs) == 0
        assert len(processing_service._job_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_start_processing_success(self, processing_service):
        """Test successful processing start"""
        ticker = "AAPL"
        time_range = 3
        
        # Mock the background processing task
        with patch.object(processing_service, '_process_company_documents', new_callable=AsyncMock) as mock_process:
            status = await processing_service.start_processing(ticker, time_range)
            
            assert status.ticker == ticker
            assert status.time_range == time_range
            assert status.phase == ProcessingPhase.PENDING
            assert status.job_id in processing_service._processing_jobs
            
            # Verify background task was started
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_processing_invalid_time_range(self, processing_service):
        """Test processing start with invalid time range"""
        with pytest.raises(ValueError, match="Time range must be 1, 3, or 5 years"):
            await processing_service.start_processing("AAPL", 7)
    
    @pytest.mark.asyncio
    async def test_start_processing_already_in_progress(self, processing_service):
        """Test starting processing when already in progress"""
        ticker = "AAPL"
        time_range = 3
        
        # Create existing job
        existing_status = ProcessingStatus(ticker, time_range)
        existing_status.phase = ProcessingPhase.SCRAPING
        processing_service._processing_jobs[existing_status.job_id] = existing_status
        
        with patch.object(processing_service, '_process_company_documents', new_callable=AsyncMock):
            status = await processing_service.start_processing(ticker, time_range)
            
            # Should return existing job
            assert status.job_id == existing_status.job_id
            assert status.phase == ProcessingPhase.SCRAPING
    
    def test_get_processing_status_by_ticker(self, processing_service):
        """Test getting processing status by ticker"""
        ticker = "AAPL"
        status = ProcessingStatus(ticker, 3)
        processing_service._processing_jobs[status.job_id] = status
        
        result = processing_service.get_processing_status(ticker=ticker)
        
        assert result is not None
        assert result.ticker == ticker
        assert result.job_id == status.job_id
    
    def test_get_processing_status_by_job_id(self, processing_service):
        """Test getting processing status by job ID"""
        status = ProcessingStatus("AAPL", 3)
        processing_service._processing_jobs[status.job_id] = status
        
        result = processing_service.get_processing_status(job_id=status.job_id)
        
        assert result is not None
        assert result.job_id == status.job_id
    
    def test_get_processing_status_not_found(self, processing_service):
        """Test getting processing status when not found"""
        result = processing_service.get_processing_status(ticker="NONEXISTENT")
        assert result is None
        
        result = processing_service.get_processing_status(job_id="nonexistent-job")
        assert result is None
    
    def test_cancel_processing_success(self, processing_service):
        """Test successful processing cancellation"""
        status = ProcessingStatus("AAPL", 3)
        status.phase = ProcessingPhase.SCRAPING
        processing_service._processing_jobs[status.job_id] = status
        
        # Mock background task
        mock_task = MagicMock()
        mock_task.done.return_value = False
        processing_service._job_tasks[status.job_id] = mock_task
        
        result = processing_service.cancel_processing(status.job_id)
        
        assert result is True
        assert status.phase == ProcessingPhase.ERROR
        assert status.error_message == "Processing cancelled by user"
        assert status.completed_at is not None
        mock_task.cancel.assert_called_once()
    
    def test_cancel_processing_not_found(self, processing_service):
        """Test cancelling non-existent processing job"""
        result = processing_service.cancel_processing("nonexistent-job")
        assert result is False
    
    def test_cancel_processing_already_completed(self, processing_service):
        """Test cancelling already completed job"""
        status = ProcessingStatus("AAPL", 3)
        status.phase = ProcessingPhase.COMPLETE
        processing_service._processing_jobs[status.job_id] = status
        
        result = processing_service.cancel_processing(status.job_id)
        assert result is False
    
    def test_get_all_jobs(self, processing_service):
        """Test getting all processing jobs"""
        status1 = ProcessingStatus("AAPL", 3)
        status2 = ProcessingStatus("MSFT", 1)
        
        processing_service._processing_jobs[status1.job_id] = status1
        processing_service._processing_jobs[status2.job_id] = status2
        
        jobs = processing_service.get_all_jobs()
        
        assert len(jobs) == 2
        assert status1 in jobs
        assert status2 in jobs
    
    def test_cleanup_completed_jobs(self, processing_service):
        """Test cleanup of old completed jobs"""
        # Create old completed job
        old_status = ProcessingStatus("AAPL", 3)
        old_status.phase = ProcessingPhase.COMPLETE
        old_status.completed_at = datetime.utcnow() - datetime.timedelta(hours=25)
        
        # Create recent completed job
        recent_status = ProcessingStatus("MSFT", 1)
        recent_status.phase = ProcessingPhase.COMPLETE
        recent_status.completed_at = datetime.utcnow() - datetime.timedelta(hours=1)
        
        # Create active job
        active_status = ProcessingStatus("GOOGL", 5)
        active_status.phase = ProcessingPhase.SCRAPING
        
        processing_service._processing_jobs[old_status.job_id] = old_status
        processing_service._processing_jobs[recent_status.job_id] = recent_status
        processing_service._processing_jobs[active_status.job_id] = active_status
        
        cleaned_count = processing_service.cleanup_completed_jobs(max_age_hours=24)
        
        assert cleaned_count == 1
        assert old_status.job_id not in processing_service._processing_jobs
        assert recent_status.job_id in processing_service._processing_jobs
        assert active_status.job_id in processing_service._processing_jobs
    
    @pytest.mark.asyncio
    async def test_update_progress(self, processing_service):
        """Test progress update functionality"""
        status = ProcessingStatus("AAPL", 3)
        
        await processing_service._update_progress(status, "scraping", 25, 100)
        
        assert status.phase == ProcessingPhase.SCRAPING
        assert status.progress == 25
        assert status.estimated_time_remaining is not None
    
    @pytest.mark.asyncio
    async def test_process_company_documents_success(self, processing_service):
        """Test successful document processing workflow"""
        status = ProcessingStatus("AAPL", 3)
        filing_types = ["10-K", "10-Q"]
        
        # Mock document storage service
        mock_result = {
            "status": "completed",
            "filings_found": 5,
            "documents_stored": 5
        }
        
        with patch('app.services.processing_service.DocumentStorageService') as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.process_company_filings.return_value = mock_result
            mock_storage_class.return_value.__aenter__.return_value = mock_storage
            
            with patch('app.services.processing_service.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__enter__.return_value = mock_db
                
                await processing_service._process_company_documents(status, filing_types)
                
                assert status.phase == ProcessingPhase.COMPLETE
                assert status.progress == 100
                assert status.documents_found == 5
                assert status.documents_processed == 5
                assert status.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_process_company_documents_error(self, processing_service):
        """Test document processing with error"""
        status = ProcessingStatus("AAPL", 3)
        filing_types = ["10-K"]
        
        with patch('app.services.processing_service.DocumentStorageService') as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.process_company_filings.side_effect = Exception("Test error")
            mock_storage_class.return_value.__aenter__.return_value = mock_storage
            
            with patch('app.services.processing_service.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__enter__.return_value = mock_db
                
                await processing_service._process_company_documents(status, filing_types)
                
                assert status.phase == ProcessingPhase.ERROR
                assert status.error_message == "Test error"
                assert status.completed_at is not None


def test_get_processing_service():
    """Test getting processing service singleton"""
    from app.services.processing_service import get_processing_service
    
    with patch('app.services.processing_service.SessionLocal') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        service1 = get_processing_service()
        service2 = get_processing_service()
        
        # Should return same instance (singleton)
        assert service1 is service2
        assert isinstance(service1, ProcessingService)