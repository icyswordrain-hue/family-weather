"""health_alerts.py — Cardiac safety and Ménière's risk detection."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

def _cardiac_alert(segmented: dict[str, Optional[dict]]) -> dict:
    """Flag cardiac risk if temperature is low and precipitation/humidity is high."""
    triggered = False
    reasons = []
    
    # Morning is most critical for cardiac events
    morn = segmented.get("Morning")
    if morn:
        at = morn.get("AT")
        pop = morn.get("PoP6h") or 0
        
        if at is not None and at <= 15:
            if pop >= 50:
                triggered = True
                reasons.append("Cold & Wet morning — vascular constriction risk")
            elif at <= 10:
                triggered = True
                reasons.append("Extreme cold — strain risk")

    return {
        "triggered": triggered,
        "reasons": reasons,
        "type": "Cardiac"
    }


def _detect_menieres_alert(
    current: dict,
    station_history: list[dict] | None = None,
) -> dict:
    """Detect conditions triggering Ménière's symptoms (pressure swings, high humidity)."""
    triggered = False
    severity = "none"
    reasons = []

    # 1. Barometric Pressure Swing
    pres = current.get("PRES")
    if pres is not None:
        if pres < 1005:
            # Moderate risk — record for observability but do not trigger alert
            severity = "moderate"
            reasons.append(f"Low pressure ({pres}hPa)")

        # Use fine-grained station history for 24h trend when available
        if station_history and len(station_history) >= 2:
            from data.station_history import pressure_change_24h
            delta = pressure_change_24h(station_history)
            if delta is not None and abs(delta) >= 6:
                triggered = True
                severity = "high"
                direction = "rise" if delta > 0 else "drop"
                reasons.append(f"Pressure {direction} {abs(delta):.1f} hPa over 24h")

    # 2. Extreme Humidity — moderate risk only, does not trigger alert
    rh = current.get("RH")
    if rh is not None and rh > 85:
        if severity == "none": severity = "moderate"
        reasons.append("High humidity discomfort")

    return {
        "triggered": triggered,
        "severity": severity,
        "reasons": reasons,
        "type": "Menieres"
    }


def _compute_heads_ups(
    segmented: dict[str, Optional[dict]],
    morning_commute: dict,
    evening_commute: dict,
    aqi: dict,
    cardiac: dict,
    menieres: dict,
) -> list[dict]:
    """Priority-ordered list of critical dashboard alerts."""
    alerts = []
    
    # Priority 1: Critical Health
    if cardiac.get("triggered"):
        alerts.append({"level": "CRITICAL", "type": "Health", "msg": cardiac["reasons"][0]})
    if menieres.get("triggered"):  # only True for severity=="high" (rapid pressure change)
        alerts.append({"level": "CRITICAL", "type": "Health", "msg": "High Ménière's risk — avoid sudden movements"})

    # Priority 2: Weather Hazards
    for commute in [morning_commute, evening_commute]:
        for hazard in commute.get("hazards", []):
            alerts.append({"level": "WARNING", "type": "Commute", "msg": hazard})

    # Priority 3: Air Quality
    aqi_val = aqi.get("realtime", {}).get("aqi")
    if aqi_val and aqi_val > 100:
        status = aqi.get("realtime", {}).get("status", "Poor")
        alerts.append({"level": "WARNING", "type": "Air", "msg": f"AQI is {status} ({aqi_val})"})

    return alerts
