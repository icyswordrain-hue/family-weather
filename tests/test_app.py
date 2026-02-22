import pytest
from app import app

def test_debug_log_forbidden_in_cloud(monkeypatch):
    # Mock config.RUN_MODE to CLOUD
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    with app.test_client() as client:
        res = client.post("/debug/log", json={"msg": "test"})
        assert res.status_code == 403

def test_debug_log_allowed_in_local(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "LOCAL")
    with app.test_client() as client:
        res = client.post("/debug/log", json={"msg": "test"})
        assert res.status_code == 200
