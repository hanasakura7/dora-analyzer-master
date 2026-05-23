# Project Structure Guide

## 1. What This Project Does

This project is a Python-based DORA metrics analyzer for the public GitHub repository `AppFlowy-IO/AppFlowy`.

Its goal is to automatically collect software delivery telemetry from:

- GitHub releases
- Git commit history
- GitHub issues
- GitHub pull requests

Then it uses that data to estimate four DORA-related metrics:

- Deployment Frequency
- Lead Time for Changes
- Mean Time to Recover
- `adapted_bugfix_deployment_rate` as a practical proxy for Change Failure Rate

The project is based on the article:

`A Framework for Automating the Measurement of DevOps Research and Assessment (DORA) Metrics`

In simple terms, this project acts like a research tool. It observes how AppFlowy publishes releases, how quickly code changes reach releases, how bug issues are fixed, and how quickly those fixes appear in later deployments.

## 2. Purpose of Every Main Folder

### Root folder

The root folder contains the whole project: code, data, charts, documentation, tests, and automation files.

### `src/dora_appflowy/`

This is the main source-code folder.

It contains the real Python logic for:

- configuration
- data collection
- GitHub API access
- Git repository updating
- fix and recovery mapping
- metric calculation
- chart generation
- running the full pipeline

### `data/`

This folder stores all generated data files.

- `data/raw/`
  - stores raw collected data
- `data/processed/`
  - stores cleaned and transformed intermediate datasets
- `data/results/`
  - stores final DORA metric outputs

### `charts/`

This folder stores the PNG chart images generated from the final metrics.

### `tests/`

This folder contains automated tests using `pytest`.

### `.github/workflows/`

This folder contains GitHub Actions automation for running the pipeline.

### `.cache/`

This folder stores cached repository data.

The most important item here is `.cache/AppFlowy/`, which is the local cloned copy of the AppFlowy repository.

### `dora_appflowy/`

This is a small compatibility package folder used so the root command works cleanly:

```bash
python -m dora_appflowy.main
```

## 3. Purpose of Every Important File

### Project-level files

#### `README.md`

Main project documentation.

#### `PROJECT_STRUCTURE_GUIDE.md`

This explanation guide for students and presentations.

#### `AGENTS.md`

Instructions for collaborators or coding assistants.

#### `requirements.txt`

Lists Python dependencies needed by the project.

#### `.env.example`

Template for environment configuration.

#### `.env`

Local private configuration file, such as GitHub token and default dates.

#### `.gitignore`

Tells Git which files should not be committed.

#### `sitecustomize.py`

Helper file that adds `src/` to Python’s import path.

#### `dora_appflowy/__init__.py`

Compatibility helper so the top-level package resolves to the real code inside `src/dora_appflowy/`.

### Source files in `src/dora_appflowy/`

#### `__init__.py`

Marks the folder as a Python package.

#### `config.py`

Central configuration file.

It defines:

- target GitHub owner and repo
- repository URL
- cache path
- output paths
- default date settings
- GitHub token loading

#### `collectors.py`

This file groups all collection logic together.

It handles:

- GitHub API requests
- cloning or updating the cached repository
- release collection
- issue collection
- commit collection between deployments
- semantic version tag detection
- bug label detection

Its outputs include:

- `data/raw/releases.csv`
- `data/raw/closed_bug_issues.csv`
- `data/processed/deployments.csv`
- `data/processed/failures.csv`
- `data/processed/commits_between_deployments.csv`

#### `recovery.py`

This file handles bug-fix and recovery mapping logic.

It:

- searches commit messages for issue references
- checks PR title/body/merge commit references
- chooses the best fix candidate
- falls back to issue close time when needed
- finds the first deployment after the fix
- runs optional `SZZ-lite`

Its outputs are:

- `data/processed/fix_mappings.csv`
- `data/processed/recovery_mappings.csv`
- `data/processed/szz_lite_results.csv`

#### `metrics.py`

