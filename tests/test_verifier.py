import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parents[1] / "researchos"))
from backend.pipeline import verifier

def test_failed_provider_returns_review_required(monkeypatch) -> None:
    """Upstream failure must never turn into approval."""
    monkeypatch.setattr(verifier.anthropic, "Anthropic", MagicMock(side_effect=RuntimeError("offline")))
    assert verifier.verify_consistency({}, "source", "change")["ready_to_submit"] is False

def test_model_claim_does_not_bypass_human_review(monkeypatch) -> None:
    """A model's confidence cannot certify an amendment."""
    import json
    result = {"overall_status": "CLEAN", "flags": [], "consistency_score": 10, "ready_to_submit": True, "reviewer_notes": "review"}
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(text=json.dumps(result))])
    monkeypatch.setattr(verifier.anthropic, "Anthropic", lambda **kwargs: client)
    assert verifier.verify_consistency({}, "source", "change")["ready_to_submit"] is False

def test_invalid_schema_falls_back(monkeypatch) -> None:
    """Valid JSON with missing fields is not a verified report."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(text='{"ready_to_submit": true}')])
    monkeypatch.setattr(verifier.anthropic, "Anthropic", lambda **kwargs: client)
    assert verifier.verify_consistency({}, "source", "change")["overall_status"] == "WARNINGS"
