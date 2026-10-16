"""Integration tests for safe Git cloning and archive creation."""

import base64
import functools
import http.server
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bb-ripper"))

import auth_helper
import ripper_utils
from ripper_utils import BackupError, clone_repo, zip_output_dir

TOKEN = "synthetic-token-that-must-not-persist"
USERNAME = "x-bitbucket-api-token-auth"


def run_git(*arguments, cwd):
    """Run fixture-only Git commands."""
    return subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class AuthenticatedFileHandler(http.server.SimpleHTTPRequestHandler):
    """Serve a dumb Git repository behind HTTP Basic authentication."""

    expected_authorization = "Basic " + base64.b64encode(
        f"{USERNAME}:{TOKEN}".encode()
    ).decode()
    authorizations = []

    def _authorized(self):
        authorization = self.headers.get("Authorization")
        self.authorizations.append(authorization)
        if authorization == self.expected_authorization:
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
        self.end_headers()
        return False

    def do_GET(self):
        if self._authorized():
            super().do_GET()

    def do_HEAD(self):
        if self._authorized():
            super().do_HEAD()

    def log_message(self, *_args):
        return


class GitFixture:
    """Disposable authenticated HTTP Git repository."""

    def __init__(self, root):
        self.root = Path(root)
        self.served = self.root / "served"
        self.served.mkdir()
        self.bare = self.served / "repo.git"
        self._create_repository()
        handler = functools.partial(
            AuthenticatedFileHandler, directory=str(self.served)
        )
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _create_repository(self):
        work = self.root / "work"
        work.mkdir()
        run_git("init", "--initial-branch=main", cwd=work)
        run_git("config", "user.email", "fixture@example.test", cwd=work)
        run_git("config", "user.name", "Fixture", cwd=work)
        (work / "README.md").write_text("fixture\n", encoding="utf-8")
        (work / "test").write_text("path colliding with branch name\n", encoding="utf-8")
        run_git("add", "README.md", "test", cwd=work)
        run_git("commit", "-m", "fixture", cwd=work)
        run_git("branch", "feature/test", cwd=work)
        run_git("branch", "test", cwd=work)
        run_git("init", "--bare", str(self.bare), cwd=self.root)
        run_git("remote", "add", "origin", str(self.bare), cwd=work)
        run_git("push", "--all", "origin", cwd=work)
        run_git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.bare)
        run_git("update-server-info", cwd=self.bare)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}/repo.git"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class RipperUtilsTests(unittest.TestCase):
    """Use real Git and tar operations with synthetic credentials."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        AuthenticatedFileHandler.authorizations = []
        self.fixture = GitFixture(self.root)
        self.environment = patch.dict(os.environ, {"BB_API_TOKEN": TOKEN})
        self.environment.start()
        self.url_patchers = [
            patch.object(auth_helper, "BITBUCKET_GIT_SCHEME", "http"),
            patch.object(auth_helper, "BITBUCKET_GIT_HOST", "127.0.0.1"),
            patch.object(
                auth_helper, "BITBUCKET_GIT_PORT", self.fixture.server.server_port
            ),
        ]
        for patcher in self.url_patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.url_patchers):
            patcher.stop()
        self.environment.stop()
        self.fixture.close()
        self.temporary.cleanup()

    def test_clone_and_archive_never_persist_token(self):
        destination = self.root / "backup"
        destination.mkdir()
        repo_name = "repo with spaces;$(no-shell)"
        repo = SimpleNamespace(name=repo_name, https=self.fixture.url)

        clone_repo(repo, destination)

        clone = destination / repo_name
        origin = run_git("remote", "get-url", "origin", cwd=clone).stdout.strip()
        branches = run_git("branch", "--format=%(refname:short)", cwd=clone).stdout
        self.assertEqual(self.fixture.url, origin)
        self.assertIn("feature/test", branches.splitlines())
        self.assertIn("test", branches.splitlines())
        local_test = run_git("rev-parse", "refs/heads/test", cwd=clone).stdout
        remote_test = run_git(
            "rev-parse", "refs/remotes/origin/test", cwd=clone
        ).stdout
        self.assertEqual(remote_test, local_test)
        self.assertTrue((clone / "test").is_file())
        self.assertTrue(any(AuthenticatedFileHandler.authorizations))
        self.assertNotIn(TOKEN, (clone / ".git" / "config").read_text())

        archive_path = Path(zip_output_dir(destination))
        self.assertTrue(destination.exists(), "archiving must not remove its source")
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    extracted = archive.extractfile(member)
                    self.assertNotIn(TOKEN.encode(), extracted.read())

    def test_clone_failure_is_nonzero_and_keeps_recoverable_directory(self):
        destination = self.root / "failed-backup"
        destination.mkdir()
        repo = SimpleNamespace(name="missing", https=self.fixture.url + "/missing")
        with self.assertRaisesRegex(BackupError, "Git backup failed"):
            clone_repo(repo, destination)
        self.assertTrue((destination / "missing").is_dir())

    def test_branch_creation_failure_is_propagated(self):
        destination = self.root / "branch-failure"
        destination.mkdir()
        repo = SimpleNamespace(name="repo", https=self.fixture.url)
        original_run_git = ripper_utils._run_git

        def fail_test_branch(arguments, cwd, **kwargs):
            if arguments[:3] == ["branch", "--track", "test"]:
                raise subprocess.CalledProcessError(1, ["git", *arguments])
            return original_run_git(arguments, cwd, **kwargs)

        with patch.object(ripper_utils, "_run_git", side_effect=fail_test_branch):
            with self.assertRaisesRegex(BackupError, "Git backup failed"):
                clone_repo(repo, destination)
        self.assertTrue((destination / "repo" / ".git").is_dir())

    def test_unsafe_repository_name_is_rejected_before_filesystem_changes(self):
        destination = self.root / "safe"
        destination.mkdir()
        repo = SimpleNamespace(name="../escape", https=self.fixture.url)
        with self.assertRaisesRegex(BackupError, "unsafe repository name"):
            clone_repo(repo, destination)
        self.assertFalse((self.root / "escape").exists())

    def test_archive_failure_keeps_source_and_removes_partial_archive(self):
        source = self.root / "archive-failure"
        source.mkdir()
        (source / "data").write_text("recoverable", encoding="utf-8")
        with patch.object(ripper_utils.tarfile, "open", side_effect=OSError("full")):
            with self.assertRaisesRegex(BackupError, "create and verify"):
                zip_output_dir(source)
        self.assertTrue(source.exists())
        self.assertFalse(source.with_name(f"{source.name}.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
