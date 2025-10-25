from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
import os, sys, io
import json, tempfile, mimetypes
from fastapi.responses import StreamingResponse
from typing import List, Annotated
from datetime import timedelta
from pydantic import BaseModel
from .routers import scraper, location

app = FastAPI()

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
    return {"status": "success"}