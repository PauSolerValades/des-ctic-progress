# TODO — Remaining Work

## ✅ Done

- [x] Pipeline: JSONL traces → 4 Parquet tables per size (cascades, posts, sessions, summary)
- [x] `out_sessions.parquet` — per-session metrics (duration, actions, reposts, backlog, empty_exit)
- [x] `out_run_summary.parquet` — global batch-means per run
- [x] Section 1: Stationary behaviour — batch means, convergence, histograms
- [x] Section 2: Queued congestion — starvation, session duration, per-user boredom
- [x] Section 3: Lifetimes and scale — γ, lifetime distribution, burstiness
- [x] Section 4: Cascades — batch means, size distribution, influencer effect
- [x] Section 5: Micro-macro coupling — ρ, π, σ, content ratio
- [x] 12 figures in `analysis/output/`
- [x] `analysis/chapter_output.txt` — all tables

## 🔧 Still useful, low effort

- [ ] Add `n_likes`, `n_ignores`, `n_impressions` columns to `out_posts` and `out_cascades`
  → Trivial extra groupby in the pipeline; reprocess needed
- [ ] Per-run π and σ batch means (currently from sample runs; sessions table enables full batch)
- [ ] `out_user_sessions.parquet` — materialize per-user aggregation (can derive from sessions)

## ⛔ Cannot do without Zig changes

- [ ] Intended Pareto session duration in traces (not emitted by simulation)
