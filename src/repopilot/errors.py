"""Domain errors with messages suitable for the command line."""


class RepoPilotError(Exception):
    """Base class for expected RepoPilot failures."""


class ConfigurationError(RepoPilotError):
    """Raised when required configuration is missing or invalid."""


class GitHubIssueError(RepoPilotError):
    """Raised when a GitHub issue cannot be retrieved or used."""


class PullRequestNumberError(GitHubIssueError):
    """Raised when a supplied issue number belongs to a pull request."""


class PlannerError(RepoPilotError):
    """Raised when the implementation planner cannot complete a run."""
