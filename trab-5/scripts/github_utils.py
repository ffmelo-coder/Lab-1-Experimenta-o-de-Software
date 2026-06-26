import os
import time

import requests

GITHUB_TOKEN = "SEU_TOKEN_AQUI"

REST_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

REPO_QUERY_GRAPHQL = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    description
    stargazerCount
    forkCount
    watchers { totalCount }
    issues(states: OPEN) { totalCount }
    primaryLanguage { name }
    licenseInfo { name }
    defaultBranchRef { name }
    createdAt
    pushedAt
  }
}
"""


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or GITHUB_TOKEN
    if not token or token == "SEU_TOKEN_AQUI":
        return None
    return token


def validate_token(token=None):
    token = token or get_token()
    if not token:
        return False
    try:
        resp = requests.get(
            f"{REST_BASE}/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=(10, 30),
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _timed_request(method, url, retries=3, **kwargs):
    last_error = None
    for attempt in range(retries):
        try:
            start = time.perf_counter()
            resp = requests.request(method, url, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "status_code": resp.status_code,
                "elapsed_ms": elapsed_ms,
                "size_bytes": len(resp.content),
                "ok": resp.status_code == 200,
                "error": None,
            }
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    return {
        "status_code": None,
        "elapsed_ms": None,
        "size_bytes": None,
        "ok": False,
        "error": str(last_error),
    }


def rest_fetch_repo(owner, name, token=None, timeout=(10, 30), retries=3):
    token = token or get_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _timed_request(
        "GET",
        f"{REST_BASE}/repos/{owner}/{name}",
        headers=headers,
        timeout=timeout,
        retries=retries,
    )


def graphql_fetch_repo(owner, name, token=None, timeout=(10, 30), retries=3):
    token = token or get_token()
    if not token:
        return {
            "status_code": 401,
            "elapsed_ms": None,
            "size_bytes": None,
            "ok": False,
            "error": "GraphQL exige autenticação (defina GITHUB_TOKEN).",
        }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": REPO_QUERY_GRAPHQL, "variables": {"owner": owner, "name": name}}
    return _timed_request(
        "POST",
        GRAPHQL_URL,
        headers=headers,
        json=payload,
        timeout=timeout,
        retries=retries,
    )


def select_top_repos(target=100, per_page=100, token=None):
    token = token or get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    repos = []
    page = 1
    while len(repos) < target:
        resp = requests.get(
            f"{REST_BASE}/search/repositories",
            params={
                "q": "stars:>1000",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
            headers=headers,
            timeout=(10, 30),
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            break
        for item in items:
            repos.append(
                {
                    "owner": item["owner"]["login"],
                    "name": item["name"],
                    "stars": item["stargazers_count"],
                }
            )
        page += 1
        time.sleep(2)
    return repos[:target]
