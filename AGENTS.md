# Project Notes for Agents

This repository contains a Python 3.11 implementation of a DORA metrics mining pipeline for the public `AppFlowy-IO/AppFlowy` GitHub repository.

## Expectations

- Keep the implementation reproducible from the repository root.
- Preserve the distinction between exact paper methodology and practical approximations.
- Do not store real credentials in the repository.
- Prefer cached API results when repeatability or rate limits are a concern.

## Key Outputs

- `data/raw/`: raw API exports
- `data/processed/`: cleaned and mapped datasets
- `data/results/`: final metrics and summary
- `charts/`: matplotlib PNG charts

## Main Entry Point

```bash
python -m dora_appflowy.main
```
