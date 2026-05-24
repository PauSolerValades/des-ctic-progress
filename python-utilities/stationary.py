#!/usr/bin/env python3
"""Compute and plot the % of users online over time from a session trace.

Detects when the simulation enters stationary state using rolling-window
convergence: the point where the rolling mean of the online fraction stops
trending and its variance stabilizes.

Usage:
    uv run --with matplotlib,numpy stationary.py traces/session_trace.jsonl
    uv run --with matplotlib,numpy stationary.py traces/session_trace.jsonl -o plot.png
"""

import argparse
import json
import os
import sys


def load_session_trace(path: str) -> list[dict]:
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def build_online_curve(events: list[dict], warmup: float = 1000) -> "tuple[list[float], list[float]]":
    """Return (times, online_fraction) sampled every 1 tick from warmup to t_max."""
    if not events:
        return [], []

    all_uids = {e["user_id"] for e in events}
    total_users = max(all_uids) + 1
    sorted_events = sorted(events, key=lambda e: e["time"])

    t_max = sorted_events[-1]["time"]
    if t_max <= warmup:
        return [], []

    times = []
    fractions = []
    online = 0
    ei = 0  # event index

    t = warmup
    while t <= t_max:
        # Advance through all events up to time t
        while ei < len(sorted_events) and sorted_events[ei]["time"] <= t:
            if sorted_events[ei]["type"] == "start":
                online += 1
            else:
                online -= 1
            ei += 1
        times.append(t)
        fractions.append(online / total_users)
        t += 1.0

    return times, fractions


def find_stationary(
    times: list[float],
    fractions: list[float],
    window: int = 0,
    threshold: float = 0.01,
) -> "float | None":
    """Return the time when online fraction enters stationary state.

    Stationary = within the window, (max - min) / mean < threshold (default 1%).
    window: number of ticks. If 0, defaults to 1% of the time span.
    """
    if len(times) < 50:
        return None

    if window == 0:
        window = max(50, len(times) // 100)  # 1% of time span in ticks

    if window >= len(times):
        return None

    # Find the first window where oscillation is < threshold of the mean
    for i in range(len(times) - window):
        chunk = fractions[i : i + window]
        avg = sum(chunk) / window
        if avg == 0:
            continue
        amplitude = max(chunk) - min(chunk)
        if amplitude / avg < threshold:
            return times[i + window // 2]

    return None


def plot_curve(
    times: list[float],
    fractions: list[float],
    stationary_time: "float | None",
    output: str,
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(times, fractions, linewidth=0.5, alpha=0.7, label="Online %")
    ax.set_ylabel("Fraction online")
    ax.set_xlabel("Time")
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    window = min(1000, max(len(times) // 20, 1))
    if window > 1 and len(times) >= window:
        rolling = np.convolve(fractions, np.ones(window) / window, mode="valid")
        roll_times = times[window // 2 : window // 2 + len(rolling)]
        ax.plot(roll_times, rolling, "r-", linewidth=1.5, label=f"Rolling mean (w={window})")

    if stationary_time is not None:
        ax.axvline(stationary_time, color="green", linestyle="--", linewidth=2,
                    label=f"Stationary @ t={stationary_time:.0f}")
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    print(f"Plot saved: {output}")


def main():
    parser = argparse.ArgumentParser(description="Stationary state detector")
    parser.add_argument("session_trace", type=str, help="Session trace JSONL")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output plot path")
    parser.add_argument("-w", "--window", type=int, default=0, help="Rolling window in ticks (default: 1%% of span)")
    parser.add_argument("--warmup", type=float, default=1000.0, help="Warmup time (default: 1000)")
    args = parser.parse_args()

    if not os.path.isfile(args.session_trace):
        print(f"Error: '{args.session_trace}' not found", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.session_trace))[0]
        args.output = f"{base}_stationary.png"

    events = load_session_trace(args.session_trace)
    print(f"Loaded {len(events)} session events")

    times, fractions = build_online_curve(events, warmup=args.warmup)
    print(f"Time range: {times[0]:.0f} – {times[-1]:.0f}")

    # Rough check: total users
    all_uids = {e["user_id"] for e in events}
    total_users = max(all_uids) + 1
    print(f"Total users: {total_users}")

    # Average online fraction over the whole run
    avg_online = sum(fractions) / len(fractions)
    print(f"Avg online fraction: {avg_online:.4f} ({avg_online * 100:.1f}%)")

    stime = find_stationary(times, fractions, window=args.window)
    if stime is not None:
        print(f"Stationary state reached at t ≈ {stime:.0f}")
    else:
        print("Stationary state NOT reached — simulation may be too short")

    plot_curve(times, fractions, stime, args.output)


if __name__ == "__main__":
    main()
