"""Tests for fail-closed orchestration and cleanup ordering."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
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
        with patch.dict(os.environ, ENVIRONMENT, clear=True), \
                patch.object(MAIN, "check_git", return_value="/usr/bin/git"), \
                patch.object(MAIN, "create_output_directory", return_value="/tmp/source"), \
                patch.object(MAIN.BBRepo, "GetWorkspaceRepos", return_value=[]), \
                patch.object(MAIN, "zip_output_dir", return_value="/tmp/source.tar.gz"), \
                patch.object(MAIN, "delete_output_directory") as delete:
            archive = MAIN.run_backup()
        self.assertEqual("/tmp/source.tar.gz", archive)
        delete.assert_called_once_with("/tmp/source")

    def test_main_returns_nonzero_without_claiming_success(self):
        with patch.object(MAIN, "run_backup", side_effect=RuntimeError("failed")):
            self.assertEqual(1, MAIN.main())


if __name__ == "__main__":
    unittest.main()
