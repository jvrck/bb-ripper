"""Tests for API-token-only configuration and URL handling."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bb-ripper"))

from auth_helper import (
    get_api_auth,
    get_git_https_url,
    use_project_folders,
    validate_environment,
)


class AuthHelperTests(unittest.TestCase):
    """Exercise authentication validation without real credentials."""

    def test_api_token_configuration_is_required(self):
        environment = {
            "BB_USER": "legacy-user",
            "BB_PASSWORD": "legacy-password",
            "BB_WORKSPACE": "workspace",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        with self.assertRaisesRegex(ValueError, "BB_EMAIL, BB_API_TOKEN"):
            validate_environment(environment)

    def test_empty_required_values_are_rejected_together(self):
        environment = {
            "BB_EMAIL": " ",
            "BB_API_TOKEN": "",
            "BB_WORKSPACE": "workspace",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        with self.assertRaisesRegex(ValueError, "BB_EMAIL, BB_API_TOKEN"):
            validate_environment(environment)

    def test_api_auth_returns_email_and_token(self):
        environment = {
            "BB_EMAIL": "backup@example.test",
            "BB_API_TOKEN": "synthetic-token",
            "BB_WORKSPACE": "workspace",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        self.assertEqual(
            ("backup@example.test", "synthetic-token"),
            get_api_auth(environment),
        )

    def test_project_folder_setting_accepts_only_boolean_words(self):
        valid_values = {
            None: False,
            "": False,
            "false": False,
            "FALSE": False,
            " true ": True,
        }
        for value, expected in valid_values.items():
            with self.subTest(value=value):
                environment = {}
                if value is not None:
                    environment["BB_USE_PROJECT_FOLDERS"] = value
                self.assertEqual(expected, use_project_folders(environment))

    def test_invalid_project_folder_setting_fails_validation(self):
        base_environment = {
            "BB_EMAIL": "backup@example.test",
            "BB_API_TOKEN": "synthetic-token",
            "BB_WORKSPACE": "workspace",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        for value in ("yes", "1", "on"):
            with self.subTest(value=value):
                environment = {
                    **base_environment,
                    "BB_USE_PROJECT_FOLDERS": value,
                }
                with self.assertRaisesRegex(
                        ValueError, "BB_USE_PROJECT_FOLDERS.*true or false"):
                    validate_environment(environment)

    def test_workspace_slug_cannot_escape_output_directory(self):
        environment = {
            "BB_EMAIL": "backup@example.test",
            "BB_API_TOKEN": "synthetic-token",
            "BB_WORKSPACE": "../escape",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        with self.assertRaisesRegex(ValueError, "workspace slug"):
            validate_environment(environment)

    def test_token_must_be_a_single_line_value(self):
        environment = {
            "BB_EMAIL": "backup@example.test",
            "BB_API_TOKEN": "synthetic\ntoken",
            "BB_WORKSPACE": "workspace",
            "BB_RIPPER_EXPORT_DIRECTORY": "/tmp/export",
        }
        with self.assertRaisesRegex(ValueError, "single-line.*BB_API_TOKEN"):
            validate_environment(environment)

    def test_clone_url_is_cleaned_without_adding_credentials(self):
        with patch.dict(os.environ, {"BB_API_TOKEN": "must-not-appear"}):
            result = get_git_https_url(
                "https://old-user@bitbucket.org/workspace/repository.git"
            )
        self.assertEqual(
            "https://bitbucket.org/workspace/repository.git", result
        )
        self.assertNotIn("must-not-appear", result)

    def test_clone_url_rejects_other_origins(self):
        with self.assertRaisesRegex(ValueError, "expected HTTPS host"):
            get_git_https_url("https://example.test/workspace/repository.git")


if __name__ == "__main__":
    unittest.main()
