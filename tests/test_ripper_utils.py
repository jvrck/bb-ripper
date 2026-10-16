"""Integration tests for safe Git cloning and archive creation."""

import base64
import functools
import http.server
import os
import subprocess
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bb_ripper import auth_helper
from bb_ripper import ripper_utils
from bb_ripper.ripper_utils import (
    BackupError,
    clone_repo,
    delete_output_directory,
    plan_repo_destinations,
    zip_output_dir,
)

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
        run_git("update-ref", "refs/heads/-leading", "HEAD", cwd=work)
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
        repo_name = "Tools/API"
        repo_slug = "tools-api"
        repo = SimpleNamespace(
            name=repo_name, slug=repo_slug, https=self.fixture.url
        )

        clone_repo(repo, destination)

        clone = destination / repo_slug
        origin = run_git("remote", "get-url", "origin", cwd=clone).stdout.strip()
        branches = run_git("branch", "--format=%(refname:short)", cwd=clone).stdout
        self.assertEqual(self.fixture.url, origin)
        self.assertIn("feature/test", branches.splitlines())
        self.assertIn("test", branches.splitlines())
        self.assertIn("-leading", branches.splitlines())
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
            member_names = [member.name for member in archive.getmembers()]
            self.assertTrue(any(
                name.startswith(f"{destination.name}/{repo_slug}/")
                for name in member_names
            ))
            for member in archive.getmembers():
                if member.isfile():
                    extracted = archive.extractfile(member)
                    self.assertNotIn(TOKEN.encode(), extracted.read())

    def test_similar_display_names_with_distinct_slugs_clone_separately(self):
        destination = self.root / "distinct"
        destination.mkdir()
        repos = [
            SimpleNamespace(
                name="Tools/API", slug="tools-api", https=self.fixture.url
            ),
            SimpleNamespace(
                name="Tools/API", slug="tools-api-2", https=self.fixture.url
            ),
        ]

        for repo, repository_path in plan_repo_destinations(repos, destination):
            clone_repo(repo, destination, repository_path)

        self.assertTrue((destination / "tools-api" / ".git").is_dir())
        self.assertTrue((destination / "tools-api-2" / ".git").is_dir())

    def test_grouped_clone_and_archive_use_project_and_fallback_folders(self):
        destination = self.root / "grouped"
        destination.mkdir()
        repos = [
            SimpleNamespace(
                name="Tools/API", slug="tools-api",
                project={"key": "TOOLS"}, https=self.fixture.url,
            ),
            SimpleNamespace(
                name="Web", slug="web", project={"key": "WEB"},
                https=self.fixture.url,
            ),
            SimpleNamespace(
                name="Loose", slug="loose", project=None,
                https=self.fixture.url,
            ),
        ]

        for repo, repository_path in plan_repo_destinations(
                repos, destination, project_folders=True):
            clone_repo(repo, destination, repository_path)

        expected_paths = (
            Path("TOOLS/tools-api"), Path("WEB/web"), Path("UNASSIGNED/loose")
        )
        for relative_path in expected_paths:
            clone = destination / relative_path
            self.assertTrue((clone / ".git").is_dir())
            branches = run_git(
                "branch", "--format=%(refname:short)", cwd=clone
            ).stdout.splitlines()
            self.assertIn("feature/test", branches)
            self.assertEqual(
                self.fixture.url,
                run_git("remote", "get-url", "origin", cwd=clone).stdout.strip(),
            )

        archive_path = Path(zip_output_dir(destination))
        with tarfile.open(archive_path, "r:gz") as archive:
            member_names = [member.name for member in archive.getmembers()]
            for relative_path in expected_paths:
                prefix = f"{destination.name}/{relative_path.as_posix()}/"
                self.assertTrue(any(name.startswith(prefix) for name in member_names))
            for member in archive.getmembers():
                if member.isfile():
                    self.assertNotIn(TOKEN.encode(), archive.extractfile(member).read())

    def test_grouped_planning_uses_unassigned_fallbacks(self):
        destination = self.root / "project-planning"
        destination.mkdir()
        for index in range(3):
            repo = SimpleNamespace(
                name="Repo", slug=f"repo-{index}", project=None
            )
            plan = plan_repo_destinations(
                [repo], destination, project_folders=True
            )
            self.assertEqual(Path(f"UNASSIGNED/repo-{index}"), plan[0][1])

    def test_planner_default_does_not_read_project_folder_environment(self):
        destination = self.root / "explicit-flat-default"
        destination.mkdir()
        repo = SimpleNamespace(
            name="Repo", slug="repo", project={"key": "TOOLS"}
        )
        with patch.dict(os.environ, {"BB_USE_PROJECT_FOLDERS": "true"}):
            plan = plan_repo_destinations([repo], destination)
        self.assertEqual(Path("repo"), plan[0][1])

    def test_project_keys_are_ignored_in_flat_mode(self):
        destination = self.root / "flat-project-metadata"
        destination.mkdir()
        projects = ({"key": 123}, {"key": "../unsafe"}, "odd-shape")
        repos = [
            SimpleNamespace(name="Repo", slug=f"repo-{index}", project=project)
            for index, project in enumerate(projects)
        ]
        plan = plan_repo_destinations(repos, destination, project_folders=False)
        self.assertEqual(
            [Path("repo-0"), Path("repo-1"), Path("repo-2")],
            [relative_path for _repo, relative_path in plan],
        )

    def test_grouped_planning_rejects_unsafe_project_keys_without_writes(self):
        destination = self.root / "unsafe-projects"
        destination.mkdir()
        unsafe_keys = (123, "../x", "a/b", ".", "..", "nul\x00key", "a" * 256)
        for project_key in unsafe_keys:
            with self.subTest(project_key=project_key):
                repo = SimpleNamespace(
                    name="Repo", slug="repo", project={"key": project_key}
                )
                with self.assertRaisesRegex(BackupError, "unsafe project key"):
                    plan_repo_destinations(
                        [repo], destination, project_folders=True
                    )
                self.assertEqual([], list(destination.iterdir()))

    def test_grouped_planning_rejects_ambiguous_project_keys(self):
        destination = self.root / "ambiguous-projects"
        destination.mkdir()
        cases = (
            (
                [
                    SimpleNamespace(name="One", slug="one", project=None),
                    SimpleNamespace(
                        name="Two", slug="two", project={"key": "unassigned"}
                    ),
                ],
                "conflicts",
            ),
            (
                [
                    SimpleNamespace(
                        name="One", slug="one", project={"key": "TOOLS"}
                    ),
                    SimpleNamespace(
                        name="Two", slug="two", project={"key": "tools"}
                    ),
                ],
                "case-insensitive key collisions",
            ),
        )
        for repos, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(BackupError, message):
                    plan_repo_destinations(
                        repos, destination, project_folders=True
                    )
                self.assertEqual([], list(destination.iterdir()))

    def test_real_unassigned_project_without_fallback_is_allowed(self):
        destination = self.root / "real-unassigned"
        destination.mkdir()
        repo = SimpleNamespace(
            name="Repo", slug="repo", project={"key": "UNASSIGNED"}
        )
        plan = plan_repo_destinations([repo], destination, project_folders=True)
        self.assertEqual(Path("UNASSIGNED/repo"), plan[0][1])

    def test_grouped_full_destination_collisions_are_rejected(self):
        destination = self.root / "grouped-duplicates"
        destination.mkdir()
        repos = [
            SimpleNamespace(
                name="One", slug="Repo", project={"key": "TOOLS"}
            ),
            SimpleNamespace(
                name="Two", slug="repo", project={"key": "TOOLS"}
            ),
        ]
        with self.assertRaisesRegex(BackupError, "duplicate destinations"):
            plan_repo_destinations(repos, destination, project_folders=True)
        self.assertEqual([], list(destination.iterdir()))

    def test_clone_rejects_grouped_path_that_does_not_match_project(self):
        destination = self.root / "project-mismatch"
        destination.mkdir()
        repo = SimpleNamespace(
            name="Repo", slug="repo", project={"key": "TOOLS"},
            https=self.fixture.url,
        )
        with self.assertRaisesRegex(BackupError, "does not match"):
            clone_repo(repo, destination, Path("OTHER/repo"))
        self.assertEqual([], list(destination.iterdir()))

    def test_clone_rejects_project_folder_symlink_outside_backup(self):
        destination = self.root / "project-symlink"
        destination.mkdir()
        outside = self.root / "outside-project"
        outside.mkdir()
        (destination / "TOOLS").symlink_to(outside, target_is_directory=True)
        repo = SimpleNamespace(
            name="Repo", slug="repo", project={"key": "TOOLS"},
            https=self.fixture.url,
        )

        with self.assertRaisesRegex(BackupError, "escapes"):
            clone_repo(repo, destination, Path("TOOLS/repo"))
        self.assertEqual([], list(outside.iterdir()))

    def test_clone_failure_is_nonzero_and_keeps_recoverable_directory(self):
        destination = self.root / "failed-backup"
        destination.mkdir()
        repo = SimpleNamespace(
            name="Missing", slug="missing", https=self.fixture.url + "/missing"
        )
        with self.assertRaisesRegex(BackupError, "Git backup failed"):
            clone_repo(repo, destination)
        self.assertTrue((destination / "missing").is_dir())

    def test_branch_creation_failure_is_propagated(self):
        destination = self.root / "branch-failure"
        destination.mkdir()
        repo = SimpleNamespace(name="Repo", slug="repo", https=self.fixture.url)
        original_run_git = ripper_utils._run_git

        def fail_test_branch(arguments, cwd, **kwargs):
            if arguments[:2] == ["update-ref", "refs/heads/test"]:
                raise subprocess.CalledProcessError(1, ["git", *arguments])
            return original_run_git(arguments, cwd, **kwargs)

        with patch.object(ripper_utils, "_run_git", side_effect=fail_test_branch):
            with self.assertRaisesRegex(BackupError, "Git backup failed"):
                clone_repo(repo, destination)
        self.assertTrue((destination / "repo" / ".git").is_dir())

    def test_unsafe_repository_slugs_are_rejected_before_filesystem_changes(self):
        destination = self.root / "safe"
        destination.mkdir()
        unsafe_slugs = (
            "../escape",
            "/abs",
            "a/b",
            "a\\b",
            "",
            ".",
            "..",
            "nul\x00byte",
            "control\ncharacter",
            123,
            "a" * 256,
        )
        for slug in unsafe_slugs:
            with self.subTest(slug=slug):
                repo = SimpleNamespace(
                    name="Unsafe display name", slug=slug, https=self.fixture.url
                )
                with self.assertRaisesRegex(BackupError, "unsafe repository slug"):
                    clone_repo(repo, destination)
                self.assertEqual([], list(destination.iterdir()))
                self.assertFalse((self.root / "escape").exists())

    def test_duplicate_destinations_are_rejected_before_directories_are_created(self):
        destination = self.root / "duplicates"
        destination.mkdir()
        duplicate_sets = (
            ("same", "same"),
            ("Case-Slug", "case-slug"),
        )
        for slugs in duplicate_sets:
            with self.subTest(slugs=slugs):
                repos = [
                    SimpleNamespace(name=f"Repo {index}", slug=slug)
                    for index, slug in enumerate(slugs)
                ]
                with self.assertRaisesRegex(BackupError, "duplicate destinations"):
                    plan_repo_destinations(repos, destination)
                self.assertEqual([], list(destination.iterdir()))

    def test_resolved_destination_must_remain_a_direct_child(self):
        destination = self.root / "contained"
        destination.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (destination / "repo").symlink_to(outside, target_is_directory=True)
        repo = SimpleNamespace(name="Repo", slug="repo")

        with self.assertRaisesRegex(BackupError, "escapes"):
            plan_repo_destinations([repo], destination)

    def test_destination_resolution_errors_fail_closed(self):
        destination = self.root / "resolution-error"
        destination.mkdir()
        repo = SimpleNamespace(name="Repo", slug="repo")
        with patch.object(
                ripper_utils.Path, "resolve", side_effect=OSError("denied")):
            with self.assertRaisesRegex(BackupError, "resolve.*safely"):
                plan_repo_destinations([repo], destination)
        self.assertEqual([], list(destination.iterdir()))

    def test_archive_failure_keeps_source_and_removes_partial_archive(self):
        source = self.root / "archive-failure"
        source.mkdir()
        (source / "data").write_text("recoverable", encoding="utf-8")
        with patch.object(ripper_utils.tarfile, "open", side_effect=OSError("full")):
            with self.assertRaisesRegex(BackupError, "create and verify"):
                zip_output_dir(source)
        self.assertTrue(source.exists())
        self.assertFalse(source.with_name(f"{source.name}.tar.gz").exists())

    def test_archive_uses_umask_default_file_mode(self):
        source = self.root / "archive-mode"
        source.mkdir()
        (source / "data").write_text("archive", encoding="utf-8")
        previous_umask = os.umask(0o027)
        try:
            archive_path = Path(zip_output_dir(source))
        finally:
            os.umask(previous_umask)
        self.assertEqual(0o640, archive_path.stat().st_mode & 0o777)

    def test_destructive_helpers_require_an_explicit_directory(self):
        with self.assertRaises(TypeError):
            delete_output_directory()
        with self.assertRaises(TypeError):
            zip_output_dir()


if __name__ == "__main__":
    unittest.main()
