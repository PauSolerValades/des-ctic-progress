# Trace Analysis — CTIC Simulation Metric Pipeline

Parses discrete-event simulation trace files (JSONL) and produces three Parquet tables for statistical analysis.

## Input

```
release-v4/traces/{SIZE}/{BATCH}/{run_id}/
    ├── action_trace.jsonl      # user → (ignore|like|repost) on a post
    ├── create_trace.jsonl      # post creation events
    ├── session_trace.jsonl     # user online/offline transitions
    └── propagate_trace.jsonl   # post delivery to follower timelines

release-v4/data/{SIZE}/network.bin   # follower graph (binary)
```

### Trace file schemas

All traces share a common preamble: `time`, `event_id`, `gen_id`, `user_id`.

| File | Extra fields | Description |
|------|-------------|-------------|
| `action_trace.jsonl` | `post_id` (i64), `type` (str: ignore/like/repost) | Timeline interactions |
| `create_trace.jsonl` | `post_id` (i64) | Post authorship |
| `session_trace.jsonl` | `type` (str: start/end), `backlog` (i64) | User connectivity |
| `propagate_trace.jsonl` | `type` (i64 = post_id being propagated) | Diffusion delivery to followers |

### Network binary format (`network.bin`)

Little-endian u32, no header:
- `num_users` (u32)
- `user_ids[num_users]` — internal ID → Bluesky parquet int_id mapping
- `num_edges` (u32)
- `edges[num_edges × 2]` — `(actor_id, subject_id)` interleaved, using parquet int_ids

## Output

Three Parquet files per dataset size, written to `output/{SIZE}/`:

### `out_cascades.parquet` — Cascade Morphology

One row per post with cascade size N ≥ 3 (≥2 reposts). Only steady-state created posts are included (t ≥ 1000).

| Column | Type | Description |
|--------|------|-------------|
| `sim_id` | str | Unique simulation replication ID |
| `post_id` | i64 | Origin post identifier |
| `author_degree` | i64 | Follower count (in-degree) of the post's author |
| `cascade_size` | i64 | Nodes in cascade tree (author + distinct reposters) |
| `cascade_depth` | i64 | Longest path from root to leaf in propagation tree |
| `struct_virality` | f64 | Wiener index normalized as average pairwise distance (ν) |
| `max_out_degree` | i64 | Max direct children for any node in the tree |

### `out_posts.parquet` — Post Lifetimes & Reposts

One row per post created during steady state.

| Column | Type | Description |
|--------|------|-------------|
| `sim_id` | str | Simulation replication ID |
| `post_id` | i64 | Post identifier |
| `total_reposts` | i64 | Number of reposts |
| `lifetime_raw` | f64 | Time from creation to last engagement (ticks) |
| `lifetime_norm` | f64 | `lifetime_raw / Δp` (Δp = 1.0, so same as raw) |
| `time_to_peak_50` | f64 | Time from first repost until 50% of total reposts |
| `burstiness_B` | f64 | Burstiness parameter B ∈ [-1, 1] from inter-repost times |

### `out_run_summary.parquet` — Global Run Summary

One row per simulation replication.

| Column | Type | Description |
|--------|------|-------------|
| `sim_id` | str | Simulation replication ID |
| `network_size` | i64 | Total agents in topology |
| `avg_online_frac` | f64 | Stationary average % users online (sweep-line integration) |
| `median_backlog` | f64 | Median unread items at session end |
| `empty_timeline_pct` | f64 | % of sessions ending with zero backlog |
| `gamma_reposts` | f64 | Power-law exponent γ (MLE, discrete, Clauset et al.) |

## Processing Pipeline

```
trace files (JSONL)                     network.bin
       │                                      │
       ▼                                      ▼
  polars DataFrame                    in-degree map
  (7.6M rows/run)                    {internal_id: followers}
       │                                      │
       ├──► cascades.py ───► batch tree reconstruction
       │         │              - repost_by_post + prop_by_post
       │         │              - parent matching (most recent propagator)
       │         │              - BFS depth, post-order Wiener index
       │         ▼
       │    out_cascades.parquet
       │
       ├──► posts.py ──────► vectorized aggregations + per-post metrics
       │         │              - Polars groupby for repost counts & times
       │         │              - time_to_peak_50 & burstiness_B (Python UDF)
       │         ▼
       │    out_posts.parquet
       │
       └──► summary.py ────► run-level aggregation
                 │              - sweep-line online fraction
                 │              - median backlog & empty timeline %
                 │              - power-law MLE (Clauset-Shalizi-Newman)
                 ▼
            out_run_summary.parquet
```

### Key design decisions

1. **Steady-state only**: All events before t=1000 (warmup phase) are excluded from metrics. Posts created during warmup that get reposts in steady state DO appear in cascades (their author is resolved from the full create trace), but warmup propagations are excluded.

2. **Batch cascade reconstruction**: Instead of filtering DataFrames per post (O(N×P)), reposts and propagates are grouped into Python dicts in a single pass, then trees are built by walking sorted lists in tandem.

3. **Two-level author-degree lookup**: Simulation traces use internal IDs (0..N-1). The network.bin stores edges with Bluesky parquet int_ids. The `user_ids` array maps internal→parquet, then indegree is looked up by parquet ID. Both maps are built once per network size and cached.

4. **Power-law fitting**: Uses the discrete MLE estimator from Clauset, Shalizi & Newman (2009): γ̂ = 1 + n / Σ ln(xᵢ / (x_min − 0.5)). Applied to the per-run `total_reposts` distribution with x_min = 1.

5. **Memory efficiency**: Each run's traces (~9M rows for 100K) are processed independently and concatenated. The network.bin edge list (120M edges) is read with numpy to avoid Python-level materialization, yielding a compact {user: followers} dict in ~1s.

## Usage

```bash
# Process a single dataset size
python main.py --traces ../release-v4/traces --size 100K

# Process all sizes (single process)
python main.py --traces ../release-v4/traces

# Parallel — three separate processes:
python -u main.py --traces ../release-v4/traces --size 100K > output/run_100K.log 2>&1 &
python -u main.py --traces ../release-v4/traces --size 500K > output/run_500K.log 2>&1 &
python -u main.py --traces ../release-v4/traces --size 1M  > output/run_1M.log  2>&1 &

# Test with first 5 runs
python main.py --traces ../release-v4/traces --size 100K --limit 5

# Dry run (list what would be processed)
python main.py --traces ../release-v4/traces --size 100K --dry-run
```

### Dependencies

```
polars>=1.0
pyarrow>=14.0
numpy>=1.24
```

Managed with `uv` via `pyproject.toml`.

## Directory Layout

```
trace-analysis/
├── main.py                      # CLI entry point
├── pyproject.toml               # uv project manifest
├── README.md                    # This file
├── trace_analysis/
│   ├── __init__.py
│   ├── cascades.py              # Cascade morphology (Table 1)
│   ├── network.py               # network.bin → in-degree lookup
│   ├── posts.py                 # Post lifetimes (Table 2)
│   ├── runner.py                # Per-run orchestration
│   └── summary.py               # Run summary (Table 3)
└── output/
    ├── 100K/
    │   ├── out_cascades.parquet
    │   ├── out_posts.parquet
    │   └── out_run_summary.parquet
    ├── 500K/
    │   └── ...
    └── 1M/
        └── ...
```
