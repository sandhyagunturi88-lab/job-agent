"""Assemble the JobPilot StateGraph.

    retrieve → llm_rerank → pick_jobs (interrupt 1)
        ├─ dismissals → learn_preferences ─┐
        └──────────────────────────────────┤
                                           ├─ nothing selected → END
                                           └─ tailor_cv → validate_cv
                                                 ├─ violations, retries left → tailor_cv
                                                 ├─ exhausted → flag_manual_edit → approve_cv
                                                 └─ clean → approve_cv (interrupt 2)
                                                       ├─ edits requested → tailor_cv
                                                       └─ approved → build_application_pack → END
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.state import AgentState


def _route_after_picks(state: AgentState) -> str:
    if state.get("dismissals"):
        return "learn_preferences"
    return "tailor_cv" if state.get("selected_job_ids") else END


def _route_after_learn(state: AgentState) -> str:
    return "tailor_cv" if state.get("selected_job_ids") else END


def _route_after_validate(state: AgentState) -> str:
    if not state.get("violations"):
        return "approve_cv"
    if (state.get("tailor_retries") or 0) <= nodes.MAX_TAILOR_RETRIES:
        return "tailor_cv"
    return "flag_manual_edit"


def _route_after_approval(state: AgentState) -> str:
    return "build_application_pack" if state.get("cv_approved") else "tailor_cv"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    g = StateGraph(AgentState)

    g.add_node("retrieve", nodes.retrieve)
    g.add_node("llm_rerank", nodes.llm_rerank)
    g.add_node("pick_jobs", nodes.pick_jobs)
    g.add_node("learn_preferences", nodes.learn_preferences)
    g.add_node("tailor_cv", nodes.tailor_cv)
    g.add_node("validate_cv", nodes.validate_cv)
    g.add_node("flag_manual_edit", nodes.flag_manual_edit)
    g.add_node("approve_cv", nodes.approve_cv)
    g.add_node("build_application_pack", nodes.build_application_pack)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "llm_rerank")
    g.add_edge("llm_rerank", "pick_jobs")
    g.add_conditional_edges(
        "pick_jobs",
        _route_after_picks,
        {"learn_preferences": "learn_preferences", "tailor_cv": "tailor_cv", END: END},
    )
    g.add_conditional_edges(
        "learn_preferences", _route_after_learn, {"tailor_cv": "tailor_cv", END: END}
    )
    g.add_edge("tailor_cv", "validate_cv")
    g.add_conditional_edges(
        "validate_cv",
        _route_after_validate,
        {
            "approve_cv": "approve_cv",
            "tailor_cv": "tailor_cv",
            "flag_manual_edit": "flag_manual_edit",
        },
    )
    g.add_edge("flag_manual_edit", "approve_cv")
    g.add_conditional_edges(
        "approve_cv",
        _route_after_approval,
        {"build_application_pack": "build_application_pack", "tailor_cv": "tailor_cv"},
    )
    g.add_edge("build_application_pack", END)

    return g.compile(checkpointer=checkpointer)
