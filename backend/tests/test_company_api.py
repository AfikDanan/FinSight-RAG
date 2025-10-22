import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, mock_open
import json

from app.main import app
from app.models.company import CompanyResponse, CompanySearchResponse, CompanyDisambiguationResponse


class TestCompanyAPI:
    """Test cases for Company API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_company_data(self):
        """Mock company data for testing"""
        return {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
            "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
            "3": {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms, Inc."},
            "4": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}
        }
    
    @pytest.fixture(autouse=True)
    def setup_mock_data(self, mock_company_data):
        """Setup mock data for all tests"""
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_company_data))):
            with patch("pathlib.Path.exists", return_value=True):
                yield
    
    def test_search_companies_success(self, client):
        """Test successful company search"""
        response = client.get("/api/companies/search?query=AAPL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "companies" in data
        assert "total_count" in data
        assert "query" in data
        assert data["query"] == "AAPL"
        assert data["total_count"] >= 1
        assert len(data["companies"]) >= 1
        
        # Check first result
        first_company = data["companies"][0]
        assert first_company["ticker"] == "AAPL"
        assert first_company["name"] == "Apple Inc."
        assert first_company["cik_str"] == 320193
    
    def test_search_companies_fuzzy_match(self, client):
        """Test fuzzy matching in company search"""
        response = client.get("/api/companies/search?query=Apple")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] > 0
        # Apple Inc. should be in the results
        apple_found = any(company["ticker"] == "AAPL" for company in data["companies"])
        assert apple_found
    
    def test_search_companies_with_limit(self, client):
        """Test company search with limit parameter"""
        response = client.get("/api/companies/search?query=Corp&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["companies"]) <= 2
    
    def test_search_companies_empty_query(self, client):
        """Test company search with empty query"""
        response = client.get("/api/companies/search?query=")
        
        assert response.status_code == 422  # Validation error for empty query
    
    def test_search_companies_invalid_limit(self, client):
        """Test company search with invalid limit"""
        response = client.get("/api/companies/search?query=AAPL&limit=0")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_companies_large_limit(self, client):
        """Test company search with limit exceeding maximum"""
        response = client.get("/api/companies/search?query=AAPL&limit=100")
        
        assert response.status_code == 422  # Validation error for limit > 50
    
    def test_disambiguate_company_exact_match(self, client):
        """Test company disambiguation with exact match"""
        response = client.get("/api/companies/disambiguate?query=AAPL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "matches" in data
        assert "exact_match" in data
        assert "message" in data
        assert "suggestions" in data
        
        assert data["query"] == "AAPL"
        assert data["exact_match"] is not None
        assert data["exact_match"]["ticker"] == "AAPL"
    
    def test_disambiguate_company_multiple_matches(self, client):
        """Test company disambiguation with multiple matches"""
        response = client.get("/api/companies/disambiguate?query=Corp")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["matches"]) > 1
        assert data["exact_match"] is None or len(data["matches"]) == 1
        assert len(data["suggestions"]) > 0
    
    def test_disambiguate_company_no_matches(self, client):
        """Test company disambiguation with no matches"""
        response = client.get("/api/companies/disambiguate?query=NONEXISTENT")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should either have no matches or very few low-quality matches
        assert len(data["matches"]) == 0 or data["matches"][0]["ticker"] != "NONEXISTENT"
    
    def test_get_company_suggestions(self, client):
        """Test getting company suggestions"""
        response = client.get("/api/companies/suggestions?q=AA")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "suggestions" in data
        assert data["query"] == "AA"
        assert isinstance(data["suggestions"], list)
    
    def test_get_company_suggestions_short_query(self, client):
        """Test suggestions with query too short"""
        response = client.get("/api/companies/suggestions?q=A")
        
        assert response.status_code == 422  # Validation error for query < 2 chars
    
    def test_get_company_by_ticker_success(self, client):
        """Test getting company by ticker"""
        response = client.get("/api/companies/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["cik_str"] == 320193
        assert "last_filing_date" in data
        assert "total_filings" in data
        assert "available_documents" in data
    
    def test_get_company_by_ticker_case_insensitive(self, client):
        """Test getting company by ticker (case insensitive)"""
        response = client.get("/api/companies/aapl")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "AAPL"
        assert data["name"] == "Apple Inc."
    
    def test_get_company_by_ticker_not_found(self, client):
        """Test getting company with non-existent ticker"""
        response = client.get("/api/companies/INVALID")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_validate_ticker_valid(self, client):
        """Test ticker validation with valid ticker"""
        response = client.post("/api/companies/validate?ticker=AAPL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "AAPL"
        assert data["is_valid"] is True
        assert data["normalized_ticker"] == "AAPL"
        assert "valid" in data["message"].lower()
    
    def test_validate_ticker_invalid(self, client):
        """Test ticker validation with invalid ticker"""
        response = client.post("/api/companies/validate?ticker=INVALID")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "INVALID"
        assert data["is_valid"] is False
        assert data["normalized_ticker"] is None
        assert "not found" in data["message"].lower()
    
    def test_validate_ticker_case_insensitive(self, client):
        """Test ticker validation is case insensitive"""
        response = client.post("/api/companies/validate?ticker=aapl")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ticker"] == "aapl"
        assert data["is_valid"] is True
        assert data["normalized_ticker"] == "AAPL"
    
    def test_api_error_handling(self, client):
        """Test API error handling for missing query parameter"""
        response = client.get("/api/companies/search")
        
        assert response.status_code == 422  # Validation error
        
        response = client.get("/api/companies/disambiguate")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_companies_no_results_suggestions(self, client):
        """Test that search provides suggestions when no good matches found"""
        response = client.get("/api/companies/search?query=ZZZZZZ")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have few or no results for nonsense query
        if data["total_count"] == 0:
            assert data["suggestions"] is not None
        else:
            # If there are results, they should be low quality
            assert data["total_count"] < 5
    
    def test_concurrent_requests(self, client):
        """Test handling multiple concurrent requests"""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/companies/search?query=AAPL")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["companies"][0]["ticker"] == "AAPL"