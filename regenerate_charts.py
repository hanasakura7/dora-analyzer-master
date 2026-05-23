"""
Regenerate all charts from existing results CSVs without re-running the pipeline.

Usage:
    python regenerate_charts.py                          # all 3 repos
    python regenerate_charts.py --repo keycloak/keycloak # one repo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd

from dora_analyzer.config import AppConfig, make_config
from dora_analyzer.generate_charts import generate_charts, generate_summary_yearly_chart

DEFAULT_REPOS = [
    ("AppFlowy-IO", "AppFlowy"),
    ("keycloak",    "keycloak"),
    ("grafana",     "grafana"),
]


def regenerate(owner: str, repo: str) -> None:
    config = make_config(owner, repo)
    monthly_path = config.results_dir / "dora_metrics_monthly.csv"
    yearly_path  = config.results_dir / "dora_metrics_yearly.csv"

    if not yearly_path.exists():
        print(f"  SKIP {owner}/{repo} — no results found at {yearly_path}")
        print(f"  Run:  python -m dora_analyzer.main --repo {owner}/{repo}")
        return

    monthly_metrics = pd.read_csv(monthly_path) if monthly_path.exists() else pd.DataFrame()
    yearly_metrics  = pd.read_csv(yearly_path)

    config.charts_dir.mkdir(parents=True, exist_ok=True)
    generate_charts(config, monthly_metrics, yearly_metrics)
    print(f"  Done  {owner}/{repo}  →  {config.charts_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate DORA charts from existing results.")
    parser.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help="Single repo to regenerate (e.g. keycloak/keycloak). Omit to regenerate all.",
    )
    args = parser.parse_args()

    if args.repo:
        parts = args.repo.split("/", 1)
        if len(parts) != 2:
            raise SystemExit("--repo must be owner/repo format, e.g. keycloak/keycloak")
        repos = [tuple(parts)]
    else:
        repos = DEFAULT_REPOS

    for owner, repo in repos:
        print(f"Regenerating charts for {owner}/{repo}...")
        regenerate(owner, repo)

    print("\nAll done. Charts saved to charts/<repo_slug>/")


if __name__ == "__main__":
    main()
