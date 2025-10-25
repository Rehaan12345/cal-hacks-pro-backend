from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
import os, requests, json, re
from typing import List, Dict
from datetime import datetime

load_dotenv()

router = APIRouter(prefix="/scraper", tags=["scraper"])

# Optional/third-party imports: wrap in try/except so missing packages or missing
# environment variables don't crash the function at import time in Vercel.
try:
    from firecrawl import Firecrawl
except Exception:
    Firecrawl = None

try:
    from apify_client import ApifyClient
except Exception:
    ApifyClient = None

# Playwright is not required in the lightweight deployment; avoid importing it at module import time
try:
    # from playwright.async_api import async_playwright
    async_playwright = None
except Exception:
    async_playwright = None

try:
    import anthropic
except Exception:
    anthropic = None

# Initialize clients only if modules are present. If missing, set to None and
# handle gracefully in request handlers.
firecrawl = None
maps_client = None
client = None
MAPS_URL = os.environ.get("MAPS_URL")
MAPS_KEY = os.environ.get("MAPS_API")
GEO_URL = os.environ.get("GOOGLE_GEOCODING_URL")
GEO_KEY = os.environ.get("GOOGLE_GEOCODING_API")
CIVIC_HUB_BASE = os.environ.get("CIVIC_HUB_BASE")
SPACE = " "

if Firecrawl is not None:
    try:
        firecrawl = Firecrawl(api_key=os.environ.get("FIRE_KEY"))
    except Exception:
        firecrawl = None

if ApifyClient is not None:
    try:
        maps_client = ApifyClient(os.environ.get("APIFY_API"))
    except Exception:
        maps_client = None

if anthropic is not None:
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
    except Exception:
        client = None

class Crime(BaseModel):
    coords: List[str]
    neighborhood: str
    city: str
    state: str
    user_stats: Dict[str, str]

class PublicSentiment(BaseModel):
    neighborhood: str
    city: str
    state: str

class PoliceStations(BaseModel):
    coords: List[str]
    neighborhood: str
    city: str
    state: str
    transport: str = "walk"
    max_search: int
    radius: float

# RESPONSE SCHEMA FOR CRIME-RECS:

class UserProfile(BaseModel):
    jewelry: str
    clothes: str
    time_preference: str
    risk_factors: str

class CrimePatterns(BaseModel):
    total_incidents: int
    theft_related: int
    assault_battery: int
    robbery: int
    drug_offenses: int
    weapon_offenses: int
    high_risk_neighborhoods: List[str]

class SafestTimesWithinPreference(BaseModel):
    earliest_safe_time: str
    latest_safe_time: str
    rationale: str

class TimeSafetyLevel(BaseModel):
    safety_level: str
    incidents: int
    concerning_incidents: List[str]

class JewelryAndClothingRiskAssessment(BaseModel):
    risk_level: str
    recommendation: str

class Analysis(BaseModel):
    user_profile: UserProfile
    crime_patterns_during_preferred_hours: Dict[str, CrimePatterns]
    safest_times_within_preference: SafestTimesWithinPreference
    safety_levels_by_time: Dict[str, TimeSafetyLevel]
    jewelry_and_clothing_risk_assessment: JewelryAndClothingRiskAssessment

class Recommendations(BaseModel):
    safest_earliest_time: str
    safest_latest_time: str
    overall_safety_level_3pm_to_6pm: str
    overall_safety_level_6pm_to_9pm: str
    jewelry_precaution: str
    high_risk_areas_to_avoid: List[str]

class Data(BaseModel):
    analysis: Analysis
    recommendations: Recommendations

class SafetyAnalysisResponse(BaseModel):
    status: int
    data: Data

