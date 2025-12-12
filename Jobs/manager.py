import sqlite3
import json
import datetime as dt
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, validator
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Enums
class JobStatus(str, Enum):
    POSTED = "posted"          # Job created, waiting for workers
    PENDING = "pending"        # Worker applied, waiting for client approval
    ASSIGNED = "assigned"      # Worker assigned, not started
    IN_PROGRESS = "in_progress" # Job in progress
    COMPLETED = "completed"    # Job completed
    CANCELLED = "cancelled"    # Job cancelled
    EXPIRED = "expired"        # Job expired without assignment

class JobType(str, Enum):
    MOVING = "moving"
    LANDSCAPING = "landscaping"
    HEAVY_LIFTING = "heavy_lifting"
    CLEANING = "cleaning"
    ASSEMBLY = "assembly"
    DELIVERY = "delivery"
    GENERAL = "general"

# Data Models
class JobLocation(BaseModel):
    address: str
    city: str = "Durban"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None

class JobCreate(BaseModel):
    client_id: int
    title: str
    description: str
    job_type: JobType
    location: JobLocation
    scheduled_date: str  # ISO format datetime
    estimated_hours: int
    budget: float
    required_workers: int = 1
    urgent: bool = False
    special_requirements: Optional[str] = None
    
    @validator('budget')
    def budget_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Budget must be positive')
        return v
    
    @validator('required_workers')
    def workers_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Required workers must be positive')
        return v

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_hours: Optional[int] = None
    budget: Optional[float] = None
    status: Optional[JobStatus] = None
    special_requirements: Optional[str] = None

class JobApplication(BaseModel):
    worker_id: int
    job_id: int
    proposed_rate: Optional[float] = None
    message: Optional[str] = None
    estimated_completion_time: Optional[int] = None  # In hours

class NotificationType(str, Enum):
    JOB_POSTED = "job_posted"
    JOB_APPLIED = "job_applied"
    JOB_ASSIGNED = "job_assigned"
    JOB_COMPLETED = "job_completed"
    JOB_CANCELLED = "job_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    REVIEW_RECEIVED = "review_received"