This file calculates the final DORA-style metrics.

It builds monthly and yearly summaries for:

- deployment frequency
- lead time for changes
- mean time to recover
- adapted bugfix deployment rate

Its outputs are:

- `data/results/dora_metrics_monthly.csv`
- `data/results/dora_metrics_yearly.csv`
- `data/results/summary.json`

#### `reporting.py`

This file turns the final metrics into charts.

It creates:

- deployment frequency chart
- lead time chart
- MTTR chart
- adapted CFR chart
- yearly summary chart

#### `main.py`

This is the entry point of the whole project.

It:

- reads command-line arguments
- builds the configuration
- runs the pipeline in order
- shows progress messages
- handles pipeline failure cleanly

### Test files

#### `tests/test_rules.py`

Tests rule-based logic such as:

- semantic version tag detection
- bug label detection
- excluded label detection

#### `tests/test_metrics.py`

Tests the basic metric calculations.

### Automation file

#### `.github/workflows/dora-metrics.yml`

GitHub Actions workflow that:

- sets up Python 3.11
- installs requirements
- runs the pipeline
- uploads results and charts as artifacts

## 4. Pipeline Flow

The full pipeline works in this order:

### Step 1. Clone or fetch the target repository

`main.py` starts the process by calling the collection logic in `collectors.py`.

If `.cache/AppFlowy/` does not exist, the project clones the repository.

If it already exists, the project fetches the latest tags and updates.

### Step 2. Collect releases

`collectors.py` downloads release metadata and filters which releases count as deployments.

By default:

- draft releases are removed
- prereleases are removed unless enabled
- only semantic-version-like tags are treated as deployments

### Step 3. Collect commits between deployments

`collectors.py` compares each deployment to the previous one and calculates lead time per commit.

### Step 4. Collect bug issues

`collectors.py` downloads closed GitHub issues and keeps only those that look like bug failures.

### Step 5. Map failures to fixes

`recovery.py` tries to answer:

“Which commit or PR fixed this bug issue?”

### Step 6. Map fixes to recovery deployments

Still in `recovery.py`, the project asks:

“Which deployment first contains the fix?”

### Step 7. Optional SZZ-lite

The project optionally runs a lightweight experimental SZZ-style step.

### Step 8. Calculate metrics

`metrics.py` aggregates the collected data into monthly and yearly DORA metrics.

### Step 9. Generate charts

`reporting.py` turns the final metrics into chart images.

## 5. Which Files to Edit for Common Changes

### Change the target GitHub repository

Edit:

- `src/dora_appflowy/config.py`

### Change the GitHub API token or environment configuration

Edit:

- `.env`
- `.env.example`
- sometimes `src/dora_appflowy/config.py`

### Change the date range

Use:

- command-line arguments in `main.py`

Or change defaults in:

- `.env`
- `src/dora_appflowy/config.py`

### Change the definition of deployment

Edit:

- `src/dora_appflowy/collectors.py`

### Change the definition of bug or failure

Edit:

- `src/dora_appflowy/collectors.py`

### Change the fix mapping logic

Edit:

- `src/dora_appflowy/recovery.py`

### Change the metric formulas

Edit:

- `src/dora_appflowy/metrics.py`

### Change chart appearance or output files

Edit:

- `src/dora_appflowy/reporting.py`

### Change automation behavior

Edit:

- `.github/workflows/dora-metrics.yml`

## 6. Which Files to Avoid Editing

Avoid editing these unless there is a strong reason:

- `.cache/AppFlowy/`
- `data/raw/*.csv`
- `data/processed/*.csv`
- `data/results/*.csv`
- `data/results/summary.json`
- `charts/*.png`
- `sitecustomize.py`
- `dora_appflowy/__init__.py`
- `.venv/`
- `.pytest_cache/`
- `.git/`

## 7. Important Files and Risk Level

