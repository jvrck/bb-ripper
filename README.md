# bb-ripper
# Bitbucket Repo Ripper

This project downloads all Bitbucket repositories and every branch for each repository. The resulting downloads are compressed with `tar`.

## Bitbucket Authentication

This application works with [Bitbucket App Passwords](https://support.atlassian.com/bitbucket-cloud/docs/app-passwords/)

## Environment Settings

The ripper requires the following environment variables to run.

`BB_USER` The username component of the Bitbucket App Password.

`BB_PASSWORD` The password component of the Bitbucket App Password.

`BB_WORKSPACE` The name of the Bitbucket workspace.

`BB_RIPPER_EXPORT_DIRECTORY` The path of the output.

You can use the optional environment variable `BB_TEST_COUNTER` to only pull down a specified number of repositories. This is useful for testing purposes. All values that are non integer and lower that 1 will be ignored.

## Running the ripper

### Local Environment

This has been developed and tested on `Python 3.8.16` and MacOS

To install python dependencies 
```
pip install -r requirements.txt
```

### Set the environment variables 
Open `env_setup.sh.example` and add the values for your environment. Rename the file to `env_setup.sh` Source the environment variables to add the to you session.
```
source env_setup.sh
```


### Run


To run the ripper
```
cd bb-ripper
python3 .
```

### Running the docker image
To run the image, create a docker environment file with the variables required named `docenv`. Create a directory named `data` to store the repositories. This directory will be mounted to the `/data` volume in the container.

```
docker pull jvrck/bbripper
docker run --env-file dockenv -v $(pwd)/data:/data  --rm -it  jvrck/bbripper:latest
```


### Building and running the docker image
To build the docker image
```
docker build --no-cache -t ripper .
```

To run the image, create a docker environment file with the variables required named `docenv`. Create a directory named `data` to store the repositories. This directory will be mounted to the `/data` volume in the container.

```
 docker run --env-file dockenv -v $(pwd)/data:/data  --rm -it  ripper:latest
```

## Docker image with AWS CLI.
There is a variant of the image that has the AWS CLI preinstalled. This is done during the build by passing a build argument to the Docker command.

```
docker build --no-cache -t bbripper-aws --build-arg AWSCLI=TRUE .
```