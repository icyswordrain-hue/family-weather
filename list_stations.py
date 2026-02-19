import requests
import json

API_KEY = "CWA-148CA2A7-11C1-4E65-8C51-3EEBAAA5F96A"
URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"

params = {
    "Authorization": API_KEY,
    "format": "JSON",
    "StationStatus": "OPEN" # Optional, to get only active stations
}

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    response = requests.get(URL, params=params, timeout=30, verify=False)
    response.raise_for_status()
    data = response.json()
    
    stations = data.get("records", {}).get("Station", [])
    print(f"Found {len(stations)} stations.")
    
    # Filter for New Taipei City (or Banqiao in address/name)
    candidates = []
    for s in stations:
        name = s.get("StationName", "")
        addr = s.get("StationAddress", "") # Note: O-A0003-001 might not return address, let's check GeoInfo
        geo = s.get("GeoInfo", {})
        town = geo.get("TownName", "")
        county = geo.get("CountyName", "") # or CityName

        # Check location
        if "新北" in county or "板橋" in name or "板橋" in town:
             candidates.append(f"{s.get('StationId')} - {name} ({county}{town})")
    
    with open("stations.txt", "w", encoding="utf-8") as f:
        f.write("Results for New Taipei/Banqiao:\n")
        for c in candidates:
            f.write(c + "\n")
    print("Written to stations.txt")

except Exception as e:
    print(f"Error: {e}")