@router.get("/safety-analysis", response_model=SafetyAnalysisResponse)
def get_safety_analysis():
    return {
        "status": 1,
        "data": {
            "analysis": {
                "user_profile": {
                    "jewelry": "silver bracelet, gold necklace",
                    "clothes": "medium expensive, not too flashy",
                    "time_preference": "3:00 p.m. to 9:00 p.m.",
                    "risk_factors": "Wearing visible jewelry increases theft risk"
                },
                "crime_patterns_during_preferred_hours": {
                    "3:00_pm_to_9:00_pm": {
                        "total_incidents": 89,
                        "theft_related": 18,
                        "assault_battery": 12,
                        "robbery": 3,
                        "drug_offenses": 24,
                        "weapon_offenses": 4,
                        "high_risk_neighborhoods": [
                            "Mission", "Tenderloin", "South of Market"
                        ]
                    }
                }
            },
            "recommendations": {
                "safest_earliest_time": "3:00 p.m.",
                "safest_latest_time": "6:00 p.m.",
                "high_risk_areas_to_avoid": [
                    "Mission", "Tenderloin", "South of Market"
                ]
            }
        }
    }

# CRIME

@router.post("/crime-recs/")
async def crime_recs(nhood: Crime):
    '''
    Returns user specs and crime recs.
    Access recommendations key to get ideal hours and areas to avoid and areas to prefer.
    '''
    try:
        # Scrape data
        n_hood_stats = await scrape_civic_hub(nhood.neighborhood)
        data = claude_compose(nhood.user_stats, n_hood_stats)

        # Try to extract JSON from Claude response
        text = data[0].text if isinstance(data, list) and hasattr(data[0], "text") else str(data)
        json_match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)

        print(text)

        if json_match:
            json_str = json_match.group(1)
            parsed = json.loads(json_str)
            return {"status": 1, "data": parsed}
        else:
            print("No JSON found in text.")
            return {
                "status": 0,
                "message": "No JSON found in response",
                "raw_output": text[:1000]  # Optional: limit to prevent huge strings
            }

    except Exception as e:
        return {"status": -1, "error_message": f"Failed to find crime stats: {e}"}

