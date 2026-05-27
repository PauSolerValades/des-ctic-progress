"""Generate the high-priority missing plots for the chapter."""
import duckdb
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "output"
DATA = Path(__file__).parent.parent / "output"
SIZES = ["100K", "500K", "1M"]
NL = {"100K": "$10^5$", "500K": "$5\\times10^5$", "1M": "$10^6$"}

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def ccdf(vals):
    """Return (x, ccdf) for log-log CCDF plot."""
    sorted_vals = np.sort(vals)
    ccdf_y = 1.0 - np.arange(len(sorted_vals)) / len(sorted_vals)
    return sorted_vals, ccdf_y


def plot_reposts_ccdf():
    """Log-log CCDF of total_reposts — sample for speed."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        vals = duckdb.sql(f"""
            SELECT total_reposts FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0
            USING SAMPLE 200000
        """).df()["total_reposts"].values
        x, y = ccdf(vals)
        ax.loglog(x, y, ".", markersize=2, alpha=0.6, color="steelblue")
        mid = (x >= 5) & (x <= np.percentile(x, 95))
        if mid.sum() > 2:
            a, b = np.polyfit(np.log10(x[mid]), np.log10(y[mid]), 1)
            ax.loglog(x[mid], 10**(a * np.log10(x[mid]) + b), "r--", lw=1.5)
            ax.text(0.95, 0.15, f"α≈{-a:.1f}", transform=ax.transAxes,
                    ha="right", fontsize=9, color="red")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("total_reposts"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("P(X ≥ x)")
    fig.suptitle("CCDF of total_reposts (sampled, posts with reposts > 0)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_reposts_ccdf.png", bbox_inches="tight")
    plt.close()


def plot_lifetime_ccdf():
    """Log-log CCDF of lifetime_norm — sample for speed."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        vals = duckdb.sql(f"""
            SELECT lifetime_norm FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0 AND lifetime_norm > 0
            USING SAMPLE 200000
        """).df()["lifetime_norm"].values
        x, y = ccdf(vals)
        ax.loglog(x, y, ".", markersize=2, alpha=0.6, color="darkorange")
        mid = (x >= 100) & (x <= np.percentile(x, 95))
        if mid.sum() > 2:
            a, b = np.polyfit(np.log10(x[mid]), np.log10(y[mid]), 1)
            ax.loglog(x[mid], 10**(a * np.log10(x[mid]) + b), "r--", lw=1.5)
            ax.text(0.95, 0.15, f"α≈{-a:.1f}", transform=ax.transAxes,
                    ha="right", fontsize=9, color="red")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("lifetime_norm (ticks)"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("P(X ≥ x)")
    fig.suptitle("CCDF of lifetime_norm (sampled, posts with reposts > 0)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_lifetime_ccdf.png", bbox_inches="tight")
    plt.close()


def plot_cascade_size_ccdf():
    """Log-log CCDF of cascade_size — sample."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        vals = duckdb.sql(f"""
            SELECT cascade_size FROM '{DATA}/{s}/out_cascades.parquet'
            USING SAMPLE 200000
        """).df()["cascade_size"].values
        x, y = ccdf(vals)
        ax.loglog(x, y, ".", markersize=2, alpha=0.6, color="mediumseagreen")
        mid = (x >= 5) & (x <= np.percentile(x, 99))
        if mid.sum() > 2:
            a, b = np.polyfit(np.log10(x[mid]), np.log10(y[mid]), 1)
            ax.loglog(x[mid], 10**(a * np.log10(x[mid]) + b), "r--", lw=1.5)
            ax.text(0.95, 0.15, f"α≈{-a:.1f}", transform=ax.transAxes,
                    ha="right", fontsize=9, color="red")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("cascade_size"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("P(X ≥ x)")
    fig.suptitle("CCDF of cascade_size (sampled)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_cascade_size_ccdf.png", bbox_inches="tight")
    plt.close()


def plot_influencer_scatter():
    """Hexbin: author_degree vs cascade_size."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT author_degree, cascade_size
            FROM '{DATA}/{s}/out_cascades.parquet'
            USING SAMPLE 100000
        """).df()
        ax.hexbin(df["author_degree"], df["cascade_size"],
                  gridsize=30, cmap="YlOrRd", mincnt=1)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("author_degree (followers)")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_size")
    fig.suptitle("Influencer effect: author_degree vs cascade_size (sampled)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_influencer_scatter.png", bbox_inches="tight")
    plt.close()


def plot_broadcast_vs_viral():
    """Hexbin: max_out_degree vs cascade_depth."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT max_out_degree, cascade_depth
            FROM '{DATA}/{s}/out_cascades.parquet'
            USING SAMPLE 100000
        """).df()
        ax.hexbin(df["max_out_degree"], df["cascade_depth"],
                  gridsize=30, cmap="Blues", mincnt=1)
        ax.set_xscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("max_out_degree (broadcast)")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_depth")
    fig.suptitle("Broadcast vs viral: max_out_degree vs cascade_depth (sampled)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_broadcast_vs_viral.png", bbox_inches="tight")
    plt.close()


def plot_ttp50_hist():
    """Histogram of time_to_peak_50 for posts with >= 2 reposts."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, s in zip(axes, SIZES):
        vals = duckdb.sql(f"""
            SELECT time_to_peak_50 FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts >= 2 AND time_to_peak_50 > 0
        """).df()["time_to_peak_50"].values
        bins = np.logspace(0, np.log10(max(vals.max(), 10)), 50)
        ax.hist(vals, bins=bins, color="teal", alpha=0.7, edgecolor="white")
        ax.set_xscale("log")
        ax.set_title(f"{NL[s]} (n={len(vals):,})")
        ax.set_xlabel("time_to_peak_50"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Posts")
    fig.suptitle("Time to 50% of reposts (posts with ≥2 reposts and ttp50>0)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_ttp50_hist.png", bbox_inches="tight")
    plt.close()


def main():
    print("Generating CCDFs...")
    plot_reposts_ccdf()
    plot_lifetime_ccdf()
    print("Generating cascade plots...")
    plot_cascade_size_ccdf()
    plot_influencer_scatter()
    plot_broadcast_vs_viral()
    print("Generating ttp50 histogram...")
    plot_ttp50_hist()
    print(f"Done → {OUTPUT}/")


if __name__ == "__main__":
    main()
