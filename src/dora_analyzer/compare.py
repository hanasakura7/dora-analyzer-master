from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .config import ROOT_DIR

METRIC_SPECS = [
    ("deployment_frequency", "Deployment Frequency", "Deployments / Year"),
    ("lead_time_days_mean", "Lead Time for Changes (Mean)", "Days"),
    ("recovery_time_days_mean", "MTTR (Mean)", "Days"),
    ("adapted_bugfix_deployment_rate", "Adapted Change Failure Rate", "Rate"),
]

REPO_DISPLAY_NAMES = {
    "appflowy-io_appflowy": "AppFlowy (Rust)",
    "keycloak_keycloak": "Keycloak (Java)",
    "grafana_grafana": "Grafana (Go)",
}


def _slug(owner_repo: str) -> str:
    owner, repo = owner_repo.split("/", 1)
    return f"{owner.lower()}_{repo.lower()}"


def load_yearly_metrics(repos: list[str]) -> pd.DataFrame:
    frames = []
    for owner_repo in repos:
        slug = _slug(owner_repo)
        results_path = ROOT_DIR / "data" / slug / "results" / "dora_metrics_yearly.csv"
        if not results_path.exists():
            print(f"  WARNING: No yearly results found for {owner_repo} at {results_path}")
            print(f"  Run the pipeline first: python -m dora_appflowy.main --repo {owner_repo}")
            continue
        df = pd.read_csv(results_path)
        df["repo_slug"] = slug
        df["repo_label"] = REPO_DISPLAY_NAMES.get(slug, owner_repo)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def generate_comparison_charts(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_labels = df["repo_label"].unique().tolist()
    colors = ["#4C72B0", "#DD8452", "#55A868"]

    for metric_name, title, ylabel in METRIC_SPECS:
        metric_df = df[df["metric_name"] == metric_name].copy()
        if metric_df.empty:
            print(f"  Skipping {metric_name} — no data found across repos.")
            continue

        all_periods = sorted(metric_df["period"].unique())
        x = range(len(all_periods))
        bar_width = 0.25

        fig, ax = plt.subplots(figsize=(12, 6))
        for i, label in enumerate(repo_labels):
            repo_df = metric_df[metric_df["repo_label"] == label]
            values = [
                repo_df.loc[repo_df["period"] == p, "metric_value"].values[0]
                if p in repo_df["period"].values else 0.0
                for p in all_periods
            ]
            offsets = [xi + i * bar_width for xi in x]
            ax.bar(offsets, values, width=bar_width, label=label, color=colors[i % len(colors)])

        ax.set_title(f"{title} — Cross-Repo Comparison")
        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)
        ax.set_xticks([xi + bar_width for xi in x])
        ax.set_xticklabels(all_periods, rotation=45, ha="right")
        ax.legend()
        plt.tight_layout()

        out_path = output_dir / f"comparison_{metric_name}_yearly.png"
        plt.savefig(out_path)
        plt.close()
        print(f"  Saved: {out_path}")


def generate_summary_table(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_names = [m for m, _, _ in METRIC_SPECS]
    summary_rows = []
    for label in df["repo_label"].unique():
        repo_df = df[df["repo_label"] == label]
        row: dict = {"repo": label}
        for metric_name in metric_names:
            m_df = repo_df[repo_df["metric_name"] == metric_name]
            if not m_df.empty:
                row[metric_name + "_mean"] = round(m_df["metric_value"].mean(), 2)
            else:
                row[metric_name + "_mean"] = None
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    out_path = output_dir / "comparison_summary.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"  Saved summary table: {out_path}")
    print()
    print(summary_df.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare DORA metrics across multiple GitHub repositories.")
    parser.add_argument(
        "--repos",
        nargs="+",
        default=["AppFlowy-IO/AppFlowy", "keycloak/keycloak", "grafana/grafana"],
        metavar="OWNER/REPO",
        help="Repositories to compare (space-separated owner/repo pairs).",
    )
    args = parser.parse_args()

    output_dir = ROOT_DIR / "charts" / "comparison"
    print(f"Loading yearly metrics for: {', '.join(args.repos)}")
    df = load_yearly_metrics(args.repos)

    if df.empty:
        raise SystemExit("No data loaded. Run the pipeline for each repo first.")

    print(f"Generating comparison charts -> {output_dir}")
    generate_comparison_charts(df, output_dir)
    generate_summary_table(df, output_dir)
    print("Comparison complete.")


if __name__ == "__main__":
    main()
