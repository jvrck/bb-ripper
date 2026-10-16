"""Filesystem, Git, and archive utilities for bb-ripper."""

import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from shutil import which

from auth_helper import GIT_USERNAME, get_git_https_url, use_project_folders

_SAFE_COMPONENT_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)
_MAX_COMPONENT_BYTES = 255
_UNASSIGNED_PROJECT = "UNASSIGNED"
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


def _validate_component(value, label):
    """Validate and return one safe filesystem path component."""
    if (
            not isinstance(value, str)
            or not value
            or value in {".", ".."}
            or any(character not in _SAFE_COMPONENT_CHARACTERS for character in value)
            or len(value.encode("utf-8")) > _MAX_COMPONENT_BYTES
    ):
        raise BackupError(f"Bitbucket returned an unsafe {label}")
    return value


def _validate_repository_slug(slug):
    """Validate and return one safe repository directory component."""
    return _validate_component(slug, "repository slug")


def _repository_project_key(repo):
    """Return a repository's project key and whether it is a fallback."""
    project = getattr(repo, "project", None)
    if not isinstance(project, dict) or not project:
        return _UNASSIGNED_PROJECT, True

    key = project.get("key")
    if key is None or key == "":
        return _UNASSIGNED_PROJECT, True
    return _validate_component(key, "project key"), False


def _resolve_repository_destination(backup_directory, repository_path):
    """Return an exact one- or two-component repository destination."""
    relative_path = Path(repository_path)
    if relative_path.is_absolute() or len(relative_path.parts) not in {1, 2}:
        raise BackupError("Bitbucket returned an unsafe repository destination")
    for component in relative_path.parts:
        _validate_component(component, "repository destination")

    try:
        backup_root = Path(backup_directory).resolve()
        destination = backup_root / relative_path
        resolved_destination = destination.resolve()
    except (OSError, RuntimeError) as error:
        raise BackupError("Unable to resolve repository destination safely") from error
    if resolved_destination != destination:
        raise BackupError("Repository destination escapes the backup directory")
    return destination


def _grouped_repository_path(repo, project_keys, project_state):
    """Return a grouped path while tracking project-level ambiguities."""
    project_key, is_fallback = _repository_project_key(repo)
    if is_fallback:
        project_state["fallback"] = True
    else:
        folded_project = project_key.casefold()
        previous_key = project_keys.get(folded_project)
        if previous_key is not None and previous_key != project_key:
            raise BackupError(
                "Bitbucket projects have case-insensitive key collisions"
            )
        project_keys[folded_project] = project_key
        if folded_project == _UNASSIGNED_PROJECT.casefold():
            project_state["real_unassigned"] = True
    return Path(project_key) / _validate_repository_slug(repo.slug)


def plan_repo_destinations(
        repositories, backup_directory, project_folders=None):
    """Validate all repository destinations and reject collisions up front."""
    grouped = use_project_folders() if project_folders is None else project_folders
    planned = []
    destinations = set()
    project_keys = {}
    project_state = {"fallback": False, "real_unassigned": False}
    for repo in repositories:
        if grouped:
            relative_path = _grouped_repository_path(
                repo, project_keys, project_state
            )
        else:
            relative_path = Path(_validate_repository_slug(repo.slug))
        _resolve_repository_destination(backup_directory, relative_path)
        collision_key = str(relative_path).casefold()
        if collision_key in destinations:
            raise BackupError("Bitbucket repositories have duplicate destinations")
        destinations.add(collision_key)
        planned.append((repo, relative_path))
    if project_state["fallback"] and project_state["real_unassigned"]:
        raise BackupError(
            "A real UNASSIGNED project conflicts with unassigned repositories"
        )
    return planned


def _validated_repository_path(repo, repository_path):
    """Validate a clone path against the repository slug and project."""
    slug = _validate_repository_slug(repo.slug)
    relative_path = Path(slug) if repository_path is None else Path(repository_path)
    if len(relative_path.parts) == 1:
        expected_path = Path(slug)
    elif len(relative_path.parts) == 2:
        project_key, _is_fallback = _repository_project_key(repo)
        expected_path = Path(project_key) / slug
    else:
        expected_path = None
    if relative_path != expected_path:
        raise BackupError("Repository destination does not match its slug")
    return relative_path


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


def clone_repo(repo, destination, repository_path=None):
    """Clone a repository securely and create local refs for all branches."""
    relative_path = _validated_repository_path(repo, repository_path)
    clean_url = get_git_https_url(repo.https)
    clone_dir = _resolve_repository_destination(destination, relative_path)
    try:
        if len(relative_path.parts) == 2:
            clone_dir.parent.mkdir(exist_ok=True)
            clone_dir = _resolve_repository_destination(destination, relative_path)
        clone_dir.mkdir()
    except OSError as error:
        raise BackupError(
            f"Unable to create backup directory for {repo.name} ({repo.slug})"
        ) from error

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
