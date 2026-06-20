"""Section 1: Stationary Behaviour — Batch means of global metrics."""
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUT = Path(__file__).parent / "figures"
OUTPUT.mkdir(exist_ok=True)
DATA = Path(__file__).parent.parent / "output"
SIZES = ["100K", "500K", "1M"]
NETWORK_LABEL = {"100K": "$10^5$", "500K": "$5\\times10^5$", "1M": "$10^6$"}

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def load():
    return {s: pl.read_parquet(DATA / s / "out_run_summary.parquet") for s in SIZES}


def table_batch_means(ss):
    for col, label in [
        ("avg_online_frac", "avg_online_frac"),
        ("empty_timeline_pct", "empty_timeline_pct"),
        ("median_backlog", "median_backlog"),
        ("gamma_reposts", "gamma_reposts"),
    ]:
        print(f"\n  {label}:")
        print(f"  {'Size':<8} {'Mean':>10} {'±CI95':>10} {'Std':>10} {'N':>6}")
        for s in SIZES:
            vals = ss[s][col].to_numpy()
            mu = vals.mean()
            ci = 1.96 * vals.std(ddof=1) / np.sqrt(len(vals))
            print(f"  {s:<8} {mu:>10.4f} {ci:>10.4f} {vals.std(ddof=1):>10.4f} {len(vals):>6}")


def plot_convergence(ss):
    for s in SIZES:
        fig, ax = plt.subplots(figsize=(7, 4))
        vals = ss[s]["avg_online_frac"].to_numpy()
        rolling = np.cumsum(vals) / np.arange(1, len(vals) + 1)
        ax.plot(rolling, lw=0.8, color="steelblue")
        ax.axhline(vals.mean(), color="crimson", ls="--", lw=1,
                   label=f"μ = {vals.mean():.4f}")
        ax.set_title(f"Convergence — {NETWORK_LABEL[s]} (n={len(vals)})")
        ax.set_xlabel("Run"); ax.set_ylabel("avg_online_frac")
        ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(OUTPUT / f"s1_convergence_{s}.png", bbox_inches="tight")
        plt.close(fig)


def plot_histograms(ss):
    metrics = [
        ("avg_online_frac", "Average Online Fraction"),
        ("empty_timeline_pct", "Empty Timeline %"),
        ("gamma_reposts", "γ (reposts)"),
    ]
    for s in SIZES:
        fig, axes = plt.subplots(len(metrics), 1, figsize=(7, 8), sharex=False)
        for ax, (col, title) in zip(axes, metrics):
            vals = ss[s][col].to_numpy()
            ax.hist(vals, bins=min(50, len(vals)//5), color="steelblue",
                    edgecolor="white", alpha=0.8)
            ax.axvline(vals.mean(), color="crimson", ls="--", lw=1.5)
            ax.set_ylabel(title, fontsize=10)
            ax.grid(True, alpha=0.3)
        axes[-1].set_xlabel("Value")
        fig.suptitle(f"Histograms — {NETWORK_LABEL[s]} (n={len(ss[s])})", fontsize=12)
        fig.tight_layout()
        fig.savefig(OUTPUT / f"s1_histograms_{s}.png", bbox_inches="tight")
        plt.close(fig)


def main():
    ss = load()
    print("=== 1.1 Batch means ± CI95 ===")
    table_batch_means(ss)
    print("\n=== 1.2 Convergence plot → s1_convergence.png ===")
    plot_convergence(ss)
    print("=== 1.3 Histograms → s1_histograms.png ===")
    plot_histograms(ss)
    print("Done.")


if __name__ == "__main__":
    main()