@router.post("/scrap-civic-hub/")
async def scrape_civic_hub(neighborhood: str):
    """
    Scrapes the civic hub website
    Returns list of values to be parsed by Claude
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(f"{CIVIC_HUB_BASE}/{neighborhood}", headers=headers, timeout=30)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            return []
            
        table_data = []
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['th', 'td'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            table_data.append(row_data)
            
        return table_data
        
    except Exception as e:
        print(f"Error scraping civic hub: {str(e)}")
        return []

@router.post("/claude-digest/")
def claude_compose(user, nhood):
    '''
    Runs user profile and data scraped through Claude
    Returns a set of recommendations and analysis based on the data.
    '''
    # If Anthropic client isn't configured, return a clear error
    if client is None:
        return {"status": -1, "error_message": "Anthropic client not configured (CLAUDE_API_KEY missing or anthropic package not installed)"}

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=20000,
            temperature=1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Provide ONLY A JSON ouput! Do NOT respond with your reasoning or analysis. Make sure all of that is internal. You are provided with a user profile of {user}. Compare that with the neighborhood data of {nhood}. BY ONLY USING THE DATA PRESENTED IN THE TABLE, DO NOT EXTRAPULATE OR ADD DATA. THE DATA ON THE TABLE IS THE ONLY INFORMATION YOU HAVE ON THE SAFETY OF THE NEIGHBORHOOD, combined with the data from the user profile, RESPONDING ONLY IN JSON FORMAT, return the safest earliest times to go out, and the safest latest times to go out. The user may be wearing expensive or inexpensive jewelery, clothing, etc., so the JSON ONLY response should acknowledge that. Also make sure to give safety levels like high, medium, or low."
                        }
                    ]
                },
            ]
        )

        data = message.content

        return data
    except Exception as e:
        return {"status": -1, "error_message": str(e)}

# POLICE

@router.post("/police-stations/")
def police_stations(ps: PoliceStations):
    '''
    Finds all police stations within a certain radius.
    Returns only the police stations in the correct radius.
    '''
    if maps_client is None:
        return {"status": -1, "error_message": "Apify/Maps client not configured (APIFY_API missing or apify-client not installed)"}

    p_stations = find_police(ps.city, ps.state, ps.max_search)

    data = filter_police(ps.coords, p_stations, ps.radius)

    return {"status": 0, "data": data}

def find_police(city, state, max_search):
    '''
    Uses Apify Google Maps scraper to find specified amount of police stations
    Returns all police stations, amount specified.
    '''
    run_input = {
        "searchStringsArray": ["police stations"],
        "locationQuery": f"{city}, {state}",
        "maxCrawledPlacesPerSearch": max_search,
        "language": "en",
        "maximumLeadsEnrichmentRecords": 0,
        "maxImages": 0,
    }
    if maps_client is None:
        return []

    try:
        run = maps_client.actor("compass/crawler-google-places").call(run_input=run_input)
        p_stations = []

        for item in maps_client.dataset(run["defaultDatasetId"]).iterate_items():
            p_stations.append(item)

        return p_stations
    except Exception:
        return []

def filter_police(og_coords, stations, radius):
    '''
    Filters the police findings based on radius specified
    Returns only the ones <= to that radius.
    '''
    result = []
    keep = ["title", "address", "phone", "location"]

    for p in stations:
        # calculate the distance from the original location to the police stations
        # only add if the distance is within 1 mile (with that transport option)
        dest_coords = [p["location"]["lat"], p["location"]["lng"]]
        t_dist = find_distance(og_coords, dest_coords)
        dist = -1
        if t_dist["status"] == 0:
            dist = t_dist["data"]
        else:
            print(f"failed to find location: {t_dist["error_message"]}")
            continue
        if dist <= radius:
            temp = {}
            for k in keep:
                temp[k] = p[k]
            temp["distance"] = dist
            result.append(temp)

    return result

def find_distance(origin, dest): # origin, dest are both list of coordinates
    '''
    Uses Google Maps Distance Matrix API to find distance between two points (coordinates), in miles
    Returns the mile difference of the two points
    '''
    try:
        if not MAPS_URL or not MAPS_KEY:
            return {"status": -1, "error_message": "MAPS_URL or MAPS_KEY not configured"}

        dist = -1
        url = f"{MAPS_URL}destinations={dest[0]},{dest[1]}&origins={origin[0]},{origin[1]}&units=imperial&key={MAPS_KEY}"
        response = requests.get(url)
        r_json = response.json()

        # just take the first one
        dist = r_json["rows"][0]["elements"][0]["distance"]["text"]
        ind_space = dist.find(" ")
        dist = float(dist[:ind_space])

        return {"status": 0, "data": dist}
    except Exception as e:
        return {"status": -1, "error_message": str(e)}
    
def get_coords(address):
    '''
    Uses Google Maps Geolocation API to return coordinates from an address
    '''
    try:
        if not GEO_URL or not GEO_KEY:
            return {"status": -1, "error_message": "GEO_URL or GEO_KEY not configured"}

        url = f"{GEO_URL}address={address}&key={GEO_KEY}"
        response = requests.get(url)
        r_json = response.json()
        t_coords = r_json["results"][0]["geometry"]["location"]
        coords = [t_coords["lat"], t_coords["lng"]]
        return {"status": 0, "data": coords}
    except Exception as e:
        return {"status": -1, "error_message": str(e)}

# SOCIAL SENTIMENT

@router.post("/public-sentiment/")
def pub_sent(ps: PublicSentiment):
    return {"status": 0, "data": ps}

# METRIC SCORE

@router.post("/safety-metric/")
async def safety_metric(crime: Crime):
    score = 10

    recs = await crime_recs(crime)
    print(recs)
    recs = recs["data"]["recommendations"]

    # Now parse the recommendations to develop some metric for safety.

    # Check time:
    curr_time = datetime.now().time()
    low_time = recs["safest_earliest_time"]
    high_time = recs["safest_latest_time"]
    ind_l = low_time.find(SPACE)
    low_time = int(low_time[:ind_l - 3])
    # high_l = 

    return {"status": 0, "data": score}
    