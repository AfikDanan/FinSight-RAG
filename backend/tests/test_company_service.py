import pytest
from unittest.mock import patch, mock_open
import json
from app.services.company_service import CompanyService
from app.models.company import CompanyResponse


class TestCompanyService:
    """Test cases for CompanyService"""
    
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
    
    @pytest.fixture
    def company_service(self, mock_company_data):
        """Create CompanyService instance with mocked data"""
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_company_data))):
            with patch("pathlib.Path.exists", return_value=True):
                return CompanyService()
    
    def test_get_company_by_ticker_exact_match(self, company_service):
        """Test getting company by exact ticker match"""
        result = company_service.get_company_by_ticker("AAPL")
        
        assert result is not None
        assert result.ticker == "AAPL"
        assert result.name == "Apple Inc."
        assert result.cik_str == 320193
    
    def test_get_company_by_ticker_case_insensitive(self, company_service):
        """Test ticker lookup is case insensitive"""
        result = company_service.get_company_by_ticker("aapl")
        
        assert result is not None
        assert result.ticker == "AAPL"
        assert result.name == "Apple Inc."
    
    def test_get_company_by_ticker_not_found(self, company_service):
        """Test getting company with non-existent ticker"""
        result = company_service.get_company_by_ticker("INVALID")
        
        assert result is None
    
    def test_search_companies_exact_ticker_match(self, company_service):
        """Test search with exact ticker match"""
        result = company_service.search_companies("AAPL")
        
        assert result.total_count == 1
        assert len(result.companies) == 1
        assert result.companies[0].ticker == "AAPL"
        assert result.query == "AAPL"
    
    def test_search_companies_fuzzy_name_match(self, company_service):
        """Test fuzzy search by company name"""
        result = company_service.search_companies("Apple")
        
        assert result.total_count > 0
        assert len(result.companies) > 0
        # Apple Inc. should be in the results
        apple_found = any(company.ticker == "AAPL" for company in result.companies)
        assert apple_found
    
    def test_search_companies_partial_ticker_match(self, company_service):
        """Test search with partial ticker match"""
        result = company_service.search_companies("MS")
        
        assert result.total_count > 0
        # MSFT should be in the results
        msft_found = any(company.ticker == "MSFT" for company in result.companies)
        assert msft_found
    
    def test_search_companies_empty_query(self, company_service):
        """Test search with empty query"""
        result = company_service.search_companies("")
        
        assert result.total_count == 0
        assert len(result.companies) == 0
        assert result.query == ""
    
    def test_search_companies_limit(self, company_service):
        """Test search result limiting"""
        result = company_service.search_companies("Corp", limit=2)
        
        assert len(result.companies) <= 2
    
    def test_validate_ticker_valid(self, company_service):
        """Test ticker validation with valid ticker"""
        is_valid, normalized = company_service.validate_ticker("aapl")
        
        assert is_valid is True
        assert normalized == "AAPL"
    
    def test_validate_ticker_invalid(self, company_service):
        """Test ticker validation with invalid ticker"""
        is_valid, normalized = company_service.validate_ticker("INVALID")
        
        assert is_valid is False
        assert normalized is None
    
    def test_validate_ticker_empty(self, company_service):
        """Test ticker validation with empty input"""
        is_valid, normalized = company_service.validate_ticker("")
        
        assert is_valid is False
        assert normalized is None
    
    def test_validate_ticker_none(self, company_service):
        """Test ticker validation with None input"""
        is_valid, normalized = company_service.validate_ticker(None)
        
        assert is_valid is False
        assert normalized is None
    
    def test_disambiguate_exact_match(self, company_service):
        """Test disambiguation with exact match"""
        result = company_service.disambiguate_company_query("AAPL")
        
        assert result.exact_match is not None
        assert result.exact_match.ticker == "AAPL"
        assert "exact match" in result.message.lower()
    
    def test_disambiguate_multiple_matches(self, company_service):
        """Test disambiguation with multiple matches"""
        result = company_service.disambiguate_company_query("Corp")
        
        assert len(result.matches) > 1
        assert result.exact_match is None
        assert "select one" in result.message.lower()
        assert len(result.suggestions) > 0
    
    def test_disambiguate_no_matches(self, company_service):
        """Test disambiguation with no matches"""
        result = company_service.disambiguate_company_query("NONEXISTENT")
        
        assert len(result.matches) == 0
        assert result.exact_match is None
        assert "no companies found" in result.message.lower() or len(result.matches) == 0
    
    def test_get_company_suggestions(self, company_service):
        """Test getting company suggestions for autocomplete"""
        suggestions = company_service.get_company_suggestions("AA")
        
        assert isinstance(suggestions, list)
        # Should include AAPL
        assert "AAPL" in suggestions or any("AAPL" in s for s in suggestions)
    
    def test_get_company_suggestions_short_query(self, company_service):
        """Test suggestions with very short query"""
        suggestions = company_service.get_company_suggestions("A")
        
        assert isinstance(suggestions, list)
        # Should return empty list for single character
        assert len(suggestions) == 0
    
    def test_normalize_company_name(self, company_service):
        """Test company name normalization"""
        normalized = company_service._normalize_company_name("Apple Inc.")
        assert normalized == "APPLE"
        
        normalized = company_service._normalize_company_name("Microsoft Corp")
        assert normalized == "MICROSOFT"
        
        normalized = company_service._normalize_company_name("Alphabet Inc.")
        assert normalized == "ALPHABET"
    
    def test_calculate_similarity(self, company_service):
        """Test similarity calculation"""
        similarity = company_service._calculate_similarity("AAPL", "AAPL")
        assert similarity == 1.0
        
        similarity = company_service._calculate_similarity("AAPL", "APPLE")
        assert 0 < similarity < 1
        
        similarity = company_service._calculate_similarity("AAPL", "MSFT")
        assert similarity < 0.5
    
    def test_calculate_match_quality(self, company_service):
        """Test match quality calculation"""
        company = CompanyResponse(ticker="AAPL", name="Apple Inc.", cik_str=320193)
        
        # Exact ticker match should get highest score
        quality = company_service._calculate_match_quality("AAPL", company)
        assert quality == 1.0
        
        # Partial ticker match should get high score
        quality = company_service._calculate_match_quality("AAP", company)
        assert quality >= 0.8
        
        # Name match should get good score
        quality = company_service._calculate_match_quality("Apple", company)
        assert quality >= 0.7