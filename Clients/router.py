from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from .manager import ClientManager, ClientCreate, ClientUpdate, ClientLogin, ClientResponse
import logging

router = APIRouter(prefix="/api/clients", tags=["clients"])
client_manager = ClientManager()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_client(client_data: ClientCreate):
    """Register a new client"""
    try:
        result = client_manager.add_client(client_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Add token and format for frontend
        if "client" in result:
            result["client"]["token"] = f"client-token-{result['client']['id']}"
            return {
                "data": result["client"],  # ✅ Frontend expects response.data
                "success": True,
                "message": result.get("message", "Client registered successfully")
            }
        
        return result
    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=dict)
async def login_client(login_data: ClientLogin):
    """Login a client"""
    try:
        client = client_manager.authenticate_client(login_data.email, login_data.password)
        if not client:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Add token for frontend
        client['token'] = f"client-token-{client['id']}"
        
        # Match frontend expectation
        return {
            "data": client,  # ✅ Frontend expects response.data
            "success": True,
            "message": "Login successful"
        }
    except Exception as e:
        logger.error(f"Client login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int):
    """Get client by ID"""
    try:
        client = client_manager.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except Exception as e:
        logger.error(f"Get client error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{client_id}", response_model=dict)
async def update_client(client_id: int, update_data: ClientUpdate):
    """Update client information"""
    try:
        result = client_manager.update_client(client_id, update_data)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Update client error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{client_id}/favorites/{worker_id}", response_model=dict)
async def add_favorite_worker(client_id: int, worker_id: int, notes: str = None):
    """Add worker to client's favorites"""
    try:
        result = client_manager.add_favorite_worker(client_id, worker_id, notes)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Add favorite worker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}/favorites", response_model=List[dict])
async def get_favorite_workers(client_id: int):
    """Get client's favorite workers"""
    try:
        workers = client_manager.get_favorite_workers(client_id)
        return workers
    except Exception as e:
        logger.error(f"Get favorite workers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
