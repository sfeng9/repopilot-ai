"""Friendly command-line interface for RepoPilot AI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dotenv import load_dotenv

from .errors import ConfigurationError, GitHubIssueError, PlannerError
from .github_service import GitHubIssueService
from .planner import IssuePlanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repopilot-ai",
        description="Turn a GitHub issue into a structured implementation plan.",
    )
    parser.add_argument("repository", help="GitHub repository in owner/name format")
    parser.add_argument("issue_number", type=int, help="GitHub issue number (not a PR number)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)

    try:
        issue = GitHubIssueService().get_issue(args.repository, args.issue_number)
        print(f"Retrieved {issue.repository}#{issue.number}: {issue.title}", file=sys.stderr)
        plan = IssuePlanner().create_plan(issue)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except GitHubIssueError as exc:
        print(f"GitHub error: {exc}", file=sys.stderr)
        return 3
    except PlannerError as exc:
        print(f"Planner error: {exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130

    print(plan)
    return 0
