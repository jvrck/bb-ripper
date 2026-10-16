"""Deterministic tests for container image publishing tags."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from image_metadata import image_metadata


class ImageMetadataTests(unittest.TestCase):
    """Prevent old release tags from being rewritten by rebuilds."""

    def test_master_push_updates_latest_only(self):
        push, tags = image_metadata("push", "refs/heads/master", "standard")
        self.assertTrue(push)
        self.assertEqual(
            ["jvrck/bbripper:latest", "ghcr.io/jvrck/bbripper:latest"], tags
        )

    def test_schedule_updates_latest_aws_only(self):
        push, tags = image_metadata("schedule", "refs/heads/master", "aws")
        self.assertTrue(push)
        self.assertEqual(
            ["jvrck/bbripper:latest-aws", "ghcr.io/jvrck/bbripper:latest-aws"],
            tags,
        )

    def test_tag_event_uses_only_the_actual_tag(self):
        push, tags = image_metadata("push", "refs/tags/2.0.0", "standard")
        self.assertTrue(push)
        self.assertIn("jvrck/bbripper:2.0.0", tags)
        self.assertIn("ghcr.io/jvrck/bbripper:2.0.0", tags)
        self.assertNotIn("jvrck/bbripper:1.2.7", tags)

    def test_release_branch_build_does_not_push(self):
        push, tags = image_metadata("push", "refs/heads/release/2.0.0", "aws")
        self.assertFalse(push)
        self.assertEqual(["ghcr.io/jvrck/bbripper:ci-aws"], tags)

    def test_invalid_docker_tag_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Docker tag"):
            image_metadata("push", "refs/tags/release/2.0.0", "standard")

    def test_tag_reserves_space_for_aws_suffix_in_both_jobs(self):
        overlong_with_aws_suffix = "a" * 125
        for variant in ("standard", "aws"):
            with self.subTest(variant=variant):
                with self.assertRaisesRegex(ValueError, "Docker tag"):
                    image_metadata(
                        "push", f"refs/tags/{overlong_with_aws_suffix}", variant
                    )


if __name__ == "__main__":
    unittest.main()
