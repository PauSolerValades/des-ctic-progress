#!/usr/bin/env python3
"""Plot session-end backlog over time from a session trace.

Usage:
    uv run --with matplotlib,numpy backlog.py traces/session_trace.jsonl
    uv run --with matplotlib,numpy backlog.py traces/session_trace.jsonl -o backlog.png
"""

import argparse
import json
import os
import sys


def load_events(path: str) -> list[dict]:
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def main():
    parser = argparse.ArgumentParser(description="Plot session-end backlog")
    parser.add_argument("session_trace", type=str, help="Session trace JSONL")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output plot path")
    args = parser.parse_args()

    if not os.path.isfile(args.session_trace):
        print(f"Error: '{args.session_trace}' not found", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.session_trace))[0]
        args.output = f"{base}_backlog.png"

    events = load_events(args.session_trace)
    print(f"Loaded {len(events)} session events")

    times = []
    backlogs = []
    for e in events:
        if e["type"] == "end":
            bl = e.get("backlog")
            if bl is not None:
                times.append(e["time"])
                backlogs.append(bl)

    if not backlogs:
        print("No backlog data found (old trace, missing field?)")
        sys.exit(1)

    print(f"Session ends with backlog: {len(backlogs)}")
    print(f"Backlog range: {min(backlogs)} – {max(backlogs)}")
    print(f"Backlog mean:  {sum(backlogs)/len(backlogs):.1f}")

    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Top: scatter
    ax1.scatter(times, backlogs, s=1, alpha=0.3, color="blue")
    ax1.set_ylabel("Backlog at session end")
    ax1.grid(True, alpha=0.3)

    # Bottom: histogram
    ax2.hist(backlogs, bins=100, color="blue", alpha=0.7, edgecolor="black", linewidth=0.3)
    ax2.set_xlabel("Backlog size")
    ax2.set_ylabel("Frequency")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"Plot saved: {args.output}")


if __name__ == "__main__":
    main()
