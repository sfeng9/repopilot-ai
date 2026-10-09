from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from repopilot.errors import ConfigurationError, GitHubIssueError, PullRequestNumberError
from repopilot.github_service import GitHubIssueService


class FakeRepository:
    def __init__(self, issue):
        self.issue = issue

    def get_issue(self, *, number):
        assert number == self.issue.number
        return self.issue


class FakeGithub:
    def __init__(self, *, auth, issue):
        self.auth = auth
        self.issue = issue
        self.requested_repository = None

    def get_repo(self, repository):
        self.requested_repository = repository
        return FakeRepository(self.issue)


def make_issue(*, pull_request=None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        number=42,
        title="Improve retry handling",
        body="Retry transient API failures.",
        state="open",
        user=SimpleNamespace(login="octocat"),
        labels=[SimpleNamespace(name="enhancement"), SimpleNamespace(name="api")],
        comments=3,
        html_url="https://github.com/acme/widgets/issues/42",
        created_at=now,
        updated_at=now,
        pull_request=pull_request,
    )


def service_for(issue):
    holder = {}

    def factory(*, auth):
        holder["client"] = FakeGithub(auth=auth, issue=issue)
        return holder["client"]

    return GitHubIssueService(token="test-token", github_factory=factory), holder


def test_missing_github_token_is_rejected(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ConfigurationError, match="GITHUB_TOKEN"):
        GitHubIssueService(token="")


def test_retrieves_and_normalizes_issue():
    service, holder = service_for(make_issue())

    issue = service.get_issue("acme/widgets", 42)

    assert holder["client"].requested_repository == "acme/widgets"
    assert issue.repository == "acme/widgets"
    assert issue.number == 42
    assert issue.title == "Improve retry handling"
    assert issue.labels == ("enhancement", "api")
    assert issue.author == "octocat"


def test_rejects_pull_request_number():
    service, _ = service_for(make_issue(pull_request={"url": "example"}))

    with pytest.raises(PullRequestNumberError, match="pull request"):
        service.get_issue("acme/widgets", 42)


@pytest.mark.parametrize("repository", ["widgets", "owner/repo/extra", "owner /repo", ""])
def test_rejects_invalid_repository_format(repository):
    service, _ = service_for(make_issue())
    with pytest.raises(GitHubIssueError, match="owner/name"):
        service.get_issue(repository, 42)
