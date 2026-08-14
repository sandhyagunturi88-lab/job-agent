"""Billing: quotas (stated, idempotent, weekly), dev upgrade flow, webhooks."""

import json
from datetime import date, timedelta

from app import billing
from app.billing import sign_stripe_payload, verify_stripe_signature
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

# Two days guaranteed to fall in the same ISO week (Monday + Tuesday)
MONDAY = date.today() - timedelta(days=date.today().weekday())
DAY_1 = MONDAY.isoformat()
DAY_2 = (MONDAY + timedelta(days=1)).isoformat()
DAY_3 = (MONDAY + timedelta(days=2)).isoformat()


def _client() -> TestClient:
    return TestClient(create_app())


def _complete_day(client, run_date, picks=1):
    start = client.post("/api/v1/runs/start", json={"run_date": run_date})
    if start.status_code != 200:
        return start
    thread_id = start.json()["thread_id"]
    job_ids = [m["job"]["id"] for m in start.json()["interrupt"]["matches"][:picks]]
    return client.post(
        f"/api/v1/runs/{thread_id}/resume", json={"value": {"selected_job_ids": job_ids}}
    )


# --- signature verification (pure) -------------------------------------------


def test_webhook_signature_roundtrip():
    payload = b'{"type":"checkout.session.completed"}'
    header = sign_stripe_payload(payload, "whsec_x", timestamp=1_000_000)
    assert verify_stripe_signature(payload, header, "whsec_x", now=1_000_000)
    assert not verify_stripe_signature(payload + b" ", header, "whsec_x", now=1_000_000)
    assert not verify_stripe_signature(payload, header, "whsec_other", now=1_000_000)
    assert not verify_stripe_signature(payload, header, "whsec_x", now=1_000_600)  # stale
    assert not verify_stripe_signature(payload, "garbage", "whsec_x")
    assert not verify_stripe_signature(payload, "", "whsec_x")


# --- plan + quota status, dev upgrade/downgrade ------------------------------


def test_billing_status_and_dev_flow():
    with _client() as client:
        status = client.get("/api/v1/billing").json()
        assert status["plan"] == "free"
        assert status["limits"] == {"matches": 5, "cvs": 1}
        assert status["used"] == {"matches": 0, "cvs": 0}
        assert status["dev_billing"] is True

        # mock provider: checkout has no Stripe URL; dev upgrade path instead
        assert client.post("/api/v1/billing/checkout").json()["url"] is None
        assert client.post("/api/v1/billing/dev-upgrade").json()["plan"] == "pro"
        assert client.get("/api/v1/billing").json()["limits"] is None  # unlimited

        assert client.post("/api/v1/billing/dev-downgrade").json()["plan"] == "free"
        assert client.get("/api/v1/billing").json()["limits"] is not None


# --- match quota -------------------------------------------------------------


def test_free_weekly_match_quota_blocks_second_run():
    with _client() as client:
        first = client.post("/api/v1/runs/start", json={"run_date": DAY_1})
        assert first.status_code == 200
        assert len(first.json()["interrupt"]["matches"]) == 5  # all 5 weekly matches shown

        second = client.post("/api/v1/runs/start", json={"run_date": DAY_2})
        assert second.status_code == 402
        assert "free matches this week" in second.json()["detail"]


def test_pro_has_no_match_quota():
    with _client() as client:
        client.post("/api/v1/billing/dev-upgrade")
        assert client.post("/api/v1/runs/start", json={"run_date": DAY_1}).status_code == 200
        assert client.post("/api/v1/runs/start", json={"run_date": DAY_2}).status_code == 200


def test_match_cap_is_stated_not_silent(monkeypatch):
    monkeypatch.setattr(billing, "FREE_WEEKLY_MATCHES", 3)
    with _client() as client:
        start = client.post("/api/v1/runs/start", json={"run_date": DAY_1}).json()
        interrupt = start["interrupt"]
        assert len(interrupt["matches"]) == 3  # top 3 by score
        assert interrupt["limited_from"] == 5  # and the cap is declared


def test_quota_never_double_charged_by_retriggering():
    with _client() as client:
        client.post("/api/v1/runs/start", json={"run_date": DAY_1})
        client.post("/api/v1/runs/start", json={"run_date": DAY_1})  # idempotent re-trigger
        used = client.get("/api/v1/billing").json()["used"]
        assert used["matches"] == 5  # not 10


# --- CV quota ----------------------------------------------------------------


def test_free_cv_quota_enforced_at_pick():
    with _client() as client:
        start = client.post("/api/v1/runs/start", json={"run_date": DAY_1}).json()
        thread_id = start["thread_id"]
        job_ids = [m["job"]["id"] for m in start["interrupt"]["matches"]]

        over = client.post(
            f"/api/v1/runs/{thread_id}/resume",
            json={"value": {"selected_job_ids": job_ids[:2]}},
        )
        assert over.status_code == 402
        assert "1 tailored CV per week" in over.json()["detail"]

        ok = client.post(
            f"/api/v1/runs/{thread_id}/resume",
            json={"value": {"selected_job_ids": job_ids[:1]}},
        )
        assert ok.status_code == 200
        assert ok.json()["interrupt"]["type"] == "approve_cv"
        assert client.get("/api/v1/billing").json()["used"]["cvs"] == 1


def test_pro_can_pick_many():
    with _client() as client:
        client.post("/api/v1/billing/dev-upgrade")
        resumed = _complete_day(client, DAY_1, picks=3)
        assert resumed.status_code == 200
        assert resumed.json()["interrupt"]["type"] == "approve_cv"


# --- webhook -----------------------------------------------------------------


def test_webhook_flips_plan(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    get_settings.cache_clear()
    try:
        with _client() as client:
            demo = "00000000-0000-0000-0000-000000000001"  # dev-mode user id

            def post_event(event: dict, secret: str = "whsec_test"):
                payload = json.dumps(event).encode()
                import time as _time

                header = sign_stripe_payload(payload, secret, int(_time.time()))
                return client.post(
                    "/api/v1/billing/webhook",
                    content=payload,
                    headers={"stripe-signature": header},
                )

            completed = {
                "type": "checkout.session.completed",
                "data": {"object": {"client_reference_id": demo, "customer": "cus_123"}},
            }
            assert post_event(completed).status_code == 200
            assert client.get("/api/v1/billing").json()["plan"] == "pro"

            deleted = {
                "type": "customer.subscription.deleted",
                "data": {"object": {"customer": "cus_123"}},
            }
            assert post_event(deleted).status_code == 200
            assert client.get("/api/v1/billing").json()["plan"] == "free"

            bad = post_event(completed, secret="whsec_wrong")
            assert bad.status_code == 400
    finally:
        get_settings.cache_clear()
