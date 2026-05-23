from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .config import AppConfig

ADAPTED_CFR_NOTE = (
    "This is an adapted proxy for change failure rate because full SZZ bug-inducing commit detection was not implemented."
)


def prepare_period_column(df: pd.DataFrame, datetime_column: str, freq: str) -> pd.Series:
    timestamps = pd.to_datetime(df[datetime_column], utc=True, errors="coerce")
    return timestamps.dt.tz_localize(None).dt.to_period(freq).astype(str)


def calculate_deployment_frequency(deployments_df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if deployments_df.empty:
        return pd.DataFrame(columns=["period", "metric_name", "metric_value"])
    working = deployments_df.copy()
    working["period"] = prepare_period_column(working, "published_at", freq)
    summary = working.groupby("period").size().reset_index(name="metric_value")
    summary["metric_name"] = "deployment_frequency"
    return summary[["period", "metric_name", "metric_value"]]


def calculate_lead_time_metrics(commits_df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if commits_df.empty:
        return pd.DataFrame(columns=["period", "metric_name", "metric_value"])
    working = commits_df.copy()
    working["period"] = prepare_period_column(working, "deployment_date", freq)
    grouped = working.groupby("period")["lead_time_days"].agg(["mean", "median", "min", "max"]).reset_index()
    melted = grouped.melt(id_vars="period", var_name="statistic", value_name="metric_value")
    melted["metric_name"] = melted["statistic"].map(
        {
            "mean": "lead_time_days_mean",
            "median": "lead_time_days_median",
            "min": "lead_time_days_min",
            "max": "lead_time_days_max",
        }
    )
    return melted[["period", "metric_name", "metric_value"]]


def calculate_mttr_metrics(recovery_df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if recovery_df.empty:
        return pd.DataFrame(columns=["period", "metric_name", "metric_value"])
    working = recovery_df.dropna(subset=["recovery_deployment_date", "recovery_time_days"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "metric_name", "metric_value"])
    working["period"] = prepare_period_column(working, "recovery_deployment_date", freq)
    grouped = working.groupby("period")["recovery_time_days"].agg(["mean", "median"]).reset_index()
    melted = grouped.melt(id_vars="period", var_name="statistic", value_name="metric_value")
    melted["metric_name"] = melted["statistic"].map(
        {
            "mean": "recovery_time_days_mean",
            "median": "recovery_time_days_median",
        }
    )
    return melted[["period", "metric_name", "metric_value"]]


def calculate_adapted_cfr(
    deployments_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    if deployments_df.empty:
        return pd.DataFrame(columns=["period", "metric_name", "metric_value", "metric_note"])

    deployments = deployments_df.copy()
    deployments["period"] = prepare_period_column(deployments, "published_at", freq)

    fixes = recovery_df.dropna(subset=["recovery_deployment_tag"]).copy()
    bugfix_counts = fixes.groupby("recovery_deployment_tag").size().reset_index(name="bugfix_count")

    merged = deployments.merge(
        bugfix_counts,
        how="left",
        left_on="tag_name",
        right_on="recovery_deployment_tag",
    )
    merged["has_bugfix"] = merged["bugfix_count"].fillna(0).gt(0).astype(int)

    grouped = (
        merged.groupby("period")
        .agg(total_deployments=("tag_name", "count"), bugfix_deployments=("has_bugfix", "sum"))
        .reset_index()
    )
    grouped["metric_value"] = grouped["bugfix_deployments"] / grouped["total_deployments"]
    grouped["metric_name"] = "adapted_bugfix_deployment_rate"
    grouped["metric_note"] = ADAPTED_CFR_NOTE

    return grouped[["period", "metric_name", "metric_value", "metric_note"]]


def assemble_metrics(
    deployments_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    parts = [
        calculate_deployment_frequency(deployments_df, freq),
        calculate_lead_time_metrics(commits_df, freq),
        calculate_mttr_metrics(recovery_df, freq),
        calculate_adapted_cfr(deployments_df, recovery_df, freq),
    ]
    normalized_parts: list[pd.DataFrame] = []
    for part in parts:
        if "metric_note" not in part.columns:
            part = part.copy()
            part["metric_note"] = None
        normalized_parts.append(part[["period", "metric_name", "metric_value", "metric_note"]])
    return pd.concat(normalized_parts, ignore_index=True) if normalized_parts else pd.DataFrame()


def calculate_metrics(
    config: AppConfig,
    deployments_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    monthly = assemble_metrics(deployments_df, commits_df, recovery_df, "M")
    yearly = assemble_metrics(deployments_df, commits_df, recovery_df, "Y")

    monthly_path = config.results_dir / "dora_metrics_monthly.csv"
    yearly_path = config.results_dir / "dora_metrics_yearly.csv"
    summary_path = config.results_dir / "summary.json"

    monthly.to_csv(monthly_path, index=False)
    yearly.to_csv(yearly_path, index=False)

    summary: dict[str, Any] = {
        "repository": f"{config.owner}/{config.repo}",
        "start_date": config.start_date,
        "end_date": config.end_date,
        "include_prereleases": config.include_prereleases,
        "monthly_rows": int(len(monthly)),
        "yearly_rows": int(len(yearly)),
        "notes": [ADAPTED_CFR_NOTE],
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return monthly, yearly, summary
