"""API contract smoke tests. Run: pip install pytest httpx; PYTHONPATH=backend pytest -q backend/tests
Uses an isolated temporary data tree: never modifies the shipped synthetic demo data.
"""
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("echomind-integration")
    root = Path(__file__).resolve().parents[2]
    shutil.copytree(root / "data" / "persona", tmp / "persona")
    shutil.copytree(root / "data" / "synthetic", tmp / "synthetic")
    shutil.copyfile(root / "data" / "memories.json", tmp / "memories.json")
    orig_env = dict(os.environ)
    os.environ.update({
        "DATA_DIR": str(tmp),
        "PERSONA_DIR": str(tmp / "persona"),
        "UPLOADS_DIR": str(tmp / "runtime" / "uploads"),
        "MEMORIES_FILE": str(tmp / "memories.json"),
        "AUDIT_FILE": str(tmp / "runtime" / "audit.json"),
        "DRAFTS_FILE": str(tmp / "runtime" / "drafts.json"),
        "OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "",
    })
    # The app config captures environment defaults upon module import.
    from app.main import app
    from app.config import get_settings
    get_settings.cache_clear()
    with TestClient(app) as instance:
        yield instance
    os.environ.clear()
    os.environ.update(orig_env)


def test_persona_get_and_edit_preserves_unchanged_rules(client):
    r = client.get("/api/persona")
    assert r.status_code == 200
    p = r.json()
    assert p["name"]
    assert len(p["decision_heuristics"]) >= 2
    old_rule = p["decision_heuristics"][0]
    p["knowledge_facts"].append("Manually confirmed statement")
    p["decision_heuristics"].append("Never accept unverified customer claims")
    edited = client.put("/api/persona", json=p)
    assert edited.status_code == 200, edited.text
    updated = edited.json()
    assert old_rule in updated["decision_heuristics"]
    assert "Never accept unverified customer claims" in updated["decision_heuristics"]
    assert updated["persona_version"] > p["persona_version"]


def test_upload_ingestion_and_live_persona(client):
    content = b"Project note. Use synthetic testing and owner review before deployment."
    r = client.post("/api/ingest", files={"files": ("test-note.txt", content, "text/plain")})
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["count"] == 1
    assert payload["chunks"] > 0
    assert payload["persona"]["persona_version"] == payload["persona_version"]
    latest = client.get("/api/persona").json()
    assert latest["source_stats"]["note"] == 1
    assert "Manually confirmed statement" in latest["knowledge_facts"]


def test_draft_review_and_audit_are_persistent(client):
    r = client.post("/api/twin/respond", json={"incoming_message": "When will we deploy?"})
    assert r.status_code == 200, r.text
    draft = r.json()
    assert draft["status"] == "needs_human_input"
    assert draft["is_uncertain"] is True
    assert draft["confidence_score"] == 0
    approved = client.post(f"/api/twin/review/{draft['draft_id']}", json={
        "action": "approved", "edited_reply": "Approved by the owner"
    })
    assert approved.status_code == 200
    assert approved.json()["sent"] is False
    audit = client.get("/api/audit").json()["events"]
    assert audit[0]["reply"] == "Approved by the owner"
    repeated = client.post(f"/api/twin/review/{draft['draft_id']}", json={
        "action": "rejected", "edited_reply": ""
    })
    assert repeated.status_code == 409


def test_evaluation_needs_live_llm(client):
    assert client.get("/api/evaluation/latest").status_code == 200
    r = client.post("/api/evaluation/run?limit=1")
    assert r.status_code == 503


def test_upload_validation(client):
    r = client.post("/api/ingest", files={"files": ("script.exe", b"unsafe", "application/octet-stream")})
    assert r.status_code == 415