| File | Purpose | When to edit it | Risk level |
|---|---|---|---|
| `README.md` | Main documentation | When updating project explanation or usage notes | Low |
| `PROJECT_STRUCTURE_GUIDE.md` | Beginner guide | When improving explanation for presentations | Low |
| `AGENTS.md` | Project instructions | When you want better project guidance | Low |
| `.env.example` | Example environment config | When adding new config options | Low |
| `.env` | Local private config | When changing token or default dates | Medium |
| `src/dora_appflowy/config.py` | Main configuration | When changing repo target, defaults, or output paths | Medium |
| `src/dora_appflowy/collectors.py` | API, Git update, release collection, issue collection, commit collection | When changing deployment rules, bug rules, or collection behavior | High |
| `src/dora_appflowy/recovery.py` | Fix and recovery mapping | When changing fix detection or recovery logic | High |
| `src/dora_appflowy/metrics.py` | Metric formulas and aggregation | When changing DORA calculations | High |
| `src/dora_appflowy/reporting.py` | Chart generation | When changing graph design or outputs | Low |
| `src/dora_appflowy/main.py` | Pipeline entry point | When changing CLI args or pipeline sequence | Medium |
| `.github/workflows/dora-metrics.yml` | GitHub Actions automation | When changing CI behavior | Medium |

## 8. How This Project Connects to the Selected DORA Article Methodology

This project is directly inspired by the selected article’s idea that DORA metrics can be estimated automatically from Git and GitHub telemetry.

The article’s core methodology is reflected in this project in these ways:

- GitHub releases and version tags are used as deployment evidence
- Git commit history is used to estimate lead time
- bug-labelled GitHub issues are used as evidence of failure
- delivery and stability metrics are produced from repository telemetry rather than manual reporting

## 9. How Throughput Metrics Are Calculated

Throughput metrics measure delivery speed and output.

### A. Deployment Frequency

Definition used here:

- count how many deployments happened in a month or year

Formula:

`deployment_frequency = number of deployments in the period`

### B. Lead Time for Changes

Definition used here:

- how long it takes a code change to appear in a deployment

Formula:

`lead_time_days = deployment_date - commit_date`

The project then calculates mean, median, min, and max by month or year.

## 10. How Stability Metrics Are Calculated

Stability metrics measure failures and recovery behavior.

### C. Mean Time to Recover

Definition used here:

- how long it takes from the start of a bug issue until a deployment contains the fix

Formula:

`recovery_time_days = recovery_deployment_date - issue_created_at`

### D. Adapted Change Failure Rate

This project uses a practical adapted version:

`adapted_bugfix_deployment_rate = deployments containing at least one bug-fix / total deployments`

This is clearly labelled as an adapted proxy and not claimed to be the exact original CFR from the paper.

## 11. What Parts Are Reused From the Paper

These ideas are reused from the selected article:

- use repository telemetry instead of manual measurement
- use versioned releases/tags as deployments
- use commit history for lead time analysis
- use closed bug-related issues as failures
- combine Git and GitHub data into one automated pipeline
- measure both throughput and stability dimensions

## 12. What Parts Are Modified From the Paper

These parts are practical modifications in this student implementation:

### Adapted CFR instead of exact original CFR

The project uses `adapted_bugfix_deployment_rate` instead of claiming full exact Change Failure Rate.

### Fallback mapping behavior

If the project cannot find an exact fixing commit, it falls back to the issue close time.

If the project cannot prove which deployment contains a fix, it falls back to the first deployment after issue closure.

### Optional SZZ-lite

The project includes an experimental lightweight `SZZ-lite` step rather than a full SZZ implementation.

## Final Summary

This project is an automated software delivery analytics pipeline. It studies the AppFlowy GitHub repository using Git and GitHub data, then estimates DORA metrics using a research-paper-inspired method. It follows the paper closely for deployments, commit lead time, and bug issue failures, while clearly adapting the change failure rate into a practical proxy because full bug-inducing commit tracing was beyond the scope of the student implementation.
