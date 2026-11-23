"""
NyxaLensAI — GitHub API Client
Retrieves GITHUB_TOKEN from AWS Secrets Manager (never plaintext env var).
Uses @lru_cache so the secret is fetched once per Lambda cold start.
"""
from __future__ import annotations

import os
import logging
from functools import lru_cache

import boto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

GITHUB_SECRET_ARN = os.environ.get("GITHUB_SECRET_ARN", "")
GITHUB_API_BASE   = "https://api.github.com"
_TIMEOUT          = httpx.Timeout(8.0, connect=3.0)


@lru_cache(maxsize=1)
def _get_token() -> str:
    """Fetch GitHub token from Secrets Manager once per warm Lambda instance."""
    secret_arn = os.environ.get("GITHUB_SECRET_ARN", "")
    if not secret_arn:
        logger.warning("GITHUB_SECRET_ARN not set — using unauthenticated GitHub API (60 req/hr)")
        return ""
    try:
        client = boto3.client("secretsmanager",
                               region_name=os.environ.get("AWS_REGION", "us-east-1"))
        return client.get_secret_value(SecretId=secret_arn)["SecretString"]
    except ClientError as e:
        logger.error("Failed to retrieve GitHub token: %s", e)
        return ""


def _headers() -> dict[str, str]:
    token = _get_token()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_repo_tree(owner: str, repo: str, depth: int = 2) -> dict:
    """Fetch the repository file tree (truncated to depth)."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(url, headers=_headers())
        r.raise_for_status()
        return r.json()


def get_public_repo(owner: str, repo: str) -> dict:
    """Return public repository metadata; 404 includes private repositories."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.get(url, headers=_headers())
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()


def get_repo_head_sha(owner: str, repo: str) -> str:
    """Return current default-branch commit SHA for cache invalidation."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/HEAD"
    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.get(url, headers=_headers())
        response.raise_for_status()
        return response.json().get("sha", "")


def get_file_content(owner: str, repo: str, path: str) -> str:
    """Fetch a single file's decoded text content (max 1MB)."""
    import base64
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(url, headers=_headers())
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        data = r.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")


def search_repos(query: str, sort: str = "stars", per_page: int = 5) -> list[dict]:
    """Search GitHub repositories by keyword query."""
    url = f"{GITHUB_API_BASE}/search/repositories"
    params = {"q": query, "sort": sort, "order": "desc", "per_page": per_page}
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(url, headers=_headers(), params=params)
        r.raise_for_status()
        return r.json().get("items", [])


def search_repos_by_name(name: str, per_page: int = 10) -> list[dict]:
    """Search for repos with a name similar to the given string."""
    return search_repos(f"{name} in:name", sort="stars", per_page=per_page)
