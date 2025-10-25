from scraper import find_distance, get_coords, scrape_civic_hub, claude_compose, safety_metric, police_stations, PoliceStations, find_police, filter_police
from firecrawl import Firecrawl
import os, requests, json, re
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import time

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

    # user = {
    #     "jewelry": "silver bracelet, gold necklace",
    #     "clothes": "medium expensive, not too flashy",
    #     "time of day": "3:00 p.m. to 9:00 p.m."
    # }

    # nhood = await scrape_civic_hub("Civic Center")
    # data = claude_compose(user, nhood)

    # print(data)

    # curr_time = datetime.now().time()
    # hour = int(curr_time.hour())
    # ind_c = curr_time.find(":")
    # print()

    p_data = PoliceStations(
        coords=[
            "37.78126085987053", 
            "-122.4164403448156"
        ],
        neighborhood="Civic Center",
        city="San Francisco",
        state="California",
        max_search=10,
        radius=1
    )

    p_stations = find_police("San Francisco", "California", 10)

    data = []
    for i in range(1, 4):
        data.append(filter_police([
            "37.78126085987053", 
            "-122.4164403448156"
        ], p_stations, i))

    print(data, len(data))
    

if __name__ == "__main__":
    asyncio.run(main())