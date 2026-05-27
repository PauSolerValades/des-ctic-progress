#!/usr/bin/env python3
"""CTIC Simulation Trace Parser & Metric Aggregation.

Walks the release-v4/traces/ directory tree, processes every simulation
replication (one pass per run), and produces three Parquet files:

    output/out_cascades.parquet    — Cascade morphology (N >= 2)
    output/out_posts.parquet      — Post lifetimes & reposts
    output/out_run_summary.parquet — Global run summary (one row per sim)

Usage:
    uv run main.py
    uv run main.py --traces ../release-v4/traces --data ../release-v4/data --output output
    uv run main.py --dry-run          # Print what would be processed
    uv run main.py --limit 5          # Process only first 5 runs (for testing)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import polars as pl

from trace_analysis.network import load_indegree
from trace_analysis.runner import process_single_run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_network_size(dirname: str) -> int:
    """Extract numeric network size from directory name ('100K' → 100000)."""
    dirname = dirname.upper().replace("K", "000").replace("M", "000000")
    try:
        return int(dirname)
    except ValueError:
        return 0


def _iter_runs(traces_root: Path) -> "list[tuple[Path, str, int]]":
    """Discover all (run_path, sim_id, network_size) triples.

    Directory layout: traces/{SIZE}/{BATCH}/{run_id}/
    """
    runs = []
    for size_dir in sorted(traces_root.iterdir()):
        if not size_dir.is_dir():
            continue
        network_size = _parse_network_size(size_dir.name)
        if network_size == 0:
            print(f"  [skip] Cannot parse size from {size_dir.name}")
            continue

        for batch_dir in sorted(size_dir.iterdir()):
            if not batch_dir.is_dir():
                continue
            for run_dir in sorted(batch_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                # Validate the four required trace files exist
                required = [
                    run_dir / f
                    for f in (
                        "action_trace.jsonl",
                        "create_trace.jsonl",
                        "session_trace.jsonl",
                        "propagate_trace.jsonl",
                    )
                ]
                if all(p.exists() for p in required):
                    sim_id = f"{size_dir.name}_{batch_dir.name}_{run_dir.name}"
                    runs.append((run_dir, sim_id, network_size))
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CTIC trace parser — JSONL → Parquet metric tables"
    )
    parser.add_argument(
        "--traces",
        type=Path,
        default=Path("release-v4/traces"),
        help="Root directory of trace JSONL files",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("../release-v4/data"),
        help="Root directory of network.bin files (for author degree)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for Parquet files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered runs without processing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N runs (0 = all)",
    )
    parser.add_argument(
        "--size",
        type=str,
        default="",
        help="Process only this dataset size (e.g. '100K', '500K', '1M')",
    )
    args = parser.parse_args()

    # Resolve relative paths relative to the script location
    script_dir = Path(__file__).resolve().parent
    traces_root = (script_dir / args.traces).resolve()
    data_root = (script_dir / args.data).resolve()
    output_dir = (script_dir / args.output).resolve()

    if not traces_root.is_dir():
        print(f"Error: traces directory not found: {traces_root}", file=sys.stderr)
        sys.exit(1)

    # Discover all runs
    runs = _iter_runs(traces_root)
    print(f"Discovered {len(runs)} simulation runs in {traces_root}")

    # Filter by size if requested
    if args.size:
        size_int = _parse_network_size(args.size)
        runs = [(p, sid, ns) for p, sid, ns in runs if ns == size_int]
        if not runs:
            print(f"No runs found for size '{args.size}'. Exiting.")
            sys.exit(1)
        print(f"Filtered to size={args.size}: {len(runs)} runs")
        # Use size-specific output: output/100K/, output/500K/, output/1M/
        output_dir = output_dir / args.size

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.limit > 0:
        runs = runs[: args.limit]
        print(f"Limited to first {args.limit} runs")

    if args.dry_run:
        for run_path, sim_id, nw_size in runs:
            print(f"  {sim_id}  (network_size={nw_size})  path={run_path}")
        return

    if not runs:
        print("No runs to process. Exiting.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Cached in-degree maps by network size
    indegree_cache: dict[int, dict] = {}

    all_cascades: list[pl.DataFrame] = []
    all_posts: list[pl.DataFrame] = []
    all_sessions: list[pl.DataFrame] = []
    all_summaries: list[dict] = []

    t_start = time.perf_counter()
    processed = 0
    errors = 0

    for i, (run_path, sim_id, nw_size) in enumerate(runs):
        print(f"[{i+1}/{len(runs)}] {sim_id}")

        # Load (or retrieve cached) in-degree map
        if nw_size not in indegree_cache:
            network_bin = data_root / f"{nw_size // 1000}K" / "network.bin"
            # Try alternate naming
            if not network_bin.exists():
                # Check exact size_dir name match
                for d in data_root.iterdir():
                    if d.is_dir() and _parse_network_size(d.name) == nw_size:
                        network_bin = d / "network.bin"
                        break
            if not network_bin.exists():
                print(f"  [warn] network.bin not found for size {nw_size}, "
                      f"author_degree will be 0")
                indegree_cache[nw_size] = {}
            else:
                indegree_cache[nw_size] = load_indegree(network_bin)

        try:
            cascades_df, posts_df, sessions_df, summary = process_single_run(
                run_path, sim_id, nw_size, indegree_cache[nw_size]
            )
            all_cascades.append(cascades_df)
            all_posts.append(posts_df)
            all_sessions.append(sessions_df)
            all_summaries.append(summary)
            processed += 1
        except Exception as exc:
            print(f"  [ERROR] {exc}", file=sys.stderr)
            errors += 1

    elapsed = time.perf_counter() - t_start
    print(f"\nProcessed {processed} runs ({errors} errors) in {elapsed:.1f}s")

    if processed == 0:
        print("No runs successfully processed. Exiting.")
        sys.exit(1)

    # --- Write output Parquet files ------------------------------------------------
    print("\nWriting output files...")

    t_write = time.perf_counter()

    # out_cascades.parquet
    cascade_path = output_dir / "out_cascades.parquet"
    pl.concat(all_cascades, how="diagonal_relaxed").write_parquet(cascade_path)
    print(f"  {cascade_path}  ({cascade_path.stat().st_size:,} bytes)")

    # out_posts.parquet
    posts_path = output_dir / "out_posts.parquet"
    pl.concat(all_posts, how="diagonal_relaxed").write_parquet(posts_path)
    print(f"  {posts_path}  ({posts_path.stat().st_size:,} bytes)")

    # out_sessions.parquet
    sessions_path = output_dir / "out_sessions.parquet"
    pl.concat(all_sessions, how="diagonal_relaxed").write_parquet(sessions_path)
    print(f"  {sessions_path}  ({sessions_path.stat().st_size:,} bytes)")

    # out_run_summary.parquet
    summary_path = output_dir / "out_run_summary.parquet"
    pl.DataFrame(all_summaries).write_parquet(summary_path)
    print(f"  {summary_path}  ({summary_path.stat().st_size:,} bytes)")

    print(f"Write time: {time.perf_counter() - t_write:.1f}s")
    print("Done.")


if __name__ == "__main__":
    main()
