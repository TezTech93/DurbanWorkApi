from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from .manager import JobManager, JobCreate, JobUpdate, JobApplication, JobStatus, JobType
import logging

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
job_manager = JobManager()
logger = logging.getLogger(__name__)

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_job(job_data: JobCreate):
    """Create a new job posting"""
    try:
        result = job_manager.create_job(job_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Create job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[dict])
async def get_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    client_id: Optional[int] = None,
    urgent: Optional[bool] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get jobs with filters"""
    try:
        filters = {}
        if status: filters['status'] = status.value
        if job_type: filters['job_type'] = job_type.value
        if client_id: filters['client_id'] = client_id
        if urgent is not None: filters['urgent'] = urgent
        if min_budget: filters['min_budget'] = min_budget
        if max_budget: filters['max_budget'] = max_budget
        
        jobs = job_manager.get_jobs(filters, limit, offset)
        return jobs
    except Exception as e:
        logger.error(f"Get jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available", response_model=List[dict])
async def get_available_jobs(
    worker_id: Optional[int] = None,
    limit: int = 20
):
    """Get jobs available for workers to apply"""
    try:
        jobs = job_manager.get_available_jobs(worker_id, limit)
        return jobs
    except Exception as e:
        logger.error(f"Get available jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}", response_model=dict)
async def get_job(job_id: int):
    """Get job by ID"""
    try:
        job = job_manager.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except Exception as e:
        logger.error(f"Get job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply", response_model=dict)
async def apply_for_job(application: JobApplication):
    """Worker applies for a job"""
    try:
        result = job_manager.apply_for_job(application)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Apply for job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/applications", response_model=List[dict])
async def get_job_applications(job_id: int):
    """Get all applications for a job"""
    try:
        applications = job_manager.get_job_applications(job_id)
        return applications
    except Exception as e:
        logger.error(f"Get job applications error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/accept/{worker_id}", response_model=dict)
async def accept_worker_for_job(job_id: int, worker_id: int, client_id: int):
    """Client accepts a worker for a job"""
    try:
        result = job_manager.accept_worker(job_id, worker_id, client_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Accept worker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/worker-accept", response_model=dict)
async def worker_accept_job(job_id: int, worker_id: int):
    """Worker accepts an assigned job"""
    try:
        result = job_manager.worker_accept_job(job_id, worker_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Worker accept job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/worker-reject", response_model=dict)
async def worker_reject_job(job_id: int, worker_id: int):
    """Worker rejects an assigned job"""
    try:
        result = job_manager.worker_reject_job(job_id, worker_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Worker reject job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/complete", response_model=dict)
async def complete_job(
    job_id: int, 
    client_id: int,
    actual_hours: float,
    final_payment: float
):
    """Mark job as completed"""
    try:
        result = job_manager.complete_job(job_id, client_id, actual_hours, final_payment)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Complete job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/{user_id}/{user_type}", response_model=List[dict])
async def get_user_notifications(
    user_id: int,
    user_type: str,
    unread_only: bool = False,
    limit: int = 20
):
    """Get notifications for user"""
    try:
        notifications = job_manager.get_notifications(user_id, user_type, unread_only, limit)
        return notifications
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(notification_id: int, user_id: int):
    """Mark notification as read"""
    try:
        result = job_manager.mark_notification_read(notification_id, user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))