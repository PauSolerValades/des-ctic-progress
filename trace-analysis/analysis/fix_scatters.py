"""Fix scatter/hexbin plots with proper rendering."""
import duckdb
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "figures"
DATA = Path(__file__).parent.parent / "output"
SIZES = ["100K", "500K", "1M"]
NL = {"100K": "$10^5$", "500K": "$5\\times10^5$", "1M": "$10^6$"}

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def plot_lifetime_vs_reposts():
    """hist2d: lifetime_norm vs total_reposts (log-log)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT lifetime_norm, total_reposts
            FROM '{DATA}/{s}/out_posts.parquet'
            WHERE total_reposts > 0 AND lifetime_norm > 0
            USING SAMPLE 50000
        """).df()
        x, y = df["total_reposts"].values, df["lifetime_norm"].values
        xbins = np.logspace(0, np.log10(max(x.max(), 10)), 40)
        ybins = np.logspace(0, np.log10(max(y.max(), 10)), 40)
        ax.hist2d(x, y, bins=[xbins, ybins], cmap="YlOrRd", norm="log")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("total_reposts"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("lifetime_norm (ticks)")
    fig.suptitle("Post lifetime vs repost count (sampled, log-log density)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s3_lifetime_vs_reposts.png", bbox_inches="tight")
    plt.close()


def plot_depth_vs_size():
    """hist2d: cascade_depth vs cascade_size."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT cascade_size, cascade_depth
            FROM '{DATA}/{s}/out_cascades.parquet'
            WHERE cascade_depth > 0
            USING SAMPLE 100000
        """).df()
        x, y = df["cascade_size"].values, df["cascade_depth"].values
        xbins = np.logspace(0, np.log10(max(x.max(), 10)), 40)
        ybins = np.linspace(0, max(y.max(), 10), 40)
        ax.hist2d(x, y, bins=[xbins, ybins], cmap="Blues", norm="log")
        ax.set_xscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("cascade_size"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_depth")
    fig.suptitle("Cascade depth vs size (sampled, log-x density)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_depth_vs_size.png", bbox_inches="tight")
    plt.close()


def plot_influencer_scatter():
    """hist2d: author_degree vs cascade_size (log-log)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT author_degree, cascade_size
            FROM '{DATA}/{s}/out_cascades.parquet'
            USING SAMPLE 100000
        """).df()
        x = df["author_degree"].values
        y = df["cascade_size"].values
        xbins = np.logspace(0, np.log10(max(max(x), 10)), 40)
        ybins = np.logspace(0, np.log10(max(y.max(), 10)), 40)
        ax.hist2d(x, y, bins=[xbins, ybins], cmap="YlOrRd", norm="log")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("author_degree"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_size")
    fig.suptitle("Influencer effect: author_degree vs cascade_size (sampled, log-log density)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_influencer_scatter.png", bbox_inches="tight")
    plt.close()


def plot_broadcast_vs_viral():
    """hist2d: max_out_degree vs cascade_depth."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        df = duckdb.sql(f"""
            SELECT max_out_degree, cascade_depth
            FROM '{DATA}/{s}/out_cascades.parquet'
            WHERE max_out_degree > 0
            USING SAMPLE 100000
        """).df()
        x = df["max_out_degree"].values
        y = df["cascade_depth"].values
        xbins = np.logspace(0, np.log10(max(max(x), 10)), 40)
        ybins = np.linspace(0, max(y.max(), 10), 40)
        ax.hist2d(x, y, bins=[xbins, ybins], cmap="Blues", norm="log")
        ax.set_xscale("log")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel("max_out_degree"); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("cascade_depth")
    fig.suptitle("Broadcast vs viral: max_out_degree vs cascade_depth (sampled, log-x density)")
    plt.tight_layout()
    fig.savefig(OUTPUT / "s4_broadcast_vs_viral.png", bbox_inches="tight")
    plt.close()


def plot_ccdf_panels(name, query, xlabel, suptitle, color="steelblue", sample=200000):
    """Generic log-log CCDF with 3 panels."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, s in zip(axes, SIZES):
        sql = query.format(DATA=DATA, s=s, sample=sample)
        vals = duckdb.sql(sql).df().iloc[:, 0].values
        if len(vals) == 0:
            continue
        srt = np.sort(vals)
        ccdf = 1.0 - np.arange(len(srt)) / len(srt)
        ax.loglog(srt, ccdf, ".", markersize=1.5, alpha=0.5, color=color)
        # Fit tail
        tail = srt >= np.percentile(srt, 80)
        if tail.sum() > 5:
            a, b = np.polyfit(np.log10(srt[tail]), np.log10(ccdf[tail]), 1)
            ax.loglog(srt[tail], 10**(a * np.log10(srt[tail]) + b), "r--", lw=1.5)
            ax.text(0.95, 0.15, f"α≈{-a:.1f}", transform=ax.transAxes,
                    ha="right", fontsize=9, color="red")
        ax.set_title(f"{NL[s]}")
        ax.set_xlabel(xlabel); ax.grid(True, alpha=0.3, which="both")
    axes[0].set_ylabel("P(X ≥ x)")
    fig.suptitle(suptitle)
    plt.tight_layout()
    fig.savefig(OUTPUT / f"{name}.png", bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    print("Fixing scatter plots...")
    plot_lifetime_vs_reposts()
    plot_depth_vs_size()
    plot_influencer_scatter()
    plot_broadcast_vs_viral()
    print("Regenerating CCDFs...")
    plot_ccdf_panels("s3_reposts_ccdf",
        "SELECT total_reposts FROM '{DATA}/{s}/out_posts.parquet' WHERE total_reposts>0 USING SAMPLE {sample}",
        "total_reposts", "CCDF of total_reposts (sampled)", "steelblue")
    plot_ccdf_panels("s3_lifetime_ccdf",
        "SELECT lifetime_norm FROM '{DATA}/{s}/out_posts.parquet' WHERE total_reposts>0 AND lifetime_norm>0 USING SAMPLE {sample}",
        "lifetime_norm", "CCDF of lifetime_norm (sampled)", "darkorange")
    plot_ccdf_panels("s4_cascade_size_ccdf",
        "SELECT cascade_size FROM '{DATA}/{s}/out_cascades.parquet' USING SAMPLE {sample}",
        "cascade_size", "CCDF of cascade_size (sampled)", "mediumseagreen")
    plot_ccdf_panels("s4_virality_ccdf",
        "SELECT struct_virality FROM '{DATA}/{s}/out_cascades.parquet' WHERE struct_virality>1.34 USING SAMPLE {sample}",
        "struct_virality ν", "CCDF of structural virality (sampled, ν > 1.34)", "darkviolet")
    print(f"Done → {OUTPUT}/")
