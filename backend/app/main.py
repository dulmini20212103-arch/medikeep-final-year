from fastapi import FastAPI
#Handles Cross-Origin Resource Sharing
from fastapi.middleware.cors import CORSMiddleware
#Serves static files
from fastapi.staticfiles import StaticFiles
#SQLAlchemy database engine and declarative base
from .database import engine, Base
#Models - imported for table creation
from .models import User, Clinic, Patient, Document, Extraction
#Routers - modular route groups for auth, users, documents, patients
from .routers import auth_router, users_router
from .routers.documents import router as documents_router
from .routers.patients import router as patients_router
#for file system operations
import os

# Automatically create database tables
Base.metadata.create_all(bind=engine)

# Create upload directory
#Ensures the folder exists (where uploaded medical documents will be stored)
os.makedirs("uploads/documents", exist_ok=True)

# Initialize FastAPI app
#Adds API metadata
app = FastAPI(
    title="Healthcare AI API",
    description="Healthcare AI platform for medical document analysis",
    version="1.0.0"
)

# Configure CORS(Cross-Origin Resource Sharing)
#allows your frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
#Enables users to access uploaded files via HTTP
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth_router)  #authentication endpoints
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(patients_router)

@app.get("/")
async def root():
    return {"message": "Healthcare AI API is running"}

@app.get("/health")
async def health_check():
    #Indicates database is connected
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)