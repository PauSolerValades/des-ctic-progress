"""
Batch-means analysis for the CTIC simulation chapter.
Uses the existing output parquets directly — no reprocessing needed.
"""
import duckdb
import numpy as np

SIZES = ["100K", "500K", "1M"]
NETWORK_NAME = {"100K": "100K", "500K": "500K", "1M": "1M"}

# We'll need per-run session pairing for some metrics.
# DuckDB can't do join_asof. We pre-process one sample run per size
# for metrics that need pairing, but batch-means use the parquet only.

for size in SIZES:
    s = f"output/{size}/out_run_summary.parquet"
    c = f"output/{size}/out_cascades.parquet"
    p = f"output/{size}/out_posts.parquet"
    
    print(f"{'='*70}")
    print(f"  {size}")
    print(f"{'='*70}")
    
    # === STATIONARY BEHAVIOUR ===
    print(f"\n--- Stationary Behaviour ---")
    duckdb.sql(f"""
        SELECT
            AVG(avg_online_frac)::FLOAT as mean_online,
            STDDEV(avg_online_frac)::FLOAT as std_online,
            AVG(empty_timeline_pct)::FLOAT as mean_empty,
            STDDEV(empty_timeline_pct)::FLOAT as std_empty,
            AVG(median_backlog)::FLOAT as mean_med_backlog,
            STDDEV(median_backlog)::FLOAT as std_med_backlog,
            AVG(gamma_reposts)::FLOAT as mean_gamma,
            STDDEV(gamma_reposts)::FLOAT as std_gamma
        FROM '{s}'
    """).show()
    
    # === QUEUED CONTENT CONGESTION ===
    print(f"\n--- Cascade batch means ---")
    duckdb.sql(f"""
        SELECT
            COUNT(*) as n_cascades,
            AVG(cascade_size)::FLOAT as mean_size,
            MEDIAN(cascade_size) as med_size,
            STDDEV(cascade_size)::FLOAT as std_size,
            AVG(cascade_depth)::FLOAT as mean_depth,
            MAX(cascade_depth) as max_depth,
            AVG(struct_virality)::FLOAT as mean_virality,
            MEDIAN(struct_virality) as med_virality,
            AVG(max_out_degree)::FLOAT as mean_max_out,
            MAX(max_out_degree) as max_max_out,
            -- % viral (size >= 10)
            (SUM(CASE WHEN cascade_size >= 10 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_viral_size10,
            (SUM(CASE WHEN cascade_size >= 20 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_viral_size20,
            (SUM(CASE WHEN cascade_size >= 50 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_viral_size50,
            -- % with branching
            (SUM(CASE WHEN max_out_degree >= 2 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_branching
        FROM '{c}'
    """).show()
    
    # === LIFETIMES AND SCALE ===
    print(f"\n--- Post lifetimes ---")
    duckdb.sql(f"""
        SELECT
            AVG(total_reposts)::FLOAT as mean_reposts,
            MEDIAN(total_reposts) as med_reposts,
            AVG(lifetime_raw)::FLOAT as mean_lifetime,
            MEDIAN(lifetime_raw) as med_lifetime,
            AVG(lifetime_norm)::FLOAT as mean_lifetime_norm,
            AVG(time_to_peak_50)::FLOAT as mean_ttp50,
            AVG(burstiness_B)::FLOAT as mean_burstiness,
            MEDIAN(burstiness_B) as med_burstiness,
            STDDEV(burstiness_B)::FLOAT as std_burstiness
        FROM '{p}'
        WHERE total_reposts > 0
    """).show()
    
    # Posts with 0 reposts but engagement
    print(f"\n  Posts with 0 reposts:")
    duckdb.sql(f"""
        SELECT
            COUNT(*) as n,
            AVG(lifetime_raw)::FLOAT as mean_lifetime,
            MEDIAN(lifetime_raw) as med_lifetime,
            (SUM(CASE WHEN lifetime_raw = 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_no_engagement
        FROM '{p}'
        WHERE total_reposts = 0
    """).show()
    
    # === INFLUENCER EFFECT ===
    print(f"\n--- Author degree vs cascade size ---")
    duckdb.sql(f"""
        SELECT
            CASE
                WHEN author_degree = 0 THEN 'zero'
                WHEN author_degree < 10 THEN '1-9'
                WHEN author_degree < 100 THEN '10-99'
                WHEN author_degree < 1000 THEN '100-999'
                WHEN author_degree < 10000 THEN '1K-10K'
                ELSE '10K+'
            END as degree_bucket,
            COUNT(*) as n,
            AVG(cascade_size)::FLOAT as mean_size,
            AVG(cascade_depth)::FLOAT as mean_depth,
            AVG(struct_virality)::FLOAT as mean_virality,
            AVG(max_out_degree)::FLOAT as mean_max_out
        FROM '{c}'
        GROUP BY degree_bucket
        ORDER BY MIN(author_degree)
    """).show()

print(f"\n{'='*70}")
print(f"  MICRO-MACRO COUPLING RATIOS")
print(f"{'='*70}")

# These need constants from the model config
INTER_ACTION_MEAN = 3.0      # Exp(mean=3) from config.zig
INTER_REPOST_MEAN = 1.0 / 0.012  # p_repost = 0.012 → mean encounters per repost
# Actually: inter-repost time = inter_action_time * (1/p_repost) = 3 * 83.33 ≈ 250
# But that's per-user. Let's compute from data.

