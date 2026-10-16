# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project overview

BBRipper is a Python 3.12 application that downloads every repository and
branch in a Bitbucket workspace, then creates a compressed tar archive.

## Development commands

```bash
uvx uv@0.12.24 sync --locked
uvx uv@0.12.24 run --locked python -m unittest discover -v
uvx uv@0.12.24 run --locked pylint src/bb_ripper bb-ripper scripts
uvx uv@0.12.24 run --locked pip-audit -r requirements.txt
uvx uv@0.12.24 build
```

For the supported pip fallback, create and activate a Python 3.12 virtual
environment with `uvx uv@0.12.24 venv --seed --python 3.12 .venv` and `source
.venv/bin/activate`, run `python -m pip install -r requirements.txt`, and use
`PYTHONPATH=src python -m unittest discover -v`. After dependency changes,
regenerate the pip fallback with `BBRIPPER_UV="uvx uv@0.12.24"
scripts/export_requirements.sh`.

Build both supported image variants with:

```bash
docker build -t bbripper:local .
docker build -t bbripper:local-aws --build-arg AWSCLI=TRUE .
```

## Runtime configuration

All four values are required and validated before backup work starts:

- `BB_EMAIL`: Atlassian account email used by REST authentication.
- `BB_API_TOKEN`: Bitbucket API token used by REST and Git authentication.
- `BB_WORKSPACE`: Bitbucket workspace slug.
- `BB_RIPPER_EXPORT_DIRECTORY`: destination for the completed archive.

`BB_TEST_COUNTER` optionally limits the number of repositories. `LOGLEVEL`
controls API logging. `BB_USE_PROJECT_FOLDERS` optionally groups repository
slugs under project keys (`true`/`false`, default `false`). App-password
variables are intentionally unsupported.

## Architecture and safety invariants

- `src/bb_ripper/__main__.py` validates configuration, orchestrates the backup,
  and deletes temporary source only after an archive is created and verified.
- `src/bb_ripper/bbhelper.py` performs bounded REST requests with status, shape,
  timeout, and same-origin pagination checks.
- `src/bb_ripper/ripper_utils.py` clones without shell interpolation. A
  process-local Git credential helper exposes the API token only to the clone
  process; persisted origins and archives must remain credential-free.
- `bb-ripper/__main__.py` is only the legacy source and container launcher; it
  delegates to the installed `bb_ripper` package.
- Repository display names are report-only. Repository slugs are validated as
  single path components, and all selected destinations are checked for
  containment and case-insensitive collisions before cloning begins.
- The output directory is assumed to be exclusively owned by the backup
  process. Concurrent local modification or symlink swapping is outside the
  threat model; containment is re-checked after project folders are created.
- Git, branch, API, and archive failures are terminal. Never turn these into a
  successful or partial backup result.
- Tests use disposable local Git and HTTP fixtures. Do not use real Bitbucket
  credentials, production backups, or existing archives as fixtures.
- `scripts/image_metadata.py` is the tested source of image tags. Branch and
  scheduled builds may update only `latest`; a version tag may be published
  only for the matching Git tag event.
