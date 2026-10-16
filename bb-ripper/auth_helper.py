"""Authentication and configuration helpers for Bitbucket API tokens."""

import os
from urllib.parse import urlsplit, urlunsplit

GIT_USERNAME = "x-bitbucket-api-token-auth"
BITBUCKET_GIT_SCHEME = "https"
BITBUCKET_GIT_HOST = "bitbucket.org"
BITBUCKET_GIT_PORT = None
REQUIRED_ENVIRONMENT = (
    "BB_EMAIL",
    "BB_API_TOKEN",
    "BB_WORKSPACE",
    "BB_RIPPER_EXPORT_DIRECTORY",
)
PROJECT_FOLDERS_ENVIRONMENT = "BB_USE_PROJECT_FOLDERS"


def use_project_folders(environment=None):
    """Return whether project folders are enabled, rejecting unknown values."""
    values = os.environ if environment is None else environment
    value = values.get(PROJECT_FOLDERS_ENVIRONMENT, "").strip().lower()
    if value in {"", "false"}:
        return False
    if value == "true":
        return True
    raise ValueError(
        f"{PROJECT_FOLDERS_ENVIRONMENT} must be true or false"
    )


def validate_environment(environment=None):
    """Validate all required settings before a backup starts."""
    values = os.environ if environment is None else environment
    missing = [name for name in REQUIRED_ENVIRONMENT if not values.get(name, "").strip()]
    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    multiline = [
        name for name in REQUIRED_ENVIRONMENT
        if "\n" in values[name] or "\r" in values[name]
    ]
    if multiline:
        raise ValueError(
            "Environment variables must be single-line values: "
            + ", ".join(multiline)
        )

    workspace = values["BB_WORKSPACE"]
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if workspace in {".", ".."} or any(char not in allowed for char in workspace):
        raise ValueError("BB_WORKSPACE must be a valid Bitbucket workspace slug")

    use_project_folders(values)


def get_api_auth(environment=None):
    """Return the email and API token used for Bitbucket REST requests."""
    values = os.environ if environment is None else environment
    validate_environment(values)
    return values["BB_EMAIL"], values["BB_API_TOKEN"]


def get_git_https_url(base_url):
    """Return a clean, credential-free Bitbucket HTTPS clone URL."""
    parsed = urlsplit(base_url)
    if (
            parsed.scheme != BITBUCKET_GIT_SCHEME
            or parsed.hostname != BITBUCKET_GIT_HOST
            or parsed.port != BITBUCKET_GIT_PORT
            or not parsed.path
    ):
        raise ValueError("Bitbucket clone URL must use the expected HTTPS host")
    if parsed.query or parsed.fragment:
        raise ValueError("Bitbucket clone URL must not include query or fragment data")

    netloc = parsed.hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
