"""
solar.py — Sunrise/sunset and solar event calculator.

Uses the `astral` library (pure Python) with the configured lat/lon from config.
Returns a plain dict; no side effects.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from astral import LocationInfo
from astral.sun import sun

CST = timezone(timedelta(hours=8))


def get_solar_times(for_date: date, lat: float, lon: float) -> dict:
    """
    Return solar event times for the given date at the given coordinates.

    All times are expressed as "HH:MM" strings in Asia/Taipei (UTC+8).

    Returns:
        {
            "sunrise":          "06:12",
            "sunset":           "18:07",
            "solar_noon":       "12:09",
            "day_length_hours": 11.9,
            "is_daytime":       True,
            "next_event":       {"type": "sunset", "at": "18:07", "in_minutes": 45}
        }
    """
    loc = LocationInfo(latitude=lat, longitude=lon, timezone="Asia/Taipei")
    s = sun(loc.observer, date=for_date, tzinfo=CST)

    sunrise = s["sunrise"]
    sunset  = s["sunset"]
    noon    = s["noon"]
    day_len = (sunset - sunrise).total_seconds() / 3600

    now = datetime.now(CST)
    is_daytime = sunrise <= now <= sunset

    if now < sunrise:
        next_event = {
            "type": "sunrise",
            "at": sunrise.strftime("%H:%M"),
            "in_minutes": int((sunrise - now).total_seconds() / 60),
        }
    elif now < sunset:
        next_event = {
            "type": "sunset",
            "at": sunset.strftime("%H:%M"),
            "in_minutes": int((sunset - now).total_seconds() / 60),
        }
    else:
        # Past sunset — next event is tomorrow's sunrise
        tomorrow = sun(loc.observer, date=for_date + timedelta(days=1), tzinfo=CST)
        sr_tomorrow = tomorrow["sunrise"]
        next_event = {
            "type": "sunrise",
            "at": sr_tomorrow.strftime("%H:%M"),
            "in_minutes": int((sr_tomorrow - now).total_seconds() / 60),
        }

    return {
        "sunrise":          sunrise.strftime("%H:%M"),
        "sunset":           sunset.strftime("%H:%M"),
        "solar_noon":       noon.strftime("%H:%M"),
        "day_length_hours": round(day_len, 1),
        "is_daytime":       is_daytime,
        "next_event":       next_event,
    }
