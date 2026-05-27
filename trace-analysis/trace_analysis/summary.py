"""Global Run Summary — Table 3: out_run_summary.parquet

Highest-level aggregation. One row per simulation replication.
Acts as the batch-means index for rapid plotting of confidence intervals.

Metrics:
    - network_size: total number of agents in the topology
    - avg_online_frac: stationary average % of users online
    - median_backlog: median unread items in the timeline queue across sessions
    - empty_timeline_pct: % of sessions ending with empty timeline
    - gamma_reposts: fitted power-law exponent for reposts (MLE)
"""

from __future__ import annotations

import math
from typing import Dict

import polars as pl

SUMMARY_COLUMNS = [
    "sim_id",
    "network_size",
    "avg_online_frac",
    "median_backlog",
    "empty_timeline_pct",
    "gamma_reposts",
]


# ---------------------------------------------------------------------------
# Online fraction
# ---------------------------------------------------------------------------

def _compute_avg_online_frac(
    sessions_df: pl.DataFrame, warmup: float
) -> float:
    """Compute average % of users online during steady state (t >= warmup).

    Uses a sweep-line algorithm: walks through session start/end events
    sorted by time, tracking net online count, and integrates over time.
    """
    if sessions_df.height == 0:
        return 0.0

    # Filter to steady-state window
    ss = sessions_df.filter(pl.col("time") >= warmup)

    all_uids = sessions_df["user_id"].unique()
    total_users = len(all_uids)

    if ss.height == 0 or total_users == 0:
        return 0.0

    # Build sorted delta events: +1 for start, -1 for end
    starts = ss.filter(pl.col("type") == "start").select(
        pl.col("time").alias("t"),
        pl.lit(1).alias("delta"),
    )
    ends = ss.filter(pl.col("type") == "end").select(
        pl.col("time").alias("t"),
        pl.lit(-1).alias("delta"),
    )
    deltas = pl.concat([starts, ends]).sort("t")

    times = deltas["t"].to_list()
    delta_vals = deltas["delta"].to_list()

    if not times:
        return 0.0

    # Integrate: online count * duration between changes
    online = 0
    prev_t = times[0]
    weighted_sum = 0.0

    for t, d in zip(times, delta_vals):
        weighted_sum += online * (t - prev_t)
        online += d
        prev_t = t

    # Normalise by total span and total users
    span = times[-1] - times[0]
    if span <= 0:
        return online / total_users
    return weighted_sum / (span * total_users)


# ---------------------------------------------------------------------------
# Backlog metrics
# ---------------------------------------------------------------------------

def _compute_backlog_metrics(
    sessions_df: pl.DataFrame, warmup: float
) -> tuple[float, float]:
    """Return (median_backlog, empty_timeline_pct) for steady-state session ends."""
    ends = sessions_df.filter(
        (pl.col("time") >= warmup) & (pl.col("type") == "end")
    )

    if ends.height == 0:
        return 0.0, 0.0

    backlogs = ends["backlog"].drop_nulls()
    if backlogs.len() == 0:
        return 0.0, 0.0

    median_bl = backlogs.median()
    empty_pct = (backlogs == 0).sum() / backlogs.len() * 100.0

    return float(median_bl), float(empty_pct)


# ---------------------------------------------------------------------------
# Power-law exponent fitting (MLE)
# ---------------------------------------------------------------------------

def _fit_power_law_discrete(values: list[float], xmin: float = 1.0) -> float:
    """Estimate power-law exponent γ using MLE for discrete data.

    Uses the Clauset-Shalizi-Newman discrete MLE estimator:
        γ̂ = 1 + n * [ Σ ln(x_i / (xmin - 0.5)) ]⁻¹

    Parameters
    ----------
    values : list[float]
        Observed values (must be >= xmin).
    xmin : float
        Lower bound for the power-law behaviour (default 1.0).

    Returns
    -------
    float
        Estimated scaling exponent γ̂. Returns NaN if insufficient data.
    """
    filtered = [x for x in values if x >= xmin]
    n = len(filtered)
    if n < 2:
        return float("nan")

    sum_logs = sum(math.log(x / (xmin - 0.5)) for x in filtered)
    if sum_logs == 0:
        return float("nan")

    return 1.0 + n / sum_logs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_run_summary(
    sim_id: str,
    network_size: int,
    sessions_df: pl.DataFrame,
    posts_df: pl.DataFrame,
    warmup: float = 1000.0,
) -> dict:
    """Produce a single-row dict for the run summary.

    Parameters
    ----------
    sim_id : str
        Unique simulation identifier.
    network_size : int
        Total number of agents (e.g. 100000).
    sessions_df : pl.DataFrame
        Full session_trace.
    posts_df : pl.DataFrame
        The out_posts DataFrame for this run (needed for gamma_reposts).
    warmup : float
        Warmup time cutoff (default 1000.0).
    """
    avg_online = _compute_avg_online_frac(sessions_df, warmup)
    median_bl, empty_pct = _compute_backlog_metrics(sessions_df, warmup)

    # Fit power-law to total_reposts distribution
    repost_values = (
        posts_df.filter(pl.col("total_reposts") > 0)["total_reposts"]
        .to_list()
    )
    gamma = _fit_power_law_discrete(repost_values, xmin=1.0)

    return {
        "sim_id": sim_id,
        "network_size": network_size,
        "avg_online_frac": avg_online,
        "median_backlog": median_bl,
        "empty_timeline_pct": empty_pct,
        "gamma_reposts": gamma,
    }
