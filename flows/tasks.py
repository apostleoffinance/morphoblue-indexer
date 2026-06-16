"""Prefect tasks for the Morpho daily pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from prefect import task

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = REPO_ROOT / "morpho_analytics"
PYTHON = sys.executable
DBT = str(Path(sys.executable).parent / "dbt")
EVENT_FILES = [
    "supply_events.csv",
    "borrow_events.csv",
    "repay_events.csv",
    "withdraw_events.csv",
]


def _run(cmd: list[str], *, cwd: Path = REPO_ROOT) -> str:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    return result.stdout


@task(
    name="Extract Events",
    log_prints=True,
    retries=2,
    retry_delay_seconds=30,
)
def extract_events(chains: list[str], block_range_args: list[str]) -> None:
    cmd = [PYTHON, "main.py", "--event", "all", "--chain", *chains, *block_range_args]
    _run(cmd)


@task(name="Resolve Markets", log_prints=True, retries=2, retry_delay_seconds=30)
def resolve_markets(chains: list[str]) -> None:
    cmd = [PYTHON, "main.py", "--event", "market", "--chain", *chains]
    _run(cmd)


@task(name="Resolve Tokens", log_prints=True, retries=2, retry_delay_seconds=30)
def resolve_tokens(chains: list[str]) -> None:
    cmd = [PYTHON, "main.py", "--event", "token", "--chain", *chains]
    _run(cmd)


@task(name="Resolve Token Prices", log_prints=True, retries=2, retry_delay_seconds=30)
def resolve_prices(chains: list[str]) -> None:
    cmd = [PYTHON, "main.py", "--event", "price", "--chain", *chains]
    _run(cmd)


@task(name="Enrich Events", log_prints=True)
def enrich_events() -> None:
    for filename in EVENT_FILES:
        path = REPO_ROOT / "data" / filename
        if not path.exists():
            print(f"Skipping enrich — missing {path}")
            continue
        _run([PYTHON, "main.py", "--event", "enrich", "--input", str(path)])


@task(name="Validate Pipeline", log_prints=True)
def validate_pipeline(chains: list[str], block_range_args: list[str]) -> None:
    cmd = [PYTHON, "main.py", "--event", "validate", "--chain", *chains, *block_range_args]
    _run(cmd)


@task(name="Load CSV to PostgreSQL", log_prints=True)
def load_csv_to_postgres() -> None:
    _run([PYTHON, "-m", "database.load_csv"])


@task(name="Run dbt Models", log_prints=True)
def run_dbt() -> None:
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(DBT_DIR)
    cmd = [DBT, "run"]
    print(f"Running: {' '.join(cmd)} (cwd={DBT_DIR})")
    subprocess.run(cmd, cwd=DBT_DIR, check=True, env=env)


@task(name="Run dbt Tests", log_prints=True)
def test_dbt() -> None:
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(DBT_DIR)
    cmd = [DBT, "test"]
    print(f"Running: {' '.join(cmd)} (cwd={DBT_DIR})")
    subprocess.run(cmd, cwd=DBT_DIR, check=True, env=env)
