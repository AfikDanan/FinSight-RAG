"""
Base repository class providing common database operations.
All specific repositories inherit from this base class.
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc
import logging

from app.database import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class with common CRUD operations.
    Provides a consistent interface for database operations across all models.
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record in the database.
        
        Args:
            obj_in: Dictionary of field values
            
        Returns:
            Created model instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__} with ID: {getattr(db_obj, 'id', 'N/A')}")
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise
    
    def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a single record by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} with ID {id}: {e}")
            raise
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and ordering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            
        Returns:
            List of model instances
        """
        try:
            query = self.db.query(self.model)
            
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise
    
    def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update an existing record.
        
        Args:
            id: Primary key value
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance or None if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.get(id)
            if not db_obj:
                return None
            
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.commit()
            self.db.refresh(db_obj)
            logger.info(f"Updated {self.model.__name__} with ID: {id}")
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.get(id)
            if not db_obj:
                return False
            
            self.db.delete(db_obj)
            self.db.commit()
            logger.info(f"Deleted {self.model.__name__} with ID: {id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            self.db.rollback()
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filters.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            Number of matching records
        """
        try:
            query = self.db.query(self.model)
            
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)
            
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise
    
    def exists(self, id: Any) -> bool:
        """
        Check if a record exists by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} with ID {id}: {e}")
            raise
    
    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            objects: List of dictionaries with field values
            
        Returns:
            List of created model instances
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_objects = [self.model(**obj) for obj in objects]
            self.db.add_all(db_objects)
            self.db.commit()
            
            for db_obj in db_objects:
                self.db.refresh(db_obj)
            
            logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
        except SQLAlchemyError as e:
            logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise