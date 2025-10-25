from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from firecrawl import Firecrawl
from dotenv import load_dotenv
import os, requests, anthropic, json, re
from typing import List, Dict
from apify_client import ApifyClient
from playwright.async_api import async_playwright

load_dotenv()

router = APIRouter(prefix="/scraper", tags=["scraper"])

firecrawl = Firecrawl(api_key=os.environ.get("FIRE_KEY"))

maps_client = ApifyClient(os.environ.get("APIFY_API"))
MAPS_URL = os.environ.get("MAPS_URL")
MAPS_KEY = os.environ.get("MAPS_API")

GEO_URL = os.environ.get("GOOGLE_GEOCODING_URL")
GEO_KEY = os.environ.get("GOOGLE_GEOCODING_API")

CIVIC_HUB_BASE = os.environ.get("CIVIC_HUB_BASE")

client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

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
    transport: str
    max_search: int
    radius: float

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
    Scrapes the civic hub (https://www.civichub.us/ca/san-francisco/gov/police-department/crime-data/neighborhoods) website
    Returns list of values to be parsed by Claude
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(f"{CIVIC_HUB_BASE}/{neighborhood}", timeout=60000)
        await page.wait_for_timeout(2000)

        await page.wait_for_selector("table")

        rows = page.locator("table tr")
        table_data = []
        for i in range(await rows.count()):
            cells = rows.nth(i).locator("th, td")
            row_data = [await cells.nth(j).inner_text() for j in range(await cells.count())]
            table_data.append(row_data)

        await browser.close()

    return table_data

@router.post("/claude-digest/")
def claude_compose(user, nhood):
    '''
    Runs user profile and data scraped through Claude
    Returns a set of recommendations and analysis based on the data.
    '''
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
        return {"status": -1, "error_message": {e}}

# POLICE

@router.post("/police-stations/")
def police_stations(ps: PoliceStations):
    '''
    Finds all police stations within a certain radius.
    Returns only the police stations in the correct radius.
    '''
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
    run = maps_client.actor("compass/crawler-google-places").call(run_input=run_input)
    p_stations = []

    for item in maps_client.dataset(run["defaultDatasetId"]).iterate_items():
        p_stations.append(item)

    return p_stations

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
        return {"status": -1, "error_message": {e}}
    
def get_coords(address):
    '''
    Uses Google Maps Geolocation API to return coordinates from an address
    '''
    try:
        url = f"{GEO_URL}address={address}&key={GEO_KEY}"
        print(url)
        response = requests.get(url)
        r_json = response.json()
        t_coords = r_json["results"][0]["geometry"]["location"]
        coords = [t_coords["lat"], t_coords["lng"]]
        return {"status": 0, "data": coords}
    
    except Exception as e:
        return {"status": -1, "error_message": e}

# SOCIAL SENTIMENT

@router.post("/public-sentiment/")
def pub_sent(ps: PublicSentiment):
    return {"status": 0, "data": ps}

# METRIC SCORE

@router.post("/safety-metric/")
async def safety_metric(crime: Crime):
    score = 10

    recs = crime_recs(crime)
    recs = recs["recommendations"]

    return recs

    return {"status": 0, "data": score}
    