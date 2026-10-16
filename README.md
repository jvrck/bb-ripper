# bb-ripper - Bitbucket Repo Ripper

This project downloads all Bitbucket repositories and every branch for each repository. The resulting downloads are compressed with `tar`.

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

## Running the ripper

### Local Environment

The application supports Python 3.12.

To install Python dependencies

```bash
pip install -r requirements.txt
```

### Set the environment variables

Rename `env_setup.sh.example` to `env_setup.sh`, add the required values, and
source it. Existing installations must replace `BB_USER` and `BB_PASSWORD`
with `BB_EMAIL` and `BB_API_TOKEN` before upgrading.

```bash
source env_setup.sh
```

### Run

To run the application

```bash
cd bb-ripper
python3 .
```

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

To build the docker image

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
