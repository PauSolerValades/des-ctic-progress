import duckdb

for size in ["1M", "500K"]:
    s = f"output/{size}/out_run_summary.parquet"
    print(f"=== {size} — Session / Starvation Analysis ===")
    
    print(f"\n  Run summary:")
    duckdb.sql(f"""
        SELECT 
            AVG(avg_online_frac)::FLOAT as mean_online,
            STDDEV(avg_online_frac)::FLOAT as std_online,
            AVG(median_backlog)::FLOAT as mean_med_backlog,
            AVG(empty_timeline_pct)::FLOAT as mean_empty_pct,
            STDDEV(empty_timeline_pct)::FLOAT as std_empty_pct
        FROM '{s}'
    """).show()

# Now analyze the raw session traces to compute actual session durations
print("\n=== Session Duration Analysis from RAW traces ===")

# We need to look at the raw session traces for a sample run
import polars as pl
from pathlib import Path

for size_dir in ["1M", "500K"]:
    # Find first run
    traces_root = Path("../release-v4/traces")
    size_path = traces_root / size_dir
    batch = next(size_path.iterdir())
    run = next(batch.iterdir())
    session_file = run / "session_trace.jsonl"
    
    df = pl.read_ndjson(str(session_file))
    
    # Filter to steady state
    ss = df.filter(pl.col("time") >= 1000)
    
    # Compute session durations: pair start/end events per user
    starts = ss.filter(pl.col("type") == "start").select([
        pl.col("user_id"), pl.col("time").alias("start_time")
    ]).sort(["user_id", "start_time"])
    
    ends = ss.filter(pl.col("type") == "end").select([
        pl.col("user_id"), pl.col("time").alias("end_time"),
        pl.col("backlog")
    ]).sort(["user_id", "end_time"])
    
    # Match each end to its preceding start (per user)
    # Simple approach: for each user, pair consecutive start/end
    durations = []
    backlogs_at_end = []
    backlogs_at_start = []
    
    for uid in ss["user_id"].unique().to_list():
        u_starts = starts.filter(pl.col("user_id") == uid)["start_time"].to_list()
        u_ends = ends.filter(pl.col("user_id") == uid)
        u_end_times = u_ends["end_time"].to_list()
        u_end_bl = u_ends["backlog"].to_list()
        
        # Pair: each end corresponds to the most recent start before it
        si = 0
        for ei, et in enumerate(u_end_times):
            while si < len(u_starts) and u_starts[si] < et:
                si += 1
            if si > 0:
                start_t = u_starts[si - 1]
                dur = et - start_t
                if dur >= 0:
                    durations.append(dur)
                    backlogs_at_end.append(u_end_bl[ei])
                    # Get the start backlog (session_trace has backlog on start too)
    
    # Also: what fraction of sessions end with backlog=0? 
    # And what's the distribution of backlogs at session start vs end?
    starts_bl = ss.filter(pl.col("type") == "start")["backlog"].drop_nulls().to_list()
    ends_bl = ss.filter(pl.col("type") == "end")["backlog"].drop_nulls().to_list()
    
    import numpy as np
    durs = np.array(durations)
    bl_end = np.array(backlogs_at_end) if backlogs_at_end else np.array([])
    
    print(f"\n--- {size_dir} (sample run: {batch.name}/{run.name}) ---")
    print(f"  Session events: {ss.height} (starts: {len(starts)}, ends: {len(ends)})")
    print(f"  Unique users: {ss['user_id'].n_unique()}")
    print(f"  Paired sessions: {len(durations)}")
    print(f"  Session duration (ticks):")
    print(f"    mean={durs.mean():.0f}, median={np.median(durs):.0f}")
    print(f"    min={durs.min():.0f}, max={durs.max():.0f}")
    print(f"    p5={np.percentile(durs, 5):.0f}, p25={np.percentile(durs, 25):.0f}, p75={np.percentile(durs, 75):.0f}, p95={np.percentile(durs, 95):.0f}")
    
    if len(bl_end) > 0:
        print(f"  Backlog at session end: mean={bl_end.mean():.1f}, median={np.median(bl_end):.0f}, "
              f"zero_pct={(bl_end==0).mean()*100:.1f}%")
    
    # Histogram of durations
    print(f"  Duration histogram (log buckets):")
    for bound in [0, 1, 5, 10, 30, 60, 120, 300, 600, 1000, 999999]:
        if bound == 0:
            continue
        prev = 0 if bound == 1 else (bound // 2 if bound <= 10 else bound * 2 // 3)
        cnt = ((durs >= prev) & (durs < bound)).sum()
        pct = cnt / len(durs) * 100
        print(f"    {prev:>4}-{bound:<5}: {cnt:>8,} ({pct:5.1f}%)")
    
    # Also: show backlogs at session start vs end
    print(f"  Backlog at session START: mean={np.mean(starts_bl):.1f}, median={np.median(starts_bl):.0f}, "
          f"zero_pct={(np.array(starts_bl)==0).mean()*100:.1f}%")
    
    # Key question: do short sessions correlate with backlogs?
    # Sessions that end with backlogs=0 → what's their duration?
    if len(bl_end) > 0:
        zero_bl = durs[bl_end == 0]
        nonzero_bl = durs[bl_end > 0]
        print(f"  Duration of sessions ending with backlogs=0: mean={zero_bl.mean():.0f}, median={np.median(zero_bl):.0f}")
        if len(nonzero_bl) > 0:
            print(f"  Duration of sessions ending with backlogs>0: mean={nonzero_bl.mean():.0f}, median={np.median(nonzero_bl):.0f}")
    
    print()
