import pytest
import json
from backend.db.database import Job, JobStatus, SelectionKind


class TestJobsAPI:
    """Test suite for Jobs API endpoints."""

    def test_create_bulk_add_job_explicit_selection(self, client, sample_collections, sample_companies):
        """Test creating a bulk add job with explicit company selection."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        # Select first 3 companies
        selected_ids = [companies[0].id, companies[1].id, companies[2].id]
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": selected_ids}
        }
        
        response = client.post("/jobs/bulk-add", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["estimated_total"] == 3
        assert "created_at" in data

    def test_create_bulk_add_job_all_matching_selection(self, client, sample_collections):
        """Test creating a bulk add job with all_matching selection."""
        source_collection, target_collection = sample_collections
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "all_matching",
            "selection_data": {
                "filter": {"name_contains": "test"},
                "total_at_snapshot": 100
            }
        }
        
        response = client.post("/jobs/bulk-add", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["estimated_total"] == 100
        assert "created_at" in data

    def test_create_bulk_add_job_idempotency(self, client, sample_collections, sample_companies):
        """Test that duplicate requests return the same job (idempotency)."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [companies[0].id]}
        }
        
        # Make first request
        response1 = client.post("/jobs/bulk-add", json=payload)
        assert response1.status_code == 200
        job1_data = response1.json()
        
        # Make identical request
        response2 = client.post("/jobs/bulk-add", json=payload)
        assert response2.status_code == 200
        job2_data = response2.json()
        
        # Should return the same job
        assert job1_data["job_id"] == job2_data["job_id"]
        assert job1_data["created_at"] == job2_data["created_at"]

    def test_create_bulk_add_job_custom_idempotency_key(self, client, sample_collections, sample_companies):
        """Test custom idempotency key."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [companies[0].id]},
            "client_idempotency_key": "custom-key-123"
        }
        
        # Make first request
        response1 = client.post("/jobs/bulk-add", json=payload)
        assert response1.status_code == 200
        job1_data = response1.json()
        
        # Make request with same custom key
        response2 = client.post("/jobs/bulk-add", json=payload)
        assert response2.status_code == 200
        job2_data = response2.json()
        
        # Should return the same job
        assert job1_data["job_id"] == job2_data["job_id"]

    def test_create_bulk_add_job_same_collection_error(self, client, sample_collections):
        """Test that adding companies to the same collection returns an error."""
        source_collection, _ = sample_collections
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(source_collection.id),  # Same as source
            "selection_kind": "explicit",
            "selection_data": {"ids": [1, 2, 3]}
        }
        
        response = client.post("/jobs/bulk-add", json=payload)
        
        assert response.status_code == 400
        assert "Cannot add companies to the same collection" in response.json()["detail"]

    def test_create_bulk_add_job_nonexistent_source_collection(self, client, sample_collections):
        """Test error when source collection doesn't exist."""
        _, target_collection = sample_collections
        
        payload = {
            "source_collection_id": "00000000-0000-0000-0000-000000000000",  # Non-existent
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [1, 2, 3]}
        }
        
        response = client.post("/jobs/bulk-add", json=payload)
        
        assert response.status_code == 404
        assert "Source collection" in response.json()["detail"]

    def test_create_bulk_add_job_nonexistent_target_collection(self, client, sample_collections):
        """Test error when target collection doesn't exist."""
        source_collection, _ = sample_collections
        
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": "00000000-0000-0000-0000-000000000000",  # Non-existent
            "selection_kind": "explicit",
            "selection_data": {"ids": [1, 2, 3]}
        }
        
        response = client.post("/jobs/bulk-add", json=payload)
        
        assert response.status_code == 404
        assert "Target collection" in response.json()["detail"]

    def test_get_job_status(self, client, sample_collections, sample_companies):
        """Test getting job status."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        # Create a job first
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [companies[0].id]}
        }
        
        create_response = client.post("/jobs/bulk-add", json=payload)
        job_id = create_response.json()["job_id"]
        
        # Get job status
        response = client.get(f"/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["total_items"] == 1
        assert data["processed_items"] == 0
        assert data["added_items"] == 0
        assert data["skipped_items"] == 0
        assert data["failed_items"] == 0
        assert data["progress_pct"] == 0.0
        assert data["error_message"] is None

    def test_get_job_status_nonexistent(self, client):
        """Test getting status of non-existent job."""
        response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
        assert "Job" in response.json()["detail"]

    def test_cancel_job(self, client, sample_collections, sample_companies):
        """Test cancelling a job."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        # Create a job first
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [companies[0].id]}
        }
        
        create_response = client.post("/jobs/bulk-add", json=payload)
        job_id = create_response.json()["job_id"]
        
        # Cancel the job
        response = client.post(f"/jobs/{job_id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Cancellation requested"
        assert data["job_id"] == job_id

    def test_cancel_job_nonexistent(self, client):
        """Test cancelling non-existent job."""
        response = client.post("/jobs/00000000-0000-0000-0000-000000000000/cancel")
        
        assert response.status_code == 404
        assert "Job" in response.json()["detail"]

    def test_cancel_completed_job(self, client, db_session, sample_collections, sample_companies):
        """Test that completed jobs cannot be cancelled."""
        source_collection, target_collection = sample_collections
        companies = sample_companies
        
        # Create a job first
        payload = {
            "source_collection_id": str(source_collection.id),
            "target_collection_id": str(target_collection.id),
            "selection_kind": "explicit",
            "selection_data": {"ids": [companies[0].id]}
        }
        
        create_response = client.post("/jobs/bulk-add", json=payload)
        job_id = create_response.json()["job_id"]
        
        # Manually mark job as completed
        job = db_session.query(Job).filter(Job.id == job_id).first()
        job.status = JobStatus.COMPLETED
        db_session.commit()
        
        # Try to cancel
        response = client.post(f"/jobs/{job_id}/cancel")
        
        assert response.status_code == 400
        assert "Cannot cancel job in completed status" in response.json()["detail"]

    def test_get_collection_count(self, client, sample_collections, sample_companies):
        """Test getting collection company count."""
        source_collection, _ = sample_collections
        companies = sample_companies  # 10 companies added to source collection
        
        response = client.get(f"/jobs/collections/{source_collection.id}/count")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 10
        assert data["collection_id"] == str(source_collection.id)
        assert data["collection_name"] == "Source Collection"

    def test_get_collection_count_nonexistent(self, client):
        """Test getting count for non-existent collection."""
        response = client.get("/jobs/collections/00000000-0000-0000-0000-000000000000/count")
        
        assert response.status_code == 404
        assert "Collection" in response.json()["detail"]

    def test_get_collection_count_empty_collection(self, client, sample_collections):
        """Test getting count for empty collection."""
        _, target_collection = sample_collections  # Target collection has no companies
        
        response = client.get(f"/jobs/collections/{target_collection.id}/count")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 0
        assert data["collection_id"] == str(target_collection.id)
        assert data["collection_name"] == "Target Collection"
