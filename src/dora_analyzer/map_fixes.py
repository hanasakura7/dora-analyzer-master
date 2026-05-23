from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import pandas as pd
from git import Repo
from pydriller import Repository

from .config import AppConfig
from .git_utils import commit_is_ancestor
from .github_api import GitHubApiClient

FIX_KEYWORD_PATTERN = re.compile(
    r"\b(?:fixes|fix|fixed|closes|close|closed|resolves|resolve|resolved)\s+#(?P<issue>\d+)\b",
    re.IGNORECASE,
)


def extract_issue_numbers(text: str | None) -> list[int]:
    if not text:
        return []
    return [int(match.group("issue")) for match in FIX_KEYWORD_PATTERN.finditer(text)]


def build_commit_index(repo: Repo) -> dict[int, list[dict[str, Any]]]:
    matches: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for commit in Repository(path_to_repo=str(repo.working_tree_dir), only_no_merge=False).traverse_commits():
        issue_numbers = extract_issue_numbers(commit.msg)
        for issue_number in issue_numbers:
            matches[issue_number].append(
                {
                    "fix_commit_sha": commit.hash,
                    "fix_commit_date": pd.Timestamp(commit.committer_date),
                    "fixing_pr_number": None,
                    "mapping_confidence": "high",
                    "mapping_method": "commit_message_keyword",
                }
            )
    return matches


def build_pr_index(client: GitHubApiClient, config: AppConfig) -> dict[int, list[dict[str, Any]]]:
    if config.skip_api_cache_refresh:
        return {}
    matches: dict[int, list[dict[str, Any]]] = defaultdict(list)
    try:
        pull_requests = client.get_pull_requests(state="closed")
    except Exception:
        return {}
    for pr in pull_requests:
        texts = [pr.get("title"), pr.get("body"), pr.get("merge_commit_sha")]
        issue_numbers = set()
        for text in texts:
            issue_numbers.update(extract_issue_numbers(text))
        for issue_number in issue_numbers:
            merged_at = pr.get("merged_at") or pr.get("closed_at")
            matches[issue_number].append(
                {
                    "fix_commit_sha": pr.get("merge_commit_sha"),
                    "fix_commit_date": pd.to_datetime(merged_at, utc=True, errors="coerce"),
                    "fixing_pr_number": pr.get("number"),
                    "mapping_confidence": "medium",
                    "mapping_method": "pull_request_keyword",
                }
            )
    return matches


def choose_best_mapping(candidates: list[dict[str, Any]], closed_at: pd.Timestamp) -> dict[str, Any] | None:
    if not candidates:
        return None
    valid_candidates = [candidate for candidate in candidates if pd.notna(candidate.get("fix_commit_date"))]
    if not valid_candidates:
        return candidates[0]
    valid_candidates.sort(
        key=lambda candidate: (
            abs((candidate["fix_commit_date"] - closed_at).total_seconds()),
            {"high": 0, "medium": 1, "low": 2}.get(str(candidate.get("mapping_confidence")), 9),
        )
    )
    return valid_candidates[0]