class JobManager:
    def __init__(self, db_name: str = 'durban_works.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database with jobs and related tables"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Create jobs table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    location_json TEXT NOT NULL,
                    scheduled_date TIMESTAMP NOT NULL,
                    estimated_hours INTEGER NOT NULL,
                    budget REAL NOT NULL,
                    required_workers INTEGER DEFAULT 1,
                    assigned_workers INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'posted',
                    urgent BOOLEAN DEFAULT FALSE,
                    special_requirements TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            ''')
            
            # Create job applications table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    proposed_rate REAL,
                    message TEXT,
                    estimated_completion_time INTEGER,
                    status TEXT DEFAULT 'pending',  -- pending, accepted, rejected
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id),
                    FOREIGN KEY (worker_id) REFERENCES workers (id),
                    UNIQUE(job_id, worker_id)
                )
            ''')
            
            # Create job assignments table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS job_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    assigned_by INTEGER,  -- client_id who assigned
                    accepted_by_worker BOOLEAN DEFAULT FALSE,
                    worker_accepted_at TIMESTAMP,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    actual_hours REAL,
                    final_payment REAL,
                    worker_rating INTEGER CHECK(worker_rating >= 1 AND worker_rating <= 5),
                    client_rating INTEGER CHECK(client_rating >= 1 AND client_rating <= 5),
                    completed_at TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id),
                    FOREIGN KEY (worker_id) REFERENCES workers (id),
                    FOREIGN KEY (assigned_by) REFERENCES clients (id)
                )
            ''')
            
            # Create notifications table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_type TEXT NOT NULL,  -- 'worker' or 'client'
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    related_id INTEGER,  -- job_id, application_id, etc.
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP
                )
            ''')
            
            # Create job reviews table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS job_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL,
                    reviewer_type TEXT NOT NULL,  -- 'client' or 'worker'
                    reviewed_id INTEGER NOT NULL,  -- worker_id if client reviewing, client_id if worker reviewing
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            ''')
            
            # Create indexes
            cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_client ON jobs(client_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_applications_job ON job_applications(job_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_applications_worker ON job_applications(worker_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, user_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)')
            
            conn.commit()
            logger.info("Jobs database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Jobs database initialization error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_job(self, job_data: JobCreate) -> Dict:
        """Create a new job posting"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Verify client exists
            cur.execute("SELECT id FROM clients WHERE id = ?", (job_data.client_id,))
            if not cur.fetchone():
                return {"error": "Client not found"}
            
            # Convert location to JSON
            location_json = json.dumps(job_data.location.dict())
            
            # Insert job
            cur.execute('''
                INSERT INTO jobs (
                    client_id, title, description, job_type, location_json,
                    scheduled_date, estimated_hours, budget, required_workers,
                    urgent, special_requirements
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.client_id, job_data.title, job_data.description,
                job_data.job_type.value, location_json, job_data.scheduled_date,
                job_data.estimated_hours, job_data.budget, job_data.required_workers,
                job_data.urgent, job_data.special_requirements
            ))
            
            job_id = cur.lastrowid
            
            # Update client's job count
            cur.execute('''
                UPDATE clients 
                SET total_jobs_posted = total_jobs_posted + 1,
                    active_jobs = active_jobs + 1
                WHERE id = ?
            ''', (job_data.client_id,))
            
            # Create notification for relevant workers
            self._notify_workers_for_job(job_id, job_data.job_type.value, cur)
            
            conn.commit()
            
            # Get the created job
            job = self.get_job_by_id(job_id)
            
            logger.info(f"Job created successfully: {job_data.title}")
            return {"success": True, "job": job, "message": "Job posted successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error creating job: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def _notify_workers_for_job(self, job_id: int, job_type: str, cursor):
        """Notify relevant workers about new job"""
        try:
            # Find workers with matching skills
            cursor.execute('''
                SELECT id, fname, lname FROM workers 
                WHERE available = TRUE 
                AND json_array_length(skills_json) > 0
                AND EXISTS (
                    SELECT 1 FROM json_each(skills_json) 
                    WHERE json_each.value LIKE ? || '%'
                )
            ''', (job_type,))
            
            workers = cursor.fetchall()
            
            # Create notifications
            for worker in workers:
                cursor.execute('''
                    INSERT INTO notifications 
                    (user_id, user_type, type, title, message, related_id)
                    VALUES (?, 'worker', 'job_posted', ?, ?, ?)
                ''', (
                    worker['id'],
                    "New Job Available",
                    f"A new {job_type} job has been posted that matches your skills",
                    job_id
                ))
            
            logger.info(f"Notified {len(workers)} workers about job {job_id}")
            
        except Exception as e:
            logger.error(f"Error notifying workers: {e}")
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get job by ID"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting job by ID: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_jobs(self, filters: Dict = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get jobs with optional filters"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if filters:
                if filters.get('status'):
                    query += " AND status = ?"
                    params.append(filters['status'])
                
                if filters.get('job_type'):
                    query += " AND job_type = ?"
                    params.append(filters['job_type'])
                
                if filters.get('client_id'):
                    query += " AND client_id = ?"
                    params.append(filters['client_id'])
                
                if filters.get('urgent'):
                    query += " AND urgent = ?"
                    params.append(filters['urgent'])
                
                if filters.get('min_budget'):
                    query += " AND budget >= ?"
                    params.append(filters['min_budget'])
                
                if filters.get('max_budget'):
                    query += " AND budget <= ?"
                    params.append(filters['max_budget'])
            
            query += " ORDER BY scheduled_date ASC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            
            jobs = []
            for row in cur.fetchall():
                jobs.append(self._row_to_dict(row))
            
            return jobs
            
        except sqlite3.Error as e:
            logger.error(f"Error getting jobs: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_available_jobs(self, worker_id: Optional[int] = None, limit: int = 20) -> List[Dict]:
        """Get jobs available for workers to apply"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = '''
                SELECT j.* FROM jobs j
                WHERE j.status = 'posted'
                AND j.scheduled_date > datetime('now')
                AND j.assigned_workers < j.required_workers
            '''
            params = []
            
            if worker_id:
                # Exclude jobs the worker has already applied to
                query += '''
                    AND NOT EXISTS (
                        SELECT 1 FROM job_applications ja
                        WHERE ja.job_id = j.id AND ja.worker_id = ?
                    )
                '''
                params.append(worker_id)
            
            query += " ORDER BY j.urgent DESC, j.created_at DESC LIMIT ?"
            params.append(limit)
            
            cur.execute(query, params)
            
            jobs = []
            for row in cur.fetchall():
                jobs.append(self._row_to_dict(row))
            
            return jobs
            
        except sqlite3.Error as e:
            logger.error(f"Error getting available jobs: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def apply_for_job(self, application_data: JobApplication) -> Dict:
        """Worker applies for a job"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if job exists and is available
            cur.execute("SELECT * FROM jobs WHERE id = ? AND status = 'posted'", (application_data.job_id,))
            job_row = cur.fetchone()
            if not job_row:
                return {"error": "Job not found or not available"}
            
            job = dict(job_row)
            
            # Check if worker exists
            cur.execute("SELECT id FROM workers WHERE id = ?", (application_data.worker_id,))
            if not cur.fetchone():
                return {"error": "Worker not found"}
            
            # Check if already applied
            cur.execute('''
                SELECT id FROM job_applications 
                WHERE job_id = ? AND worker_id = ?
            ''', (application_data.job_id, application_data.worker_id))
            
            if cur.fetchone():
                return {"error": "Already applied for this job"}
            
            # Create application
            cur.execute('''
                INSERT INTO job_applications 
                (job_id, worker_id, proposed_rate, message, estimated_completion_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                application_data.job_id, application_data.worker_id,
                application_data.proposed_rate, application_data.message,
                application_data.estimated_completion_time
            ))
            
            application_id = cur.lastrowid
            
            # Create notification for client
            cur.execute('''
                SELECT fname, lname FROM workers WHERE id = ?
            ''', (application_data.worker_id,))
            worker = cur.fetchone()
            
            cur.execute('''
                INSERT INTO notifications 
                (user_id, user_type, type, title, message, related_id)
                VALUES (?, 'client', 'job_applied', ?, ?, ?)
            ''', (
                job['client_id'],
                "New Job Application",
                f"{worker['fname']} {worker['lname']} applied for your job '{job['title']}'",
                application_data.job_id
            ))
            
            conn.commit()
            
            logger.info(f"Worker {application_data.worker_id} applied for job {application_data.job_id}")
            return {"success": True, "application_id": application_id, "message": "Application submitted"}
            
        except sqlite3.Error as e:
            logger.error(f"Error applying for job: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_job_applications(self, job_id: int) -> List[Dict]:
        """Get all applications for a job"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT ja.*, w.fname, w.lname, w.rating, w.total_jobs_done
                FROM job_applications ja
                JOIN workers w ON ja.worker_id = w.id
                WHERE ja.job_id = ?
                ORDER BY ja.applied_at DESC
            ''', (job_id,))
            
            applications = []
            for row in cur.fetchall():
                applications.append(dict(row))
            
            return applications
            
        except sqlite3.Error as e:
            logger.error(f"Error getting job applications: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def accept_worker(self, job_id: int, worker_id: int, client_id: int) -> Dict:
        """Client accepts a worker for a job"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if client owns the job
            cur.execute("SELECT client_id FROM jobs WHERE id = ?", (job_id,))
            job_row = cur.fetchone()
            if not job_row or job_row['client_id'] != client_id:
                return {"error": "Unauthorized or job not found"}
            
            # Check if worker applied
            cur.execute('''
                SELECT id FROM job_applications 
                WHERE job_id = ? AND worker_id = ? AND status = 'pending'
            ''', (job_id, worker_id))
            
            if not cur.fetchone():
                return {"error": "Worker hasn't applied or already processed"}
            
            # Update application status
            cur.execute('''
                UPDATE job_applications 
                SET status = 'accepted', responded_at = CURRENT_TIMESTAMP
                WHERE job_id = ? AND worker_id = ?
            ''', (job_id, worker_id))
            
            # Reject other applications
            cur.execute('''
                UPDATE job_applications 
                SET status = 'rejected', responded_at = CURRENT_TIMESTAMP
                WHERE job_id = ? AND worker_id != ? AND status = 'pending'
            ''', (job_id, worker_id))
            
            # Create job assignment
            cur.execute('''
                INSERT INTO job_assignments (job_id, worker_id, assigned_by)
                VALUES (?, ?, ?)
            ''', (job_id, worker_id, client_id))
            
            # Update job status and assigned workers count
            cur.execute('''
                UPDATE jobs 
                SET status = 'assigned', 
                    assigned_workers = assigned_workers + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (job_id,))
            
            # Update client active jobs
            cur.execute('''
                UPDATE clients 
                SET active_jobs = (
                    SELECT COUNT(*) FROM jobs 
                    WHERE client_id = ? AND status IN ('posted', 'assigned', 'in_progress')
                )
                WHERE id = ?
            ''', (client_id, client_id))
            
            # Create notification for worker
            cur.execute('''
                INSERT INTO notifications 
                (user_id, user_type, type, title, message, related_id)
                VALUES (?, 'worker', 'job_assigned', ?, ?, ?)
            ''', (
                worker_id,
                "Job Assignment",
                f"You've been assigned to a job! Check your assignments.",
                job_id
            ))
            
            conn.commit()
            
            logger.info(f"Worker {worker_id} accepted for job {job_id}")
            return {"success": True, "message": "Worker accepted for job"}
            
        except sqlite3.Error as e:
            logger.error(f"Error accepting worker: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def worker_accept_job(self, job_id: int, worker_id: int) -> Dict:
        """Worker accepts an assigned job"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if worker is assigned to this job
            cur.execute('''
                SELECT id FROM job_assignments 
                WHERE job_id = ? AND worker_id = ? AND accepted_by_worker = FALSE
            ''', (job_id, worker_id))
            
            if not cur.fetchone():
                return {"error": "Job assignment not found or already accepted"}
            
            # Update assignment
            cur.execute('''
                UPDATE job_assignments 
                SET accepted_by_worker = TRUE, 
                    worker_accepted_at = CURRENT_TIMESTAMP,
                    start_time = CURRENT_TIMESTAMP
                WHERE job_id = ? AND worker_id = ?
            ''', (job_id, worker_id))
            
            # Update job status if all assigned workers have accepted
            cur.execute('''
                UPDATE jobs 
                SET status = 'in_progress',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'assigned'
            ''', (job_id,))
            
            # Create notification for client
            cur.execute('''
                SELECT client_id, title FROM jobs WHERE id = ?
            ''', (job_id,))
            job = cur.fetchone()
            
            cur.execute('''
                SELECT fname, lname FROM workers WHERE id = ?
            ''', (worker_id,))
            worker = cur.fetchone()
            
            if job and worker:
                cur.execute('''
                    INSERT INTO notifications 
                    (user_id, user_type, type, title, message, related_id)
                    VALUES (?, 'client', 'job_assigned', ?, ?, ?)
                ''', (
                    job['client_id'],
                    "Worker Accepted Job",
                    f"{worker['fname']} {worker['lname']} has accepted your job '{job['title']}'",
                    job_id
                ))
            
            conn.commit()
            
            logger.info(f"Worker {worker_id} accepted job {job_id}")
            return {"success": True, "message": "Job accepted successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error worker accepting job: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def worker_reject_job(self, job_id: int, worker_id: int) -> Dict:
        """Worker rejects an assigned job"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if worker is assigned to this job
            cur.execute('''
                SELECT id FROM job_assignments 
                WHERE job_id = ? AND worker_id = ?
            ''', (job_id, worker_id))
            
            if not cur.fetchone():
                return {"error": "Job assignment not found"}
            
            # Remove assignment
            cur.execute('''
                DELETE FROM job_assignments 
                WHERE job_id = ? AND worker_id = ?
            ''', (job_id, worker_id))
            
            # Update job assigned workers count
            cur.execute('''
                UPDATE jobs 
                SET assigned_workers = assigned_workers - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (job_id,))
            
            # Update job status back to posted if no assigned workers
            cur.execute('''
                UPDATE jobs 
                SET status = 'posted'
                WHERE id = ? AND assigned_workers = 0
            ''', (job_id,))
            
            # Create notification for client
            cur.execute('''
                SELECT client_id, title FROM jobs WHERE id = ?
            ''', (job_id,))
            job = cur.fetchone()
            
            cur.execute('''
                SELECT fname, lname FROM workers WHERE id = ?
            ''', (worker_id,))
            worker = cur.fetchone()
            
            if job and worker:
                cur.execute('''
                    INSERT INTO notifications 
                    (user_id, user_type, type, title, message, related_id)
                    VALUES (?, 'client', 'job_cancelled', ?, ?, ?)
                ''', (
                    job['client_id'],
                    "Worker Declined Job",
                    f"{worker['fname']} {worker['lname']} declined your job '{job['title']}'",
                    job_id
                ))
            
            conn.commit()
            
            logger.info(f"Worker {worker_id} rejected job {job_id}")
            return {"success": True, "message": "Job declined successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error worker rejecting job: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def complete_job(self, job_id: int, client_id: int, actual_hours: float, final_payment: float) -> Dict:
        """Mark job as completed"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if client owns the job
            cur.execute("SELECT client_id, assigned_workers FROM jobs WHERE id = ?", (job_id,))
            job = cur.fetchone()
            if not job or job['client_id'] != client_id:
                return {"error": "Unauthorized or job not found"}
            
            # Update job assignments
            cur.execute('''
                UPDATE job_assignments 
                SET end_time = CURRENT_TIMESTAMP,
                    actual_hours = ?,
                    final_payment = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            ''', (actual_hours, final_payment, job_id))
            
            # Update job status
            cur.execute('''
                UPDATE jobs 
                SET status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (job_id,))
            
            # Update client stats
            cur.execute('''
                UPDATE clients 
                SET active_jobs = active_jobs - ?,
                    total_spent = total_spent + ?
                WHERE id = ?
            ''', (job['assigned_workers'], final_payment, client_id))
            
            # Get assigned workers to update their stats
            cur.execute('''
                SELECT worker_id FROM job_assignments WHERE job_id = ?
            ''', (job_id,))
            
            workers = cur.fetchall()
            payment_per_worker = final_payment / len(workers) if workers else 0
            
            # Update each worker's stats
            for worker in workers:
                cur.execute('''
                    UPDATE workers 
                    SET total_jobs_done = total_jobs_done + 1
                    WHERE id = ?
                ''', (worker['worker_id'],))
                
                # Create notification for worker
                cur.execute('''
                    INSERT INTO notifications 
                    (user_id, user_type, type, title, message, related_id)
                    VALUES (?, 'worker', 'job_completed', ?, ?, ?)
                ''', (
                    worker['worker_id'],
                    "Job Completed",
                    f"A job has been marked as completed. Payment of R{payment_per_worker:.2f} will be processed.",
                    job_id
                ))
            
            # Create notification for client
            cur.execute('''
                INSERT INTO notifications 
                (user_id, user_type, type, title, message, related_id)
                VALUES (?, 'client', 'job_completed', ?, ?, ?)
            ''', (
                client_id,
                "Job Completed",
                f"Your job has been marked as completed. Total payment: R{final_payment:.2f}",
                job_id
            ))
            
            conn.commit()
            
            logger.info(f"Job {job_id} marked as completed")
            return {"success": True, "message": "Job completed successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error completing job: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_notifications(self, user_id: int, user_type: str, unread_only: bool = False, limit: int = 20) -> List[Dict]:
        """Get notifications for user"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = '''
                SELECT * FROM notifications 
                WHERE user_id = ? AND user_type = ?
            '''
            params = [user_id, user_type]
            
            if unread_only:
                query += " AND is_read = FALSE"
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cur.execute(query, params)
            
            notifications = []
            for row in cur.fetchall():
                notifications.append(dict(row))
            
            return notifications
            
        except sqlite3.Error as e:
            logger.error(f"Error getting notifications: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> Dict:
        """Mark notification as read"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                UPDATE notifications 
                SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (notification_id, user_id))
            
            conn.commit()
            return {"success": True}
            
        except sqlite3.Error as e:
            logger.error(f"Error marking notification read: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def _row_to_dict(self, row) -> Dict:
        """Convert SQLite row to dictionary"""
        job_dict = dict(row)
        
        # Parse JSON fields
        if 'location_json' in job_dict and job_dict['location_json']:
            job_dict['location'] = json.loads(job_dict['location_json'])
            del job_dict['location_json']
        
        # Convert datetime strings if needed
        for field in ['scheduled_date', 'created_at', 'updated_at']:
            if field in job_dict and job_dict[field]:
                if isinstance(job_dict[field], str):
                    try:
                        # Convert to ISO format string
                        dt_obj = datetime.fromisoformat(job_dict[field].replace('Z', '+00:00'))
                        job_dict[field] = dt_obj.isoformat()
                    except:
                        pass
        
        return job_dict