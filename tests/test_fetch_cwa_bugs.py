import pytest
from data.fetch_cwa import fetch_forecast

def test_fetch_forecast_name_error(mocker):
    data = {
        "success": "true",
        "records": {
            "locations": [{"location": [{"locationName": "三峽區", "weatherElement": [
                {"elementName": "WeatherCode", "time": [{"startTime": "2026-02-22T18:00:00+08:00", "endTime": "2026-02-23T06:00:00+08:00", "elementValue": [{"value": "1"}]}]}
            ]}]}]
        }
    }
    mocker.patch("requests.get")
    mocker.patch("data.fetch_cwa.json.loads", return_value=data)
    
    # Should raise NameError if not fixed
    fetch_forecast()
