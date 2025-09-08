from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from backend.db.database import get_db, Job, JobStatus, CompanyCollection
from backend.models.job_models import (
    BulkAddRequest, 
    JobResponse, 
    JobStatusResponse,
    CollectionCountResponse
)
from backend.services.job_service import (
    create_bulk_add_job,
    get_job_by_id,
    mark_job_status,
    calculate_progress_percentage,
    get_collection_company_count
)
from backend.services.simple_processor import process_bulk_add_job

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


@router.post("/bulk-add", response_model=JobResponse)
def create_bulk_add_operation(
    request: BulkAddRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a bulk add operation to move companies between collections."""
    
    # Validate collections exist
    source_collection = db.query(CompanyCollection).filter(
        CompanyCollection.id == uuid.UUID(request.source_collection_id)
    ).first()
    if not source_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source collection {request.source_collection_id} not found"
        )
    
    target_collection = db.query(CompanyCollection).filter(
        CompanyCollection.id == uuid.UUID(request.target_collection_id)
    ).first()
    if not target_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target collection {request.target_collection_id} not found"
        )
    
    # Prevent adding to same collection
    if request.source_collection_id == request.target_collection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add companies to the same collection"
        )
    
    # Create or get existing job
    job = create_bulk_add_job(db, request)
    
    # Decide processing strategy based on estimated size
    if job.total_items <= 50:
        # Process immediately (small operations)
        process_bulk_add_job(job.id)
    else:
        # Process in background (large operations)
        background_tasks.add_task(process_bulk_add_job, job.id)
    
    return JobResponse(
        job_id=job.id,
        status=job.status,
        estimated_total=job.total_items,
        created_at=job.created_at
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed status of a job."""
    
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    progress_pct = calculate_progress_percentage(job)
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        added_items=job.added_items,
        skipped_items=job.skipped_items,
        failed_items=job.failed_items,
        progress_pct=progress_pct,
        error_message=job.error_message
    )


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Request cancellation of a job."""
    
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status"
        )
    
    job.cancel_requested = True
    db.commit()
    
    return {"message": "Cancellation requested", "job_id": job_id}


@router.get("/collections/{collection_id}/count", response_model=CollectionCountResponse)
def get_collection_count(
    collection_id: str,
    db: Session = Depends(get_db)
):
    """Get count of companies in a collection for preflight confirmation."""
    
    collection = db.query(CompanyCollection).filter(
        CompanyCollection.id == uuid.UUID(collection_id)
    ).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found"
        )
    
    count = get_collection_company_count(db, collection_id)
    
    return CollectionCountResponse(
        count=count,
        collection_id=str(collection.id),
        collection_name=collection.collection_name
    )
