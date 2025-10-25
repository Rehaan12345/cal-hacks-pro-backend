from scraper import find_distance, get_coords, scrape_civic_hub, claude_compose
from firecrawl import Firecrawl
import os, requests, json, re
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
import asyncio

load_dotenv()

client = Firecrawl(api_key=os.environ.get("FIRE_KEY"))

# API_KEY = "GnxDXsSkeUSOTgwNHVdgJQlvYrCfdnlgzsdSSBT1"
# BASE = "https://api.usa.gov/crime/fbi/cde"

# def get_fbi_data(crime="aggravated-assault", data_type="victim", level="national", sublevel="age"):
#     url = f"{BASE}/{crime}/{data_type}/{level}/{sublevel}?api_key={API_KEY}"
#     r = requests.get(url)
#     r.raise_for_status()
#     return r.json()

async def main():
    # print(find_distance(["37.781146897023916", "-122.41645173191911"], ["37.802167204586695", "-122.44930210031018"]))
    # print(get_coords("Asian Art Museum, 200 Larkin St, San Francisco, CA 94102"))

    # url = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"

    # API_KEY = "GnxDXsSkeUSOTgwNHVdgJQlvYrCfdnlgzsdSSBT1"
    # url = f"https://api.usa.gov/crime/fbi/sapi/api/data/nibrs/aggravated-assault/offense/national?api_key={API_KEY}"
    # data = requests.get(url).json()
    # print(data)

    # data = get_fbi_data()
    # print(data["results"][:3])

    # data = await scrape_civic_hub("alamo-square")
    # print(data)

    user = {
        "jewelry": "silver bracelet, gold necklace",
        "clothes": "medium expensive, not too flashy",
        "time of day": "3:00 p.m. to 9:00 p.m."
    }

    nhood = await scrape_civic_hub("Civic Center")
    data = claude_compose(user, nhood)

    print(data)

    

if __name__ == "__main__":
    asyncio.run(main())