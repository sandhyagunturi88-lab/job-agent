"""Onboarding + tracker endpoints, and the run using the stored profile."""

from app.main import create_app
from fastapi.testclient import TestClient
from test_cv_parse import SAMPLE_CV

PROFILE = {
    "desired_titles": ["Senior Python Engineer"],
    "locations": ["London", "Remote"],
    "min_salary": 70000,
    "contract_types": ["permanent"],
    "avoid_keywords": [],
    "notes": [],
}


def _client() -> TestClient:
    return TestClient(create_app())


def test_cv_upload_builds_inventory():
    with _client() as client:
        res = client.post("/api/v1/me/cv", json={"cv_text": SAMPLE_CV})
        assert res.status_code == 200
        body = res.json()
        assert body["counts"]["skill"] >= 4
        assert body["counts"]["role"] >= 1
        assert body["counts"]["achievement"] >= 2

        inventory = client.get("/api/v1/me/inventory").json()
        assert len(inventory) == len(body["inventory"])


def test_cv_upload_rejects_unusable_text():
    with _client() as client:
        # long enough to pass the length gate, but nothing survives parsing
        # (contact lines are never evidence)
        junk = "jane@example.com\nlinkedin.com/in/janedoe\ngithub.com/janedoe\n" * 2
        assert client.post("/api/v1/me/cv", json={"cv_text": junk}).status_code == 422


def test_onboarded_requires_cv_and_preferences():
    with _client() as client:
        assert client.get("/api/v1/me/profile").json()["onboarded"] is False

        client.put("/api/v1/me/profile", json=PROFILE)
        assert client.get("/api/v1/me/profile").json()["onboarded"] is False  # no CV yet

        client.post("/api/v1/me/cv", json={"cv_text": SAMPLE_CV})
        state = client.get("/api/v1/me/profile").json()
        assert state["onboarded"] is True
        assert state["profile"]["min_salary"] == 70000
        assert state["plan"] == "free"

        client.put("/api/v1/me/plan", json={"plan": "pro"})
        assert client.get("/api/v1/me/profile").json()["plan"] == "pro"


def test_run_uses_stored_profile_and_feeds_tracker():
    with _client() as client:
        client.post("/api/v1/me/cv", json={"cv_text": SAMPLE_CV})
        client.put("/api/v1/me/profile", json=PROFILE)

        start = client.post("/api/v1/runs/start", json={"run_date": "2026-08-14"}).json()
        assert start["interrupt"]["type"] == "pick_jobs"
        thread_id = start["thread_id"]
        job = start["interrupt"]["matches"][0]["job"]

        approve = client.post(
            f"/api/v1/runs/{thread_id}/resume",
            json={"value": {"selected_job_ids": [job["id"]]}},
        ).json()
        # the diff screen gets job summaries alongside each tailored CV
        assert approve["interrupt"]["jobs"][job["id"]]["title"] == job["title"]

        done = client.post(
            f"/api/v1/runs/{thread_id}/resume", json={"value": {"approved": True}}
        ).json()
        assert done["phase"] == "done"
        pack = done["values"]["application_packs"][0]
        assert pack["job_title"] == job["title"]

        # finished pack lands in the tracker automatically…
        [row] = client.get("/api/v1/me/applications").json()
        assert row["job_id"] == job["id"]
        assert row["status"] == "pack_ready"
        assert row["job_title"] == job["title"]

        # …and the user can advance its status after pressing submit themselves
        res = client.put(
            f"/api/v1/me/applications/{job['id']}", json={"status": "applied"}
        )
        assert res.status_code == 200
        [row] = client.get("/api/v1/me/applications").json()
        assert row["status"] == "applied"
        assert row["applied_at"] is not None

        # export now reflects the real store
        export = client.get("/api/v1/me/export").json()
        assert export["applications"][0]["job_id"] == job["id"]
        assert export["preference_profile"] is not None

        # the extension can fetch the full pack for autofill
        full = client.get(f"/api/v1/me/applications/{job['id']}/pack").json()
        assert full["job_title"] == job["title"]
        assert {a["field"] for a in full["answers"]} >= {"notice_period", "right_to_work"}
        assert full["tailored_cv"]["full_text"]
        assert client.get("/api/v1/me/applications/nope/pack").status_code == 404


def test_application_status_validation():
    with _client() as client:
        assert (
            client.put("/api/v1/me/applications/nope", json={"status": "applied"}).status_code
            == 404
        )
        assert (
            client.put("/api/v1/me/applications/nope", json={"status": "ghosted"}).status_code
            == 422
        )


def test_runs_today_reports_absence_then_presence():
    with _client() as client:
        before = client.get("/api/v1/runs/today").json()
        assert before["phase"] is None
        assert before["next_nodes"] == []

        client.post("/api/v1/runs/start", json={})  # defaults to today
        after = client.get("/api/v1/runs/today").json()
        assert after["interrupt"]["type"] == "pick_jobs"
