from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import Workers.router as workers_router
import Clients.router as clients_router
import Jobs.router as jobs_router
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DurbanWork API",
    description="API for DurbanWork - Connecting Workers with Clients",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React Native app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workers_router.router)
app.include_router(clients_router.router)
app.include_router(jobs_router.router)

@app.get("/")
async def root():
    return {"message": "Welcome to DurbanWork API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)