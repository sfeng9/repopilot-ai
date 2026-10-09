"""Implementation-plan orchestration using LangGraph and local Ollama."""

from __future__ import annotations

import os
from typing import Any, NotRequired, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from .errors import PlannerError
from .github_service import IssueDetails


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"


PLANNER_INSTRUCTIONS = """\
You are RepoPilot, a senior software engineer who converts GitHub issues into practical
implementation plans. Work only from the supplied issue context. If information is
missing, state assumptions and open questions instead of inventing repository details.

Return concise Markdown with these sections:
1. Summary
2. Assumptions and open questions
3. Implementation steps
4. Files likely to change
5. Test plan
6. Risks and edge cases

Do not claim that code was changed. Do not expose credentials or suggest committing secrets.
"""


class PlannerState(TypedDict):
    """State passed through the RepoPilot planning graph."""

    issue_context: str
    plan: NotRequired[str]


class IssuePlanner:
    """Run a one-node LangGraph planning workflow through local Ollama."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        llm: Any | None = None,
    ) -> None:
        selected_model = (model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)).strip()
        selected_base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ).strip()

        self.model = llm or ChatOllama(
            model=selected_model,
            base_url=selected_base_url,
            temperature=0,
            num_ctx=4096,
            num_predict=1024,
            validate_model_on_init=True,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(PlannerState)
        workflow.add_node("draft_plan", self._draft_plan)
        workflow.add_edge(START, "draft_plan")
        workflow.add_edge("draft_plan", END)
        return workflow.compile()

    def _draft_plan(self, state: PlannerState) -> PlannerState:
        response = self.model.invoke(
            [
                ("system", PLANNER_INSTRUCTIONS),
                (
                    "human",
                    "Create an implementation plan for this GitHub issue.\n\n"
                    + state["issue_context"],
                ),
            ]
        )
        plan = self._content_as_text(getattr(response, "content", ""))
        if not plan:
            raise PlannerError("The local planning model returned an empty response.")
        return {"plan": plan}

    @staticmethod
    def _content_as_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            return "".join(parts).strip()
        return str(content).strip()

    def create_plan(self, issue: IssueDetails) -> str:
        """Execute the LangGraph workflow for one normalized GitHub issue."""
        try:
            result = self.graph.invoke({"issue_context": issue.as_prompt_context()})
        except PlannerError:
            raise
        except Exception as exc:
            raise PlannerError(
                "The local LangGraph planner could not complete the request. "
                "Make sure Ollama is running and qwen2.5-coder:7b is installed."
            ) from exc

        plan = str(result.get("plan", "")).strip()
        if not plan:
            raise PlannerError("The LangGraph workflow returned no implementation plan.")
        return plan
