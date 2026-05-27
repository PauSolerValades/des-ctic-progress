"""Sections 3 & 4: Lifetimes, Scale, and Cascade Analysis."""
import duckdb
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "output"
OUTPUT.mkdir(exist_ok=True)
DATA = Path(__file__).parent.parent / "output"
SIZES = ["100K", "500K", "1M"]
NL = {"100K": "$10^5$", "500K": "$5\\times10^5$", "1M": "$10^6$"}

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: LIFETIMES AND SCALE
# ═══════════════════════════════════════════════════════════════════════

def table_lifetimes():
    print("\n=== 3.1 Post Lifetime Metrics ===\n")
    print(f"  {'Size':<8} {'% reposted':>12} {'mean_reposts':>14} "
          f"{'mean_lifetime':>15} {'med_lifetime':>14} {'mean_B':>10} {'mean_ttp50':>12}")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT
                (SUM(CASE WHEN total_reposts>0 THEN 1 ELSE 0 END)*100.0/COUNT(*)) as pct_reposted,
                AVG(total_reposts) as mean_rp,
                AVG(lifetime_raw) as mean_lt,
                MEDIAN(lifetime_raw) as med_lt,
                AVG(burstiness_B) as mean_B,
                AVG(time_to_peak_50) as mean_t50
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0
        """).df().iloc[0]
        print(f"  {s:<8} {r['pct_reposted']:>11.1f}% {r['mean_rp']:>13.1f} "
              f"{r['mean_lt']:>14.0f} {r['med_lt']:>13.0f} "
              f"{r['mean_B']:>9.3f} {r['mean_t50']:>11.1f}")
    
    # Zero-repost posts
    print(f"\n  Posts with 0 reposts:")
    print(f"  {'Size':<8} {'count':>12} {'% no engage':>14} "
          f"{'mean_lifetime':>15} {'med_lifetime':>14}")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT COUNT(*) as n,
                   (SUM(CASE WHEN lifetime_raw=0 THEN 1 ELSE 0 END)*100.0/COUNT(*)) as pct_dead,
                   AVG(lifetime_raw) as mean_lt,
                   MEDIAN(lifetime_raw) as med_lt
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts = 0
        """).df().iloc[0]
        print(f"  {s:<8} {int(r['n']):>12,} {r['pct_dead']:>13.1f}% "
              f"{r['mean_lt']:>14.0f} {r['med_lt']:>13.1f}")


def plot_lifetime_vs_reposts():
    """Scatter: lifetime_norm vs total_reposts (sample for speed)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT lifetime_norm, total_reposts
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0
            USING SAMPLE 50000
        """).df()
        ax.hexbin(df["total_reposts"], df["lifetime_norm"],
                  gridsize=30, cmap="YlOrRd", mincnt=1)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("total_reposts"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("lifetime_norm (ticks)")
    fig.suptitle("Post lifetime vs repost count (sampled, hexbin)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_lifetime_vs_reposts.png", bbox_inches="tight")
    plt.close()


def plot_burstiness_vs_reposts():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        r = duckdb.sql(f"""
            SELECT
                CASE WHEN total_reposts=1 THEN '1'
                     WHEN total_reposts<5 THEN '2-4'
                     WHEN total_reposts<10 THEN '5-9'
                     WHEN total_reposts<50 THEN '10-49'
                     ELSE '50+' END as bucket,
                AVG(burstiness_B) as mean_B,
                STDDEV(burstiness_B) as std_B
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0
            GROUP BY bucket
            ORDER BY MIN(total_reposts)
        """).df()
        ax.bar(range(len(r)), r["mean_B"], yerr=r["std_B"],
               color="steelblue", capsize=4)
        ax.set_xticks(range(len(r)))
        ax.set_xticklabels(r["bucket"])
        ax.set_title(f"{NL[s]}")
        ax.set_ylabel("Burstiness B"); ax.grid(True, alpha=0.3, axis="y")
    fig.suptitle("Burstiness by repost count bucket")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_burstiness.png", bbox_inches="tight")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: CASCADES
# ═══════════════════════════════════════════════════════════════════════

def table_cascade_means():
    print("\n=== 4.1 Cascade Batch Means ===\n")
    print(f"  {'Size':<8} {'cascades':>12} {'mean_size':>12} {'mean_depth':>12} "
          f"{'mean_v':>10} {'%viral10':>10} {'%branch':>10}")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT COUNT(*) as n,
                   AVG(cascade_size) as mean_sz,
                   AVG(cascade_depth) as mean_dp,
                   AVG(struct_virality) as mean_v,
                   SUM(CASE WHEN cascade_size>=10 THEN 1 ELSE 0 END)*100.0/COUNT(*) as pct10,
                   SUM(CASE WHEN max_out_degree>=2 THEN 1 ELSE 0 END)*100.0/COUNT(*) as pct_branch
            FROM '{DATA}/{s}/out_cascades.parquet'
        """).df().iloc[0]
        print(f"  {s:<8} {int(r['n']):>12,} {r['mean_sz']:>11.1f} {r['mean_dp']:>11.1f} "
              f"{r['mean_v']:>9.2f} {r['pct10']:>9.1f}% {r['pct_branch']:>9.1f}%")


def table_cascade_size_dist():
    print("\n─── 4.2 Cascade size distribution ───")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT FLOOR(LOG10(cascade_size)) as log_sz, COUNT(*) as n,
                   AVG(cascade_depth) as mean_dp, AVG(struct_virality) as mean_v,
                   AVG(max_out_degree) as mean_mo
            FROM '{DATA}/{s}/out_cascades.parquet'
            GROUP BY log_sz ORDER BY log_sz
        """).df()
        print(f"\n  {s}:")
        print(f"  {'log10(size)':<14} {'N':>12} {'mean_depth':>12} "
              f"{'mean_virality':>15} {'mean_max_out':>14}")
        for _, row in r.iterrows():
            print(f"  {int(row['log_sz']):<14} {int(row['n']):>12,} {row['mean_dp']:>11.1f} "
                  f"{row['mean_v']:>14.2f} {row['mean_mo']:>13.1f}")


