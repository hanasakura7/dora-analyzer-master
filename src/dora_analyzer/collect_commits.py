from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from git import Repo
from pydriller import Repository

from .config import AppConfig


@dataclass(frozen=True)
class DeploymentWindow:
    previous_tag: str
    deployment_tag: str
    deployment_date: pd.Timestamp


def build_deployment_windows(deployments_df: pd.DataFrame) -> list[DeploymentWindow]:
    if deployments_df.empty or len(deployments_df) < 2:
        return []
    windows: list[DeploymentWindow] = []
    ordered = deployments_df.sort_values("published_at").reset_index(drop=True)
    for index in range(1, len(ordered)):
        windows.append(
            DeploymentWindow(
                previous_tag=str(ordered.loc[index - 1, "tag_name"]),
                deployment_tag=str(ordered.loc[index, "tag_name"]),
                deployment_date=pd.Timestamp(ordered.loc[index, "published_at"]),
            )
        )
    return windows


def collect_commits_between_deployments(
    config: AppConfig,
    repo: Repo,
    deployments_df: pd.DataFrame,
) -> pd.DataFrame:
    output_path = config.processed_data_dir / "commits_between_deployments.csv"
    rows: list[dict[str, object]] = []

    for window in build_deployment_windows(deployments_df):
        for commit in Repository(
            path_to_repo=str(repo.working_tree_dir),
            from_tag=window.previous_tag,
            to_tag=window.deployment_tag,
            order="date-order",
            only_no_merge=False,
        ).traverse_commits():
            commit_date = pd.Timestamp(commit.committer_date)
            lead_time_days = (window.deployment_date - commit_date).total_seconds() / 86400
            rows.append(
                {
                    "deployment_tag": window.deployment_tag,
                    "previous_tag": window.previous_tag,
                    "deployment_date": window.deployment_date.isoformat(),
                    "commit_sha": commit.hash,
                    "commit_date": commit_date.isoformat(),
                    "author_name": commit.author.name,
                    "author_email": commit.author.email,
                    "commit_message": commit.msg,
                    "lead_time_days": lead_time_days,
                }
            )

    commits_df = pd.DataFrame(rows)
    commits_df.to_csv(output_path, index=False)
    return commits_df
