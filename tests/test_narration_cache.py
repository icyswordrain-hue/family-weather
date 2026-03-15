from backend.cache import NarrationCache, make_cache_key

def test_cache_key_includes_lang():
    key_en = make_cache_key('en', 'Shulin', 'Rain', 'morning')
    key_zh = make_cache_key('zh-TW', 'Shulin', 'Rain', 'morning')
    assert key_en != key_zh
    assert key_en.startswith('en_')
    assert key_zh.startswith('zh-tw_')

def test_cache_key_same_temp_bucket():
    """Temps within same 3°C bucket produce identical keys."""
    key1 = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24)
    key2 = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=25)
    assert key1 == key2  # both round to 24

def test_cache_key_different_temp_bucket():
    """Temps in different 3°C buckets produce different keys."""
    key1 = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24)
    key2 = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=27)
    assert key1 != key2  # 24 vs 27

def test_cache_key_rain_flag():
    """Rain flag changes the cache key."""
    key_dry = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24, rain=False)
    key_wet = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24, rain=True)
    assert key_dry != key_wet

def test_cache_key_differs_by_wx_class():
    key_rain = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24)
    key_sunny = make_cache_key('en', "Shulin", "Sunny", "morning", temp_c=24)
    assert key_rain != key_sunny

def test_cache_key_differs_by_time_of_day():
    key_am = make_cache_key('en', "Shulin", "Rain", "morning", temp_c=24)
    key_pm = make_cache_key('en', "Shulin", "Rain", "evening", temp_c=24)
    assert key_am != key_pm

def test_cache_hit_returns_cached_value():
    cache = NarrationCache(ttl_seconds=60)
    cache.set("test_key", ("narration text", "claude"))
    result = cache.get("test_key")
    assert result == ("narration text", "claude")

def test_cache_miss_returns_none():
    cache = NarrationCache(ttl_seconds=60)
    assert cache.get("missing_key") is None
