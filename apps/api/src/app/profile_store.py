"""User profile / CV inventory / application-tracker persistence.

Same pattern as everything else in this codebase: a small protocol with a
Postgres implementation (Supabase tables from 0001_init.sql) and an in-memory
implementation used automatically when DATABASE_URL is unset, so dev and tests
run without infrastructure. All methods are synchronous — async endpoints call
them via run_in_threadpool.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from jobpilot_schemas import ApplicationPack, CVInventoryItem, PreferenceProfile

APPLICATION_STATUSES = ("pack_ready", "applied", "interviewing", "offer", "rejected", "withdrawn")


@dataclass
class ApplicationRow:
    job_id: str
    status: str
    job_title: str = ""
    company: str = ""
    apply_url: str = ""
    applied_at: str | None = None
    created_at: str | None = None


class ProfileStore(Protocol):
    def get_profile(self, user_id: str) -> PreferenceProfile | None: ...
    def save_profile(self, user_id: str, profile: PreferenceProfile) -> None: ...
    def get_plan(self, user_id: str) -> str: ...
    def save_plan(self, user_id: str, plan: str) -> None: ...
    def get_inventory(self, user_id: str) -> list[CVInventoryItem]: ...
    def save_inventory(self, user_id: str, items: list[CVInventoryItem]) -> None: ...
    def list_applications(self, user_id: str) -> list[ApplicationRow]: ...
    def record_pack(self, user_id: str, pack: ApplicationPack) -> None: ...
    def set_application_status(self, user_id: str, job_id: str, status: str) -> bool: ...
    def delete_user(self, user_id: str) -> None: ...


# --- in-memory (dev / tests) --------------------------------------------------


@dataclass
class _UserData:
    profile: PreferenceProfile | None = None
    plan: str = "free"
    inventory: list[CVInventoryItem] = field(default_factory=list)
    applications: dict[str, ApplicationRow] = field(default_factory=dict)


class MemoryProfileStore:
    def __init__(self) -> None:
        self._users: dict[str, _UserData] = {}

    def _user(self, user_id: str) -> _UserData:
        return self._users.setdefault(user_id, _UserData())

    def get_profile(self, user_id: str) -> PreferenceProfile | None:
        return self._user(user_id).profile

    def save_profile(self, user_id: str, profile: PreferenceProfile) -> None:
        self._user(user_id).profile = profile

    def get_plan(self, user_id: str) -> str:
        return self._user(user_id).plan

    def save_plan(self, user_id: str, plan: str) -> None:
        self._user(user_id).plan = plan

    def get_inventory(self, user_id: str) -> list[CVInventoryItem]:
        return list(self._user(user_id).inventory)

    def save_inventory(self, user_id: str, items: list[CVInventoryItem]) -> None:
        self._user(user_id).inventory = list(items)

    def list_applications(self, user_id: str) -> list[ApplicationRow]:
        rows = self._user(user_id).applications.values()
        return sorted(rows, key=lambda r: r.created_at or "", reverse=True)

    def record_pack(self, user_id: str, pack: ApplicationPack) -> None:
        apps = self._user(user_id).applications
        existing = apps.get(pack.job_id)
        apps[pack.job_id] = ApplicationRow(
            job_id=pack.job_id,
            # never regress a status the user has advanced (e.g. back to pack_ready)
            status=existing.status if existing else "pack_ready",
            job_title=pack.job_title,
            company=pack.company,
            apply_url=pack.apply_url,
            applied_at=existing.applied_at if existing else None,
            created_at=(existing.created_at if existing else datetime.now().isoformat()),
        )

    def set_application_status(self, user_id: str, job_id: str, status: str) -> bool:
        row = self._user(user_id).applications.get(job_id)
        if row is None:
            return False
        row.status = status
        if status == "applied" and row.applied_at is None:
            row.applied_at = datetime.now().isoformat()
        return True

    def delete_user(self, user_id: str) -> None:
        self._users.pop(user_id, None)


# --- Postgres (Supabase) ------------------------------------------------------


class PostgresProfileStore:
    """Reads/writes the profiles / cv_inventory / applications tables."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self):
        import psycopg

        return psycopg.connect(self._dsn)

    def get_profile(self, user_id: str) -> PreferenceProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT preference_profile FROM public.profiles WHERE user_id = %s::uuid",
                (user_id,),
            ).fetchone()
        if row is None or not row[0]:
            return None
        return PreferenceProfile.model_validate(row[0])

    def save_profile(self, user_id: str, profile: PreferenceProfile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO public.profiles (user_id, preference_profile, updated_at)
                VALUES (%s::uuid, %s::jsonb, now())
                ON CONFLICT (user_id) DO UPDATE
                SET preference_profile = excluded.preference_profile, updated_at = now()
                """,
                (user_id, profile.model_dump_json()),
            )

    def get_plan(self, user_id: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT plan FROM public.profiles WHERE user_id = %s::uuid", (user_id,)
            ).fetchone()
        return row[0] if row else "free"

    def save_plan(self, user_id: str, plan: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO public.profiles (user_id, plan, updated_at)
                VALUES (%s::uuid, %s, now())
                ON CONFLICT (user_id) DO UPDATE SET plan = excluded.plan, updated_at = now()
                """,
                (user_id, plan),
            )

    def get_inventory(self, user_id: str) -> list[CVInventoryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, text, source_span FROM public.cv_inventory
                WHERE user_id = %s::uuid ORDER BY id
                """,
                (user_id,),
            ).fetchall()
        return [CVInventoryItem(id=r[0], kind=r[1], text=r[2], source_span=r[3]) for r in rows]

    def save_inventory(self, user_id: str, items: list[CVInventoryItem]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM public.cv_inventory WHERE user_id = %s::uuid", (user_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO public.cv_inventory (id, user_id, kind, text, source_span)
                    VALUES (%s, %s::uuid, %s, %s, %s)
                    """,
                    [(i.id, user_id, i.kind, i.text, i.source_span) for i in items],
                )

    def list_applications(self, user_id: str) -> list[ApplicationRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, status, application_pack, applied_at, created_at
                FROM public.applications WHERE user_id = %s::uuid
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        out = []
        for job_id, status, pack_json, applied_at, created_at in rows:
            pack = pack_json or {}
            out.append(
                ApplicationRow(
                    job_id=job_id,
                    status=status,
                    job_title=pack.get("job_title", ""),
                    company=pack.get("company", ""),
                    apply_url=pack.get("apply_url", ""),
                    applied_at=applied_at.isoformat() if applied_at else None,
                    created_at=created_at.isoformat() if created_at else None,
                )
            )
        return out

    def record_pack(self, user_id: str, pack: ApplicationPack) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO public.applications (user_id, job_id, tailored_cv, application_pack)
                VALUES (%s::uuid, %s, %s::jsonb, %s::jsonb)
                ON CONFLICT (user_id, job_id) DO UPDATE
                SET tailored_cv = excluded.tailored_cv,
                    application_pack = excluded.application_pack
                """,
                (
                    user_id,
                    pack.job_id,
                    json.dumps(pack.tailored_cv.model_dump(mode="json")),
                    json.dumps(pack.model_dump(mode="json")),
                ),
            )

    def set_application_status(self, user_id: str, job_id: str, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE public.applications
                SET status = %s,
                    applied_at = CASE WHEN %s = 'applied' AND applied_at IS NULL
                                      THEN now() ELSE applied_at END
                WHERE user_id = %s::uuid AND job_id = %s
                """,
                (status, status, user_id, job_id),
            )
            return cur.rowcount > 0

    def delete_user(self, user_id: str) -> None:
        with self._connect() as conn:
            for table in ("applications", "matches", "cv_inventory", "usage", "profiles"):
                conn.execute(f"DELETE FROM public.{table} WHERE user_id = %s::uuid", (user_id,))


def make_profile_store(database_url: str | None) -> ProfileStore:
    return PostgresProfileStore(database_url) if database_url else MemoryProfileStore()
