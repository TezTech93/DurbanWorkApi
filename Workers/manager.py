import sqlite3
import json
import datetime as dt
from typing import Dict, List, Optional, Tuple
import bcrypt
from pydantic import BaseModel, EmailStr, validator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data Models
class Address(BaseModel):
    street: str
    city: str = "Durban"
    province: str = "KwaZulu-Natal"
    postal_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Experience(BaseModel):
    job_type: str
    years: int
    description: Optional[str] = None
    company: Optional[str] = None

class WorkerCreate(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    phone: str
    password: str
    age: int
    address: Address
    skills: List[str]
    experience: List[Experience]
    hourly_rate: Optional[float] = 150.00
    available: bool = True
    profile_image: Optional[str] = None
    id_number: Optional[str] = None

class WorkerUpdate(BaseModel):
    fname: Optional[str] = None
    lname: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    address: Optional[Address] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Experience]] = None
    hourly_rate: Optional[float] = None
    available: Optional[bool] = None
    profile_image: Optional[str] = None
    rating: Optional[float] = None
    total_jobs_done: Optional[int] = None
    # Add these fields for onboarding
    onboarding_completed: Optional[bool] = None
    payment_type: Optional[str] = None  # 'contractor' or 'employee'
    business_info: Optional[Dict] = None
    bank_info: Optional[Dict] = None
    employee_details: Optional[Dict] = None
    tax_status: Optional[str] = None
    id_verified: Optional[bool] = None
    background_check_passed: Optional[bool] = None
    verification_status: Optional[str] = None
    # Add missing fields for resume upload
    resume_url: Optional[str] = None
    # Add fields for stats
    response_rate: Optional[float] = None
    acceptance_rate: Optional[float] = None
    avg_response_time: Optional[str] = None
    reliability_score: Optional[float] = None
    # Add other missing fields
    id_number: Optional[str] = None

class WorkerResponse(BaseModel):
    id: int
    fname: str
    lname: str
    email: str
    phone: str
    age: int
    address: Dict
    skills: List[str]
    experience: List[Dict]
    hourly_rate: float
    available: bool
    rating: float
    total_jobs_done: int
    created_at: str
    profile_image: Optional[str] = None
    id_number: Optional[str] = None
    # Add onboarding fields
    onboarding_completed: Optional[bool] = None
    payment_type: Optional[str] = None
    business_info: Optional[Dict] = None
    bank_info: Optional[Dict] = None
    employee_details: Optional[Dict] = None
    tax_status: Optional[str] = None
    id_verified: Optional[bool] = None
    background_check_passed: Optional[bool] = None
    verification_status: Optional[str] = None
    # Add stats fields
    response_rate: Optional[float] = None
    acceptance_rate: Optional[float] = None
    avg_response_time: Optional[str] = None
    reliability_score: Optional[float] = None
    # Add resume field
    resume_url: Optional[str] = None

class WorkerLogin(BaseModel):
    email: EmailStr
    password: str

