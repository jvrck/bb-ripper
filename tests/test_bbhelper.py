"""Tests for bounded, validated Bitbucket API pagination."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bb-ripper"))

from bbhelper import BBRepo, BitbucketAPIError, REQUEST_TIMEOUT

ENVIRONMENT = {
    "BB_EMAIL": "backup@example.test",
    "BB_API_TOKEN": "synthetic-token",
    "BB_WORKSPACE": "workspace",
    "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
}
MISSING = object()


def repo_payload(name, slug=MISSING, project=MISSING):
    """Build the minimum valid Bitbucket repository response."""
    payload = {
        "name": name,
        "links": {
            "clone": [
                {"name": "https", "href": f"https://bitbucket.org/ws/{name}.git"},
                {"name": "ssh", "href": f"git@bitbucket.org:ws/{name}.git"},
            ]
        },
    }
    if project is MISSING:
        payload["project"] = {"key": "TEST"}
    else:
        payload["project"] = project
    if slug is MISSING:
        payload["slug"] = name
    elif slug is not None:
        payload["slug"] = slug
    return payload


class FakeResponse:
    """Minimal requests response fixture."""

    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    """Context-managed requests session with ordered responses."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
        self.auth = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, url, timeout, allow_redirects):
        self.calls.append((url, timeout, allow_redirects))
        return next(self.responses)


class BBHelperTests(unittest.TestCase):
    """Verify happy and failing REST API behavior."""

    def setUp(self):
        self.environment = patch.dict(os.environ, ENVIRONMENT, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_pagination_uses_timeout_and_returns_every_repo(self):
        next_url = "https://api.bitbucket.org/2.0/repositories/workspace?page=2"
        session = FakeSession([
            FakeResponse({"values": [repo_payload("one")], "next": next_url}),
            FakeResponse({"values": [repo_payload("two")]}),
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            repos = BBRepo.GetWorkspaceRepos("workspace")

        self.assertEqual(["one", "two"], [repo.name for repo in repos])
        self.assertEqual(REQUEST_TIMEOUT, session.calls[0][1])
        self.assertFalse(session.calls[0][2])
        self.assertIn("pagelen=100", session.calls[0][0])
        self.assertEqual(
            ("backup@example.test", "synthetic-token"), session.auth
        )

    def test_repository_maps_display_name_and_slug_separately(self):
        session = FakeSession([
            FakeResponse({"values": [repo_payload("Tools/API", "tools-api")]})
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            repos = BBRepo.GetWorkspaceRepos("workspace")

        self.assertEqual("Tools/API", repos[0].name)
        self.assertEqual("tools-api", repos[0].slug)

    def test_repository_tolerates_unassigned_project_shapes(self):
        projects = (MISSING, None, "not-a-mapping", {}, {"key": None}, {"key": ""})
        for project in projects:
            with self.subTest(project=project):
                payload = repo_payload("repo", project=project)
                if project is MISSING:
                    payload.pop("project")
                repo = BBRepo(payload)
                self.assertIsNone(repo.project)

    def test_non_string_project_key_is_preserved_for_grouped_validation(self):
        repo = BBRepo(repo_payload("repo", project={"key": 123}))
        self.assertEqual({"key": 123}, repo.project)

    def test_missing_or_non_string_slug_is_rejected(self):
        invalid_payloads = (
            repo_payload("missing", None),
            repo_payload("number", 123),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                session = FakeSession([FakeResponse({"values": [payload]})])
                with patch("bbhelper.requests.Session", return_value=session):
                    with self.assertRaisesRegex(BitbucketAPIError, "invalid item"):
                        BBRepo.GetWorkspaceRepos("workspace")

    def test_http_failure_is_closed(self):
        session = FakeSession([
            FakeResponse({"values": []}, status_code=500)
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            with self.assertRaisesRegex(BitbucketAPIError, "non-success status"):
                BBRepo.GetWorkspaceRepos("workspace")

    def test_redirect_is_not_followed(self):
        session = FakeSession([
            FakeResponse(
                {"values": []}, status_code=302
            )
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            with self.assertRaisesRegex(BitbucketAPIError, "non-success status"):
                BBRepo.GetWorkspaceRepos("workspace")
        self.assertEqual(1, len(session.calls))

    def test_malformed_response_is_rejected(self):
        session = FakeSession([FakeResponse({"unexpected": []})])
        with patch("bbhelper.requests.Session", return_value=session):
            with self.assertRaisesRegex(BitbucketAPIError, "values list"):
                BBRepo.GetWorkspaceRepos("workspace")

    def test_pagination_loop_is_rejected(self):
        first_url = (
            "https://api.bitbucket.org/2.0/repositories/workspace?pagelen=100"
        )
        session = FakeSession([
            FakeResponse({"values": [], "next": first_url}),
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            with self.assertRaisesRegex(BitbucketAPIError, "loop"):
                BBRepo.GetWorkspaceRepos("workspace")

    def test_cross_origin_pagination_is_rejected_before_request(self):
        session = FakeSession([
            FakeResponse({"values": [], "next": "https://example.test/steal"}),
        ])
        with patch("bbhelper.requests.Session", return_value=session):
            with self.assertRaisesRegex(BitbucketAPIError, "unexpected URL"):
                BBRepo.GetWorkspaceRepos("workspace")
        self.assertEqual(1, len(session.calls))


if __name__ == "__main__":
    unittest.main()
