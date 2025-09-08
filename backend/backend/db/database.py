# app/database.py
import os
import uuid
from datetime import datetime
from typing import Union
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLAlchemy models
Base = declarative_base()

class Settings(Base):
    __tablename__ = "harmonic_settings"

    setting_name = Column(String, primary_key=True)

class Company(Base):
    __tablename__ = "companies"

    created_at: Union[datetime, Column[datetime]] = Column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)

class CompanyCollection(Base):
    __tablename__ = "company_collections"

    created_at: Union[datetime, Column[datetime]] = Column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    id: Column[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_name = Column(String, index=True)

class CompanyCollectionAssociation(Base):
    __tablename__ = "company_collection_associations"

    __table_args__ = (
        UniqueConstraint('company_id', 'collection_id', name='uq_company_collection'),
    )
    
    created_at: Union[datetime, Column[datetime]] = Column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("company_collections.id"))


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SelectionKind(str, Enum):
    EXPLICIT = "explicit"
    ALL_MATCHING = "all_matching"


class Job(Base):
    __tablename__ = "jobs"
    
    # Core identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False)  # "bulk_add_companies"
    idempotency_key = Column(String, unique=True, nullable=False)  # Keep idempotency
    
    # Selection semantics
    selection_kind = Column(SQLEnum(SelectionKind), nullable=False)
    selection_snapshot = Column(JSON, nullable=False)  # {ids: [...]} or {filter: {...}}
    source_collection_id = Column(UUID(as_uuid=True), ForeignKey("company_collections.id"), nullable=False)
    target_collection_id = Column(UUID(as_uuid=True), ForeignKey("company_collections.id"), nullable=False)
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    added_items = Column(Integer, default=0)
    skipped_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Simple job lifecycle
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    cancel_requested = Column(Boolean, default=False)  # Keep cancellation
    
    # Timestamps
    created_at: Union[datetime, Column[datetime]] = Column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Relationships
    source_collection = relationship("CompanyCollection", foreign_keys=[source_collection_id])
    target_collection = relationship("CompanyCollection", foreign_keys=[target_collection_id])


