"""Core pipeline: process a single simulation run's trace files.

Orchestrates the four trace files through the metric modules:
    cascades.py  → out_cascades.parquet
    posts.py     → out_posts.parquet
    sessions.py  → out_sessions.parquet
    summary.py   → out_run_summary.parquet
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import polars as pl

from .cascades import compute_cascades
from .network import load_indegree
from .posts import compute_posts
from .sessions import compute_sessions
from .summary import compute_run_summary

WARMUP_TIME = 1000.0

# Shared schema for all four trace types — fast path on read
TRACE_SCHEMA = {
    "time": pl.Float64,
    "event_id": pl.Int64,
    "gen_id": pl.Int64,
    "user_id": pl.Int64,
}


def _load_trace(path: Path, extra_schema: dict | None = None) -> pl.DataFrame:
    """Load a JSONL trace file with known schema for performance."""
    schema = {**TRACE_SCHEMA}
    if extra_schema:
        schema.update(extra_schema)
    return pl.read_ndjson(str(path), schema=schema)


def process_single_run(
    run_path: Path,
    sim_id: str,
    network_size: int,
    indegree_map: Dict[int, int],
) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, dict]:
    """Process all four trace files for one simulation replication.

    Parameters
    ----------
    run_path : Path
        Directory containing {action,create,session,propagate}_trace.jsonl.
    sim_id : str
        Unique identifier for this run (e.g. "100K_batch-1_42").
    network_size : int
        Total number of users in the topology.
    indegree_map : Dict[int, int]
        {user_id: follower_count} for author_degree.

    Returns
    -------
    cascades_df : pl.DataFrame
    posts_df : pl.DataFrame
    sessions_df : pl.DataFrame
    summary : dict (one-row data)
    """
    t0 = time.perf_counter()

    # --- Load traces -----------------------------------------------------------------
    action_df = _load_trace(
        run_path / "action_trace.jsonl",
        extra_schema={"post_id": pl.Int64, "type": pl.Utf8},
    )
    create_df = _load_trace(
        run_path / "create_trace.jsonl",
        extra_schema={"post_id": pl.Int64},
    )
    session_df = _load_trace(
        run_path / "session_trace.jsonl",
        extra_schema={"type": pl.Utf8, "backlog": pl.Int64},
    )
    # propagate_trace: type field = post_id (integer)
    propagate_df = _load_trace(
        run_path / "propagate_trace.jsonl",
        extra_schema={"type": pl.Int64},
    )

    # Filter to steady state (t >= WARMUP). Everything before t=1000 is the warmup
    # phase and is excluded from all metric computations.
    action_ss = action_df.filter(pl.col("time") >= WARMUP_TIME)
    create_ss = create_df.filter(pl.col("time") >= WARMUP_TIME)
    propagate_ss = propagate_df.filter(pl.col("time") >= WARMUP_TIME)

    # --- Compute metrics -------------------------------------------------------------
    # posts: only steady-state created posts
    # cascades: any post that gets reposts during SS (including warmup-created)
    cascades_df = compute_cascades(sim_id, create_df, action_ss, propagate_ss, indegree_map)
    posts_df = compute_posts(sim_id, create_ss, action_ss)
    sessions_df = compute_sessions(
        sim_id,
        session_df.filter(pl.col("time") >= WARMUP_TIME),
        action_ss,
        create_ss,
    )
    summary = compute_run_summary(sim_id, network_size, session_df, posts_df, warmup=WARMUP_TIME)

    elapsed = time.perf_counter() - t0
    print(
        f"  {sim_id}: cascades={cascades_df.height}, posts={posts_df.height}, "
        f"sessions={sessions_df.height}, gamma={summary['gamma_reposts']:.3f}  [{elapsed:.1f}s]"
    )

    return cascades_df, posts_df, sessions_df, summary
