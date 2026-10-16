# bb-ripper - Bitbucket Repo Ripper

This project downloads all Bitbucket repositories and every branch for each repository. The resulting downloads are compressed with `tar`.

Each repository is stored in a directory named after its Bitbucket repository
slug. This differs from versions through 1.2.8, which used the display name, so
on-disk and archive paths change when a repository's name and slug differ.

## Bitbucket Authentication

This application uses Bitbucket API tokens. App passwords are no longer
supported.

API tokens provide:
- Expiration control
- Centralized management for admins
- Modern security scopes

[Create an API token](https://support.atlassian.com/bitbucket-cloud/docs/create-an-api-token/)

## Environment Settings

The application validates all of the following environment variables before
creating a backup:

`BB_EMAIL` Your Atlassian account email.

`BB_API_TOKEN` Your Bitbucket API token.

`BB_WORKSPACE` The name of the Bitbucket workspace.

`BB_RIPPER_EXPORT_DIRECTORY` The path of the output.

### Optional Settings

`BB_TEST_COUNTER` Limit the number of repositories to process (useful for testing). All values that are non-integer or less than 1 will be ignored.

`BB_USE_PROJECT_FOLDERS` Organize repositories by Bitbucket project key when
set to `true` (default: `false`). Values are case-insensitive and may include
surrounding whitespace; values other than `true` or `false` are rejected.
Repository paths use slugs in either mode. For example:

```text
bbr-workspace-2026-03-05-T10.00.00/
  TOOLS/
    tools-api/
  UNASSIGNED/
    standalone-repo/
```

Repositories without a project key use the `UNASSIGNED` folder. To prevent
ambiguous backups on case-insensitive filesystems, a real project key that
differs from another only by case is rejected, as is a real `UNASSIGNED`
project when the same run contains repositories needing the fallback folder.

## Running the ripper

### Local Environment

The application supports Python 3.12. Install [uv](https://docs.astral.sh/uv/)
first, then use the pinned uv 0.12.24 to create the locked development
environment:

```bash
uvx uv@0.12.24 sync --locked
```

`pyproject.toml` and `uv.lock` are authoritative. `requirements.txt` is a
generated, hashed runtime-only fallback for environments that do not use uv.
To use that fallback, create a Python 3.12 virtual environment with the same
pinned uv, then install the runtime dependencies:

```bash
uvx uv@0.12.24 venv --seed --python 3.12 .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Set the environment variables

Rename `env_setup.sh.example` to `env_setup.sh`, add the required values, and
source it. Existing installations must replace `BB_USER` and `BB_PASSWORD`
with `BB_EMAIL` and `BB_API_TOKEN` before upgrading.

```bash
source env_setup.sh
```

### Run

Run the installed command through the locked environment:

```bash
uvx uv@0.12.24 run --locked bb-ripper
```

`uvx uv@0.12.24 run --locked python -m bb_ripper` is equivalent. A checkout
installed with the pip fallback can retain the legacy launch path with
`python3 bb-ripper/` or `cd bb-ripper && python3 .`.

### Running the docker image

To run the Docker image, create a `dockenv` file containing the required API
token settings. Create a `data` directory for the resulting archive and mount
it at `/data`.

Copy `docenv.example` to `dockenv` and replace its placeholder values.

```bash
docker pull jvrck/bbripper
docker run --env-file dockenv -v "$(pwd)/data:/data" --rm -it jvrck/bbripper:latest
```

### Building and running the docker image

The Dockerfile uses BuildKit features. BuildKit is enabled by default in
current Docker and Docker Buildx releases.

To build the docker image:

```bash
docker build --no-cache -t ripper .
```

To run the locally built image, use the same `dockenv` file and `/data` mount.

```bash
docker run --env-file dockenv -v "$(pwd)/data:/data" --rm -it ripper:latest
```

## Docker image with AWS CLI

A variant of the image that has the AWS CLI preinstalled. This can be done during the build by passing a build argument to the Docker `build` command.

```bash
docker build --no-cache -t bbripper-aws --build-arg AWSCLI=TRUE .
```
