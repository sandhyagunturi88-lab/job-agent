"""Onboarding + tracker endpoints: preferences, CV upload, plan, applications.

CV upload takes text (paste or extracted client-side from .txt/.md); binary CV
files go to Supabase Storage once provisioned — the parse path is the same.
Endpoints are sync `def`s so the (blocking) store runs in FastAPI's threadpool.
"""

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Request
from jobpilot_schemas import CVInventoryItem, PreferenceProfile
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.cv_parse import parse_cv_text
from app.profile_store import APPLICATION_STATUSES, ProfileStore

router = APIRouter(prefix="/api/v1/me", tags=["profile"])


def _store(request: Request) -> ProfileStore:
    return request.app.state.profile_store


class ProfileResponse(BaseModel):
    profile: PreferenceProfile | None
    plan: str
    inventory_count: int
    onboarded: bool  # CV parsed AND preferences saved


def _profile_response(store: ProfileStore, user_id: str) -> ProfileResponse:
    profile = store.get_profile(user_id)
    count = len(store.get_inventory(user_id))
    return ProfileResponse(
        profile=profile,
        plan=store.get_plan(user_id),
        inventory_count=count,
        onboarded=profile is not None and count > 0,
    )


@router.get("/profile")
def get_profile(request: Request, user: CurrentUser = Depends(get_current_user)) -> ProfileResponse:
    return _profile_response(_store(request), user.id)


@router.put("/profile")
def put_profile(
    profile: PreferenceProfile,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> ProfileResponse:
    store = _store(request)
    store.save_profile(user.id, profile)
    return _profile_response(store, user.id)


class PlanRequest(BaseModel):
    plan: str = Field(pattern="^(free|pro)$")


@router.put("/plan")
def put_plan(
    body: PlanRequest, request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    _store(request).save_plan(user.id, body.plan)
    return {"plan": body.plan}


class CVUploadRequest(BaseModel):
    cv_text: str = Field(min_length=40, description="Plain text of the CV")


class CVUploadResponse(BaseModel):
    inventory: list[CVInventoryItem]
    counts: dict[str, int]


@router.post("/cv")
def upload_cv(
    body: CVUploadRequest, request: Request, user: CurrentUser = Depends(get_current_user)
) -> CVUploadResponse:
    items = parse_cv_text(body.cv_text)
    if not items:
        raise HTTPException(
            status_code=422, detail="Could not find any usable content in that CV text"
        )
    _store(request).save_inventory(user.id, items)
    return CVUploadResponse(inventory=items, counts=dict(Counter(i.kind for i in items)))


@router.get("/inventory")
def get_inventory(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> list[CVInventoryItem]:
    return _store(request).get_inventory(user.id)


@router.get("/applications")
def list_applications(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return [vars(row) for row in _store(request).list_applications(user.id)]


@router.get("/applications/{job_id}/pack")
def get_application_pack(
    job_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Full Application Pack (tailored CV + answers) — consumed by the Chrome
    extension for desktop autofill. The user still presses submit themselves."""
    pack = _store(request).get_pack(user.id, job_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="No pack for that job")
    return pack


class StatusRequest(BaseModel):
    status: str


@router.put("/applications/{job_id}")
def set_application_status(
    job_id: str,
    body: StatusRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if body.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {APPLICATION_STATUSES}")
    if not _store(request).set_application_status(user.id, job_id, body.status):
        raise HTTPException(status_code=404, detail="No tracked application for that job")
    return {"job_id": job_id, "status": body.status}
