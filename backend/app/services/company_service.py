import json
import os
from typing import List, Optional, Dict, Tuple
from difflib import SequenceMatcher
import re
from pathlib import Path

from app.models.company import Company, CompanyResponse, CompanySearchResponse, CompanyDisambiguationResponse


class CompanyService:
    """Service for company validation, search, and ticker resolution"""
    
    def __init__(self):
        self.companies_data: Dict[str, Dict] = {}
        self.ticker_to_company: Dict[str, Dict] = {}
        self.name_to_companies: Dict[str, List[Dict]] = {}
        self._load_company_data()
    
    def _load_company_data(self):
        """Load company data from company_tickers.json"""
        try:
            # Get the path to company_tickers.json in the project root
            current_dir = Path(__file__).parent.parent.parent.parent
            json_path = current_dir / "company_tickers.json"
            
            with open(json_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Process the data into more usable formats
            for key, company_data in raw_data.items():
                ticker = company_data['ticker']
                name = company_data['title']
                cik_str = str(company_data['cik_str']).zfill(10)
                
                # Store in various indexes for efficient lookup
                self.companies_data[key] = company_data
                self.ticker_to_company[ticker.upper()] = company_data
                
                # Index by company name for fuzzy matching
                name_key = self._normalize_company_name(name)
                if name_key not in self.name_to_companies:
                    self.name_to_companies[name_key] = []
                self.name_to_companies[name_key].append(company_data)
                
        except FileNotFoundError:
            print("Warning: company_tickers.json not found. Company service will have limited functionality.")
        except json.JSONDecodeError as e:
            print(f"Error parsing company_tickers.json: {e}")
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for matching"""
        # Remove common suffixes and normalize
        name = re.sub(r'\s+(INC\.?|CORP\.?|LTD\.?|LLC\.?|CO\.?|PLC\.?|SA\.?|SE\.?|AG\.?|NV\.?)$', '', name.upper())
        name = re.sub(r'\s+', ' ', name.strip())
        return name
    
    def _calculate_similarity(self, query: str, target: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, query.upper(), target.upper()).ratio()
    
    def get_company_by_ticker(self, ticker: str) -> Optional[CompanyResponse]:
        """Get company by exact ticker match"""
        company_data = self.ticker_to_company.get(ticker.upper())
        if company_data:
            return CompanyResponse(
                ticker=company_data['ticker'],
                name=company_data['title'],
                cik_str=company_data['cik_str']
            )
        return None
    
    def search_companies(self, query: str, limit: int = 10) -> CompanySearchResponse:
        """Search companies by name or ticker with fuzzy matching"""
        query = query.strip()
        if not query:
            return CompanySearchResponse(
                companies=[],
                total_count=0,
                query=query
            )
        
        # First try exact ticker match
        exact_ticker_match = self.get_company_by_ticker(query)
        if exact_ticker_match:
            return CompanySearchResponse(
                companies=[exact_ticker_match],
                total_count=1,
                query=query
            )
        
        # Fuzzy search by company name and ticker
        matches = []
        query_upper = query.upper()
        
        for ticker, company_data in self.ticker_to_company.items():
            name = company_data['title']
            
            # Calculate similarity scores
            ticker_similarity = self._calculate_similarity(query_upper, ticker)
            name_similarity = self._calculate_similarity(query_upper, name.upper())
            
            # Check for partial matches
            ticker_contains = query_upper in ticker
            name_contains = query_upper in name.upper()
            
            # Calculate overall score
            score = max(ticker_similarity, name_similarity)
            if ticker_contains:
                score = max(score, 0.8)
            if name_contains:
                score = max(score, 0.7)
            
            # Only include matches above threshold
            # Use higher threshold for better quality results
            threshold = 0.4 if len(query) > 2 else 0.6
            if score > threshold:
                matches.append({
                    'company': CompanyResponse(
                        ticker=company_data['ticker'],
                        name=company_data['title'],
                        cik_str=company_data['cik_str']
                    ),
                    'score': score
                })
        
        # Sort by score and limit results
        matches.sort(key=lambda x: x['score'], reverse=True)
        top_matches = [match['company'] for match in matches[:limit]]
        
        # Generate suggestions for similar queries
        suggestions = self._generate_suggestions(query, matches[:5])
        
        return CompanySearchResponse(
            companies=top_matches,
            total_count=len(matches),
            query=query,
            suggestions=suggestions if not top_matches else None
        )
    
    def _generate_suggestions(self, query: str, matches: List[Dict]) -> List[str]:
        """Generate search suggestions based on partial matches"""
        suggestions = []
        query_upper = query.upper()
        
        # If we have good matches, suggest their tickers
        if matches:
            for match in matches[:3]:
                ticker = match['company'].ticker
                if ticker not in suggestions:
                    suggestions.append(ticker)
        
        # Get suggestions from ticker matches
        for ticker in self.ticker_to_company.keys():
            if query_upper in ticker and ticker not in suggestions and len(suggestions) < 5:
                suggestions.append(ticker)
        
        # Get suggestions from company names
        for company_data in self.ticker_to_company.values():
            name = company_data['title']
            if query_upper in name.upper() and len(suggestions) < 5:
                # Extract meaningful parts of company name
                words = name.split()
                for word in words:
                    if (len(word) > 3 and 
                        query_upper in word.upper() and 
                        word not in suggestions and 
                        len(suggestions) < 5):
                        suggestions.append(word)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def disambiguate_company_query(self, query: str) -> CompanyDisambiguationResponse:
        """Handle disambiguation when multiple companies match a query"""
        search_result = self.search_companies(query, limit=10)
        
        if len(search_result.companies) == 0:
            # Generate better suggestions for no matches
            suggestions = self._generate_no_match_suggestions(query)
            return CompanyDisambiguationResponse(
                query=query,
                matches=[],
                message=f"No companies found matching '{query}'. Try one of these suggestions:",
                suggestions=suggestions
            )
        
        if len(search_result.companies) == 1:
            return CompanyDisambiguationResponse(
                query=query,
                matches=search_result.companies,
                exact_match=search_result.companies[0],
                message=f"Found exact match for '{query}'"
            )
        
        # Multiple matches found - check if first match is significantly better
        if len(search_result.companies) > 1:
            # Calculate match quality to determine if we have a clear winner
            first_match_quality = self._calculate_match_quality(query, search_result.companies[0])
            second_match_quality = self._calculate_match_quality(query, search_result.companies[1])
            
            # If first match is significantly better, treat as exact match
            if first_match_quality > 0.9 and first_match_quality - second_match_quality > 0.3:
                return CompanyDisambiguationResponse(
                    query=query,
                    matches=search_result.companies[:1],
                    exact_match=search_result.companies[0],
                    message=f"Best match for '{query}'"
                )
        
        # Multiple good matches found
        suggestions = [f"{company.ticker} ({company.name})" for company in search_result.companies[:5]]
        
        return CompanyDisambiguationResponse(
            query=query,
            matches=search_result.companies,
            message=f"Found {len(search_result.companies)} companies matching '{query}'. Please select one:",
            suggestions=suggestions
        )
    
    def _calculate_match_quality(self, query: str, company: CompanyResponse) -> float:
        """Calculate the quality of a match between query and company"""
        query_upper = query.upper()
        ticker_similarity = self._calculate_similarity(query_upper, company.ticker)
        name_similarity = self._calculate_similarity(query_upper, company.name.upper())
        
        # Exact ticker match gets highest score
        if query_upper == company.ticker:
            return 1.0
        
        # Ticker contains query gets high score
        if query_upper in company.ticker:
            return 0.9
        
        # Name contains query gets good score
        if query_upper in company.name.upper():
            return 0.8
        
        # Return best similarity score
        return max(ticker_similarity, name_similarity)
    
    def _generate_no_match_suggestions(self, query: str) -> List[str]:
        """Generate suggestions when no matches are found"""
        suggestions = []
        query_upper = query.upper()
        
        # Find tickers that start with the query
        for ticker in self.ticker_to_company.keys():
            if ticker.startswith(query_upper) and len(suggestions) < 3:
                suggestions.append(ticker)
        
        # Find similar tickers using edit distance
        for ticker in self.ticker_to_company.keys():
            if (len(ticker) <= len(query) + 2 and 
                len(query) <= len(ticker) + 2 and
                self._calculate_similarity(query_upper, ticker) > 0.6 and
                ticker not in suggestions and
                len(suggestions) < 5):
                suggestions.append(ticker)
        
        # Find company names that contain similar words
        query_words = query_upper.split()
        for company_data in self.ticker_to_company.values():
            name_words = company_data['title'].upper().split()
            for query_word in query_words:
                if len(query_word) > 2:
                    for name_word in name_words:
                        if (self._calculate_similarity(query_word, name_word) > 0.7 and
                            company_data['ticker'] not in suggestions and
                            len(suggestions) < 5):
                            suggestions.append(company_data['ticker'])
                            break
        
        return suggestions[:5]
    
    def validate_ticker(self, ticker: str) -> Tuple[bool, Optional[str]]:
        """Validate if a ticker exists and return normalized version"""
        if not ticker or not isinstance(ticker, str):
            return False, None
        
        normalized_ticker = ticker.upper().strip()
        if normalized_ticker in self.ticker_to_company:
            return True, normalized_ticker
        
        return False, None
    
    def get_company_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get company suggestions for autocomplete"""
        if not partial_query or len(partial_query) < 2:
            return []
        
        suggestions = []
        query_upper = partial_query.upper()
        
        # Get ticker suggestions
        for ticker in self.ticker_to_company.keys():
            if ticker.startswith(query_upper):
                suggestions.append(ticker)
        
        # Get company name suggestions
        for company_data in self.ticker_to_company.values():
            name = company_data['title']
            if name.upper().startswith(query_upper):
                suggestions.append(name)
        
        return list(set(suggestions))[:limit]