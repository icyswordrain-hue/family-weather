import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("CWA_API_KEY")

url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-071"
params = {"Authorization": api_key, "format": "JSON", "locationName": "板橋區"}
resp = requests.get(url, params=params, verify=False)
data = resp.json()
elements = data['records']['Locations'][0]['Location'][0]['WeatherElement']
for el in elements:
    print(el['ElementName'], "-", el['Description'])
