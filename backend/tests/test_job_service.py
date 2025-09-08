import pytest
import uuid
from backend.db.database import Job, JobStatus, SelectionKind
from backend.models.job_models import BulkAddRequest
from backend.services.job_service import (
    generate_idempotency_key,
    create_bulk_add_job,
    get_job_by_id,
    update_job_progress,
    mark_job_status,
    calculate_progress_percentage,
    get_collection_company_count
)


class TestJobService:
    """Test suite for job service functions."""

    def test_generate_idempotency_key_explicit(self):
        """Test idempotency key generation for explicit selection."""
        key1 = generate_idempotency_key(
            "source-id-1",
            "target-id-1", 
            SelectionKind.EXPLICIT,
            {"ids": [1, 2, 3]},
            "user1"
        )
        
        key2 = generate_idempotency_key(
            "source-id-1",
            "target-id-1",
            SelectionKind.EXPLICIT,
            {"ids": [1, 2, 3]},
            "user1"
        )
        
        # Same input should generate same key
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex string

    def test_generate_idempotency_key_different_inputs(self):
        """Test that different inputs generate different keys."""
        base_params = {
            "source_collection_id": "source-id-1",
            "target_collection_id": "target-id-1",
            "selection_kind": SelectionKind.EXPLICIT,
            "selection_data": {"ids": [1, 2, 3]},
            "user_id": "user1"
        }
        
        key1 = generate_idempotency_key(**base_params)
        
        # Different source collection
        key2 = generate_idempotency_key(
            **{**base_params, "source_collection_id": "source-id-2"}
        )
        
        # Different selection data
        key3 = generate_idempotency_key(
            **{**base_params, "selection_data": {"ids": [1, 2, 4]}}
        )
        
        # Different user
        key4 = generate_idempotency_key(
            **{**base_params, "user_id": "user2"}
        )
        
        # All keys should be different
        keys = [key1, key2, key3, key4]
        assert len(set(keys)) == 4

    def test_create_bulk_add_job_explicit(self, db_session, sample_collections):
        """Test creating a bulk add job with explicit selection."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3, 4, 5]}
        )
        
        job = create_bulk_add_job(db_session, request)
        
        assert job.job_type == "bulk_add_companies"
        assert job.selection_kind == SelectionKind.EXPLICIT
        assert job.selection_snapshot == {"ids": [1, 2, 3, 4, 5]}
        assert job.source_collection_id == source_collection.id
        assert job.target_collection_id == target_collection.id
        assert job.total_items == 5
        assert job.status == JobStatus.PENDING
        assert job.idempotency_key is not None

    def test_create_bulk_add_job_all_matching(self, db_session, sample_collections):
        """Test creating a bulk add job with all_matching selection."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.ALL_MATCHING,
            selection_data={
                "filter": {"name_contains": "test"},
                "total_at_snapshot": 150
            }
        )
        
        job = create_bulk_add_job(db_session, request)
        
        assert job.selection_kind == SelectionKind.ALL_MATCHING
        assert job.selection_snapshot["filter"]["name_contains"] == "test"
        assert job.total_items == 150

    def test_create_bulk_add_job_idempotency(self, db_session, sample_collections):
        """Test that creating the same job twice returns the existing job."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3]}
        )
        
        # Create first job
        job1 = create_bulk_add_job(db_session, request)
        
        # Create "same" job again
        job2 = create_bulk_add_job(db_session, request)
        
        # Should return the same job
        assert job1.id == job2.id
        assert job1.idempotency_key == job2.idempotency_key

    def test_create_bulk_add_job_custom_idempotency_key(self, db_session, sample_collections):
        """Test creating job with custom idempotency key."""
        source_collection, target_collection = sample_collections
        
        custom_key = "my-custom-key-123"
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3]},
            client_idempotency_key=custom_key
        )
        
        job = create_bulk_add_job(db_session, request)
        
        assert job.idempotency_key == custom_key

    def test_get_job_by_id(self, db_session, sample_collections):
        """Test getting job by ID."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3]}
        )
        
        created_job = create_bulk_add_job(db_session, request)
        
        # Get job by ID
        retrieved_job = get_job_by_id(db_session, created_job.id)
        
        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id
        assert retrieved_job.job_type == created_job.job_type

    def test_get_job_by_id_nonexistent(self, db_session):
        """Test getting non-existent job returns None."""
        job = get_job_by_id(db_session, "nonexistent-id")
        assert job is None

    def test_update_job_progress(self, db_session, sample_collections):
        """Test updating job progress."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3, 4, 5]}
        )
        
        job = create_bulk_add_job(db_session, request)
        
        # Update progress
        update_job_progress(db_session, job.id, processed=3, added=2, skipped=1, failed=0)
        
        # Refresh job from database
        db_session.refresh(job)
        
        assert job.processed_items == 3
        assert job.added_items == 2
        assert job.skipped_items == 1
        assert job.failed_items == 0

    def test_mark_job_status(self, db_session, sample_collections):
        """Test marking job status."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3]}
        )
        
        job = create_bulk_add_job(db_session, request)
        
        # Mark as processing
        mark_job_status(db_session, job.id, JobStatus.PROCESSING)
        db_session.refresh(job)
        
        assert job.status == JobStatus.PROCESSING
        assert job.started_at is not None
        
        # Mark as completed
        mark_job_status(db_session, job.id, JobStatus.COMPLETED)
        db_session.refresh(job)
        
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

    def test_mark_job_status_with_error(self, db_session, sample_collections):
        """Test marking job status with error message."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3]}
        )
        
        job = create_bulk_add_job(db_session, request)
        
        error_message = "Database connection failed"
        mark_job_status(db_session, job.id, JobStatus.FAILED, error_message)
        db_session.refresh(job)
        
        assert job.status == JobStatus.FAILED
        assert job.error_message == error_message
        assert job.completed_at is not None

    def test_calculate_progress_percentage(self, db_session, sample_collections):
        """Test progress percentage calculation."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.EXPLICIT,
            selection_data={"ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
        )
        
        job = create_bulk_add_job(db_session, request)
        
        # No progress yet
        assert calculate_progress_percentage(job) == 0.0
        
        # Update progress
        update_job_progress(db_session, job.id, processed=3, added=2, skipped=1, failed=0)
        db_session.refresh(job)
        
        # 3 out of 10 = 30%
        assert calculate_progress_percentage(job) == 30.0
        
        # Complete
        update_job_progress(db_session, job.id, processed=10, added=8, skipped=2, failed=0)
        db_session.refresh(job)
        
        assert calculate_progress_percentage(job) == 100.0

    def test_calculate_progress_percentage_zero_total(self, db_session, sample_collections):
        """Test progress percentage calculation with zero total items."""
        source_collection, target_collection = sample_collections
        
        request = BulkAddRequest(
            source_collection_id=str(source_collection.id),
            target_collection_id=str(target_collection.id),
            selection_kind=SelectionKind.ALL_MATCHING,
            selection_data={"filter": {}}  # No total_at_snapshot provided
        )
        
        job = create_bulk_add_job(db_session, request)
        
        # Should handle zero total gracefully
        assert calculate_progress_percentage(job) == 0.0

    def test_get_collection_company_count(self, db_session, sample_collections, sample_companies):
        """Test getting company count for a collection."""
        source_collection, target_collection = sample_collections
        companies = sample_companies  # 10 companies added to source collection
        
        # Source collection should have 10 companies
        count = get_collection_company_count(db_session, str(source_collection.id))
        assert count == 10
        
        # Target collection should have 0 companies
        count = get_collection_company_count(db_session, str(target_collection.id))
        assert count == 0
