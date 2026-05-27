"""Post Lifetimes & Reposts — Table 2: out_posts.parquet

Captures the temporal rhythms and heavy-tailed engagement distributions.
One row for every post created during the steady-state execution phase
(not warmup).

Metrics:
    - total_reposts: absolute count of reposts
    - lifetime_raw: time between creation and last engagement (in simulation ticks)
    - lifetime_norm: lifetime_raw / propagation_delay (Δ_p = 1.0)
    - time_to_peak_50: time from creation until 50% of total_reposts reached
    - burstiness_B: burstiness parameter from inter-event times
"""

from __future__ import annotations

import math
import time

import polars as pl

DELTA_P = 1.0

POSTS_COLUMNS = [
    "sim_id",
    "post_id",
    "total_reposts",
    "lifetime_raw",
    "lifetime_norm",
    "time_to_peak_50",
    "burstiness_B",
]


# ---------------------------------------------------------------------------
# Per-post scalar metrics computed from sorted lists
# ---------------------------------------------------------------------------

def _compute_time_to_peak_50_burst(
    repost_times: list[float], total_reposts: int
) -> tuple[float, float]:
    """Return (time_to_peak_50, burstiness_B) from sorted repost times.

    time_to_peak_50: time from creation until cumulative reposts ≥ 50% of total_reposts.
        (measured from the first repost, not from creation)
    burstiness_B: (σ_τ − μ_τ) / (σ_τ + μ_τ) from inter-repost times.
    """
    n = len(repost_times)

    # time_to_peak_50
    if total_reposts < 2 or n < 2:
        ttp50 = 0.0
    else:
        half = total_reposts / 2.0
        cum = 0
        t0 = repost_times[0]
        ttp50 = 0.0
        for t in repost_times:
            cum += 1
            if cum >= half:
                ttp50 = t - t0
                break
        else:
            ttp50 = repost_times[-1] - t0

    # burstiness
    if n < 2:
        burst = 0.0
    else:
        inter = [repost_times[i] - repost_times[i - 1] for i in range(1, n)]
        mu = sum(inter) / (n - 1)
        if mu == 0:
            burst = 1.0
        else:
            var = sum((x - mu) ** 2 for x in inter) / (n - 1)
            sigma = math.sqrt(var)
            denom = sigma + mu
            burst = 0.0 if denom == 0 else (sigma - mu) / denom

    return ttp50, burst


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_posts(
    sim_id: str,
    creates_ss: pl.DataFrame,
    actions_ss: pl.DataFrame,
) -> pl.DataFrame:
    """Produce the out_posts DataFrame for a single simulation run.

    Parameters
    ----------
    sim_id : str
        Unique simulation identifier.
    creates_ss : pl.DataFrame
        create_trace filtered to steady state (t >= warmup).
        Columns: post_id, user_id, time.
    actions_ss : pl.DataFrame
        action_trace filtered to steady state.
    """
    t0 = time.perf_counter()

    # --- Phase 1: vectorized Polars aggregations ---

    # Repost counts + sorted repost times (for ttp50 + burstiness)
    repost_data = (
        actions_ss.filter(pl.col("type") == "repost")
        .group_by("post_id")
        .agg([
            pl.len().alias("total_reposts"),
            pl.col("time").sort().alias("repost_times"),
        ])
    )

    # All engagement times: for lifetime_raw (last engagement of any type)
    engagement_times = (
        actions_ss.filter(pl.col("type").is_in(["repost", "like"]))
        .group_by("post_id")
        .agg(pl.col("time").sort().alias("times"))
    )

    # Join creation info → base DataFrame
    base = (
        creates_ss.select(["post_id", pl.col("time").alias("creation_time")])
        .join(repost_data, on="post_id", how="left")
        .join(engagement_times, on="post_id", how="left")
        .with_columns([
            pl.col("total_reposts").fill_null(0),
        ])
    )

    # lifetime_raw: last engagement - creation_time
    base = base.with_columns(
        pl.when(pl.col("times").is_not_null())
        .then(pl.col("times").list.last() - pl.col("creation_time"))
        .otherwise(0.0)
        .alias("lifetime_raw"),
    )

    # --- Phase 2: per-post scalar metrics (only for posts with reposts > 0) ---
    # time_to_peak_50 and burstiness are computed from repost_times (not all engagements)
    has_reposts = base.filter(pl.col("total_reposts") > 0)

    ttp50_map: dict[int, float] = {}
    burst_map: dict[int, float] = {}

    for row in has_reposts.iter_rows(named=True):
        pid = row["post_id"]
        rt = row["repost_times"] if row["repost_times"] is not None else []
        ttp50, burst = _compute_time_to_peak_50_burst(rt, row["total_reposts"])
        ttp50_map[pid] = ttp50
        burst_map[pid] = burst

    # --- Phase 3: assemble final DataFrame ---
    rows = []
    # Batch collect from base + maps
    for row in base.iter_rows(named=True):
        pid = row["post_id"]
        rows.append({
            "sim_id": sim_id,
            "post_id": pid,
            "total_reposts": row["total_reposts"],
            "lifetime_raw": row["lifetime_raw"],
            "lifetime_norm": row["lifetime_raw"] / DELTA_P,
            "time_to_peak_50": ttp50_map.get(pid, 0.0),
            "burstiness_B": burst_map.get(pid, 0.0),
        })

    result = pl.DataFrame(
        rows,
        schema={
            "sim_id": pl.Utf8,
            "post_id": pl.Int64,
            "total_reposts": pl.Int64,
            "lifetime_raw": pl.Float64,
            "lifetime_norm": pl.Float64,
            "time_to_peak_50": pl.Float64,
            "burstiness_B": pl.Float64,
        },
    )
    print(f"  [posts] {result.height} rows in {time.perf_counter() - t0:.1f}s")
    return result
