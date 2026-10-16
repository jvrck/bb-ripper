"""Bitbucket REST API helpers."""

import logging
import os
from urllib.parse import quote, urlsplit

import requests

from auth_helper import get_api_auth

BB_API_ENDPOINT = "https://api.bitbucket.org/2.0"
BB_API_HOST = "api.bitbucket.org"
REQUEST_TIMEOUT = (5, 30)
MAX_PAGES = 1000

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)


class BitbucketAPIError(RuntimeError):
    """Raised when Bitbucket returns an unusable or unsafe API response."""


def _validate_api_url(url):
    parsed = urlsplit(url)
    if (
            parsed.scheme != "https"
            or parsed.hostname != BB_API_HOST
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
    ):
        raise BitbucketAPIError("Bitbucket pagination returned an unexpected URL")


def _page_values(session, request_endpoint):
    try:
        response = session.get(
            request_endpoint, timeout=REQUEST_TIMEOUT, allow_redirects=False
        )
    except requests.RequestException as error:
        raise BitbucketAPIError("Bitbucket API request failed") from error
    if not 200 <= response.status_code < 300:
        raise BitbucketAPIError("Bitbucket API returned a non-success status")
    try:
        payload = response.json()
    except ValueError as error:
        raise BitbucketAPIError("Bitbucket API returned invalid JSON") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("values"), list):
        raise BitbucketAPIError("Bitbucket API response is missing a values list")

    next_url = payload.get("next")
    if next_url is not None and not isinstance(next_url, str):
        raise BitbucketAPIError("Bitbucket API response has an invalid next URL")
    return payload["values"], next_url


def _get_paginated(path, factory):
    request_endpoint = f"{BB_API_ENDPOINT}/{path}?pagelen=100"
    visited = set()
    results = []

    with requests.Session() as session:
        session.auth = get_api_auth()
        for _ in range(MAX_PAGES):
            _validate_api_url(request_endpoint)
            if request_endpoint in visited:
                raise BitbucketAPIError("Bitbucket pagination loop detected")
            visited.add(request_endpoint)

            values, request_endpoint = _page_values(session, request_endpoint)
            try:
                results.extend(factory(value) for value in values)
            except (KeyError, TypeError, ValueError) as error:
                raise BitbucketAPIError("Bitbucket API returned an invalid item") from error

            if request_endpoint is None:
                return results

    raise BitbucketAPIError("Bitbucket pagination exceeded the safety limit")


class BBProject:
    """A Bitbucket project returned by the REST API."""

    def __init__(self, data):
        self.name = data["name"]
        self.key = data["key"]
        self.repo_rest_url = data["links"]["repositories"]["href"]

    @staticmethod
    def GetProjects(workspace_name):
        """Return every project for a workspace."""
        workspace = quote(workspace_name, safe="")
        return _get_paginated(f"workspaces/{workspace}/projects", BBProject)


class BBRepo:
    """A Bitbucket repository returned by the REST API."""

    def __init__(self, data):
        self.name = data["name"]
        self.slug = data["slug"]
        if not isinstance(self.slug, str):
            raise TypeError("repository slug must be a string")
        self.project = data["project"]
        clone_links = data["links"]["clone"]
        if not isinstance(clone_links, list):
            raise TypeError("clone links must be a list")

        links = {link["name"]: link["href"] for link in clone_links}
        self.ssh = links.get("ssh")
        self.https = links["https"]

    @staticmethod
    def GetWorkspaceRepos(workspace_name):
        """Return every repository for a workspace."""
        workspace = quote(workspace_name, safe="")
        logging.info("Fetching repositories for workspace %s", workspace_name)
        return _get_paginated(f"repositories/{workspace}", BBRepo)
