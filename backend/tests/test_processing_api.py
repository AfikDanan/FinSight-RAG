"""
Integration tests for processing API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.services.processing_service import ProcessingStatus, ProcessingPhase


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_company_service():
    """Mock company service"""
    mock_service = MagicMock()
    mock_service.validate_ticker.return_value = (True, "AAPL")
    return mock_service


@pytest.fixture
def mock_processing_service():
    """Mock processing service"""
    return MagicMock()


class TestProcessingAPI:
    """Test cases for processing API endpoints"""
    
    def test_start_processing_success(self, client, mock_company_service, mock_processing_service):
        """Test successful processing start"""
        # Mock processing status
        mock_status = ProcessingStatus("AAPL", 3, "test-job-id")
        
        # Make start_processing async
        async def mock_start_processing(*args, **kwargs):
            return mock_status
        
        mock_processing_service.start_processing = mock_start_processing
        
        with patch('app.api.companies.get_company_service', return_value=mock_company_service):
            with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
                response = client.post("/api/companies/process", json={
                    "ticker": "AAPL",
                    "timeRange": 3
                })
        
        assert response.status_code == 200
        data = response.json()
        # Check that response has expected structure
        assert "jobId" in data
        assert data["ticker"] == "AAPL"
        assert data["timeRange"] == 3
        assert "status" in data
    
    def test_start_processing_invalid_ticker(self, client, mock_company_service, mock_processing_service):
        """Test processing start with invalid ticker"""
        mock_company_service.validate_ticker.return_value = (False, None)
        
        with patch('app.api.companies.get_company_service', return_value=mock_company_service):
            with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
                response = client.post("/api/companies/process", json={
                    "ticker": "INVALID",
                    "timeRange": 3
                })
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_start_processing_invalid_time_range(self, client, mock_company_service, mock_processing_service):
        """Test processing start with invalid time range"""
        with patch('app.api.companies.get_company_service', return_value=mock_company_service):
            with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
                response = client.post("/api/companies/process", json={
                    "ticker": "AAPL",
                    "timeRange": 7
                })
        
        assert response.status_code == 400
        assert "Time range must be 1, 3, or 5 years" in response.json()["detail"]
    
    def test_get_processing_status_success(self, client, mock_company_service, mock_processing_service):
        """Test successful status retrieval"""
        mock_status = ProcessingStatus("AAPL", 3, "test-job-id")
        mock_status.phase = ProcessingPhase.SCRAPING
        mock_status.progress = 25
        mock_processing_service.get_processing_status.return_value = mock_status
        
        with patch('app.api.companies.get_company_service', return_value=mock_company_service):
            with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
                response = client.get("/api/companies/AAPL/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["phase"] == "scraping"
        assert data["progress"] == 25
    
    def test_get_processing_status_not_found(self, client, mock_company_service, mock_processing_service):
        """Test status retrieval when no processing found"""
        mock_processing_service.get_processing_status.return_value = None
        
        with patch('app.api.companies.get_company_service', return_value=mock_company_service):
            with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
                response = client.get("/api/companies/AAPL/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["phase"] == "not_started"
        assert data["progress"] == 0
    
    def test_get_job_status_success(self, client, mock_processing_service):
        """Test successful job status retrieval"""
        mock_status = ProcessingStatus("AAPL", 3, "test-job-id")
        mock_status.phase = ProcessingPhase.COMPLETE
        mock_status.progress = 100
        mock_processing_service.get_processing_status.return_value = mock_status
        
        with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
            response = client.get("/api/companies/jobs/test-job-id/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobId"] == "test-job-id"
        assert data["phase"] == "complete"
        assert data["progress"] == 100
    
    def test_get_job_status_not_found(self, client, mock_processing_service):
        """Test job status retrieval when job not found"""
        mock_processing_service.get_processing_status.return_value = None
        
        with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
            response = client.get("/api/companies/jobs/nonexistent/status")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_cancel_job_success(self, client, mock_processing_service):
        """Test successful job cancellation"""
        mock_processing_service.cancel_processing.return_value = True
        
        with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
            response = client.post("/api/companies/jobs/test-job-id/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobId"] == "test-job-id"
        assert data["status"] == "cancelled"
    
    def test_cancel_job_not_found(self, client, mock_processing_service):
        """Test job cancellation when job not found"""
        mock_processing_service.cancel_processing.return_value = False
        
        with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
            response = client.post("/api/companies/jobs/nonexistent/cancel")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_jobs(self, client, mock_processing_service):
        """Test listing all jobs"""
        mock_status1 = ProcessingStatus("AAPL", 3, "job-1")
        mock_status2 = ProcessingStatus("MSFT", 1, "job-2")
        mock_processing_service.get_all_jobs.return_value = [mock_status1, mock_status2]
        
        with patch('app.api.companies.get_processing_service_dep', return_value=mock_processing_service):
            response = client.get("/api/companies/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["jobs"]) == 2
        assert data["jobs"][0]["jobId"] == "job-1"
        assert data["jobs"][1]["jobId"] == "job-2"