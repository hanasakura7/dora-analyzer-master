# AppFlowy DORA Metrics Analyzer

This project is a Python 3.11 telemetry mining pipeline for a university DevOps Software Quality Assurance group project. It applies the methodology from the article "A Framework for Automating the Measurement of DevOps Research and Assessment (DORA) Metrics" to the public GitHub repository `AppFlowy-IO/AppFlowy`.

The analyzer mines Git and GitHub telemetry to estimate:

- Deployment Frequency
- Lead Time for Changes
- Mean Time to Recover
- `adapted_bugfix_deployment_rate` as a practical proxy for Change Failure Rate

## Selected Article

- Article: "A Framework for Automating the Measurement of DevOps Research and Assessment (DORA) Metrics"
- Reused ideas:
  - Semantic versioning releases/tags as deployments
  - Git commit history for change lead time
  - Closed bug-labelled GitHub issues as failures
  - Git/GitHub telemetry as the main evidence source
- Modified for practicality:
  - Exact Change Failure Rate is not claimed unless full bug-inducing commit detection is available
  - A fallback proxy called `adapted_bugfix_deployment_rate` is computed instead
  - Optional `SZZ-lite` logic is included as an experimental best-effort step

## Target Repository

- GitHub: <https://github.com/AppFlowy-IO/AppFlowy>

## How This Project Measures the Metrics

### 1. Deployment Frequency

GitHub releases with semantic-version-like tags are treated as deployments. The pipeline counts deployments by month and year.

### 2. Lead Time for Changes

For each pair of consecutive deployments, the pipeline collects the commits between their tags and computes:

`lead_time_days = deployment_date - commit_date`

Monthly and yearly aggregates include mean, median, min, and max.

### 3. Mean Time to Recover

Closed GitHub issues that look like bugs are treated as failures. The pipeline tries to map each failure to a fixing commit or fixing PR, then finds the first deployment that contains that fix. Recovery time is calculated as:

`recovery_time_days = recovery_deployment_date - issue_created_at`

### 4. Adapted Change Failure Rate

This project does not falsely claim to implement the paper's exact CFR when full SZZ bug-inducing commit detection is unavailable. Instead it computes:

`adapted_bugfix_deployment_rate = deployments containing at least one bug-fix / total deployments`

Every exported CFR-like metric includes this note:

`This is an adapted proxy for change failure rate because full SZZ bug-inducing commit detection was not implemented.`

## Fallback Mode

The project includes a practical fallback mode for large-repository or API-limited situations:

- API responses are cached under `data/raw/`
- `--skip-api-cache-refresh` reuses existing cached CSV/JSON exports
- If exact fix mapping cannot be found, the issue close time is used as a fallback with low confidence
- If commit-to-deployment ancestry checks fail, recovery is approximated using the first release after issue closure
- `SZZ-lite` is optional and non-blocking

This means the pipeline can still produce useful results even if:

- GitHub rate limits are reached
- the repository is large and some operations take time
- exact fixing commits cannot always be identified

If the repository clone itself cannot be created because GitHub access is unavailable, the pipeline exits with a clear error message. In that case, rerun in a network-enabled environment or populate `.cache/AppFlowy` first.

## Installation

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local environment file:

```bash
copy .env.example .env
```

4. Optionally set `GITHUB_TOKEN` in `.env` to reduce API rate-limit issues.

## Usage

Run the full pipeline from the repository root:

```bash
python -m dora_appflowy.main
```

Example with a date range:

```bash
python -m dora_appflowy.main --start-date 2024-01-01 --end-date 2025-12-31
```

Include prereleases:

```bash
python -m dora_appflowy.main --include-prereleases
```

Reuse cached API data:

```bash
python -m dora_appflowy.main --skip-api-cache-refresh
```

## Reading the Results

Generated outputs:

- Raw API exports:
  - `data/raw/releases.csv`
  - `data/raw/closed_bug_issues.csv`
- Processed datasets:
  - `data/processed/deployments.csv`
  - `data/processed/commits_between_deployments.csv`
  - `data/processed/failures.csv`
  - `data/processed/fix_mappings.csv`
  - `data/processed/recovery_mappings.csv`
  - `data/processed/szz_lite_results.csv` if available
- Final metrics:
  - `data/results/dora_metrics_yearly.csv`
  - `data/results/dora_metrics_monthly.csv`
  - `data/results/summary.json`
- Charts:
  - `charts/deployment_frequency_monthly.png`
  - `charts/deployment_frequency_yearly.png`
  - `charts/lead_time_monthly.png`
  - `charts/lead_time_yearly.png`
  - `charts/mttr_monthly.png`
  - `charts/mttr_yearly.png`
  - `charts/adapted_cfr_monthly.png`
  - `charts/adapted_cfr_yearly.png`

## Project Structure

```text
dora-appflowy-analyzer/
├── .github/workflows/dora-metrics.yml
├── .env.example
├── AGENTS.md
├── PROJECT_STRUCTURE_GUIDE.md
├── README.md
├── charts/
├── data/
│   ├── processed/
│   ├── raw/
│   └── results/
├── requirements.txt
├── sitecustomize.py
├── src/dora_appflowy/
│   ├── __init__.py
│   ├── collectors.py
│   ├── config.py
│   ├── main.py
│   ├── metrics.py
│   ├── recovery.py
│   └── reporting.py
└── tests/
    ├── test_metrics.py
    └── test_rules.py
```

## Limitations

- GitHub issue labels may not perfectly represent all production failures.
- Treating releases as deployments is consistent with the selected paper, but may not reflect every internal deployment event.
- Recovery time depends on the accuracy of fix-to-deployment mapping.
- `adapted_bugfix_deployment_rate` is a proxy, not the original exact CFR.
- `SZZ-lite` is experimental and may fail on some commits or repositories.

## Sample Commands

```bash
python -m pytest
python -m dora_appflowy.main --start-date 2024-01-01 --end-date 2025-12-31
python -m dora_appflowy.main --include-prereleases --skip-api-cache-refresh
```
