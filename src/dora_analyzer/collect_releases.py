from __future__ import annotations

from typing import Any

import pandas as pd
from pandas import Timestamp

from .config import AppConfig
from .git_utils import is_semver_like_tag
from .github_api import GitHubApiClient


def normalize_release_rows(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for release in releases:
        rows.append(
            {
                "tag_name": release.get("tag_name"),
                "release_name": release.get("name"),
                "published_at": release.get("published_at"),
                "target_commitish": release.get("target_commitish"),
                "html_url": release.get("html_url"),
                "draft": bool(release.get("draft", False)),
                "prerelease": bool(release.get("prerelease", False)),
            }
        )
    return rows


def collect_releases(config: AppConfig, client: GitHubApiClient) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_path = config.raw_data_dir / "releases.csv"
    processed_path = config.processed_data_dir / "deployments.csv"

    if raw_path.exists() and config.skip_api_cache_refresh:
        raw_df = pd.read_csv(raw_path)
    elif config.skip_api_cache_refresh and not raw_path.exists():
        raise FileNotFoundError(
            f"Cached release data was requested via --skip-api-cache-refresh, but {raw_path} does not exist."
        )
    else:
        releases = client.get_releases()
        raw_df = pd.DataFrame(normalize_release_rows(releases))
        raw_df.to_csv(raw_path, index=False)

    if raw_df.empty:
        deployments_df = raw_df.copy()
    else:
        deployments_df = raw_df.copy()
        deployments_df = deployments_df[deployments_df["draft"] == False]  # noqa: E712
        if not config.include_prereleases:
            deployments_df = deployments_df[deployments_df["prerelease"] == False]  # noqa: E712
        deployments_df = deployments_df[deployments_df["tag_name"].astype(str).map(is_semver_like_tag)]
        deployments_df["published_at"] = pd.to_datetime(deployments_df["published_at"], utc=True, errors="coerce")
        if config.start_date:
            deployments_df = deployments_df[deployments_df["published_at"] >= Timestamp(config.start_date, tz="UTC")]
        if config.end_date:
            end_of_day = Timestamp(config.end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            deployments_df = deployments_df[deployments_df["published_at"] <= end_of_day]
        deployments_df = deployments_df.sort_values("published_at").reset_index(drop=True)

    deployments_df.to_csv(processed_path, index=False)
    return raw_df, deployments_df
