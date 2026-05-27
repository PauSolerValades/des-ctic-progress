"""Per-Session Metrics — out_sessions.parquet

One row per session during steady state.

Metrics:
    - duration: session_end - session_start
    - backlog_at_start, backlog_at_end
    - n_actions: total timeline pops (ignore+like+repost)
    - n_reposts, n_likes, n_ignores
    - n_posts_created
    - empty_timeline_exit: backlog_at_end == 0
"""

from __future__ import annotations

import time

import polars as pl

SESSION_COLUMNS = [
    "sim_id",
    "user_id",
    "start_time",
    "end_time",
    "duration",
    "backlog_at_start",
    "backlog_at_end",
    "n_actions",
    "n_reposts",
    "n_likes",
    "n_ignores",
    "n_posts_created",
    "empty_timeline_exit",
]


def compute_sessions(
    sim_id: str,
    session_df: pl.DataFrame,
    action_df: pl.DataFrame,
    create_df: pl.DataFrame,
) -> pl.DataFrame:
    """Produce the out_sessions DataFrame for a single simulation run.

    Uses join_asof to pair session start/end events, then join_asof again
    to assign each action and creation to its enclosing session.

    Parameters
    ----------
    sim_id : str
    session_df : pl.DataFrame
        Full session_trace (warmup is filtered here: t >= 1000).
    action_df : pl.DataFrame
        Full action_trace (t >= 1000).
    create_df : pl.DataFrame
        Full create_trace (t >= 1000).
    """
    t0 = time.perf_counter()

    # --- Pair session starts and ends ---
    starts = (
        session_df.filter(pl.col("type") == "start")
        .select([
            "user_id",
            pl.col("time").alias("start_time"),
            pl.col("backlog").alias("backlog_at_start"),
        ])
        .sort(["user_id", "start_time"])
    )
    ends = (
        session_df.filter(pl.col("type") == "end")
        .select([
            "user_id",
            pl.col("time").alias("end_time"),
            pl.col("backlog").alias("backlog_at_end"),
        ])
        .sort(["user_id", "end_time"])
    )

    paired = ends.join_asof(
        starts,
        by="user_id",
        left_on="end_time",
        right_on="start_time",
        strategy="backward",
    )
    paired = paired.with_columns([
        (pl.col("end_time") - pl.col("start_time")).alias("duration"),
        pl.int_range(0, paired.height).alias("session_id"),
    ])

    # --- Assign actions to sessions ---
    session_lookup = paired.select([
        "user_id", "start_time", "end_time", "session_id",
    ]).sort(["user_id", "start_time"])

    actions_sorted = (
        action_df.select([
            "user_id", "time", pl.col("type").alias("action_type"),
        ])
        .sort(["user_id", "time"])
    )

    actions_tagged = (
        actions_sorted.join_asof(
            session_lookup,
            by="user_id",
            left_on="time",
            right_on="start_time",
            strategy="backward",
        )
        .filter(pl.col("time") <= pl.col("end_time"))
    )

    action_counts = actions_tagged.group_by(["user_id", "session_id"]).agg([
        pl.len().alias("n_actions"),
        (pl.col("action_type") == "repost").sum().alias("n_reposts"),
        (pl.col("action_type") == "like").sum().alias("n_likes"),
        (pl.col("action_type") == "ignore").sum().alias("n_ignores"),
    ])

    # --- Assign creates to sessions ---
    creates_sorted = create_df.select([
        "user_id", pl.col("time").alias("create_time"),
    ]).sort(["user_id", "create_time"])

    creates_tagged = (
        creates_sorted.join_asof(
            session_lookup,
            by="user_id",
            left_on="create_time",
            right_on="start_time",
            strategy="backward",
        )
        .filter(pl.col("create_time") <= pl.col("end_time"))
    )

    create_counts = creates_tagged.group_by(["user_id", "session_id"]).agg(
        pl.len().alias("n_posts_created")
    )

    # --- Join everything together ---
    result = (
        paired
        .join(action_counts, on=["user_id", "session_id"], how="left")
        .join(create_counts, on=["user_id", "session_id"], how="left")
        .with_columns([
            pl.col("n_actions").fill_null(0),
            pl.col("n_reposts").fill_null(0),
            pl.col("n_likes").fill_null(0),
            pl.col("n_ignores").fill_null(0),
            pl.col("n_posts_created").fill_null(0),
            pl.lit(sim_id).alias("sim_id"),
            (pl.col("backlog_at_end") == 0).alias("empty_timeline_exit"),
        ])
        .select(SESSION_COLUMNS)
    )

    print(
        f"  [sessions] {result.height} rows in {time.perf_counter() - t0:.1f}s"
    )
    return result


def compute_user_sessions(
    sessions_df: pl.DataFrame,
) -> pl.DataFrame:
    """Aggregate per-user session statistics from out_sessions data.

    Produces one row per (sim_id, user_id).
    """
    return (
        sessions_df.group_by(["sim_id", "user_id"])
        .agg([
            pl.len().alias("n_sessions"),
            pl.col("duration").sum().alias("total_online_time"),
            pl.col("duration").mean().alias("mean_session_duration"),
            pl.col("duration").median().alias("median_session_duration"),
            (pl.col("empty_timeline_exit").sum() * 100.0 / pl.len()).alias(
                "pct_empty_exit"
            ),
            pl.col("n_actions").sum().alias("total_actions"),
            pl.col("n_reposts").sum().alias("total_reposts"),
            pl.col("n_posts_created").sum().alias("total_posts_created"),
        ])
    )
