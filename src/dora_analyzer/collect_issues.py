from __future__ import annotations

from typing import Any

import pandas as pd

from .config import AppConfig
from .github_api import GitHubApiClient

BUG_LABEL_TOKENS = {"bug", "type:bug", "kind:bug", "kind/bug", "kind-bug", "confirmed bug"}
EXCLUDED_LABEL_TOKENS = {
    "invalid",
    "wontfix",
    "won't fix",
    "duplicate",
    "feature",
    "enhancement",
    "question",
    "documentation",
    "not planned",
}


def normalize_labels(labels: list[dict[str, Any]] | None) -> list[str]:
    normalized: list[str] = []
    for label in labels or []:
        name = str(label.get("name", "")).strip().lower()
        if name:
            normalized.append(name)
    return normalized


def is_bug_issue(labels: list[str]) -> bool:
    return any(token in label for label in labels for token in BUG_LABEL_TOKENS)


def has_excluded_label(labels: list[str]) -> bool:
    return any(token in label for label in labels for token in EXCLUDED_LABEL_TOKENS)


def normalize_issue_rows(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        labels = normalize_labels(issue.get("labels"))
        rows.append(
            {
                "issue_number": issue.get("number"),
                "title": issue.get("title"),
                "created_at": issue.get("created_at"),
                "closed_at": issue.get("closed_at"),
                "labels": "|".join(labels),
                "state": issue.get("state"),
                "html_url": issue.get("html_url"),
            }
        )
    return rows


def collect_issues(config: AppConfig, client: GitHubApiClient) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_path = config.raw_data_dir / "closed_bug_issues.csv"
    processed_path = config.processed_data_dir / "failures.csv"

    if raw_path.exists() and config.skip_api_cache_refresh:
        raw_df = pd.read_csv(raw_path)
    elif config.skip_api_cache_refresh and not raw_path.exists():
        raise FileNotFoundError(
            f"Cached issue data was requested via --skip-api-cache-refresh, but {raw_path} does not exist."
        )
    else:
        issues = client.get_issues(state="closed")
        all_issues_df = pd.DataFrame(normalize_issue_rows(issues))
        if all_issues_df.empty:
            raw_df = all_issues_df
        else:
            labels_series = all_issues_df["labels"].fillna("").map(lambda value: value.split("|") if value else [])
            raw_df = all_issues_df[labels_series.map(is_bug_issue)].copy()
        raw_df.to_csv(raw_path, index=False)

    if raw_df.empty:
        failures_df = raw_df.copy()
    else:
        failures_df = raw_df.copy()
        failures_df["created_at"] = pd.to_datetime(failures_df["created_at"], utc=True, errors="coerce")
        failures_df["closed_at"] = pd.to_datetime(failures_df["closed_at"], utc=True, errors="coerce")
        failures_df = failures_df[
            ~failures_df["labels"].fillna("").map(
                lambda value: has_excluded_label(value.split("|") if value else [])
            )
        ]
        if config.start_date:
            failures_df = failures_df[failures_df["created_at"] >= pd.Timestamp(config.start_date, tz="UTC")]
        if config.end_date:
            end_of_day = pd.Timestamp(config.end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            failures_df = failures_df[failures_df["created_at"] <= end_of_day]
        failures_df = failures_df.sort_values("closed_at").reset_index(drop=True)

    failures_df.to_csv(processed_path, index=False)
    return raw_df, failures_df
