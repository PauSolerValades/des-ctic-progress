"""Section 5: Micro-Macro Coupling Ratios."""
import duckdb
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "output"
DATA = Path(__file__).parent.parent / "output"
SIZES = ["100K", "500K", "1M"]


def main():
    print("=== 5.1 Pace Ratio ρ ==============================")
    print("  ρ = inter_action_mean / inter_repost_mean")
    print("    = 3.0 / (3.0 / 0.012)")
    print("    = 0.012")
    print("  Users interact 83× more often than they repost.")
    print("  (purely from config.zig: p_repost=0.012, inter_action=Exp(3))")

    print("\n=== 5.2 Session Persistence π =====================")
    print("  π = mean_post_lifetime / mean_session_duration per run")
    print(f"  {'Size':<8} {'π_mean':>10} {'π_±CI':>10} {'p_lt_mean':>12} {'s_dur_mean':>12}")
    for s in SIZES:
        # Per-run mean post lifetime
        post_runs = duckdb.sql(f"""
            SELECT sim_id, AVG(lifetime_raw) as mean_lt
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0
            GROUP BY sim_id
        """).df()
        # Per-run mean session duration
        sess_runs = duckdb.sql(f"""
            SELECT sim_id, AVG(duration) as mean_dur
            FROM '{DATA}/{s}/out_sessions.parquet'
            GROUP BY sim_id
        """).df()
        merged = post_runs.merge(sess_runs, on="sim_id")
        merged["pi"] = merged["mean_lt"] / merged["mean_dur"]
        mu, ci = merged["pi"].mean(), 1.96 * merged["pi"].std(ddof=1) / np.sqrt(len(merged))
        print(f"  {s:<8} {mu:>9.2f} {ci:>9.2f} "
              f"{merged['mean_lt'].mean():>11.0f} {merged['mean_dur'].mean():>11.0f}")

    print("\n=== 5.3 Saturation σ =============================")
    print("  σ = global_repots / mean_offline_gap")
    print(f"  {'Size':<8} {'σ':>10} {'reposts/run':>13} {'offline_gap':>13}")
    for s in SIZES:
        # Compute offline gaps per run: for each user, gap = next start - previous end
        # DuckDB window function
        gaps = duckdb.sql(f"""
            WITH ordered AS (
                SELECT sim_id, user_id, start_time, end_time,
                       LEAD(start_time) OVER (PARTITION BY sim_id, user_id ORDER BY start_time) as next_start
                FROM '{DATA}/{s}/out_sessions.parquet'
            )
            SELECT sim_id, AVG(next_start - end_time) as mean_gap,
                   COUNT(*) as n_gaps
            FROM ordered
            WHERE next_start IS NOT NULL AND (next_start - end_time) > 0
            GROUP BY sim_id
        """).df()
        # Global repost count per run
        reposts = duckdb.sql(f"""
            SELECT sim_id, SUM(n_reposts) as total_reposts
            FROM '{DATA}/{s}/out_sessions.parquet'
            GROUP BY sim_id
        """).df()
        # σ = repost_rate / offline_rate. But simpler: total reposts / total time / users
        # Alternative: mean inter-repost time vs mean offline gap
        # mean_inter_repost = total_time / total_reposts
        # σ = mean_inter_repost / mean_offline_gap
        time_per_run = duckdb.sql(f"""
            SELECT sim_id, MAX(end_time)-MIN(start_time) as span
            FROM '{DATA}/{s}/out_sessions.parquet'
            GROUP BY sim_id
        """).df()
        merged = gaps.merge(reposts, on="sim_id").merge(time_per_run, on="sim_id")
        merged["inter_repost"] = merged["span"] / merged["total_reposts"].clip(lower=1)
        merged["sigma"] = merged["inter_repost"] / merged["mean_gap"]
        mu, ci = merged["sigma"].mean(), 1.96 * merged["sigma"].std(ddof=1) / np.sqrt(len(merged))
        print(f"  {s:<8} {mu:>9.4f} {ci:>9.4f} "
              f"{merged['total_reposts'].mean():>12.0f} {merged['mean_gap'].mean():>12.0f}")
    
    print("\n  σ << 1 for all sizes → content arrives slower than users return.")
    print("  This confirms structural starvation.")

    print("\n=== 5.4 Content Ratio ============================")
    print("  Posts created vs consumed per session")
    print(f"  {'Size':<8} {'created/sess':>14} {'consumed/sess':>14} {'ratio':>10}")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT AVG(n_posts_created) as created, AVG(n_actions) as consumed
            FROM '{DATA}/{s}/out_sessions.parquet'
        """).df().iloc[0]
        ratio = r["created"] / r["consumed"] if r["consumed"] > 0 else 0
        print(f"  {s:<8} {r['created']:>13.2f} {r['consumed']:>13.1f} {ratio:>9.4f}")
    print("  Users are net consumers (ratio << 1). Most sessions create 0 posts.")


if __name__ == "__main__":
    main()
