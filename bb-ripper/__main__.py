"""The main entry point for bb-ripper."""

import os
import sys
import time

from auth_helper import validate_environment
from bbhelper import BBRepo
from ripper_utils import BackupError
from ripper_utils import check_git
from ripper_utils import clone_repo
from ripper_utils import create_output_directory
from ripper_utils import delete_output_directory
from ripper_utils import zip_output_dir


def run_backup():
    """Run one complete workspace backup, returning the archive path."""
    validate_environment()
    if check_git() is None:
        raise BackupError("Git is not installed")

    test_counter = os.environ.get("BB_TEST_COUNTER")
    try:
        limit = int(test_counter) if test_counter is not None else None
    except ValueError:
        limit = None
    if limit is not None and limit < 1:
        limit = None

    output_directory = create_output_directory()
    workspace_repos = BBRepo.GetWorkspaceRepos(os.environ["BB_WORKSPACE"])

    for counter, repo in enumerate(workspace_repos, start=1):
        print(f"Backing up repository: {repo.name}")
        clone_repo(repo, output_directory)
        if limit is not None and counter == limit:
            break

    archive_path = zip_output_dir(output_directory)
    delete_output_directory(output_directory)
    return archive_path


def main():
    """Validate, run the backup, and report a safe terminal status."""
    start_time = time.time()
    try:
        archive_path = run_backup()
    except Exception as error:  # pylint: disable=broad-exception-caught
        print(f"Backup failed: {error}", file=sys.stderr)
        return 1

    print(f"Backup complete: {archive_path}")
    print(f"Elapsed time: {time.time() - start_time:.2f} seconds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
