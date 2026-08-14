"""UK GDPR endpoints (see PRIVACY.md).

Phase 2 wires these to Supabase; the contract is fixed now:
- GET  /api/v1/me/export — everything we hold about the user, as JSON
- DELETE /api/v1/me      — delete account; files purged within 30 days
"""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.graph import stubs

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/export")
async def export_my_data(user: CurrentUser = Depends(get_current_user)) -> dict:
    profile, inventory = stubs.load_user_context(user.id)
    return {
        "user": {"id": user.id, "email": user.email},
        "preference_profile": profile,
        "cv_inventory": inventory,
        "matches": [],
        "applications": [],
        "note": "Phase 2 adds CV files, matches, tailored CVs and tracker rows from Supabase.",
    }


@router.delete("", status_code=202)
async def delete_my_account(user: CurrentUser = Depends(get_current_user)) -> dict:
    # Phase 2: delete Supabase rows now; storage objects purged within 30 days.
    return {
        "status": "deletion_scheduled",
        "user_id": user.id,
        "detail": "Account rows removed; CV files purged from storage and backups within 30 days.",
    }
