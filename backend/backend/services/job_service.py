import hashlib
import json
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from backend.db.database import Job, JobStatus, SelectionKind
from backend.models.job_models import BulkAddRequest


def generate_idempotency_key(
    source_collection_id: str,
    target_collection_id: str,
    selection_kind: SelectionKind,
    selection_data: Dict[str, Any],
    user_id: Optional[str] = "default"  # TODO: Add proper user auth later
) -> str:
    """Generate a deterministic idempotency key for bulk add operations."""
    key_data = {
        "source": source_collection_id,
        "target": target_collection_id,
        "kind": selection_kind.value,
        "data": selection_data,
        "user": user_id
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()


def create_bulk_add_job(
    db: Session,
    request: BulkAddRequest,
    user_id: Optional[str] = "default"
) -> Job:
    """Create a new bulk add job or return existing if idempotency key matches."""
    
    # Generate idempotency key
    idempotency_key = request.client_idempotency_key or generate_idempotency_key(
        request.source_collection_id,
        request.target_collection_id,
        request.selection_kind,
        request.selection_data.model_dump(),
        user_id
    )
    
    # Check for existing job - return it regardless of status to maintain idempotency
    existing_job = db.query(Job).filter_by(idempotency_key=idempotency_key).first()
    if existing_job:
        # If job is still active, return it
        if existing_job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            return existing_job
        
        # If job is completed, return it (idempotent - operation already succeeded)
        if existing_job.status == JobStatus.COMPLETED:
            return existing_job
            
        # If job failed or was cancelled, reset it for retry
        if existing_job.status in [JobStatus.FAILED, JobStatus.CANCELLED]:
            # Reset job for retry
            existing_job.status = JobStatus.PENDING
            existing_job.cancel_requested = False
            existing_job.processed_items = 0
            existing_job.added_items = 0
            existing_job.skipped_items = 0
            existing_job.failed_items = 0
            existing_job.started_at = None
            existing_job.completed_at = None
            existing_job.error_message = None
            
            # Update total_items estimate if provided
            if request.selection_kind == SelectionKind.EXPLICIT:
                existing_job.total_items = len(request.selection_data.ids)
            else:
                existing_job.total_items = request.selection_data.total_at_snapshot or 0
            
            db.commit()
            db.refresh(existing_job)
            return existing_job
    
    # Estimate total items
    if request.selection_kind == SelectionKind.EXPLICIT:
        total_items = len(request.selection_data.ids)
    else:
        # For ALL_MATCHING, use provided snapshot count or estimate 0
        # The actual count will be calculated when job processing starts
        total_items = request.selection_data.total_at_snapshot or 0
    
    # Create new job
    job = Job(
        id=str(uuid.uuid4()),
        job_type="bulk_add_companies",
        idempotency_key=idempotency_key,
        selection_kind=request.selection_kind,
        selection_snapshot=request.selection_data.model_dump(),
        source_collection_id=uuid.UUID(request.source_collection_id),
        target_collection_id=uuid.UUID(request.target_collection_id),
        total_items=total_items,
        status=JobStatus.PENDING
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return job


def get_job_by_id(db: Session, job_id: str) -> Optional[Job]:
    """Get job by ID."""
    return db.query(Job).filter(Job.id == job_id).first()


def update_job_progress(
    db: Session,
    job_id: str,
    processed: int,
    added: int,
    skipped: int,
    failed: int
) -> None:
    """Update job progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.processed_items = processed
        job.added_items = added
        job.skipped_items = skipped
        job.failed_items = failed
        db.commit()


def mark_job_status(db: Session, job_id: str, status: JobStatus, error_message: Optional[str] = None) -> None:
    """Update job status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = status
        if status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()
        if error_message:
            job.error_message = error_message
        db.commit()


def calculate_progress_percentage(job: Job) -> float:
    """Calculate progress percentage for a job."""
    if job.total_items == 0:
        return 0.0
    return (job.processed_items / job.total_items) * 100.0


def get_collection_company_count(db: Session, collection_id: str) -> int:
    """Get count of companies in a collection."""
    from backend.db.database import CompanyCollectionAssociation
    
    return db.query(CompanyCollectionAssociation).filter(
        CompanyCollectionAssociation.collection_id == uuid.UUID(collection_id)
    ).count()
