from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests


def _parse_next_link(link_header: str) -> str | None:
    """Parse the 'next' URL from a GitHub Link response header."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API request fails."""


@dataclass
class GitHubApiClient:
    owner: str
    repo: str
    token: str | None = None
    timeout: int = 30
    api_base_url: str = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "dora-appflowy-analyzer",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _build_url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.api_base_url}/repos/{self.owner}/{self.repo}/{endpoint}"

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> requests.Response:
        response = requests.get(
            self._build_url(endpoint),
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response

    def get_paginated(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        base_params = dict(params or {})
        base_params.setdefault("per_page", 100)

        results: list[dict[str, Any]] = []
        # Start with the endpoint URL + initial params; subsequent pages use
        # the full 'next' URL from the Link header (cursor-based pagination).
        next_url: str | None = self._build_url(endpoint)
        current_params: dict[str, Any] | None = base_params

        while next_url:
            response = requests.get(
                next_url,
                headers=self._headers(),
                params=current_params,
                timeout=self.timeout,
            )
            self._raise_for_status(response)
            payload = response.json()
            if not isinstance(payload, list):
                raise GitHubApiError(f"Expected a list response for '{endpoint}', got: {type(payload).__name__}")
            if not payload:
                break
            results.extend(payload)
            # Follow cursor-based 'next' link; params are already embedded in the URL.
            next_url = _parse_next_link(response.headers.get("Link", ""))
            current_params = None  # don't re-append params to the cursor URL

        return results

    def get_releases(self) -> list[dict[str, Any]]:
        return self.get_paginated("releases")

    def get_issues(self, *, state: str = "closed", since: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"state": state, "direction": "desc", "sort": "updated"}
        if since:
            params["since"] = since
        return self.get_paginated("issues", params=params)

    def get_pull_requests(self, *, state: str = "closed") -> list[dict[str, Any]]:
        return self.get_paginated("pulls", params={"state": state, "sort": "updated", "direction": "desc"})

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            if remaining == "0":
                raise GitHubApiError(
                    "GitHub API rate limit exceeded. "
                    f"X-RateLimit-Remaining={remaining}, X-RateLimit-Reset={reset}. "
                    "Set GITHUB_TOKEN in .env or rerun with --skip-api-cache-refresh if cached data exists."
                )
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            raise GitHubApiError(f"GitHub API request failed with status {response.status_code}: {payload}")
