import sqlite3
import json
import datetime as dt
from typing import Dict, List, Optional, Tuple
import bcrypt
from pydantic import BaseModel, EmailStr, validator
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Data Models
class ClientAddress(BaseModel):
    street: str
    city: str = "Durban"
    province: str = "KwaZulu-Natal"
    postal_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ClientCreate(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    phone: str
    password: str
    company_name: Optional[str] = None
    address: ClientAddress
    profile_image: Optional[str] = None

class ClientUpdate(BaseModel):
    fname: Optional[str] = None
    lname: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[ClientAddress] = None
    profile_image: Optional[str] = None

class ClientResponse(BaseModel):
    id: int
    fname: str
    lname: str
    email: str
    phone: str
    company_name: Optional[str] = None
    address: Dict
    total_jobs_posted: int
    active_jobs: int
    total_spent: float
    rating: float
    created_at: str
    profile_image: Optional[str] = None

class ClientLogin(BaseModel):
    email: EmailStr
    password: str

class ClientManager:
    def __init__(self, db_name: str = 'durban_works.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database with clients table"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Create clients table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fname TEXT NOT NULL,
                    lname TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    company_name TEXT,
                    address_json TEXT NOT NULL,
                    total_jobs_posted INTEGER DEFAULT 0,
                    active_jobs INTEGER DEFAULT 0,
                    total_spent REAL DEFAULT 0.0,
                    rating REAL DEFAULT 0.0,
                    profile_image TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create client preferences table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS client_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    notification_jobs BOOLEAN DEFAULT TRUE,
                    notification_updates BOOLEAN DEFAULT TRUE,
                    notification_promotions BOOLEAN DEFAULT TRUE,
                    preferred_payment_method TEXT DEFAULT 'card',
                    auto_accept_workers BOOLEAN DEFAULT FALSE,
                    min_worker_rating REAL DEFAULT 4.0,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            ''')
            
            # Create favorite workers table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS client_favorite_workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (worker_id) REFERENCES workers (id),
                    UNIQUE(client_id, worker_id)
                )
            ''')
            
            # Create indexes
            cur.execute('CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)')
            
            conn.commit()
            logger.info("Clients database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Clients database initialization error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def add_client(self, client_data: ClientCreate) -> Dict:
        """Add a new client to the database"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if client already exists
            cur.execute("SELECT id FROM clients WHERE email = ?", (client_data.email,))
            if cur.fetchone():
                return {"error": "Client with this email already exists"}
            
            # Hash password
            hashed_password = self.hash_password(client_data.password)
            
            # Convert address to JSON
            address_json = json.dumps(client_data.address.dict())
            
            # Insert client
            cur.execute('''
                INSERT INTO clients (
                    fname, lname, email, phone, password_hash,
                    company_name, address_json, profile_image
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_data.fname, client_data.lname, client_data.email,
                client_data.phone, hashed_password, client_data.company_name,
                address_json, client_data.profile_image
            ))
            
            client_id = cur.lastrowid
            
            # Initialize preferences
            cur.execute('''
                INSERT INTO client_preferences (client_id) VALUES (?)
            ''', (client_id,))
            
            conn.commit()
            
            # Get the created client
            client = self.get_client_by_id(client_id)
            
            logger.info(f"Client added successfully: {client_data.email}")
            return {"success": True, "client": client, "message": "Client registered successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error adding client: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_client_by_id(self, client_id: int) -> Optional[Dict]:
        """Get client by ID"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting client by ID: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_client_by_email(self, email: str) -> Optional[Dict]:
        """Get client by email"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM clients WHERE email = ?", (email,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting client by email: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def authenticate_client(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate client"""
        try:
            client = self.get_client_by_email(email)
            if not client:
                return None
            
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM clients WHERE email = ?", (email,))
            result = cur.fetchone()
            
            if not result or not self.verify_password(password, result['password_hash']):
                return None
            
            # Remove password hash from response
            if 'password_hash' in client:
                del client['password_hash']
            
            return client
            
        except Exception as e:
            logger.error(f"Client authentication error: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def update_client(self, client_id: int, update_data: ClientUpdate) -> Dict:
        """Update client information"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if client exists
            cur.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
            if not cur.fetchone():
                return {"error": "Client not found"}
            
            # Build dynamic update query
            update_fields = []
            params = []
            
            if update_data.fname is not None:
                update_fields.append("fname = ?")
                params.append(update_data.fname)
            
            if update_data.lname is not None:
                update_fields.append("lname = ?")
                params.append(update_data.lname)
            
            if update_data.phone is not None:
                update_fields.append("phone = ?")
                params.append(update_data.phone)
            
            if update_data.company_name is not None:
                update_fields.append("company_name = ?")
                params.append(update_data.company_name)
            
            if update_data.address is not None:
                address_json = json.dumps(update_data.address.dict())
                update_fields.append("address_json = ?")
                params.append(address_json)
            
            if update_data.profile_image is not None:
                update_fields.append("profile_image = ?")
                params.append(update_data.profile_image)
            
            if not update_fields:
                return {"error": "No fields to update"}
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add client_id to params
            params.append(client_id)
            
            update_query = f"UPDATE clients SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(update_query, params)
            
            conn.commit()
            
            # Get updated client
            updated_client = self.get_client_by_id(client_id)
            
            logger.info(f"Client updated successfully: ID {client_id}")
            return {"success": True, "client": updated_client, "message": "Client updated successfully"}
            
        except sqlite3.Error as e:
            logger.error(f"Error updating client: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def update_client_stats(self, client_id: int, amount_spent: float = 0) -> Dict:
        """Update client statistics after job completion"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Update total spent
            if amount_spent > 0:
                cur.execute('''
                    UPDATE clients 
                    SET total_spent = total_spent + ?
                    WHERE id = ?
                ''', (amount_spent, client_id))
            
            # Update active jobs count
            # This would be called from JobManager when job status changes
            cur.execute('''
                UPDATE clients 
                SET active_jobs = (
                    SELECT COUNT(*) FROM jobs 
                    WHERE client_id = ? AND status IN ('posted', 'assigned', 'in_progress')
                )
                WHERE id = ?
            ''', (client_id, client_id))
            
            conn.commit()
            return {"success": True}
            
        except sqlite3.Error as e:
            logger.error(f"Error updating client stats: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def add_favorite_worker(self, client_id: int, worker_id: int, notes: str = None) -> Dict:
        """Add a worker to client's favorites"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Check if already favorited
            cur.execute('''
                SELECT id FROM client_favorite_workers 
                WHERE client_id = ? AND worker_id = ?
            ''', (client_id, worker_id))
            
            if cur.fetchone():
                return {"error": "Worker already in favorites"}
            
            # Add to favorites
            cur.execute('''
                INSERT INTO client_favorite_workers (client_id, worker_id, notes)
                VALUES (?, ?, ?)
            ''', (client_id, worker_id, notes))
            
            conn.commit()
            return {"success": True, "message": "Worker added to favorites"}
            
        except sqlite3.Error as e:
            logger.error(f"Error adding favorite worker: {e}")
            return {"error": f"Database error: {e}"}
        finally:
            if conn:
                conn.close()
    
    def get_favorite_workers(self, client_id: int) -> List[Dict]:
        """Get client's favorite workers"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT w.* FROM workers w
                JOIN client_favorite_workers cfw ON w.id = cfw.worker_id
                WHERE cfw.client_id = ?
                ORDER BY cfw.created_at DESC
            ''', (client_id,))
            
            workers = []
            for row in cur.fetchall():
                # Convert row to dict and parse JSON fields
                worker_dict = dict(row)
                if 'address_json' in worker_dict and worker_dict['address_json']:
                    worker_dict['address'] = json.loads(worker_dict['address_json'])
                    del worker_dict['address_json']
                if 'password_hash' in worker_dict:
                    del worker_dict['password_hash']
                workers.append(worker_dict)
            
            return workers
            
        except sqlite3.Error as e:
            logger.error(f"Error getting favorite workers: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _row_to_dict(self, row) -> Dict:
        """Convert SQLite row to dictionary"""
        client_dict = dict(row)
        
        # Parse JSON fields
        if 'address_json' in client_dict and client_dict['address_json']:
            client_dict['address'] = json.loads(client_dict['address_json'])
            del client_dict['address_json']
        
        # Remove sensitive data
        if 'password_hash' in client_dict:
            del client_dict['password_hash']
        
        return client_dict