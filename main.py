from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
import os, sys, io
import json, tempfile, mimetypes
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Annotated
from datetime import timedelta
from pydantic import BaseModel
import logging
from dotenv import load_dotenv

# Use absolute imports for routers so this file can be executed as a top-level module
from routers import scraper, location

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scraper.router)
app.include_router(location.router)

@app.get("/")
def home():
    try:
        return {
            "status": "success",
            "message": "API is running",
            "debug_info": {
                "python_version": sys.version,
                "environment": "production" if os.environ.get("VERCEL_ENV") else "development"
            }
        }
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/debug")
async def debug():
    """Debug endpoint to check configuration"""
    try:
        # Check environment variables
        required_vars = [
            "SPLY_KEY",
            "FIRE_KEY",
            "APIFY_API",
            "MAPS_URL",
            "MAPS_API",
            "GOOGLE_GEOCODING_URL",
            "GOOGLE_GEOCODING_API",
            "CIVIC_HUB_BASE",
            "CLAUDE_API_KEY"
        ]
        
        env_status = {var: bool(os.environ.get(var)) for var in required_vars}
        
        return {
            "status": "success",
            "environment": os.environ.get("VERCEL_ENV", "development"),
            "python_version": sys.version,
            "env_variables": env_status,
            "cwd": os.getcwd(),
            "files_in_cwd": os.listdir(os.getcwd())
        }
    except Exception as e:
        logger.error(f"Error in debug route: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "type": str(type(e).__name__)
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler caught: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred",
            "detail": str(exc),
            "type": str(type(exc).__name__)
        }
    )