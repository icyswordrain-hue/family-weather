"""tests/test_scales.py — Unit tests for data/scales.py"""
from data.scales import (
    _val_to_scale, _wind_to_level, _aqi_to_level,
    wind_ms_to_beaufort, _beaufort_index, wx_to_cloud_cover,
    degrees_to_cardinal, pop_to_text, translate_aqi_status, translate_pollutant,
    wx_to_pop, _hum_to_scale,
    UV_SCALE, PRECIP_SCALE_5, PRES_SCALE_5, VIS_SCALE_5, BEAUFORT_SCALE_5,
)

# ── _val_to_scale ──────────────────────────────────────────────────────────────

def test_uv_low():         assert _val_to_scale(1, UV_SCALE) == ("Low", 1)
def test_uv_moderate():    assert _val_to_scale(3, UV_SCALE) == ("Moderate", 2)
def test_uv_high():        assert _val_to_scale(6, UV_SCALE) == ("High", 3)
def test_uv_very_high():   assert _val_to_scale(9, UV_SCALE) == ("Very High", 4)
def test_uv_extreme():     assert _val_to_scale(12, UV_SCALE) == ("Extreme", 5)
def test_uv_none():        assert _val_to_scale(None, UV_SCALE) == ("Unknown", 0)

def test_precip_dry():     assert _val_to_scale(0, PRECIP_SCALE_5)[0] == "Dry"
def test_precip_unlikely(): assert _val_to_scale(30, PRECIP_SCALE_5)[0] == "Unlikely"
def test_precip_possible(): assert _val_to_scale(50, PRECIP_SCALE_5)[0] == "Possible"
def test_precip_likely():   assert _val_to_scale(70, PRECIP_SCALE_5)[0] == "Likely"
def test_precip_very_likely(): assert _val_to_scale(90, PRECIP_SCALE_5)[0] == "Very Likely"

def test_hum_dry():        assert _hum_to_scale(15)[0] == "Very Dry"
def test_hum_soggy():      assert _hum_to_scale(90)[0] == "Very Humid"

def test_vis_very_poor():  assert _val_to_scale(0.5, VIS_SCALE_5)[0] == "Very Poor"
def test_vis_excellent():  assert _val_to_scale(15.0, VIS_SCALE_5)[0] == "Excellent"

# ── wind helpers ───────────────────────────────────────────────────────────────

def test_wind_calm():      assert wind_ms_to_beaufort(0.2) == "Calm"
def test_wind_gale():      assert wind_ms_to_beaufort(18.0) == "Gale"
def test_wind_none():      assert wind_ms_to_beaufort(None) == "Unknown"

def test_beaufort_calm():  assert _beaufort_index(0.2) == 0
def test_beaufort_gale():  assert _beaufort_index(18.0) == 8

def test_wind_level_calm():   assert _wind_to_level(0.5) == 1
def test_wind_level_storm():  assert _wind_to_level(25.0) == 5
def test_wind_level_none():   assert _wind_to_level(None) == 0

# ── AQI ───────────────────────────────────────────────────────────────────────

def test_aqi_good():       assert _aqi_to_level(40) == 1
def test_aqi_moderate():   assert _aqi_to_level(80) == 2
def test_aqi_sensitive():  assert _aqi_to_level(120) == 3
def test_aqi_unhealthy():  assert _aqi_to_level(180) == 4
def test_aqi_hazardous():  assert _aqi_to_level(350) == 5
def test_aqi_none():       assert _aqi_to_level(None) == 0

# ── text helpers ──────────────────────────────────────────────────────────────

def test_wx_sunny():       assert wx_to_cloud_cover(1) == "Sunny"
def test_wx_fair():        assert wx_to_cloud_cover(2) == "Fair"
def test_wx_overcast():    assert wx_to_cloud_cover(12) == "Rain"
def test_wx_none():        assert wx_to_cloud_cover(None) == "Unknown"

def test_cardinal_north():  assert degrees_to_cardinal(0) == "N"
def test_cardinal_east():   assert degrees_to_cardinal(90) == "E"
def test_cardinal_south():  assert degrees_to_cardinal(180) == "S"
def test_cardinal_none():   assert degrees_to_cardinal(None) == "Unknown"

def test_pop_dry():        assert pop_to_text(0) == "Dry"
def test_pop_unlikely():   assert pop_to_text(30) == "Unlikely"
def test_pop_none():       assert pop_to_text(None) == "Unknown"

def test_aqi_status_good():     assert translate_aqi_status("良好") == "Good"
def test_aqi_status_unhealthy(): assert translate_aqi_status("不健康") == "Unhealthy"

def test_pollutant_pm25():  assert translate_pollutant("細懸浮微粒") == "PM2.5"
def test_pollutant_o3():    assert translate_pollutant("臭氧") == "O3"


def test_wx_to_pop():
    assert wx_to_pop(1) == 0      # Sunny/Clear
    assert wx_to_pop(4) == 20     # Cloudy
    assert wx_to_pop(8) == 50     # Showers
    assert wx_to_pop(15) == 80    # Thunderstorms
    assert wx_to_pop(None) is None
