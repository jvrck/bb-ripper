# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
BBRipper is a Python-based Bitbucket repository backup tool that downloads all repositories and branches from a Bitbucket workspace and archives them as tar.gz files.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment variables
source env_setup.sh  # After copying env_setup.sh.example and adding values
```

### Running the Application
```bash
cd bb-ripper
python3 .
```

### Linting
```bash
# Install and run pylint
pip install pylint
pylint ./bb-ripper/
```

### Docker Commands
```bash
# Build docker image
docker build --no-cache -t ripper .

# Build with AWS CLI support
docker build --no-cache -t bbripper-aws --build-arg AWSCLI=TRUE .

# Run docker container
docker run --env-file dockenv -v $(pwd)/data:/data --rm -it ripper:latest
```

## Architecture

### Core Components

1. **bb-ripper/__main__.py**: Main entry point that orchestrates the backup process
   - Validates git installation
   - Creates output directory
   - Iterates through workspace repositories
   - Handles test mode with BB_TEST_COUNTER
   - Manages archiving and cleanup

2. **bb-ripper/bbhelper.py**: Bitbucket API integration
   - `BBProject`: Represents Bitbucket projects
   - `BBRepo`: Represents Bitbucket repositories with clone URLs
   - Static methods for fetching workspace repositories via REST API
   - Handles pagination of API responses

3. **bb-ripper/ripper_utils.py**: Utility functions for repository operations
   - `create_output_directory()`: Creates timestamped output directories
   - `clone_repo()`: Clones repositories and all branches
   - `zip_output_dir()`: Creates tar.gz archives
   - `check_git()`: Validates git installation
   - `get_https_url()`: Builds authenticated HTTPS URLs

### Environment Variables
Required:
- `BB_USER`: Bitbucket username
- `BB_PASSWORD`: Bitbucket app password
- `BB_WORKSPACE`: Target workspace name
- `BB_RIPPER_EXPORT_DIRECTORY`: Output directory path

Optional:
- `BB_TEST_COUNTER`: Limit repositories for testing (integer > 0)
- `LOGLEVEL`: Logging level (default: INFO)

### Key Design Patterns
- Global variables (`output_dir`, `output_base`) track output locations across modules
- Git operations use subprocess and os.system calls
- HTTPS authentication embedded in clone URLs
- Automatic branch discovery and checkout during cloning