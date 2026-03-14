"""test_cloud_proxy.py — Tests for Cloud Run URL generation, proxy endpoints,
and broadcast cache behaviour in CLOUD mode."""
import json
import pytest
from unittest.mock import patch, MagicMock

from app import app


@pytest.fixture(autouse=True)
def _clear_broadcast_cache():
    """Clear the in-memory broadcast cache between tests."""
    import app as app_mod
    app_mod._broadcast_cache.clear()
    app_mod._chat_context_cache.clear()
    yield
    app_mod._broadcast_cache.clear()
    app_mod._chat_context_cache.clear()


# ── /api/health & /api/warmup ────────────────────────────────────────────────


def test_health_returns_ok():
    with app.test_client() as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert "timestamp" in data


def test_warmup_returns_ok():
    with app.test_client() as client:
        res = client.get("/api/warmup")
        assert res.status_code == 200
        assert res.get_json()["status"] == "warm"


# ── /api/broadcast (CLOUD mode) ─────────────────────────────────────────────


def test_broadcast_cloud_missing_url(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.delenv("MODAL_BROADCAST_URL", raising=False)
    with app.test_client() as client:
        res = client.get("/api/broadcast")
        assert res.status_code == 500
        assert "not configured" in res.get_json()["error"]


def test_broadcast_cloud_proxy_success(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_BROADCAST_URL", "https://modal.example.com/broadcast")

    fake_broadcast = {"date": "2026-03-14", "narration_text": "Hello"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_broadcast
    mock_resp.text = json.dumps(fake_broadcast)
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}

    with patch("app.requests.get", return_value=mock_resp) as mock_get:
        with app.test_client() as client:
            res = client.get("/api/broadcast?date=2026-03-14&lang=en")
            assert res.status_code == 200
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert call_kwargs[1]["params"] == {"date": "2026-03-14", "lang": "en"}

    # Verify broadcast was cached for chat
    import app as app_mod
    assert "2026-03-14" in app_mod._broadcast_cache


def test_broadcast_cloud_proxy_failure(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_BROADCAST_URL", "https://modal.example.com/broadcast")

    with patch("app.requests.get", side_effect=ConnectionError("timeout")):
        with app.test_client() as client:
            res = client.get("/api/broadcast?date=2026-03-14")
            assert res.status_code == 500
            assert "timeout" in res.get_json()["error"]


# ── /api/refresh (CLOUD mode) ───────────────────────────────────────────────


def test_refresh_cloud_missing_url(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.delenv("MODAL_REFRESH_URL", raising=False)
    with app.test_client() as client:
        res = client.post("/api/refresh", json={"date": "2026-03-14"})
        assert res.status_code == 500
        assert "not configured" in res.get_json()["error"]


def test_refresh_cloud_proxy_success(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_REFRESH_URL", "https://modal.example.com/refresh")

    ndjson_lines = [
        json.dumps({"type": "log", "message": "Starting..."}) + "\n",
        json.dumps({"type": "result", "payload": {"date": "2026-03-14"}}) + "\n",
    ]
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = iter([line.encode() for line in ndjson_lines])
    mock_resp.headers = {"content-type": "application/x-ndjson"}

    with patch("app.requests.post", return_value=mock_resp) as mock_post:
        with app.test_client() as client:
            res = client.post("/api/refresh", json={"date": "2026-03-14", "lang": "en"})
            assert res.status_code == 200
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "modal.example.com" in call_args[0][0]
            body = call_args[1]["json"]
            assert body["date"] == "2026-03-14"
            assert body["lang"] == "en"


def test_refresh_cloud_proxy_failure(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_REFRESH_URL", "https://modal.example.com/refresh")

    with patch("app.requests.post", side_effect=TimeoutError("read timed out")):
        with app.test_client() as client:
            res = client.post("/api/refresh", json={"date": "2026-03-14"})
            assert res.status_code == 500
            assert "timed out" in res.get_json()["error"]


# ── /api/chat (CLOUD mode) ──────────────────────────────────────────────────


def test_chat_no_broadcast_returns_503(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.delenv("MODAL_BROADCAST_URL", raising=False)
    with app.test_client() as client:
        res = client.post("/api/chat", json={
            "message": "Will it rain?",
            "date": "2026-03-14",
        })
        assert res.status_code == 503
        assert res.get_json()["code"] == "no_broadcast"


def test_chat_uses_cached_broadcast(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    import app as app_mod
    app_mod._broadcast_cache["2026-03-14"] = {
        "narration_text": "Sunny day",
        "processed_data": {"current": {"AT": 25}},
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="It will be sunny!")]
    mock_client.messages.create.return_value = mock_response

    with patch("narration.claude_client._get_client", return_value=mock_client):
        with patch("narration.chat_context.build_chat_context", return_value="system prompt"):
            with app.test_client() as client:
                res = client.post("/api/chat", json={
                    "message": "Will it rain?",
                    "date": "2026-03-14",
                })
                assert res.status_code == 200
                assert res.get_json()["reply"] == "It will be sunny!"


def test_chat_fetches_broadcast_from_modal(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_BROADCAST_URL", "https://modal.example.com/broadcast")

    fake_broadcast = {"narration_text": "Rainy", "processed_data": {"current": {}}}
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = fake_broadcast

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Bring an umbrella")]
    mock_client.messages.create.return_value = mock_response

    with patch("app.requests.get", return_value=mock_get_resp):
        with patch("narration.claude_client._get_client", return_value=mock_client):
            with patch("narration.chat_context.build_chat_context", return_value="system prompt"):
                with app.test_client() as client:
                    res = client.post("/api/chat", json={
                        "message": "Do I need an umbrella?",
                        "date": "2026-03-14",
                    })
                    assert res.status_code == 200
                    assert "umbrella" in res.get_json()["reply"].lower()


# ── _get_broadcast_for_chat helper ───────────────────────────────────────────


def test_get_broadcast_for_chat_returns_cached(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    import app as app_mod
    app_mod._broadcast_cache["2026-03-14"] = {"test": True}
    result = app_mod._get_broadcast_for_chat("2026-03-14")
    assert result == {"test": True}


def test_get_broadcast_for_chat_fetches_from_modal(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.setenv("MODAL_BROADCAST_URL", "https://modal.example.com/broadcast")

    fake = {"narration_text": "test"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake

    import app as app_mod
    with patch("app.requests.get", return_value=mock_resp):
        result = app_mod._get_broadcast_for_chat("2026-03-14")
        assert result == fake
        assert app_mod._broadcast_cache["2026-03-14"] == fake


def test_get_broadcast_for_chat_no_url_returns_none(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    monkeypatch.delenv("MODAL_BROADCAST_URL", raising=False)
    import app as app_mod
    result = app_mod._get_broadcast_for_chat("2026-03-14")
    assert result is None


# ── Audio URL patterns ───────────────────────────────────────────────────────


def test_tts_cache_key_format():
    from narration.tts_client import tts_cache_key
    key = tts_cache_key("Hello world", "en", "2026-03-14", "morning")
    assert key.startswith("audio/2026-03-14/")
    assert "morning_en_" in key
    assert key.endswith(".mp3")


def test_tts_cache_key_differs_by_lang():
    from narration.tts_client import tts_cache_key
    key_en = tts_cache_key("Hello", "en", "2026-03-14", "morning")
    key_zh = tts_cache_key("Hello", "zh-TW", "2026-03-14", "morning")
    assert key_en != key_zh
    assert "_en_" in key_en
    assert "_zh-TW_" in key_zh


def test_tts_cache_key_differs_by_content():
    from narration.tts_client import tts_cache_key
    key_a = tts_cache_key("Hello world", "en", "2026-03-14", "morning")
    key_b = tts_cache_key("Goodbye world", "en", "2026-03-14", "morning")
    assert key_a != key_b


def test_synthesise_local_returns_api_audio_path(monkeypatch):
    """LOCAL mode returns /api/audio/... path."""
    from narration import tts_client
    monkeypatch.setenv("RUN_MODE", "LOCAL")
    monkeypatch.setattr(tts_client, "RUN_MODE", "LOCAL")

    with patch.object(tts_client, "_render_tts", return_value=b"fake-audio"):
        with patch("narration.tts_client.Path") as MockPath:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = False
            mock_path_inst.parent.mkdir = MagicMock()
            mock_path_inst.write_bytes = MagicMock()
            MockPath.return_value.__truediv__ = MagicMock(return_value=mock_path_inst)
            MockPath.return_value = mock_path_inst

            # Directly call with a controlled path
            url = tts_client.synthesise_with_cache("Hello", "en", "2026-03-14", "morning")
            assert url.startswith("/api/audio/")
            assert url.endswith(".mp3")


def test_synthesise_cloud_returns_gcs_url(monkeypatch):
    """CLOUD/MODAL mode returns GCS public URL."""
    from narration import tts_client
    monkeypatch.setenv("RUN_MODE", "CLOUD")
    monkeypatch.setattr(tts_client, "RUN_MODE", "CLOUD")

    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.public_url = "https://storage.googleapis.com/bucket/audio/2026-03-14/morning_en_abc.mp3"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_storage_module = MagicMock()
    mock_storage_module.Client.return_value.bucket.return_value = mock_bucket

    with patch.dict("sys.modules", {"google.cloud.storage": mock_storage_module, "google.cloud": MagicMock(), "google": MagicMock()}):
        # Re-import to pick up the mocked module
        url = tts_client.synthesise_with_cache("Hello", "en", "2026-03-14", "morning")
        assert url.startswith("https://storage.googleapis.com/")


# ── Chat validation ──────────────────────────────────────────────────────────


def test_chat_rejects_empty_message(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "LOCAL")
    with app.test_client() as client:
        res = client.post("/api/chat", json={"message": ""})
        assert res.status_code == 400
        assert res.get_json()["code"] == "bad_request"


def test_chat_rejects_long_message(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "LOCAL")
    with app.test_client() as client:
        res = client.post("/api/chat", json={"message": "x" * 501})
        assert res.status_code == 400
        assert res.get_json()["code"] == "bad_request"
