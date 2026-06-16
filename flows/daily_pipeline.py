"""Morpho Blue Len daily pipeline — Prefect orchestration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Allow: uv run python flows/daily_pipeline.py  (from repo root)
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from prefect import flow

from flows.tasks import (
    enrich_events,
    extract_events,
    load_csv_to_postgres,
    resolve_markets,
    resolve_tokens,
    run_dbt,
    test_dbt,
    validate_pipeline,
)


def _parse_chains() -> list[str]:
    raw = os.getenv("PIPELINE_CHAINS", "ethereum")
    if raw.strip().lower() == "all":
        return ["all"]
    return [c.strip() for c in raw.split(",") if c.strip()]


def _parse_block_range_args(*, allow_defaults: bool = False) -> list[str]:
    """Build --block-range flags from env, or fall back to --from-block/--to-block."""
    args: list[str] = []
    for key, value in os.environ.items():
        if not key.startswith("BLOCK_RANGE_") or not value:
            continue
        chain = key.removeprefix("BLOCK_RANGE_").lower()
        args.extend(["--block-range", f"{chain}:{value}"])

    if args:
        return args

    from_block = os.getenv("FROM_BLOCK")
    to_block = os.getenv("TO_BLOCK")
    if from_block and to_block:
        return ["--from-block", from_block, "--to-block", to_block]

    if allow_defaults:
        from_block = "22800000"
        to_block = "22801000"
        print(
            f"No block range in env — using defaults {from_block}-{to_block}. "
            "Set FROM_BLOCK/TO_BLOCK or BLOCK_RANGE_* to override."
        )
        return ["--from-block", from_block, "--to-block", to_block]

    raise ValueError(
        "Set block range via FROM_BLOCK/TO_BLOCK or BLOCK_RANGE_<chain>=from-to "
        "(e.g. BLOCK_RANGE_ETHEREUM=22800000-22801000)"
    )


@flow(name="Morpho Blue Len Daily Pipeline", log_prints=True)
def daily_pipeline(
    chains: list[str] | None = None,
    block_range_args: list[str] | None = None,
    skip_extract: bool = False,
) -> None:
    chains = chains or _parse_chains()
    if block_range_args is None and not skip_extract:
        block_range_args = _parse_block_range_args()
    block_range_args = block_range_args or []

    print(f"skip_extract={skip_extract}, block_range_args={block_range_args}")
    print(f"Starting Morpho Blue Len pipeline for chains: {chains}")

    if not skip_extract:
        print("Running extract_events")
        extract_events(chains, block_range_args)
        print("Running resolve_markets")
        resolve_markets(chains)
        print("Running resolve_tokens")
        resolve_tokens(chains)
        print("Running enrich_events")
        enrich_events()
        print("Running validate_pipeline")
        validate_pipeline(chains, block_range_args)

    print("Running load_csv_to_postgres")
    load_csv_to_postgres()
    print("Running run_dbt")
    run_dbt()
    print("Running test_dbt")
    test_dbt()

    print("Pipeline complete.")


def _prefect_api_reachable() -> bool:
    api_url = os.getenv("PREFECT_API_URL", "").strip()
    if not api_url:
        return False
    try:
        import httpx

        version_url = f"{api_url.rstrip('/')}/admin/version"
        response = httpx.get(version_url, timeout=3.0)
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"Prefect API not reachable at {api_url}: {exc}")
        return False


if __name__ == "__main__":
    # From repo root:
    #   uv run prefect server start          # terminal 1 — UI at http://127.0.0.1:4200
    #   uv run python -m flows.daily_pipeline  # terminal 2
    #
    # With PREFECT_API_URL set and server reachable: full flow + task tracking in UI.
    # Without server: falls back to daily_pipeline.fn() (no task graph in UI).
    skip_extract_env = os.getenv("SKIP_EXTRACT", "").lower()
    if skip_extract_env in {"1", "true", "yes"}:
        skip_extract = True
        block_range_args: list[str] | None = None
        print("SKIP_EXTRACT set — running load + dbt only (3 tasks).")
    else:
        skip_extract = False
        block_range_args = _parse_block_range_args(allow_defaults=True)

    kwargs = {"skip_extract": skip_extract, "block_range_args": block_range_args}

    if _prefect_api_reachable():
        print("Using Prefect server at", os.environ["PREFECT_API_URL"])
        daily_pipeline(**kwargs)
    else:
        if os.getenv("PREFECT_API_URL"):
            print("Falling back to local mode (daily_pipeline.fn) — no Prefect server.")
        daily_pipeline.fn(**kwargs)
