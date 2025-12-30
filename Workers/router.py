from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
import shutil
import os
import json
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
        
        # Get the worker data
        worker = result["worker"]
        
        # Add token to worker data (NOT in a nested "data" field)
        worker["token"] = f"worker-token-{worker['id']}"
        
        # Return worker data directly (not nested inside "data")
        return {
            **worker,  # Spread worker data at root level
            "success": True,
            "message": result.get("message", "Worker registered successfully")
        }
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
        
        # Add token directly to worker object
        worker['token'] = f"worker-token-{worker['id']}"
        
        # Return worker data at root level with success flags
        return {
            **worker,
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
        
        # Get the updated worker data
        worker = result.get("worker", {})
        
        # Return worker data at root level with success flags
        return {
            **worker,
            "success": True,
            "message": result.get("message", "Worker updated successfully")
        }
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
    rating: Optional[int] = None
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

@router.post("/{worker_id}/upload-resume", response_model=dict)
async def upload_resume(
    worker_id: int,
    file: UploadFile = File(...)
):
    """Upload resume for worker"""
    try:
        # Save file
        file_location = f"uploads/resumes/{worker_id}_{file.filename}"
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update worker record
        update_data = WorkerUpdate(resume_url=f"/{file_location}")
        result = worker_manager.update_worker(worker_id, update_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Add to documents table
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO worker_documents (worker_id, document_type, document_url)
            VALUES (?, ?, ?)
        ''', (worker_id, 'resume', file_location))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Resume uploaded successfully",
            "file_url": file_location
        }
    except Exception as e:
        logger.error(f"Resume upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{worker_id}/complete-onboarding", response_model=dict)
async def complete_onboarding(
    worker_id: int,
    onboarding_data: dict
):
    """Complete worker onboarding"""
    try:
        # Prepare update data
        update_data = WorkerUpdate(
            onboarding_completed=True,
            payment_type=onboarding_data.get('payment_type'),
            business_info=onboarding_data.get('business_info'),
            bank_info=onboarding_data.get('bank_info'),
            employee_details=onboarding_data.get('employee_details'),
            tax_status=onboarding_data.get('tax_status', 'standard'),
            id_verified=onboarding_data.get('id_verified', False),
            background_check_passed=onboarding_data.get('background_check_passed', False),
            verification_status="verified" if onboarding_data.get('id_verified', False) else "pending"
        )
        
        result = worker_manager.update_worker(worker_id, update_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get updated worker
        updated_worker = result.get("worker", {})
        
        # Return worker data at root level
        return {
            **updated_worker,
            "success": True,
            "message": "Onboarding completed successfully"
        }
    except Exception as e:
        logger.error(f"Onboarding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/documents", response_model=List[dict])
async def get_worker_documents(worker_id: int):
    """Get worker documents"""
    try:
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT * FROM worker_documents 
            WHERE worker_id = ? 
            ORDER BY uploaded_at DESC
        ''', (worker_id,))
        
        documents = []
        for row in cur.fetchall():
            documents.append(dict(row))
        
        conn.close()
        return documents
    except Exception as e:
        logger.error(f"Get documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{worker_id}/verify-background", response_model=dict)
async def verify_background_check(worker_id: int):
    """Mark background check as verified"""
    try:
        update_data = WorkerUpdate(
            background_check_passed=True,
            verification_status="verified"
        )
        result = worker_manager.update_worker(worker_id, update_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "message": "Background check verified"
        }
    except Exception as e:
        logger.error(f"Background check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/stats", response_model=dict)
async def get_worker_stats(worker_id: int):
    """Get worker statistics"""
    try:
        worker = worker_manager.get_worker_by_id(worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        
        # Get job stats
        cur.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_jobs,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_jobs,
                SUM(earnings) as total_earnings
            FROM worker_job_history 
            WHERE worker_id = ?
        ''', (worker_id,))
        
        job_stats = cur.fetchone()
        
        # Get rating stats
        cur.execute('''
            SELECT 
                AVG(rating) as avg_rating,
                COUNT(rating) as total_ratings
            FROM worker_job_history 
            WHERE worker_id = ? AND rating IS NOT NULL
        ''', (worker_id,))
        
        rating_stats = cur.fetchone()
        
        conn.close()
        
        return {
            "job_stats": {
                "completed_jobs": job_stats[0] if job_stats and job_stats[0] else 0,
                "pending_jobs": job_stats[1] if job_stats and job_stats[1] else 0,
                "active_jobs": job_stats[2] if job_stats and job_stats[2] else 0,
                "total_earnings": float(job_stats[3]) if job_stats and job_stats[3] else 0.0
            },
            "rating_stats": {
                "avg_rating": round(float(rating_stats[0] or 0), 1) if rating_stats else 0.0,
                "total_ratings": rating_stats[1] if rating_stats and rating_stats[1] else 0
            },
            "verification": {
                "background_check_passed": worker.get('background_check_passed', False),
                "id_verified": worker.get('id_verified', False),
                "verification_status": worker.get('verification_status', 'pending')
            }
        }
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/notifications", response_model=List[dict])
async def get_worker_notifications(worker_id: int, unread_only: bool = False):
    """Get worker notifications"""
    try:
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        
        if unread_only:
            cur.execute('''
                SELECT * FROM worker_notifications 
                WHERE worker_id = ? AND read = FALSE
                ORDER BY created_at DESC
            ''', (worker_id,))
        else:
            cur.execute('''
                SELECT * FROM worker_notifications 
                WHERE worker_id = ?
                ORDER BY created_at DESC
            ''', (worker_id,))
        
        notifications = []
        for row in cur.fetchall():
            notification = dict(row)
            if notification.get('data_json'):
                try:
                    notification['data'] = json.loads(notification['data_json'])
                except:
                    notification['data'] = {}
                del notification['data_json']
            notifications.append(notification)
        
        conn.close()
        return notifications
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{worker_id}/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(worker_id: int, notification_id: int):
    """Mark notification as read"""
    try:
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            UPDATE worker_notifications 
            SET read = TRUE 
            WHERE id = ? AND worker_id = ?
        ''', (notification_id, worker_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Notification marked as read"}
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/earnings", response_model=List[dict])
async def get_worker_earnings(worker_id: int, limit: int = 50, offset: int = 0):
    """Get worker earnings history"""
    try:
        conn = worker_manager.get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT * FROM worker_earnings 
            WHERE worker_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (worker_id, limit, offset))
        
        earnings = []
        for row in cur.fetchall():
            earnings.append(dict(row))
        
        conn.close()
        return earnings
    except Exception as e:
        logger.error(f"Get earnings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{worker_id}/dashboard", response_model=dict)
async def get_worker_dashboard(worker_id: int):
    """Get dashboard data for worker"""
    try:
        # Get worker info
        worker = worker_manager.get_worker_by_id(worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        # Get stats
        stats_response = await get_worker_stats(worker_id)
        
        # Get recent jobs
        history = worker_manager.get_worker_job_history(worker_id)
        recent_jobs = history[:5] if history else []
        
        # Get notifications
        notifications = await get_worker_notifications(worker_id, unread_only=True)
        
        return {
            **worker,
            "stats": stats_response,
            "recent_jobs": recent_jobs,
            "unread_notifications": len(notifications),
            "quick_stats": {
                "response_rate": worker.get('response_rate', 95),
                "acceptance_rate": worker.get('acceptance_rate', 88),
                "avg_response_time": worker.get('avg_response_time', '15 min'),
                "reliability_score": worker.get('reliability_score', 4.8)
            },
            "success": True,
            "message": "Dashboard data retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Get dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))