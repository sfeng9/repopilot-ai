from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from repopilot.errors import PlannerError
from repopilot.github_service import IssueDetails
from repopilot.planner import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    IssuePlanner,
)


def sample_issue():
    now = datetime.now(timezone.utc)
    return IssueDetails(
        repository="acme/widgets",
        number=42,
        title="Improve retry handling",
        body="Retry transient API failures.",
        state="open",
        author="octocat",
        labels=("enhancement",),
        comments=2,
        url="https://github.com/acme/widgets/issues/42",
        created_at=now,
        updated_at=now,
    )


class FakeLocalModel:
    def __init__(self, *, content="# Implementation plan\n\n1. Add retries", error=None):
        self.content = content
        self.error = error
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        if self.error is not None:
            raise self.error
        return SimpleNamespace(content=self.content)


def test_planner_executes_langgraph_and_invokes_local_model(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake_model = FakeLocalModel()
    planner = IssuePlanner(llm=fake_model)

    result = planner.create_plan(sample_issue())

    assert result.startswith("# Implementation plan")
    assert fake_model.messages[0][0] == "system"
    assert fake_model.messages[1][0] == "human"
    assert "acme/widgets" in fake_model.messages[1][1]
    assert "Issue: #42" in fake_model.messages[1][1]
    assert "Retry transient API failures." in fake_model.messages[1][1]


def test_planner_configures_chat_ollama_by_default(monkeypatch):
    captured = {}
    fake_model = FakeLocalModel()

    def fake_chat_ollama(**kwargs):
        captured.update(kwargs)
        return fake_model

    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr("repopilot.planner.ChatOllama", fake_chat_ollama)

    planner = IssuePlanner()

    assert planner.model is fake_model
    assert captured["model"] == DEFAULT_OLLAMA_MODEL
    assert captured["base_url"] == DEFAULT_OLLAMA_BASE_URL
    assert captured["temperature"] == 0
    assert captured["validate_model_on_init"] is True


def test_planner_wraps_local_model_failure():
    planner = IssuePlanner(llm=FakeLocalModel(error=RuntimeError("internal detail")))

    with pytest.raises(PlannerError, match="LangGraph"):
        planner.create_plan(sample_issue())


def test_planner_rejects_empty_model_output():
    planner = IssuePlanner(llm=FakeLocalModel(content="  "))

    with pytest.raises(PlannerError, match="empty response"):
        planner.create_plan(sample_issue())
