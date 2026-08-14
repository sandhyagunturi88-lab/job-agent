"""API-level tests (dev mode: demo user, in-memory checkpointer)."""

from app.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    return TestClient(create_app())


def test_healthz():
    with _client() as client:
        assert client.get("/healthz").json() == {"status": "ok"}


def test_start_is_idempotent_per_day_and_resumes_through_interrupts():
    with _client() as client:
        first = client.post("/api/v1/runs/start", json={"run_date": "2026-08-14"}).json()
        assert first["interrupt"]["type"] == "pick_jobs"
        thread_id = first["thread_id"]

        # Re-triggering the same day's run returns the same thread, still at
        # interrupt 1 — no duplicate matches, no double-charged quota.
        again = client.post("/api/v1/runs/start", json={"run_date": "2026-08-14"}).json()
        assert again["thread_id"] == thread_id
        assert again["interrupt"]["type"] == "pick_jobs"

        job_id = first["interrupt"]["matches"][0]["job"]["id"]
        second = client.post(
            f"/api/v1/runs/{thread_id}/resume",
            json={"value": {"selected_job_ids": [job_id]}},
        ).json()
        assert second["interrupt"]["type"] == "approve_cv"

        done = client.post(
            f"/api/v1/runs/{thread_id}/resume", json={"value": {"approved": True}}
        ).json()
        assert done["phase"] == "done"
        assert len(done["values"]["application_packs"]) == 1

        # Resuming a finished run is a 409, not a re-run
        conflict = client.post(f"/api/v1/runs/{thread_id}/resume", json={"value": {}})
        assert conflict.status_code == 409


def test_gdpr_endpoints_exist():
    with _client() as client:
        export = client.get("/api/v1/me/export").json()
        assert "cv_inventory" in export
        deletion = client.delete("/api/v1/me")
        assert deletion.status_code == 202
        assert "30 days" in deletion.json()["detail"]
