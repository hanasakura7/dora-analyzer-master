from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OWNER = "AppFlowy-IO"
REPO = "AppFlowy"
REPO_URL = "https://github.com/AppFlowy-IO/AppFlowy.git"
LOCAL_REPO_PATH = ".cache/AppFlowy"

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "dora_appflowy"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
CHARTS_DIR = ROOT_DIR / "charts" / "dora_appflowy"
CACHE_DIR = ROOT_DIR / ".cache"

DEFAULT_START_DATE = os.getenv("START_DATE")
DEFAULT_END_DATE = os.getenv("END_DATE")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DEFAULT_INCLUDE_PRERELEASES = os.getenv("INCLUDE_PRERELEASES", "false").lower() == "true"


@dataclass(frozen=True)
class AppConfig:
    owner: str = OWNER
    repo: str = REPO
    repo_url: str = REPO_URL
    local_repo_path: Path = ROOT_DIR / LOCAL_REPO_PATH
    start_date: str | None = DEFAULT_START_DATE
    end_date: str | None = DEFAULT_END_DATE
    github_token: str | None = GITHUB_TOKEN
    include_prereleases: bool = DEFAULT_INCLUDE_PRERELEASES
    skip_api_cache_refresh: bool = False
    skip_git_update: bool = False
    root_dir: Path = ROOT_DIR
    data_dir: Path = DATA_DIR
    raw_data_dir: Path = RAW_DATA_DIR
    processed_data_dir: Path = PROCESSED_DATA_DIR
    results_dir: Path = RESULTS_DIR
    charts_dir: Path = CHARTS_DIR
    cache_dir: Path = CACHE_DIR

    def with_overrides(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        include_prereleases: bool | None = None,
        skip_api_cache_refresh: bool | None = None,
        skip_git_update: bool | None = None,
    ) -> "AppConfig":
        updated = self
        if start_date is not None:
            updated = replace(updated, start_date=start_date)
        if end_date is not None:
            updated = replace(updated, end_date=end_date)
        if include_prereleases is not None:
            updated = replace(updated, include_prereleases=include_prereleases)
        if skip_api_cache_refresh is not None:
            updated = replace(updated, skip_api_cache_refresh=skip_api_cache_refresh)
        if skip_git_update is not None:
            updated = replace(updated, skip_git_update=skip_git_update)
        return updated


def make_config(
    owner: str,
    repo: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    include_prereleases: bool | None = None,
    skip_api_cache_refresh: bool = False,
) -> AppConfig:
    slug = f"{owner.lower()}_{repo.lower()}"
    data_dir = ROOT_DIR / "data" / slug
    return AppConfig(
        owner=owner,
        repo=repo,
        repo_url=f"https://github.com/{owner}/{repo}.git",
        local_repo_path=ROOT_DIR / ".cache" / repo,
        start_date=start_date if start_date is not None else DEFAULT_START_DATE,
        end_date=end_date if end_date is not None else DEFAULT_END_DATE,
        github_token=GITHUB_TOKEN,
        include_prereleases=include_prereleases if include_prereleases is not None else DEFAULT_INCLUDE_PRERELEASES,
        skip_api_cache_refresh=skip_api_cache_refresh,
        root_dir=ROOT_DIR,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        processed_data_dir=data_dir / "processed",
        results_dir=data_dir / "results",
        charts_dir=ROOT_DIR / "charts" / slug,
        cache_dir=ROOT_DIR / ".cache",
    )


def ensure_directories(config: AppConfig) -> None:
    for path in (
        config.cache_dir,
        config.raw_data_dir,
        config.processed_data_dir,
        config.results_dir,
        config.charts_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
