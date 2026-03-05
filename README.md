# bb-ripper - Bitbucket Repo Ripper

This project downloads all Bitbucket repositories and every branch for each repository. The resulting downloads are compressed with `tar`.

## Bitbucket Authentication

This application supports two authentication methods:

### API Tokens (Recommended)

**Required after June 9, 2026** when app passwords are deprecated.

API tokens provide:
- Expiration control
- Centralized management for admins
- Modern security scopes

[Create an API token](https://support.atlassian.com/bitbucket-cloud/docs/create-an-api-token/)

### App Passwords (Legacy - Deprecated)

⚠️ **App passwords will stop working on June 9, 2026**

Existing app passwords will continue to work until that date, but no new app passwords can be created as of September 9, 2025.

[More about app password deprecation](https://www.atlassian.com/blog/bitbucket/bitbucket-cloud-transitions-to-api-tokens-enhancing-security-with-app-password-deprecation)

## Environment Settings

The application requires the following environment variables to run.

### For API Token Authentication (Recommended)

`BB_EMAIL` Your Atlassian account email.

`BB_API_TOKEN` Your Bitbucket API token.

`BB_WORKSPACE` The name of the Bitbucket workspace.

`BB_RIPPER_EXPORT_DIRECTORY` The path of the output.

### For App Password Authentication (Legacy)

`BB_USER` The username component of the Bitbucket App Password.

`BB_PASSWORD` The password component of the Bitbucket App Password.

`BB_WORKSPACE` The name of the Bitbucket workspace.

`BB_RIPPER_EXPORT_DIRECTORY` The path of the output.

### Optional Settings

`BB_TEST_COUNTER` Limit the number of repositories to process (useful for testing). All values that are non-integer or less than 1 will be ignored.

## Running the ripper

### Local Environment

The application was developed and tested on MacOS with the [Python 3.11 package](https://formulae.brew.sh/formula/python@3.11) managed with [Homebrew](https://brew.sh/).

To install Python dependencies

```bash
pip install -r requirements.txt
```

### Set the environment variables

To set the environment variables: Rename `env_setup.sh.example` to `env_setup.sh` after adding values for your environment, then source the environment variables to add them to your session.

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

To run the docker image: Create a Docker environment file with the variables required, named `docenv`. Create a directory named `data` to store the repositories. This directory will be mounted to the `/data` volume in the container.

The repository contains a file named `docenv.example` that is a template for the `docenv` file.

```bash
docker pull jvrck/bbripper
docker run --env-file dockenv -v $(pwd)/data:/data  --rm -it  jvrck/bbripper:latest
```

### Building and running the docker image

To build the docker image

```bash
docker build --no-cache -t ripper .
```

To run the image, create a docker environment file with the variables required named `docenv`. Create a directory named `data` to store the repositories. This directory will be mounted to the `/data` volume in the container.

```bash
 docker run --env-file dockenv -v $(pwd)/data:/data  --rm -it  ripper:latest
```

## Docker image with AWS CLI

A variant of the image that has the AWS CLI preinstalled. This can be done during the build by passing a build argument to the Docker `build` command.

```bash
docker build --no-cache -t bbripper-aws --build-arg AWSCLI=TRUE .
```