def plot_depth_vs_size():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT cascade_size, cascade_depth
            FROM '{DATA}/{s}/out_cascades.parquet'
            USING SAMPLE 100000
        """).df()
        ax.hexbin(df["cascade_size"], df["cascade_depth"],
                  gridsize=30, cmap="Blues", mincnt=1)
        ax.set_xscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("cascade_size"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_depth")
    fig.suptitle("Cascade depth vs size (sampled, hexbin)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_depth_vs_size.png", bbox_inches="tight")
    plt.close()


def table_influencer():
    print("\n─── 4.3 Influencer effect ───")
    for s in SIZES:
        r = duckdb.sql(f"""
            SELECT
                CASE WHEN author_degree=0 THEN 'zero'
                     WHEN author_degree<100 THEN '1-99'
                     WHEN author_degree<1000 THEN '100-999'
                     WHEN author_degree<10000 THEN '1K-10K'
                     ELSE '10K+' END as bucket,
                COUNT(*) as n,
                AVG(cascade_size) as mean_sz,
                AVG(cascade_depth) as mean_dp,
                AVG(struct_virality) as mean_v
            FROM '{DATA}/{s}/out_cascades.parquet'
            GROUP BY bucket ORDER BY MIN(author_degree)
        """).df()
        print(f"\n  {s}:")
        print(f"  {'Degree':<12} {'N':>12} {'mean_size':>12} "
              f"{'mean_depth':>12} {'mean_virality':>15}")
        for _, row in r.iterrows():
            print(f"  {row['bucket']:<12} {int(row['n']):>12,} {row['mean_sz']:>11.2f} "
                  f"{row['mean_dp']:>11.2f} {row['mean_v']:>14.2f}")


def plot_virality_dist():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, s in zip(axes, SIZES):
        v = duckdb.sql(f"""
            SELECT struct_virality FROM '{DATA}/{s}/out_cascades.parquet'
            WHERE struct_virality > 1.34
        """).df()["struct_virality"].values
        ax.hist(v, bins=80, color="darkviolet", alpha=0.7, edgecolor="white")
        ax.axvline(v.mean(), color="black", ls="--", lw=1.5)
        ax.set_title(f"{NL[s]} (μ={v.mean():.2f})")
        ax.set_xlabel("struct_virality"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Cascades")
    fig.suptitle("Struct virality distribution (excluding minimal ν=1.33)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_virality_hist.png", bbox_inches="tight")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    # Section 3
    table_lifetimes()
    plot_lifetime_vs_reposts()
    plot_burstiness_vs_reposts()

    # Section 4
    table_cascade_means()
    table_cascade_size_dist()
    plot_depth_vs_size()
    table_influencer()
    plot_virality_dist()

    print(f"\nAll plots saved to {OUTPUT}/")


if __name__ == "__main__":
    main()
