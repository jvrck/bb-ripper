"""Filesystem, Git, and archive utilities for bb-ripper."""

import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from shutil import which

from auth_helper import GIT_USERNAME, get_git_https_url

_CREDENTIAL_HELPER = (
    "!f() { if [ \"$1\" = get ]; then "
    "printf '%s\\n' \"username=$BB_GIT_USERNAME\" "
    "\"password=$BB_API_TOKEN\"; fi; }; f"
)


class BackupError(RuntimeError):
    """Raised for a safe, user-facing backup failure."""


def create_output_directory():
    """Create and return a unique output directory."""
    output_base = str(Path(os.environ["BB_RIPPER_EXPORT_DIRECTORY"]).resolve())
    Path(output_base).mkdir(parents=True, exist_ok=True)

    datetime_str = datetime.today().strftime("%Y-%m-%d-T%H.%M.%S")
    destination = Path(output_base) / f"bbr-{os.environ['BB_WORKSPACE']}-{datetime_str}"
    try:
        destination.mkdir()
    except OSError as error:
        raise BackupError("Unable to create a unique backup directory") from error

    return str(destination)


def delete_output_directory(directory):
    """Delete a completed backup's temporary source directory."""
    target = Path(directory)
    if target.exists():
        shutil.rmtree(target)


def check_git():
    """Return the Git executable path, if installed."""
    return which("git")


def _validate_repo_name(name):
    if (
            not isinstance(name, str)
            or not name
            or name in {".", ".."}
            or Path(name).name != name
            or "\x00" in name
    ):
        raise BackupError("Bitbucket returned an unsafe repository name")


def _git_clone_environment():
    environment = os.environ.copy()
    for name in ("BB_EMAIL", "BB_USER", "BB_PASSWORD"):
        environment.pop(name, None)
    for name in list(environment):
        if name.startswith("GIT_TRACE") or name == "GIT_CURL_VERBOSE":
            environment.pop(name)
    environment.update({
        "BB_GIT_USERNAME": GIT_USERNAME,
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "GIT_CONFIG_COUNT": "4",
        "GIT_CONFIG_KEY_0": "http.followRedirects",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "credential.helper",
        "GIT_CONFIG_VALUE_1": "",
        "GIT_CONFIG_KEY_2": "credential.helper",
        "GIT_CONFIG_VALUE_2": _CREDENTIAL_HELPER,
        "GIT_CONFIG_KEY_3": "credential.useHttpPath",
        "GIT_CONFIG_VALUE_3": "true",
    })
    return environment


def _git_safe_environment():
    environment = os.environ.copy()
    for name in ("BB_API_TOKEN", "BB_EMAIL", "BB_USER", "BB_PASSWORD"):
        environment.pop(name, None)
    return environment


def _run_git(arguments, cwd, **kwargs):
    kwargs.setdefault("env", _git_safe_environment())
    return subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, text=True, **kwargs
    )


def clone_repo(repo, destination):
    """Clone a repository securely and create local refs for all branches."""
    _validate_repo_name(repo.name)
    clean_url = get_git_https_url(repo.https)
    clone_dir = Path(destination) / repo.name
    try:
        clone_dir.mkdir()
    except OSError as error:
        raise BackupError(f"Unable to create backup directory for {repo.name}") from error

    try:
        _run_git(
            ["clone", "--", clean_url, "."],
            cwd=clone_dir,
            env=_git_clone_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        branches = _run_git(
            [
                "for-each-ref",
                "--format=%(refname:strip=3)%09%(symref)",
                "refs/remotes/origin",
            ],
            cwd=clone_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for line in branches.stdout.splitlines():
            branch, _, symbolic_target = line.partition("\t")
            if not branch or symbolic_target:
                continue
            exists = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=clone_dir,
                check=False,
                env=_git_safe_environment(),
            )
            if exists.returncode == 0:
                continue
            if exists.returncode != 1:
                raise BackupError(f"Unable to inspect branches for {repo.name}")
            _run_git(
                [
                    "update-ref",
                    f"refs/heads/{branch}",
                    f"refs/remotes/origin/{branch}",
                ],
                cwd=clone_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
    except subprocess.CalledProcessError as error:
        raise BackupError(f"Git backup failed for {repo.name}") from error


def zip_output_dir(directory):
    """Create, verify, and atomically finalize a compressed tar archive."""
    source = Path(directory).resolve()
    if not source.is_dir():
        raise BackupError("Backup source directory does not exist")

    archive_path = source.with_name(f"{source.name}.tar.gz")
    if archive_path.exists():
        raise BackupError("Backup archive already exists")

    with tempfile.NamedTemporaryFile(
            prefix=f".{source.name}.", suffix=".tar.gz",
            dir=source.parent, delete=False) as temporary_handle:
        temporary_path = Path(temporary_handle.name)

    try:
        with tarfile.open(temporary_path, "w:gz") as archive:
            archive.add(source, arcname=source.name)
        with tarfile.open(temporary_path, "r:gz") as archive:
            members = archive.getmembers()
            if not members or members[0].name != source.name:
                raise BackupError("Backup archive verification failed")
        current_umask = os.umask(0)
        os.umask(current_umask)
        temporary_path.chmod(0o666 & ~current_umask)
        os.replace(temporary_path, archive_path)
    except (OSError, tarfile.TarError) as error:
        temporary_path.unlink(missing_ok=True)
        raise BackupError("Unable to create and verify backup archive") from error
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return str(archive_path)
