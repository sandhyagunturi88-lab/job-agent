"""Billing endpoints: plan + quota status, Stripe checkout/portal, webhook.

Honest paywall rules encoded here: quota status is always visible (GET), the
free plan is stated in numbers, upgrading requires an explicit user action,
and downgrading/cancelling is available through the same surface (portal, or
the dev endpoints when Stripe isn't configured).
"""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.billing import (
    MockBilling,
    plan_limits,
    verify_stripe_signature,
    week_key,
)
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _store(request: Request):
    return request.app.state.profile_store


def _billing(request: Request):
    return request.app.state.billing


@router.get("")
async def billing_status(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    store = _store(request)
    plan = await run_in_threadpool(store.get_plan, user.id)
    limits = plan_limits(plan)
    week = week_key(date.today())
    used = await run_in_threadpool(store.week_quota_usage, user.id, week)
    return {
        "plan": plan,
        "pro_price": get_settings().pro_price_display,
        "week": week,
        "limits": limits,  # null = unlimited
        "used": used,
        "dev_billing": isinstance(_billing(request), MockBilling),
    }


@router.post("/checkout")
async def create_checkout(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    settings = get_settings()
    url = await run_in_threadpool(
        _billing(request).checkout_url,
        user.id,
        user.email,
        f"{settings.app_base_url}/tracker?upgraded=1",
        f"{settings.app_base_url}/tracker",
    )
    # url is None in dev (mock provider): the client calls /dev-upgrade instead
    return {"url": url}


@router.post("/portal")
async def create_portal(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    billing = _billing(request)
    if isinstance(billing, MockBilling):
        # dev: the client offers /dev-downgrade instead of a portal
        return {"url": None}
    customer_id = await run_in_threadpool(_store(request).get_stripe_customer, user.id)
    if not customer_id:
        raise HTTPException(
            status_code=409,
            detail="No Stripe customer on file yet — complete a checkout first.",
        )
    url = await run_in_threadpool(
        billing.portal_url, customer_id, f"{get_settings().app_base_url}/tracker"
    )
    return {"url": url}


@router.post("/dev-upgrade")
async def dev_upgrade(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    if not isinstance(_billing(request), MockBilling):
        raise HTTPException(status_code=404, detail="Not available with live billing")
    await run_in_threadpool(_store(request).save_plan, user.id, "pro")
    return {"plan": "pro"}


@router.post("/dev-downgrade")
async def dev_downgrade(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    if not isinstance(_billing(request), MockBilling):
        raise HTTPException(status_code=404, detail="Not available with live billing")
    await run_in_threadpool(_store(request).save_plan, user.id, "free")
    return {"plan": "free"}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=404, detail="Webhooks not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    if not verify_stripe_signature(payload, signature, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(payload)
    kind = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    store = request.app.state.profile_store

    if kind == "checkout.session.completed":
        user_id = obj.get("client_reference_id")
        if user_id:
            await run_in_threadpool(store.save_plan, user_id, "pro")
            if obj.get("customer"):
                await run_in_threadpool(store.set_stripe_customer, user_id, obj["customer"])
    elif kind in ("customer.subscription.deleted", "customer.subscription.canceled"):
        user_id = await run_in_threadpool(store.user_for_stripe_customer, obj.get("customer", ""))
        if user_id:
            await run_in_threadpool(store.save_plan, user_id, "free")
    elif kind == "customer.subscription.updated":
        user_id = await run_in_threadpool(store.user_for_stripe_customer, obj.get("customer", ""))
        if user_id:
            active = obj.get("status") in ("active", "trialing")
            await run_in_threadpool(store.save_plan, user_id, "pro" if active else "free")

    return {"received": True}
