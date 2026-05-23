from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .config import AppConfig

SUMMARY_METRICS = [
    ("deployment_frequency",           "Deployment Frequency",  "Deployments / Year"),
    ("lead_time_days_mean",            "Lead Time (Mean)",      "Days"),
    ("recovery_time_days_mean",        "MTTR (Mean)",           "Days"),
    ("adapted_bugfix_deployment_rate", "Adapted CFR",           "Rate (0–1)"),
]


def _save_line_chart(series_df: pd.DataFrame, title: str, ylabel: str, output_path) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(series_df["period"], series_df["metric_value"], marker="o")
    plt.title(title)
    plt.xlabel("Period")
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def generate_summary_yearly_chart(
    yearly_metrics: pd.DataFrame,
    output_path,
    repo_label: str = "",
    start_year: int = 2022,
    end_year: int = 2025,
) -> None:
    """Grouped bar chart — all 4 DORA metrics side-by-side per year."""
    df = yearly_metrics.copy()
    df["period"] = pd.to_numeric(df["period"], errors="coerce")
    df = df[(df["period"] >= start_year) & (df["period"] <= end_year)]

    years = sorted(df["period"].dropna().unique().astype(int))
    n_metrics = len(SUMMARY_METRICS)
    bar_width = 0.18
    x = range(len(years))

    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (metric_name, label, _) in enumerate(SUMMARY_METRICS):
        m_df = df[df["metric_name"] == metric_name].set_index("period")["metric_value"]
        values = [float(m_df.get(y, 0.0)) for y in years]
        offsets = [xi + i * bar_width for xi in x]
        ax.bar(offsets, values, width=bar_width, label=label, color=colors[i])

    title = f"DORA Metrics Summary by Year ({start_year}–{end_year})"
    if repo_label:
        title = f"{repo_label} — {title}"
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Metric Value")
    ax.set_xticks([xi + bar_width * (n_metrics - 1) / 2 for xi in x])
    ax.set_xticklabels(years)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def generate_charts(config: AppConfig, monthly_metrics: pd.DataFrame, yearly_metrics: pd.DataFrame) -> None:
    monthly_chart_specs = [
        ("deployment_frequency", "Deployment Frequency by Month", "Deployments", config.charts_dir / "deployment_frequency_monthly.png"),
        ("lead_time_days_mean", "Lead Time for Changes by Month", "Days", config.charts_dir / "lead_time_monthly.png"),
        ("recovery_time_days_mean", "Mean Time to Recover by Month", "Days", config.charts_dir / "mttr_monthly.png"),
        ("adapted_bugfix_deployment_rate", "Adapted Bugfix Deployment Rate by Month", "Rate", config.charts_dir / "adapted_cfr_monthly.png"),
    ]
    yearly_chart_specs = [
        ("deployment_frequency", "Deployment Frequency by Year", "Deployments", config.charts_dir / "deployment_frequency_yearly.png"),
        ("lead_time_days_mean", "Lead Time for Changes by Year", "Days", config.charts_dir / "lead_time_yearly.png"),
        ("recovery_time_days_mean", "Mean Time to Recover by Year", "Days", config.charts_dir / "mttr_yearly.png"),
        ("adapted_bugfix_deployment_rate", "Adapted Bugfix Deployment Rate by Year", "Rate", config.charts_dir / "adapted_cfr_yearly.png"),
    ]

    for metric_name, title, ylabel, path in monthly_chart_specs:
        metric_df = monthly_metrics[monthly_metrics["metric_name"] == metric_name].copy()
        if metric_df.empty:
            continue
        _save_line_chart(metric_df, title, ylabel, path)

    for metric_name, title, ylabel, path in yearly_chart_specs:
        metric_df = yearly_metrics[yearly_metrics["metric_name"] == metric_name].copy()
        if metric_df.empty:
            continue
        _save_line_chart(metric_df, title, ylabel, path)

    # Summary grouped bar chart (2022–2025)
    repo_label = f"{config.owner}/{config.repo}"
    generate_summary_yearly_chart(
        yearly_metrics,
        config.charts_dir / "dora_summary_yearly.png",
        repo_label=repo_label,
    )