# Pace ratio ρ = mean_inter_action_time / mean_inter_repost_time
# From config: inter_action ~ Expo(3). Repost happens with p=0.012 per action.
# Expected actions per repost = 1/0.012 ≈ 83.3
# inter_repost_time ≈ 3 * 83.3 = 250 ticks
RHO = INTER_ACTION_MEAN / (INTER_ACTION_MEAN / 0.012)
print(f"\n  Pace ratio ρ = inter_action_mean / inter_repost_mean")
print(f"               = {INTER_ACTION_MEAN} / {INTER_ACTION_MEAN / 0.012:.1f}")
print(f"               = {RHO:.4f}")
print(f"  Interpretation: users interact {1/RHO:.0f}x more often than they repost")

# For session persistence and saturation, we need per-run session data.
# Let's load a sample run to estimate these.
print(f"\n  Loading sample run for session-level coupling ratios...")

import polars as pl
from pathlib import Path

for size in ["1M", "500K"]:
    traces = Path(f"../release-v4/traces/{size}")
    batch = next(traces.iterdir())
    run = next(batch.iterdir())
    session_file = run / "session_trace.jsonl"
    action_file = run / "action_trace.jsonl"
    
    sessions = pl.read_ndjson(str(session_file)).filter(pl.col("time") >= 1000)
    actions = pl.read_ndjson(str(action_file)).filter(pl.col("time") >= 1000)
    
    # Pair sessions
    starts = sessions.filter(pl.col("type") == "start").select([
        "user_id", pl.col("time").alias("start_time")
    ]).sort(["user_id", "start_time"])
    ends = sessions.filter(pl.col("type") == "end").select([
        "user_id", pl.col("time").alias("end_time"), "backlog"
    ]).sort(["user_id", "end_time"])
    
    paired = ends.join_asof(starts, by="user_id", left_on="end_time", right_on="start_time", strategy="backward")
    paired = paired.with_columns((pl.col("end_time") - pl.col("start_time")).alias("duration"))
    
    # Online time per session
    mean_session_dur = paired["duration"].mean()
    
    # Mean offline time: gap between end of session N and start of session N+1
    all_events = sessions.sort(["user_id", "time"])
    # Get consecutive start times per user and compute gaps
    from collections import defaultdict
    user_times = defaultdict(list)
    for row in all_events.iter_rows(named=True):
        user_times[row["user_id"]].append((row["time"], row["type"]))
    
    offline_gaps = []
    for uid, events in user_times.items():
        # events are sorted. Gap = start time - previous end time
        for i in range(1, len(events)):
            if events[i-1][1] == "end" and events[i][1] == "start":
                gap = events[i][0] - events[i-1][0]
                if gap > 0:
                    offline_gaps.append(gap)
    offline_gaps = np.array(offline_gaps)
    mean_offline = offline_gaps.mean()
    
    # Mean post lifetime (from posts parquet for this run)
    # But we don't have per-run posts yet. Use the full parquet:
    posts_df = pl.read_parquet(f"output/{size}/out_posts.parquet")
    rp = posts_df.filter(pl.col("total_reposts") > 0)
    mean_post_lifetime = rp["lifetime_raw"].mean()
    
    # Time between reposts: from action_trace, get repost inter-event times
    repost_actions = actions.filter(pl.col("type") == "repost").sort(["user_id", "time"])
    repost_times = repost_actions["time"].to_numpy()
    if len(repost_times) >= 2:
        inter_repost_times = np.diff(repost_times)
        avg_inter_repost = inter_repost_times.mean()
    else:
        avg_inter_repost = 0
    
    # Session persistence π = mean_post_lifetime / mean_online_per_session
    pi = mean_post_lifetime / mean_session_dur if mean_session_dur > 0 else 0
    
    # Saturation σ = avg_time_between_reposts / mean_time_offline
    sigma = avg_inter_repost / mean_offline if mean_offline > 0 else 0
    
    print(f"\n  --- {size} (sample run) ---")
    print(f"  Mean session duration: {mean_session_dur:.0f} ticks")
    print(f"  Mean offline gap: {mean_offline:.0f} ticks")
    print(f"  Mean post lifetime (with reposts): {mean_post_lifetime:.0f} ticks")
    print(f"  Avg time between reposts (global): {avg_inter_repost:.1f} ticks")
    print(f"")
    print(f"  Session persistence π = mean_post_lifetime / mean_online_per_session")
    print(f"                        = {mean_post_lifetime:.0f} / {mean_session_dur:.0f}")
    print(f"                        = {pi:.2f}")
    print(f"  Interpretation: a post outlives an average session by {pi:.1f}x")
    print(f"")
    print(f"  Saturation σ = avg_time_between_reposts / mean_time_offline")
    print(f"               = {avg_inter_repost:.0f} / {mean_offline:.0f}")
    print(f"               = {sigma:.4f}")
    print(f"  Interpretation: reposts arrive every {avg_inter_repost:.0f} ticks,")
    print(f"  while users are offline for {mean_offline:.0f} ticks on average.")
    if sigma < 1:
        print(f"  σ < 1 → reposts arrive FASTER than users return. Content piles up.")
    else:
        print(f"  σ > 1 → users return FASTER than reposts arrive. Starvation.")

print(f"\nDone.")
