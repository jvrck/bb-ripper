"""
Module that provides authentication helper functions for Bitbucket.

Supports both app passwords (legacy) and API tokens.
Detection is based on environment variables:
- If BB_API_TOKEN is set: use API token mode
- Otherwise: use app password mode (requires BB_USER + BB_PASSWORD)
"""
import os
import re


def get_auth_mode():
    """
    Determine which authentication mode to use based on environment variables.
    
    Returns:
        str: 'api_token' or 'app_password'
    """
    if 'BB_API_TOKEN' in os.environ:
        return 'api_token'
    return 'app_password'


def get_api_auth():
    """
    Get authentication credentials for REST API calls.

    Returns:
        tuple: (username, password/token) for use with requests.auth

    For API token mode: returns (email, token)
    For app password mode: returns (username, password)
    """
    mode = get_auth_mode()

    if mode == 'api_token':
        # API tokens require email for REST API calls
        email = os.environ.get('BB_EMAIL')
        token = os.environ.get('BB_API_TOKEN')

        if not email:
            raise ValueError("BB_EMAIL is required when using BB_API_TOKEN")
        if not token:
            raise ValueError("BB_API_TOKEN is set but empty")

        return (email, token)

    # App password mode
    user = os.environ.get('BB_USER')
    password = os.environ.get('BB_PASSWORD')

    if not user:
        raise ValueError("BB_USER is required when not using BB_API_TOKEN")
    if not password:
        raise ValueError(
            "BB_PASSWORD is required when not using BB_API_TOKEN")

    return (user, password)


def get_git_https_url(base_url):
    """
    Transform a Bitbucket HTTPS URL to include authentication credentials.

    Args:
        base_url (str): The base HTTPS URL from Bitbucket
                        (e.g., https://bitbucket.org/workspace/repo.git
                        or https://username@bitbucket.org/workspace/repo.git)

    Returns:
        str: The URL with embedded credentials

    For API token mode: https://x-bitbucket-api-token-auth:{token}@...
    For app password mode: https://{username}:{password}@bitbucket.org/...
    """
    mode = get_auth_mode()

    # First, remove any existing username from the URL to normalize it
    # Bitbucket URLs may come in format: https://username@bitbucket.org/...
    # We need to strip the username part first
    clean_url = re.sub(r'https://[^@]+@', 'https://', base_url)

    if mode == 'api_token':
        # API tokens use static username for git operations
        token = os.environ.get('BB_API_TOKEN')

        if not token:
            raise ValueError("BB_API_TOKEN is set but empty")

        # Replace https:// with https://x-bitbucket-api-token-auth:{token}@
        return clean_url.replace(
            'https://', f'https://x-bitbucket-api-token-auth:{token}@')

    # App password mode
    user = os.environ.get('BB_USER')
    password = os.environ.get('BB_PASSWORD')

    if not user:
        raise ValueError("BB_USER is required when not using BB_API_TOKEN")
    if not password:
        raise ValueError("BB_PASSWORD is required when not using BB_API_TOKEN")

    # Replace https:// with https://{user}:{password}@
    return clean_url.replace('https://', f'https://{user}:{password}@')