class WorkerManager:
    def __init__(self, db_name: str = 'durban_works.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    
    def init_db(self):
        """Initialize database with workers table"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Create workers table with all fields
            cur.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fname TEXT NOT NULL,
                    lname TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    address_json TEXT NOT NULL,
                    skills_json TEXT NOT NULL,
                    experience_json TEXT NOT NULL,
                    hourly_rate REAL DEFAULT 150.00,
                    available BOOLEAN DEFAULT TRUE,
                    rating REAL DEFAULT 0.0,
                    total_jobs_done INTEGER DEFAULT 0,
                    profile_image TEXT,
                    id_number TEXT,
                    
                    # Add onboarding fields
                    onboarding_completed BOOLEAN DEFAULT FALSE,
                    payment_type TEXT DEFAULT 'contractor',
                    business_info_json TEXT,
                    bank_info_json TEXT,
                    employee_details_json TEXT,
                    tax_status TEXT DEFAULT 'standard',
                    id_verified BOOLEAN DEFAULT FALSE,
                    background_check_passed BOOLEAN DEFAULT FALSE,
                    verification_status TEXT DEFAULT 'pending',
                    
                    # Add stats fields
                    response_rate REAL DEFAULT 95.0,
                    acceptance_rate REAL DEFAULT 88.0,
                    avg_response_time TEXT DEFAULT '15 min',
                    reliability_score REAL DEFAULT 4.8,
                    
                    # Add resume field
                    resume_url TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create worker job history table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL,
                    client_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'completed',
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    earnings REAL NOT NULL,
                    job_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create worker availability table for scheduling
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    day_of_week INTEGER CHECK(day_of_week >= 0 AND day_of_week <= 6),
                    start_time TIME,
                    end_time TIME,
                    is_available BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create worker verification table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_verification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    id_verified BOOLEAN DEFAULT FALSE,
                    id_document_url TEXT,
                    background_check BOOLEAN DEFAULT FALSE,
                    profile_completed BOOLEAN DEFAULT FALSE,
                    verified_at TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create worker documents table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    document_url TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create worker notifications table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    data_json TEXT,
                    read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create worker earnings table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS worker_earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    payment_date TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            ''')
            
            # Create indexes for better performance
            cur.execute('CREATE INDEX IF NOT EXISTS idx_workers_email ON workers(email)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_workers_available ON workers(available)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_workers_rating ON workers(rating)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_workers_skills ON workers(skills_json)')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storing"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a stored password against one provided by user"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def add_worker(self, worker_data: WorkerCreate) -> Dict:
        """Add a new worker to the database"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if worker already exists
            cur.execute("SELECT id FROM workers WHERE email = ?", (worker_data.email,))
            if cur.fetchone():
                return {"error": "Worker with this email already exists"}
            
            # Hash password
            hashed_password = self.hash_password(worker_data.password)
            
            # Convert address, skills, and experience to JSON
            address_json = json.dumps(worker_data.address.dict())
            skills_json = json.dumps(worker_data.skills)
            experience_json = json.dumps([exp.dict() for exp in worker_data.experience])
            
            # Insert worker
            cur.execute('''
                INSERT INTO workers (
                    fname, lname, email, phone, password_hash, age, 
                    address_json, skills_json, experience_json, 
                    hourly_rate, available, profile_image, id_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                worker_data.fname, worker_data.lname, worker_data.email, 
                worker_data.phone, hashed_password, worker_data.age,
                address_json, skills_json, experience_json,
                worker_data.hourly_rate, worker_data.available,
                worker_data.profile_image, worker_data.id_number
            ))
            
            worker_id = cur.lastrowid
            
            # Initialize verification record
            cur.execute('''
                INSERT INTO worker_verification (worker_id) VALUES (?)
            ''', (worker_id,))
            
            conn.commit()
            
            # Get the created worker
            worker = self.get_worker_by_id(worker_id)
            
            logger.info(f"Worker added successfully: {worker_data.email}")
            return {"success": True, "worker": worker, "message": "Worker registered successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error adding worker: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_worker_by_id(self, worker_id: int) -> Optional[Dict]:
        """Get worker by ID"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting worker by ID: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_worker_by_email(self, email: str) -> Optional[Dict]:
        """Get worker by email"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM workers WHERE email = ?", (email,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting worker by email: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def authenticate_worker(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate worker"""
        conn = None
        try:
            # First get worker data without password hash
            worker = self.get_worker_by_email(email)
            if not worker:
                return None
            
            # Get the password hash from database
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM workers WHERE email = ?", (email,))
            result = cur.fetchone()
            
            if not result:
                return None
            
            # Verify password
            if not self.verify_password(password, result['password_hash']):
                return None
            
            # Return worker data (password hash already removed by _row_to_dict)
            return worker
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_all_workers(self, available_only: bool = True, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get all workers with optional filters"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            if available_only:
                cur.execute('''
                    SELECT * FROM workers 
                    WHERE available = TRUE 
                    ORDER BY rating DESC, total_jobs_done DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            else:
                cur.execute('''
                    SELECT * FROM workers 
                    ORDER BY rating DESC, total_jobs_done DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            workers = []
            for row in cur.fetchall():
                worker = self._row_to_dict(row)
                workers.append(worker)
            
            return workers
            
        except sqlite3.Error as e:
            logger.error(f"Error getting all workers: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_workers_by_skills(self, skills: List[str], limit: int = 20) -> List[Dict]:
        """Find workers by skills"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Simple skill matching - for production, use better matching logic
            placeholders = ','.join(['?' for _ in skills])
            
            cur.execute(f'''
                SELECT * FROM workers 
                WHERE available = TRUE 
                ORDER BY rating DESC
                LIMIT ?
            ''', (limit,))
            
            workers = []
            for row in cur.fetchall():
                worker_skills = json.loads(row['skills_json'])
                # Check if worker has any of the required skills
                if any(skill.lower() in [s.lower() for s in worker_skills] for skill in skills):
                    workers.append(self._row_to_dict(row))
            
            return workers
            
        except sqlite3.Error as e:
            logger.error(f"Error getting workers by skills: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def update_worker(self, worker_id: int, update_data: WorkerUpdate) -> Dict:
        """Update worker information"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if worker exists
            cur.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
            if not cur.fetchone():
                return {"error": "Worker not found"}
            
            # Build dynamic update query
            update_fields = []
            params = []
            
            # Basic info fields
            if update_data.fname is not None:
                update_fields.append("fname = ?")
                params.append(update_data.fname)
            
            if update_data.lname is not None:
                update_fields.append("lname = ?")
                params.append(update_data.lname)
            
            if update_data.phone is not None:
                update_fields.append("phone = ?")
                params.append(update_data.phone)
            
            if update_data.age is not None:
                update_fields.append("age = ?")
                params.append(update_data.age)
            
            if update_data.address is not None:
                address_json = json.dumps(update_data.address.dict())
                update_fields.append("address_json = ?")
                params.append(address_json)
            
            if update_data.skills is not None:
                skills_json = json.dumps(update_data.skills)
                update_fields.append("skills_json = ?")
                params.append(skills_json)
            
            if update_data.experience is not None:
                experience_json = json.dumps([exp.dict() for exp in update_data.experience])
                update_fields.append("experience_json = ?")
                params.append(experience_json)
            
            if update_data.hourly_rate is not None:
                update_fields.append("hourly_rate = ?")
                params.append(update_data.hourly_rate)
            
            if update_data.available is not None:
                update_fields.append("available = ?")
                params.append(update_data.available)
            
            if update_data.profile_image is not None:
                update_fields.append("profile_image = ?")
                params.append(update_data.profile_image)
            
            if update_data.rating is not None:
                update_fields.append("rating = ?")
                params.append(update_data.rating)
            
            if update_data.total_jobs_done is not None:
                update_fields.append("total_jobs_done = ?")
                params.append(update_data.total_jobs_done)
            
            if update_data.id_number is not None:
                update_fields.append("id_number = ?")
                params.append(update_data.id_number)
            
            # Add onboarding fields
            if update_data.onboarding_completed is not None:
                update_fields.append("onboarding_completed = ?")
                params.append(update_data.onboarding_completed)
            
            if update_data.payment_type is not None:
                update_fields.append("payment_type = ?")
                params.append(update_data.payment_type)
            
            if update_data.business_info is not None:
                business_info_json = json.dumps(update_data.business_info)
                update_fields.append("business_info_json = ?")
                params.append(business_info_json)
            
            if update_data.bank_info is not None:
                bank_info_json = json.dumps(update_data.bank_info)
                update_fields.append("bank_info_json = ?")
                params.append(bank_info_json)
            
            if update_data.employee_details is not None:
                employee_details_json = json.dumps(update_data.employee_details)
                update_fields.append("employee_details_json = ?")
                params.append(employee_details_json)
            
            if update_data.tax_status is not None:
                update_fields.append("tax_status = ?")
                params.append(update_data.tax_status)
            
            if update_data.id_verified is not None:
                update_fields.append("id_verified = ?")
                params.append(update_data.id_verified)
            
            if update_data.background_check_passed is not None:
                update_fields.append("background_check_passed = ?")
                params.append(update_data.background_check_passed)
            
            if update_data.verification_status is not None:
                update_fields.append("verification_status = ?")
                params.append(update_data.verification_status)
            
            # Add stats fields
            if update_data.response_rate is not None:
                update_fields.append("response_rate = ?")
                params.append(update_data.response_rate)
            
            if update_data.acceptance_rate is not None:
                update_fields.append("acceptance_rate = ?")
                params.append(update_data.acceptance_rate)
            
            if update_data.avg_response_time is not None:
                update_fields.append("avg_response_time = ?")
                params.append(update_data.avg_response_time)
            
            if update_data.reliability_score is not None:
                update_fields.append("reliability_score = ?")
                params.append(update_data.reliability_score)
            
            # Add resume field
            if update_data.resume_url is not None:
                update_fields.append("resume_url = ?")
                params.append(update_data.resume_url)
            
            if not update_fields:
                return {"error": "No fields to update"}
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add worker_id to params
            params.append(worker_id)
            
            update_query = f"UPDATE workers SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(update_query, params)
            
            conn.commit()
            
            # Get updated worker
            updated_worker = self.get_worker_by_id(worker_id)
            
            logger.info(f"Worker updated successfully: ID {worker_id}")
            return {"success": True, "worker": updated_worker, "message": "Worker updated successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error updating worker: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def delete_worker(self, worker_id: int) -> Dict:
        """Delete a worker"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if worker exists
            cur.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
            if not cur.fetchone():
                return {"error": "Worker not found"}
            
            # Delete associated records
            cur.execute("DELETE FROM worker_job_history WHERE worker_id = ?", (worker_id,))
            cur.execute("DELETE FROM worker_availability WHERE worker_id = ?", (worker_id,))
            cur.execute("DELETE FROM worker_verification WHERE worker_id = ?", (worker_id,))
            cur.execute("DELETE FROM worker_documents WHERE worker_id = ?", (worker_id,))
            cur.execute("DELETE FROM worker_notifications WHERE worker_id = ?", (worker_id,))
            cur.execute("DELETE FROM worker_earnings WHERE worker_id = ?", (worker_id,))
            
            # Delete worker
            cur.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
            
            conn.commit()
            
            logger.info(f"Worker deleted successfully: ID {worker_id}")
            return {"success": True, "message": "Worker deleted successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting worker: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def add_job_history(self, worker_id: int, job_id: int, job_type: str, 
                       client_id: int, earnings: float, rating: Optional[int] = None) -> Dict:
        """Add job history for a worker"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO worker_job_history 
                (worker_id, job_id, job_type, client_id, earnings, rating, job_date)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (worker_id, job_id, job_type, client_id, earnings, rating))
            
            # Update worker stats
            if rating:
                # Calculate new average rating
                cur.execute('''
                    UPDATE workers 
                    SET total_jobs_done = total_jobs_done + 1,
                        rating = CASE 
                            WHEN total_jobs_done > 0 
                            THEN ((rating * total_jobs_done) + ?) / (total_jobs_done + 1)
                            ELSE ?
                            END
                    WHERE id = ?
                ''', (rating, rating, worker_id))
            else:
                cur.execute('''
                    UPDATE workers 
                    SET total_jobs_done = total_jobs_done + 1 
                    WHERE id = ?
                ''', (worker_id,))
            
            conn.commit()
            
            logger.info(f"Job history added for worker {worker_id}")
            return {"success": True, "message": "Job history recorded"}
            
        except sqlite3.Error as e:
            logger.error(f"Error adding job history: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_worker_job_history(self, worker_id: int) -> List[Dict]:
        """Get job history for a worker"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT * FROM worker_job_history 
                WHERE worker_id = ? 
                ORDER BY job_date DESC
            ''', (worker_id,))
            
            jobs = []
            for row in cur.fetchall():
                jobs.append(dict(row))
            
            return jobs
            
        except sqlite3.Error as e:
            logger.error(f"Error getting job history: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def set_worker_availability(self, worker_id: int, availability_slots: List[Dict]) -> Dict:
        """Set worker availability schedule"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Clear existing availability
            cur.execute("DELETE FROM worker_availability WHERE worker_id = ?", (worker_id,))
            
            # Insert new availability slots
            for slot in availability_slots:
                cur.execute('''
                    INSERT INTO worker_availability 
                    (worker_id, day_of_week, start_time, end_time, is_available)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    worker_id, 
                    slot.get('day_of_week'), 
                    slot.get('start_time'), 
                    slot.get('end_time'), 
                    slot.get('is_available', True)
                ))
            
            conn.commit()
            
            logger.info(f"Availability set for worker {worker_id}")
            return {"success": True, "message": "Availability schedule updated"}
            
        except sqlite3.Error as e:
            logger.error(f"Error setting availability: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_available_workers_for_job(self, job_type: str, date_time: str) -> List[Dict]:
        """Find available workers for a job at a specific time"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Parse date_time to get day of week and time
            try:
                dt_obj = dt.datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            except ValueError:
                dt_obj = dt.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
            
            day_of_week = dt_obj.weekday()  # Monday=0, Sunday=6
            time_str = dt_obj.time().strftime('%H:%M:%S')
            
            # Find workers with matching skills and availability
            cur.execute('''
                SELECT w.* FROM workers w
                WHERE w.available = TRUE
                AND json_extract(w.skills_json, '$') LIKE ?
                AND EXISTS (
                    SELECT 1 FROM worker_availability wa
                    WHERE wa.worker_id = w.id
                    AND wa.day_of_week = ?
                    AND wa.is_available = TRUE
                    AND wa.start_time <= ?
                    AND wa.end_time >= ?
                )
                ORDER BY w.rating DESC
            ''', (f'%{job_type}%', day_of_week, time_str, time_str))
            
            workers = []
            for row in cur.fetchall():
                workers.append(self._row_to_dict(row))
            
            return workers
            
        except Exception as e:
            logger.error(f"Error finding available workers: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _row_to_dict(self, row) -> Dict:
        """Convert SQLite row to dictionary"""
        worker_dict = dict(row)
        
        # Parse JSON fields
        if 'address_json' in worker_dict and worker_dict['address_json']:
            try:
                worker_dict['address'] = json.loads(worker_dict['address_json'])
            except:
                worker_dict['address'] = {}
            del worker_dict['address_json']
        
        if 'skills_json' in worker_dict and worker_dict['skills_json']:
            try:
                worker_dict['skills'] = json.loads(worker_dict['skills_json'])
            except:
                worker_dict['skills'] = []
            del worker_dict['skills_json']
        
        if 'experience_json' in worker_dict and worker_dict['experience_json']:
            try:
                worker_dict['experience'] = json.loads(worker_dict['experience_json'])
            except:
                worker_dict['experience'] = []
            del worker_dict['experience_json']
        
        # Parse onboarding JSON fields
        if 'business_info_json' in worker_dict and worker_dict['business_info_json']:
            try:
                worker_dict['business_info'] = json.loads(worker_dict['business_info_json'])
            except:
                worker_dict['business_info'] = {}
            del worker_dict['business_info_json']
        
        if 'bank_info_json' in worker_dict and worker_dict['bank_info_json']:
            try:
                worker_dict['bank_info'] = json.loads(worker_dict['bank_info_json'])
            except:
                worker_dict['bank_info'] = {}
            del worker_dict['bank_info_json']
        
        if 'employee_details_json' in worker_dict and worker_dict['employee_details_json']:
            try:
                worker_dict['employee_details'] = json.loads(worker_dict['employee_details_json'])
            except:
                worker_dict['employee_details'] = {}
            del worker_dict['employee_details_json']
        
        # Remove sensitive data
        if 'password_hash' in worker_dict:
            del worker_dict['password_hash']
        
        # Ensure all fields exist
        worker_dict.setdefault('onboarding_completed', False)
        worker_dict.setdefault('payment_type', 'contractor')
        worker_dict.setdefault('business_info', {})
        worker_dict.setdefault('bank_info', {})
        worker_dict.setdefault('employee_details', {})
        worker_dict.setdefault('tax_status', 'standard')
        worker_dict.setdefault('id_verified', False)
        worker_dict.setdefault('background_check_passed', False)
        worker_dict.setdefault('verification_status', 'pending')
        worker_dict.setdefault('response_rate', 95.0)
        worker_dict.setdefault('acceptance_rate', 88.0)
        worker_dict.setdefault('avg_response_time', '15 min')
        worker_dict.setdefault('reliability_score', 4.8)
        worker_dict.setdefault('resume_url', None)
        
        return worker_dict