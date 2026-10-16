#!/usr/bin/env python3
"""Derive safe image publishing metadata from the GitHub event and ref."""

import argparse
import re

REGISTRIES = ("jvrck/bbripper", "ghcr.io/jvrck/bbripper")
DOCKER_TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


def image_metadata(event_name, ref, variant):
    """Return whether to push and the exact image tags for this event."""
    suffix = "-aws" if variant == "aws" else ""
    tag_event = event_name == "push" and ref.startswith("refs/tags/")
    version = ref.removeprefix("refs/tags/") if tag_event else None
    if version and not DOCKER_TAG.fullmatch(version):
        raise ValueError("Git tag cannot be represented as a Docker tag")

    push = tag_event or event_name == "schedule" or (
        event_name == "push" and ref == "refs/heads/master"
    )
    names = []
    if push:
        for registry in REGISTRIES:
            names.append(f"{registry}:latest{suffix}")
            if version:
                names.append(f"{registry}:{version}{suffix}")
    else:
        names.append(f"ghcr.io/jvrck/bbripper:ci{suffix or '-standard'}")
    return push, names


def main():
    """Write GitHub Actions outputs to standard output."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--variant", choices=("standard", "aws"), required=True)
    args = parser.parse_args()
    push, tags = image_metadata(args.event_name, args.ref, args.variant)
    print(f"push={str(push).lower()}")
    print("tags<<BBRIPPER_TAGS")
    print("\n".join(tags))
    print("BBRIPPER_TAGS")


if __name__ == "__main__":
    main()
