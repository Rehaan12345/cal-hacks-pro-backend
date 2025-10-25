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

  
def parse_crime_table(CIVIC_HUB_BASE, neighborhood):
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    url = f"{CIVIC_HUB_BASE}/{neighborhood}"
    print(f"Fetching: {url}")

    # Step 1 – get static HTML
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")

    # Step 2 – if table missing or suspiciously constant (289 rows), check for data endpoints
    if not table:
        print("⚠️  No table tag found — trying to locate data source in page scripts...")
    else:
        rows = table.find_all("tr")
        if len(rows) == 289:  # CivicHub placeholder table symptom
            print("⚠️  Detected placeholder table (289 rows) — attempting API lookup...")
        else:
            # ✅ Static table looks legitimate
            table_data = []
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_data = [cell.get_text(strip=True) for cell in cells]
                table_data.append(row_data)
            crime_amount = len(rows) - 1 if rows and rows[0].find("th") else len(rows)
            table_data.append({"crime_amount": crime_amount})
            return table_data

    # Step 3 – try to extract JSON or CSV endpoint URLs embedded in the page
    scripts = soup.find_all("script")
    api_url = None
    for script in scripts:
        if script.string and "crime-data" in script.string:
            match = re.search(r"https://[^\s'\"]+crime-data[^\s'\"]+", script.string)
            if match:
                api_url = match.group(0)
                break

    if api_url:
        print(f"Found possible data API: {api_url}")
        try:
            data_resp = requests.get(api_url, headers=headers, timeout=30)
            data_resp.raise_for_status()
            # Try JSON first
            if data_resp.headers.get("Content-Type", "").startswith("application/json"):
                data = data_resp.json()
                table_data = data.get("data") or data
                crime_amount = len(table_data)
                table_data.append({"crime_amount": crime_amount})
                return table_data
            # Try CSV fallback
            elif "text/csv" in data_resp.headers.get("Content-Type", ""):
                lines = data_resp.text.splitlines()
                table_data = [line.split(",") for line in lines]
                crime_amount = len(table_data) - 1
                table_data.append({"crime_amount": crime_amount})
                return table_data
        except Exception as e:
            print(f"⚠️  Failed to fetch data from detected API: {e}")

    print("❌ Could not find valid data source.")
    return []


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

    # p_data = PoliceStations(
    #     coords=[
    #         "37.78126085987053", 
    #         "-122.4164403448156"
    #     ],
    #     neighborhood="Civic Center",
    #     city="San Francisco",
    #     state="California",
    #     max_search=10,
    #     radius=1
    # )

    # p_stations = find_police("San Francisco", "California", 10)

    # data = []
    # for i in range(1, 4):
    #     data.append(filter_police([
    #         "37.78126085987053", 
    #         "-122.4164403448156"
    #     ], p_stations, i))

    # print(data, len(data))

    data = parse_crime_table(
        "https://www.civichub.us/ca/san-francisco/gov/police-department/crime-data",
        "ingleside"
    )
    print(data)
    print("-" * 25)
    print(data[-1])

if __name__ == "__main__":
    asyncio.run(main())