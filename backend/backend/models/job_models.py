from pydantic import BaseModel, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid
from backend.db.database import JobStatus, SelectionKind


class ExplicitSelectionData(BaseModel):
    """Selection data for explicit company ID selection."""
    ids: List[int]  # Company IDs must be integers


class AllMatchingSelectionData(BaseModel):
    """Selection data for all matching companies selection."""
    filter: Optional[Dict[str, Any]] = None  # Future: filter criteria
    total_at_snapshot: Optional[int] = None  # Snapshot count


class BulkAddRequest(BaseModel):
    source_collection_id: str  # UUID as string
    target_collection_id: str  # UUID as string
    selection_kind: SelectionKind
    selection_data: Union[ExplicitSelectionData, AllMatchingSelectionData]
    client_idempotency_key: Optional[str] = None
    
    @field_validator('source_collection_id', 'target_collection_id')
    @classmethod
    def validate_uuid_strings(cls, v):
        """Validate that collection IDs are valid UUIDs."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")
    
    @field_validator('selection_data', mode='before')
    @classmethod
    def validate_selection_data(cls, v, info):
        """Validate selection_data matches selection_kind."""
        # Access other field values through info.data
        values = info.data if hasattr(info, 'data') else {}
        selection_kind = values.get('selection_kind')
        
        if selection_kind == SelectionKind.EXPLICIT:
            if isinstance(v, dict) and 'ids' in v:
                # Validate that all IDs are integers
                ids = v['ids']
                if not all(isinstance(id_val, int) for id_val in ids):
                    raise ValueError("Company IDs must be integers, not strings or UUIDs")
                return ExplicitSelectionData(**v)
            raise ValueError("selection_data must contain 'ids' array for explicit selection")
        
        elif selection_kind == SelectionKind.ALL_MATCHING:
            if isinstance(v, dict):
                return AllMatchingSelectionData(**v)
            raise ValueError("selection_data must be valid for all_matching selection")
        
        return v


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    job_id: str
    status: JobStatus
    estimated_total: Optional[int] = None
    created_at: datetime


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    job_id: str
    status: JobStatus
    total_items: int
    processed_items: int
    added_items: int
    skipped_items: int
    failed_items: int
    progress_pct: float
    error_message: Optional[str] = None


class CollectionCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    count: int
    collection_id: str
    collection_name: str