def map_fixes(
    config: AppConfig,
    repo: Repo,
    failures_df: pd.DataFrame,
    deployments_df: pd.DataFrame,
    client: GitHubApiClient,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fix_output_path = config.processed_data_dir / "fix_mappings.csv"
    recovery_output_path = config.processed_data_dir / "recovery_mappings.csv"

    commit_index = build_commit_index(repo)
    pr_index = build_pr_index(client, config)
    deployment_records = deployments_df.sort_values("published_at").to_dict(orient="records")

    fix_rows: list[dict[str, Any]] = []
    recovery_rows: list[dict[str, Any]] = []

    for _, failure in failures_df.iterrows():
        issue_number = int(failure["issue_number"])
        issue_created_at = pd.Timestamp(failure["created_at"])
        issue_closed_at = pd.Timestamp(failure["closed_at"])
        candidates = commit_index.get(issue_number, []) + pr_index.get(issue_number, [])
        best = choose_best_mapping(candidates, issue_closed_at)

        if best is None:
            best = {
                "fix_commit_sha": None,
                "fix_commit_date": issue_closed_at,
                "fixing_pr_number": None,
                "mapping_confidence": "low",
                "mapping_method": "issue_closed_at_fallback",
            }

        fix_rows.append(
            {
                "issue_number": issue_number,
                "issue_created_at": issue_created_at.isoformat(),
                "issue_closed_at": issue_closed_at.isoformat(),
                "fix_commit_sha": best.get("fix_commit_sha"),
                "fix_commit_date": pd.Timestamp(best.get("fix_commit_date")).isoformat()
                if pd.notna(best.get("fix_commit_date"))
                else None,
                "fixing_pr_number": best.get("fixing_pr_number"),
                "mapping_confidence": best.get("mapping_confidence"),
                "mapping_method": best.get("mapping_method"),
            }
        )

        recovery = find_recovery_deployment(
            repo_path=config.local_repo_path,
            deployment_records=deployment_records,
            issue_number=issue_number,
            issue_created_at=issue_created_at,
            issue_closed_at=issue_closed_at,
            fix_commit_sha=best.get("fix_commit_sha"),
            fix_commit_date=pd.Timestamp(best.get("fix_commit_date")) if pd.notna(best.get("fix_commit_date")) else None,
            mapping_confidence=str(best.get("mapping_confidence")),
        )
        recovery_rows.append(recovery)

    fix_df = pd.DataFrame(fix_rows)
    recovery_df = pd.DataFrame(recovery_rows)

    fix_df.to_csv(fix_output_path, index=False)
    recovery_df.to_csv(recovery_output_path, index=False)

    return fix_df, recovery_df


def find_recovery_deployment(
    *,
    repo_path: Any,
    deployment_records: list[dict[str, Any]],
    issue_number: int,
    issue_created_at: pd.Timestamp,
    issue_closed_at: pd.Timestamp,
    fix_commit_sha: str | None,
    fix_commit_date: pd.Timestamp | None,
    mapping_confidence: str,
) -> dict[str, Any]:
    selected_tag = None
    selected_date = None
    confidence = mapping_confidence

    if fix_commit_sha:
        for deployment in deployment_records:
            tag = str(deployment["tag_name"])
            published_at = pd.Timestamp(deployment["published_at"])
            if fix_commit_date is not None and published_at < fix_commit_date:
                continue
            if commit_is_ancestor(repo_path, fix_commit_sha, tag):
                selected_tag = tag
                selected_date = published_at
                confidence = "high" if mapping_confidence == "high" else "medium"
                break

    if selected_tag is None:
        for deployment in deployment_records:
            published_at = pd.Timestamp(deployment["published_at"])
            if published_at >= issue_closed_at:
                selected_tag = str(deployment["tag_name"])
                selected_date = published_at
                confidence = "low"
                break

    recovery_days = None
    if selected_date is not None:
        recovery_days = (selected_date - issue_created_at).total_seconds() / 86400

    return {
        "issue_number": issue_number,
        "issue_created_at": issue_created_at.isoformat(),
        "issue_closed_at": issue_closed_at.isoformat(),
        "fix_commit_sha": fix_commit_sha,
        "recovery_deployment_tag": selected_tag,
        "recovery_deployment_date": selected_date.isoformat() if selected_date is not None else None,
        "recovery_time_days": recovery_days,
        "mapping_confidence": confidence,
    }


def run_szz_lite(repo: Repo, fix_mappings_df: pd.DataFrame, output_path: Any) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    try:
        for _, mapping in fix_mappings_df.dropna(subset=["fix_commit_sha"]).iterrows():
            commit_sha = str(mapping["fix_commit_sha"])
            commit = repo.commit(commit_sha)
            if not commit.parents:
                continue
            parent = commit.parents[0]
            for diff in parent.diff(commit, create_patch=False):
                if diff.a_path or diff.b_path:
                    rows.append(
                        {
                            "issue_number": mapping["issue_number"],
                            "fix_commit_sha": commit_sha,
                            "changed_file": diff.b_path or diff.a_path,
                            "parent_commit_sha": parent.hexsha,
                            "note": "SZZ-lite file-level parent mapping only",
                        }
                    )
    except Exception as exc:
        rows.append({"issue_number": None, "fix_commit_sha": None, "changed_file": None, "parent_commit_sha": None, "note": f"SZZ-lite failed: {exc}"})

    szz_df = pd.DataFrame(rows)
    szz_df.to_csv(output_path, index=False)
    return szz_df
