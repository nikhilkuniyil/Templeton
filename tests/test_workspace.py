from stock_researcher.models import AgentEnvelope
from stock_researcher.workspace import WorkspaceStore


def test_workspace_store_ranks_watchlist_candidates(tmp_path) -> None:
    store = WorkspaceStore(tmp_path)
    store.add_to_watchlist("semis", "ASML")
    outputs = {
        "decision_portfolio_fit": AgentEnvelope(
            agent_name="decision_portfolio_fit",
            ticker="ASML",
            analysis_mode="investigation",
            summary="ASML is rated WATCH.",
            confidence="medium",
            open_questions=["Need better sense of demand durability."],
            payload={
                "decision": "watch",
                "confidence": "medium",
                "key_reasons": ["Valuation elevated."],
            },
        ),
        "synthesizer": AgentEnvelope(
            agent_name="synthesizer",
            ticker="ASML",
            analysis_mode="investigation",
            summary="ASML memo complete.",
            confidence="medium",
            payload={
                "memo_sections": {
                    "what_changed": "No prior memo available for comparison.",
                }
            },
        ),
        "valuation": AgentEnvelope(
            agent_name="valuation",
            ticker="ASML",
            analysis_mode="investigation",
            summary="ASML looks fair to expensive.",
            confidence="medium",
            payload={"valuation_label": "fair_to_expensive"},
        ),
        "risk": AgentEnvelope(
            agent_name="risk",
            ticker="ASML",
            analysis_mode="investigation",
            summary="Semicap cycle remains a risk.",
            confidence="medium",
            payload={
                "core_risks": ["Semiconductor capex cyclicality"],
                "monitoring_indicators": ["Order book trend"],
            },
        ),
    }

    store.update_dossier_from_outputs("ASML", outputs, run_id="req_001")
    ranked = store.rank_watchlist("semis")

    assert ranked is not None
    assert ranked["entries"][0]["ticker"] == "ASML"
    assert ranked["entries"][0]["decision"] == "watch"
    assert ranked["entries"][0]["readiness_status"] in {"building", "early", "ready"}


def test_workspace_store_tracks_portfolio_priority_themes(tmp_path) -> None:
    store = WorkspaceStore(tmp_path)
    store.add_priority_theme("semis")
    summary = store.summarize_portfolio()

    assert "semis" in summary["priority_themes"]
    assert "semis" in summary["underweight_themes"]
