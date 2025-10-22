"""
Company repository for database operations related to companies.
Provides specialized methods for company-specific queries and operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.database import Company
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CompanyRepository(BaseRepository[Company]):
    """
    Repository for Company model with specialized company operations.
    """
    
    def __init__(self, db: Session):
        super().__init__(Company, db)
    
    def get_by_ticker(self, ticker: str) -> Optional[Company]:
        """
        Get company by ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Company instance or None if not found
        """
        try:
            return self.db.query(Company).filter(
                Company.ticker.ilike(ticker.upper())
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting company by ticker {ticker}: {e}")
            raise
    
    def get_by_cik(self, cik_str: int) -> Optional[Company]:
        """
        Get company by CIK (Central Index Key).
        
        Args:
            cik_str: SEC Central Index Key
            
        Returns:
            Company instance or None if not found
        """
        try:
            return self.db.query(Company).filter(Company.cik_str == cik_str).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting company by CIK {cik_str}: {e}")
            raise
    
    def search_by_name(self, query: str, limit: int = 10) -> List[Company]:
        """
        Search companies by name using fuzzy matching.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching companies
        """
        try:
            search_term = f"%{query.lower()}%"
            return self.db.query(Company).filter(
                or_(
                    Company.name.ilike(search_term),
                    Company.ticker.ilike(search_term)
                )
            ).filter(Company.is_active == True).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error searching companies by name '{query}': {e}")
            raise
    
    def search_companies(
        self, 
        query: str, 
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 10
    ) -> List[Company]:
        """
        Advanced company search with multiple filters.
        
        Args:
            query: Search query for name or ticker
            sector: Optional sector filter
            industry: Optional industry filter
            limit: Maximum number of results
            
        Returns:
            List of matching companies
        """
        try:
            search_term = f"%{query.lower()}%"
            query_obj = self.db.query(Company).filter(
                or_(
                    Company.name.ilike(search_term),
                    Company.ticker.ilike(search_term)
                ),
                Company.is_active == True
            )
            
            if sector:
                query_obj = query_obj.filter(Company.sector.ilike(f"%{sector}%"))
            
            if industry:
                query_obj = query_obj.filter(Company.industry.ilike(f"%{industry}%"))
            
            return query_obj.limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error in advanced company search: {e}")
            raise
    
    def get_by_sector(self, sector: str, limit: int = 50) -> List[Company]:
        """
        Get companies by sector.
        
        Args:
            sector: Business sector
            limit: Maximum number of results
            
        Returns:
            List of companies in the sector
        """
        try:
            return self.db.query(Company).filter(
                Company.sector.ilike(f"%{sector}%"),
                Company.is_active == True
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting companies by sector '{sector}': {e}")
            raise
    
    def get_by_industry(self, industry: str, limit: int = 50) -> List[Company]:
        """
        Get companies by industry.
        
        Args:
            industry: Industry classification
            limit: Maximum number of results
            
        Returns:
            List of companies in the industry
        """
        try:
            return self.db.query(Company).filter(
                Company.industry.ilike(f"%{industry}%"),
                Company.is_active == True
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting companies by industry '{industry}': {e}")
            raise
    
    def get_similar_companies(
        self, 
        ticker: str, 
        limit: int = 10
    ) -> List[Company]:
        """
        Get companies similar to the given ticker (same sector/industry).
        
        Args:
            ticker: Reference ticker symbol
            limit: Maximum number of results
            
        Returns:
            List of similar companies
        """
        try:
            reference_company = self.get_by_ticker(ticker)
            if not reference_company:
                return []
            
            return self.db.query(Company).filter(
                and_(
                    Company.ticker != ticker,
                    or_(
                        Company.sector == reference_company.sector,
                        Company.industry == reference_company.industry
                    ),
                    Company.is_active == True
                )
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting similar companies for {ticker}: {e}")
            raise
    
    def get_active_companies(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Company]:
        """
        Get active companies with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of results
            
        Returns:
            List of active companies
        """
        try:
            return self.db.query(Company).filter(
                Company.is_active == True
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting active companies: {e}")
            raise
    
    def get_companies_with_documents(self, limit: int = 100) -> List[Company]:
        """
        Get companies that have associated documents.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of companies with documents
        """
        try:
            return self.db.query(Company).filter(
                Company.documents.any(),
                Company.is_active == True
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting companies with documents: {e}")
            raise
    
    def update_market_cap(self, ticker: str, market_cap: float) -> Optional[Company]:
        """
        Update market capitalization for a company.
        
        Args:
            ticker: Stock ticker symbol
            market_cap: New market capitalization value
            
        Returns:
            Updated company instance or None if not found
        """
        try:
            company = self.get_by_ticker(ticker)
            if not company:
                return None
            
            company.market_cap = market_cap
            self.db.commit()
            self.db.refresh(company)
            
            logger.info(f"Updated market cap for {ticker}: ${market_cap:,.2f}")
            return company
        except SQLAlchemyError as e:
            logger.error(f"Error updating market cap for {ticker}: {e}")
            self.db.rollback()
            raise
    
    def deactivate_company(self, ticker: str) -> bool:
        """
        Deactivate a company (soft delete).
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if deactivated, False if not found
        """
        try:
            company = self.get_by_ticker(ticker)
            if not company:
                return False
            
            company.is_active = False
            self.db.commit()
            
            logger.info(f"Deactivated company: {ticker}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating company {ticker}: {e}")
            self.db.rollback()
            raise
    
    def get_sector_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics about companies by sector.
        
        Returns:
            List of dictionaries with sector statistics
        """
        try:
            results = self.db.query(
                Company.sector,
                func.count(Company.ticker).label('company_count'),
                func.avg(Company.market_cap).label('avg_market_cap'),
                func.sum(Company.market_cap).label('total_market_cap')
            ).filter(
                Company.is_active == True,
                Company.sector.isnot(None)
            ).group_by(Company.sector).all()
            
            return [
                {
                    'sector': result.sector,
                    'company_count': result.company_count,
                    'avg_market_cap': float(result.avg_market_cap) if result.avg_market_cap else 0,
                    'total_market_cap': float(result.total_market_cap) if result.total_market_cap else 0
                }
                for result in results
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error getting sector statistics: {e}")
            raise