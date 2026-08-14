"""Billing: plans, weekly quotas, and Stripe (behind the usual interface).

Free plan: 5 matches/week, 1 tailored CV/week. Pro: unlimited.

Without STRIPE_SECRET_KEY the mock provider is used: checkout/portal resolve
to in-app dev endpoints so the whole upgrade/downgrade flow works offline.
With keys, checkout/portal sessions are created against the Stripe REST API
(httpx, form-encoded — same pattern as the Voyage embedder) and plan changes
arrive via the signature-verified webhook.

No dark patterns: quotas are stated up front, the paywall never blocks data
the user already has, and cancelling is one click into the Stripe portal.
"""

import hashlib
import hmac
import time
from datetime import date

import httpx

FREE_WEEKLY_MATCHES = 5
FREE_WEEKLY_CVS = 1

STRIPE_API = "https://api.stripe.com/v1"


def week_key(day: date) -> str:
    """ISO week bucket, Monday-based (UK convention), e.g. '2026-W33'."""
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def plan_limits(plan: str) -> dict | None:
    """None = unlimited (pro)."""
    if plan == "pro":
        return None
    return {"matches": FREE_WEEKLY_MATCHES, "cvs": FREE_WEEKLY_CVS}


# --- Stripe webhook signature (Stripe-Signature: t=...,v1=...) ---------------


def verify_stripe_signature(
    payload: bytes, header: str, secret: str, tolerance_seconds: int = 300, now: int | None = None
) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        timestamp = int(parts["t"])
        given = parts["v1"]
    except (KeyError, ValueError, AttributeError):
        return False
    if abs((now if now is not None else int(time.time())) - timestamp) > tolerance_seconds:
        return False
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, given)


def sign_stripe_payload(payload: bytes, secret: str, timestamp: int) -> str:
    """Build a valid Stripe-Signature header (tests + local webhook tooling)."""
    signed = f"{timestamp}.".encode() + payload
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={v1}"


# --- providers ----------------------------------------------------------------


class StripeBilling:
    """Real Stripe checkout/portal sessions via the REST API."""

    def __init__(self, secret_key: str, price_pro: str, client: httpx.Client | None = None):
        self._auth = {"Authorization": f"Bearer {secret_key}"}
        self._price = price_pro
        self._client = client or httpx.Client(timeout=20)

    def checkout_url(
        self, user_id: str, email: str | None, success_url: str, cancel_url: str
    ) -> str:
        res = self._client.post(
            f"{STRIPE_API}/checkout/sessions",
            headers=self._auth,
            data={
                "mode": "subscription",
                "line_items[0][price]": self._price,
                "line_items[0][quantity]": "1",
                "client_reference_id": user_id,
                **({"customer_email": email} if email else {}),
                "success_url": success_url,
                "cancel_url": cancel_url,
            },
        )
        res.raise_for_status()
        return res.json()["url"]

    def portal_url(self, customer_id: str, return_url: str) -> str:
        res = self._client.post(
            f"{STRIPE_API}/billing_portal/sessions",
            headers=self._auth,
            data={"customer": customer_id, "return_url": return_url},
        )
        res.raise_for_status()
        return res.json()["url"]


class MockBilling:
    """Dev provider: no URLs — the router exposes dev upgrade/downgrade
    endpoints instead, so the full flow is exercisable offline."""

    def checkout_url(self, *args, **kwargs) -> None:
        return None

    def portal_url(self, *args, **kwargs) -> None:
        return None


def make_billing(settings) -> StripeBilling | MockBilling:
    if settings.stripe_secret_key and settings.stripe_price_pro:
        return StripeBilling(settings.stripe_secret_key, settings.stripe_price_pro)
    return MockBilling()
