"""UK GDPR endpoints (see PRIVACY.md).

- GET  /api/v1/me/export — everything we hold about the user, as JSON
- DELETE /api/v1/me      — delete account rows now; files purged within 30 days
"""

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from app.core.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/export")
async def export_my_data(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    store = request.app.state.profile_store
    profile = await run_in_threadpool(store.get_profile, user.id)
    inventory = await run_in_threadpool(store.get_inventory, user.id)
    applications = await run_in_threadpool(store.list_applications, user.id)
    return {
        "user": {"id": user.id, "email": user.email},
        "plan": await run_in_threadpool(store.get_plan, user.id),
        "preference_profile": profile,
        "cv_inventory": inventory,
        "applications": [vars(a) for a in applications],
        "note": "CV files stored in Supabase Storage are included once storage is provisioned.",
    }


@router.delete("", status_code=202)
async def delete_my_account(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    await run_in_threadpool(request.app.state.profile_store.delete_user, user.id)
    return {
        "status": "deletion_scheduled",
        "user_id": user.id,
        "detail": "Account rows removed; CV files purged from storage and backups within 30 days.",
    }
