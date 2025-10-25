from fastapi import FastAPI, APIRouter, Query
import requests, os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/location", tags=["location"])

SPLY_URL = "https://api.slpy.com/v1/search?"
SPLY_KEY = os.environ.get("SPLY_KEY")

class Coords(BaseModel):
    lat: float
    lon: float

# coordinates (list [long, lat]) -> neighborhood
@router.post("/find-neighborhood/")
def crime_stats(coords: Coords):
    try:
        loc_level = 6
        lon = coords.lon
        lat = coords.lat
        response = requests.get(f"{SPLY_URL}level={loc_level}&lat={lat}&lon={lon}&key={SPLY_KEY}")
        r_json = response.json()
        data = r_json["properties"]

        return {"status": 0, "data": data}

    except Exception as e:
        return {"status": -1, "message": f"Failed to find neighborhood from given coordinates: {e}"}
