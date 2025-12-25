from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from .manager import WorkerManager, WorkerCreate, WorkerUpdate, WorkerLogin, WorkerResponse
import logging

router = APIRouter(prefix="/api/workers", tags=["workers"])
worker_manager = WorkerManager()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_worker(worker_data: WorkerCreate):
    """Register a new worker"""
    try:
        result = worker_manager.add_worker(worker_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=dict)
async def login_worker(login_data: WorkerLogin):
    """Login a worker"""
    try:
        worker = worker_manager.authenticate_worker(login_data.email, login_data.password)
        if not worker:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Add token for frontend
        worker['token'] = f"worker-token-{worker['id']}"
        
        # Match frontend expectation
        return {
            "data": worker,  # ✅ Frontend expects response.data
            "success": True,
            "message": "Login successful"
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/", response_model=List[WorkerResponse])
async def get_all_workers(
    available_only: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """Get all workers"""
    try:
        workers = worker_manager.get_all_workers(available_only, limit, offset)
        return workers
    except Exception as e:
        logger.error(f"Get workers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(worker_id: int):
    """Get worker by ID"""
    try:
        worker = worker_manager.get_worker_by_id(worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        return worker
    except Exception as e:
        logger.error(f"Get worker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/by-skills", response_model=List[WorkerResponse])
async def search_workers_by_skills(skills: str, limit: int = 20):
    """Search workers by skills (comma-separated)"""
    try:
        skills_list = [skill.strip() for skill in skills.split(",")]
        workers = worker_manager.get_workers_by_skills(skills_list, limit)
        return workers
    except Exception as e:
        logger.error(f"Search workers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available/{job_type}/{date_time}", response_model=List[WorkerResponse])
async def get_available_workers(job_type: str, date_time: str):
    """Get workers available for a job at specific time"""
    try:
        workers = worker_manager.get_available_workers_for_job(job_type, date_time)
        return workers
    except Exception as e:
        logger.error(f"Get available workers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{worker_id}", response_model=dict)
async def update_worker(worker_id: int, update_data: WorkerUpdate):
    """Update worker information"""
    try:
        result = worker_manager.update_worker(worker_id, update_data)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Update worker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{worker_id}", response_model=dict)
async def delete_worker(worker_id: int):
    """Delete a worker"""
    try:
        result = worker_manager.delete_worker(worker_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Delete worker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/job-history", response_model=List[dict])
async def get_worker_job_history(worker_id: int):
    """Get job history for a worker"""
    try:
        history = worker_manager.get_worker_job_history(worker_id)
        return history
    except Exception as e:
        logger.error(f"Get job history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{worker_id}/job-completed", response_model=dict)
async def add_job_completed(
    worker_id: int,
    job_id: int,
    job_type: str,
    client_id: int,
    earnings: float,
    rating: int = None
):
    """Record a completed job for a worker"""
    try:
        result = worker_manager.add_job_history(worker_id, job_id, job_type, client_id, earnings, rating)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Add job history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{worker_id}/availability", response_model=dict)
async def set_availability(worker_id: int, availability_slots: List[dict]):
    """Set worker availability schedule"""
    try:
        result = worker_manager.set_worker_availability(worker_id, availability_slots)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Set availability error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
