import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_db
from backend.db.database import Company, CompanyCollection, CompanyCollectionAssociation
from main import app

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for direct database operations in tests."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_collections(db_session):
    """Create sample collections for testing."""
    collection1 = CompanyCollection(
        id=uuid.uuid4(),
        collection_name="Source Collection"
    )
    collection2 = CompanyCollection(
        id=uuid.uuid4(),
        collection_name="Target Collection"
    )
    
    db_session.add(collection1)
    db_session.add(collection2)
    db_session.commit()
    db_session.refresh(collection1)
    db_session.refresh(collection2)
    
    return collection1, collection2


@pytest.fixture
def sample_companies(db_session, sample_collections):
    """Create sample companies in the source collection."""
    source_collection, _ = sample_collections
    
    companies = []
    for i in range(10):
        company = Company(company_name=f"Test Company {i}")
        db_session.add(company)
        companies.append(company)
    
    db_session.commit()
    
    # Add companies to source collection
    for company in companies:
        association = CompanyCollectionAssociation(
            company_id=company.id,
            collection_id=source_collection.id
        )
        db_session.add(association)
    
    db_session.commit()
    
    for company in companies:
        db_session.refresh(company)
    
    return companies
