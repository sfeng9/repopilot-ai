"""GitHub issue retrieval through PyGithub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import re
from typing import Any, Callable

from github import Auth, Github
from github.GithubException import BadCredentialsException, GithubException, UnknownObjectException

from .errors import ConfigurationError, GitHubIssueError, PullRequestNumberError


_REPOSITORY_PATTERN = re.compile(r"^[^/\s]+/[^/\s]+$")


@dataclass(frozen=True, slots=True)
class IssueDetails:
    """The issue fields the planning agent needs."""

    repository: str
    number: int
    title: str
    body: str
    state: str
    author: str
    labels: tuple[str, ...]
    comments: int
    url: str
    created_at: datetime | None
    updated_at: datetime | None

    def as_prompt_context(self) -> str:
        labels = ", ".join(self.labels) if self.labels else "None"
        return (
            f"Repository: {self.repository}\n"
            f"Issue: #{self.number}\n"
            f"Title: {self.title}\n"
            f"State: {self.state}\n"
            f"Author: {self.author}\n"
            f"Labels: {labels}\n"
            f"Comments: {self.comments}\n"
            f"URL: {self.url}\n\n"
            f"Description:\n{self.body or '(No description provided.)'}"
        )


class GitHubIssueService:
    """Retrieve public or private repository issues using a GitHub token."""

    def __init__(
        self,
        token: str | None = None,
        github_factory: Callable[..., Any] = Github,
    ) -> None:
        resolved_token = (token if token is not None else os.getenv("GITHUB_TOKEN", "")).strip()
        if not resolved_token:
            raise ConfigurationError(
                "GITHUB_TOKEN is missing. Add it to your environment or a local .env file."
            )
        self._github = github_factory(auth=Auth.Token(resolved_token))

    def get_issue(self, repository: str, issue_number: int) -> IssueDetails:
        """Return normalized issue data, rejecting pull-request numbers."""
        repository = repository.strip()
        if not _REPOSITORY_PATTERN.fullmatch(repository):
            raise GitHubIssueError("Repository must use the 'owner/name' format.")
        if issue_number < 1:
            raise GitHubIssueError("Issue number must be a positive integer.")

        try:
            issue = self._github.get_repo(repository).get_issue(number=issue_number)
        except BadCredentialsException as exc:
            raise GitHubIssueError(
                "GitHub rejected the token. Check GITHUB_TOKEN and try again."
            ) from exc
        except UnknownObjectException as exc:
            raise GitHubIssueError(
                f"Issue #{issue_number} was not found in {repository}, or the token cannot access it."
            ) from exc
        except GithubException as exc:
            message = getattr(exc, "data", None) or str(exc)
            raise GitHubIssueError(f"GitHub could not retrieve the issue: {message}") from exc
        except OSError as exc:
            raise GitHubIssueError(
                "Could not reach GitHub. Check your internet connection and try again."
            ) from exc

        if getattr(issue, "pull_request", None) is not None:
            raise PullRequestNumberError(
                f"#{issue_number} in {repository} is a pull request, not an issue."
            )

        user = getattr(issue, "user", None)
        labels = tuple(label.name for label in getattr(issue, "labels", []))
        return IssueDetails(
            repository=repository,
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            author=getattr(user, "login", "unknown"),
            labels=labels,
            comments=issue.comments,
            url=issue.html_url,
            created_at=getattr(issue, "created_at", None),
            updated_at=getattr(issue, "updated_at", None),
        )
