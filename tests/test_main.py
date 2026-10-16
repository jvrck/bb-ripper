"""Tests for fail-closed orchestration and cleanup ordering."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bb-ripper"))
SPEC = importlib.util.spec_from_file_location(
    "bbripper_main", ROOT / "bb-ripper" / "__main__.py"
)
MAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAIN)

ENVIRONMENT = {
    "BB_EMAIL": "backup@example.test",
    "BB_API_TOKEN": "synthetic-token",
    "BB_WORKSPACE": "workspace",
    "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
}


class MainTests(unittest.TestCase):
    """Ensure source deletion happens only after archive verification."""

    def test_archive_failure_does_not_delete_source(self):
        with patch.dict(os.environ, ENVIRONMENT, clear=True), \
                patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                patch.object(MAIN, "create_output_directory", return_value="/tmp/source"), \
                patch.object(MAIN.BBRepo, "GetWorkspaceRepos", return_value=[]), \
                patch.object(MAIN, "zip_output_dir", side_effect=RuntimeError("archive")), \
                patch.object(MAIN, "delete_output_directory") as delete:
            with self.assertRaisesRegex(RuntimeError, "archive"):
                MAIN.run_backup()
        delete.assert_not_called()

    def test_verified_archive_is_followed_by_source_cleanup(self):
        environment = {**ENVIRONMENT, "BB_TEST_COUNTER": "²"}
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                patch.object(MAIN, "create_output_directory", return_value="/tmp/source"), \
                patch.object(MAIN.BBRepo, "GetWorkspaceRepos", return_value=[]), \
                patch.object(MAIN, "zip_output_dir", return_value="/tmp/source.tar.gz"), \
                patch.object(MAIN, "delete_output_directory") as delete:
            archive = MAIN.run_backup()
        self.assertEqual("/tmp/source.tar.gz", archive)
        delete.assert_called_once_with("/tmp/source")

    def test_planning_failure_stops_before_clone_archive_or_cleanup(self):
        repos = [
            SimpleNamespace(name="One", slug="duplicate"),
            SimpleNamespace(name="Two", slug="DUPLICATE"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            with patch.dict(os.environ, ENVIRONMENT, clear=True), \
                    patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                    patch.object(
                        MAIN, "create_output_directory", return_value=str(source)
                    ), \
                    patch.object(
                        MAIN.BBRepo, "GetWorkspaceRepos", return_value=repos
                    ), \
                    patch.object(MAIN, "clone_repo") as clone, \
                    patch.object(MAIN, "zip_output_dir") as archive, \
                    patch.object(MAIN, "delete_output_directory") as delete:
                with self.assertRaisesRegex(
                        MAIN.BackupError, "duplicate destinations"):
                    MAIN.run_backup()

            self.assertTrue(source.is_dir())
            clone.assert_not_called()
            archive.assert_not_called()
            delete.assert_not_called()

    def test_repository_limit_is_applied_before_destination_planning(self):
        first = SimpleNamespace(name="First", slug="duplicate")
        repos = [first, SimpleNamespace(name="Second", slug="DUPLICATE")]
        environment = {**ENVIRONMENT, "BB_TEST_COUNTER": "1"}
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                patch.object(
                    MAIN, "create_output_directory", return_value="/tmp/source"
                ), \
                patch.object(
                    MAIN.BBRepo, "GetWorkspaceRepos", return_value=repos
                ), \
                patch.object(MAIN, "clone_repo") as clone, \
                patch.object(
                    MAIN, "zip_output_dir", return_value="/tmp/source.tar.gz"
                ), \
                patch.object(MAIN, "delete_output_directory"):
            self.assertEqual("/tmp/source.tar.gz", MAIN.run_backup())

        clone.assert_called_once_with(first, "/tmp/source", Path("duplicate"))

    def test_grouped_ambiguity_stops_before_clone_archive_or_cleanup(self):
        repos = [
            SimpleNamespace(
                name="Real", slug="real", project={"key": "UNASSIGNED"}
            ),
            SimpleNamespace(name="Fallback", slug="fallback", project=None),
        ]
        environment = {**ENVIRONMENT, "BB_USE_PROJECT_FOLDERS": "true"}
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            with patch.dict(os.environ, environment, clear=True), \
                    patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                    patch.object(
                        MAIN, "create_output_directory", return_value=str(source)
                    ), \
                    patch.object(
                        MAIN.BBRepo, "GetWorkspaceRepos", return_value=repos
                    ), \
                    patch.object(MAIN, "clone_repo") as clone, \
                    patch.object(MAIN, "zip_output_dir") as archive, \
                    patch.object(MAIN, "delete_output_directory") as delete:
                with self.assertRaisesRegex(MAIN.BackupError, "conflicts"):
                    MAIN.run_backup()

            self.assertEqual([], list(source.iterdir()))
            clone.assert_not_called()
            archive.assert_not_called()
            delete.assert_not_called()

    def test_invalid_project_setting_stops_before_backup_work(self):
        environment = {**ENVIRONMENT, "BB_USE_PROJECT_FOLDERS": "yes"}
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(MAIN, "check_git") as check_git, \
                patch.object(MAIN, "create_output_directory") as create:
            with self.assertRaisesRegex(ValueError, "BB_USE_PROJECT_FOLDERS"):
                MAIN.run_backup()
        check_git.assert_not_called()
        create.assert_not_called()

    def test_main_returns_nonzero_without_claiming_success(self):
        with patch.object(MAIN, "run_backup", side_effect=RuntimeError("failed")):
            self.assertEqual(1, MAIN.main())


if __name__ == "__main__":
    unittest.main()
