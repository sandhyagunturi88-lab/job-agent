"""Graph shape tests: both interrupts, learn_preferences routing, the
validator retry loop, and resuming from the checkpointer after a "restart".

Phase 3 adds the kill-the-process resume tests against real Postgres."""

from app.graph import stubs
from app.graph.build import build_graph
from jobpilot_schemas import CVChange, TailoredCV
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


def _initial_state(run_date: str = "2026-08-14") -> dict:
    profile, inventory = stubs.load_user_context("user-1")
    return {
        "user_id": "user-1",
        "run_date": run_date,
        "preference_profile": profile,
        "cv_inventory": inventory,
    }


def _config(thread: str = "user-1:2026-08-14") -> dict:
    return {"configurable": {"thread_id": thread}}


def _pending_interrupt(graph, config):
    snap = graph.get_state(config)
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    return interrupts[0] if interrupts else None


def test_happy_path_through_both_interrupts():
    graph = build_graph(checkpointer=MemorySaver())
    config = _config()

    graph.invoke(_initial_state(), config)

    # Interrupt 1: ranked matches presented for the user to pick
    interrupt1 = _pending_interrupt(graph, config)
    assert interrupt1["type"] == "pick_jobs"
    assert len(interrupt1["matches"]) >= 3
    top_job_id = interrupt1["matches"][0]["job"]["id"]

    graph.invoke(
        Command(
            resume={
                "selected_job_ids": [top_job_id],
                "dismissals": [{"job_id": "job-dwp-005", "reason": "too junior, php stack"}],
            }
        ),
        config,
    )

    # Interrupt 2: CV diff with evidence on every change
    interrupt2 = _pending_interrupt(graph, config)
    assert interrupt2["type"] == "approve_cv"
    cvs = interrupt2["tailored_cvs"]
    assert len(cvs) == 1 and cvs[0]["job_id"] == top_job_id
    assert all(change["evidence_ids"] for cv in cvs for change in cv["changes"])

    graph.invoke(Command(resume={"approved": True}), config)

    state = graph.get_state(config).values
    assert state["phase"] == "done"
    packs = state["application_packs"]
    assert len(packs) == 1
    assert packs[0].apply_url  # deep link for the user to press submit themselves
    assert {a.field for a in packs[0].answers} >= {"notice_period", "right_to_work"}

    # Dismissal reason was learned into the profile for future runs
    profile = state["preference_profile"]
    assert "php" in profile.avoid_keywords and "junior" in profile.avoid_keywords


def test_run_survives_restart_between_interrupts():
    """Same checkpointer, fresh graph instance = process restart/deploy."""
    saver = MemorySaver()
    config = _config()

    graph_before = build_graph(checkpointer=saver)
    graph_before.invoke(_initial_state(), config)
    interrupt1 = _pending_interrupt(graph_before, config)
    job_id = interrupt1["matches"][0]["job"]["id"]

    graph_after = build_graph(checkpointer=saver)  # "restarted" process
    graph_after.invoke(Command(resume={"selected_job_ids": [job_id]}), config)
    assert _pending_interrupt(graph_after, config)["type"] == "approve_cv"


def test_edit_request_loops_back_to_tailor():
    graph = build_graph(checkpointer=MemorySaver())
    config = _config()
    graph.invoke(_initial_state(), config)
    job_id = _pending_interrupt(graph, config)["matches"][0]["job"]["id"]
    graph.invoke(Command(resume={"selected_job_ids": [job_id]}), config)

    graph.invoke(
        Command(resume={"approved": False, "edit_requests": "lead with the search project"}),
        config,
    )
    # Re-tailored and waiting for approval again
    assert _pending_interrupt(graph, config)["type"] == "approve_cv"

    graph.invoke(Command(resume={"approved": True}), config)
    assert graph.get_state(config).values["phase"] == "done"


def test_fabricated_claims_exhaust_retries_and_flag_manual_edit(monkeypatch):
    """If tailoring keeps fabricating, the validator loops it back (max 2
    retries), then the CV reaches the user flagged, with fabrications stripped."""
    calls = {"n": 0}

    def fabricating_tailor(job, cv_inventory, edit_requests="", violations=None):
        calls["n"] += 1
        return TailoredCV(
            job_id=job.id,
            changes=[
                CVChange(
                    section="Experience",
                    after="Single-handedly built a £10m product",  # not in inventory
                    evidence_ids=[],
                ),
                CVChange(
                    section="Skills",
                    after=cv_inventory[3].text,
                    evidence_ids=[cv_inventory[3].id],
                ),
            ],
            full_text="",
        )

    monkeypatch.setattr(stubs, "tailor", fabricating_tailor)

    graph = build_graph(checkpointer=MemorySaver())
    config = _config()
    graph.invoke(_initial_state(), config)
    job_id = _pending_interrupt(graph, config)["matches"][0]["job"]["id"]
    graph.invoke(Command(resume={"selected_job_ids": [job_id]}), config)

    assert calls["n"] == 3  # initial attempt + 2 retries
    interrupt2 = _pending_interrupt(graph, config)
    assert interrupt2["type"] == "approve_cv"
    cv = interrupt2["tailored_cvs"][0]
    assert cv["needs_manual_edit"] is True
    # The fabricated change was stripped; the evidenced one survived.
    assert [c["after"] for c in cv["changes"]] == [stubs.SAMPLE_INVENTORY[3].text]


def test_dismissing_everything_ends_run_after_learning():
    graph = build_graph(checkpointer=MemorySaver())
    config = _config()
    graph.invoke(_initial_state(), config)
    matches = _pending_interrupt(graph, config)["matches"]

    graph.invoke(
        Command(
            resume={
                "selected_job_ids": [],
                "dismissals": [
                    {"job_id": m["job"]["id"], "reason": "not relevant"} for m in matches
                ],
            }
        ),
        config,
    )
    state = graph.get_state(config)
    assert state.next == ()  # run ended, nothing to tailor
    assert state.values["phase"] == "learn_preferences"
    assert len(state.values["preference_profile"].notes) == len(matches)
