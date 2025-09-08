from sqlalchemy.orm import Session
from typing import List
import time

from backend.db.database import (
    get_db, 
    Job, 
    JobStatus, 
    SelectionKind, 
    Company, 
    CompanyCollectionAssociation
)
from backend.services.job_service import mark_job_status, update_job_progress


def process_bulk_add_job(job_id: str):
    """
    Process a bulk add job synchronously.
    Simple approach: no workers, no leasing, just process the job.
    """
    db = next(get_db())
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        
        # Check if already processing or completed
        if job.status != JobStatus.PENDING:
            return
        
        # Mark as processing
        mark_job_status(db, job_id, JobStatus.PROCESSING)
        
        # Get companies to process
        companies = get_companies_for_job(db, job)
        job.total_items = len(companies)
        db.commit()
        
        # If no companies found, complete the job immediately
        if not companies:
            update_job_progress(db, job_id, 0, 0, 0, 0)
            mark_job_status(db, job_id, JobStatus.COMPLETED)
            return
        
        # Process companies in batches
        processed = 0
        added = 0
        skipped = 0
        failed = 0
        
        for i, company in enumerate(companies):
            # Check for cancellation
            db.refresh(job)
            if job.cancel_requested:
                mark_job_status(db, job_id, JobStatus.CANCELLED)
                return
            
            try:
                # Add company to target collection
                existing = db.query(CompanyCollectionAssociation).filter(
                    CompanyCollectionAssociation.company_id == company.id,
                    CompanyCollectionAssociation.collection_id == job.target_collection_id
                ).first()
                
                if existing:
                    skipped += 1
                else:
                    association = CompanyCollectionAssociation(
                        company_id=company.id,
                        collection_id=job.target_collection_id
                    )
                    db.add(association)
                    db.commit()
                    added += 1
                    
                    # Respect database throttling (100ms per insert)
                    time.sleep(0.1)
                
            except Exception as e:
                failed += 1
                print(f"Failed to add company {company.id}: {e}")
            
            processed += 1
            
            # Update progress every 10 companies
            if processed % 10 == 0:
                update_job_progress(db, job_id, processed, added, skipped, failed)
        
        # Final progress update
        update_job_progress(db, job_id, processed, added, skipped, failed)
        mark_job_status(db, job_id, JobStatus.COMPLETED)
        
    except Exception as e:
        mark_job_status(db, job_id, JobStatus.FAILED, str(e))
    finally:
        db.close()


def get_companies_for_job(db: Session, job: Job) -> List[Company]:
    """Get the list of companies to process for a job."""
    
    if job.selection_kind == SelectionKind.EXPLICIT:
        # Get specific companies by IDs
        company_ids = job.selection_snapshot.get("ids", [])
        return db.query(Company).filter(Company.id.in_(company_ids)).all()
    
    else:  # ALL_MATCHING
        # For now, get all companies from the source collection
        # In a real implementation, we'd apply the filter from selection_snapshot
        company_associations = db.query(CompanyCollectionAssociation).filter(
            CompanyCollectionAssociation.collection_id == job.source_collection_id
        ).all()
        
        company_ids = [assoc.company_id for assoc in company_associations]
        return db.query(Company).filter(Company.id.in_(company_ids)).all()
