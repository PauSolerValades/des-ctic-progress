# TODO — Remaining Processing

Status legend: ✅ done from existing parquets | 🔧 needs sessions.parquet | ⛔ needs Zig change (won't do)

---

## Stationary Behaviour ✅

- [x] Batch means of `avg_online_frac` → 100K: 11.54%, 500K: 12.56%, 1M: 11.33%
- [x] Batch means of `empty_timeline_pct` → 100K: 50.85%, 500K: 45.89%, 1M: 53.03%
- [x] Batch means of `median_backlog` → 100K: 0.03, 500K: 10.42, 1M: 0.00
- [x] Batch means of `gamma_reposts` → invariant at ~1.73 across all scales
- [ ] Histogram of `median_backlog` across runs (per size)
- [ ] Histogram of `empty_timeline_pct` across runs (per size)

## Queued Content Congestion

### From out_run_summary ✅
- [x] `median_backlog` batch means → done
- [ ] Histogram: how many users log in with queues at zero? → 🔧 needs per-user data
- [ ] How many times users left bored (no content)? → 🔧 needs session-level `empty_timeline_exit`
- [ ] Histogram of timeline backlog at session end across runs → 🔧 needs session-level

### From out_sessions.parquet ✅ (reprocessing now)
- [x] `n_actions` per session — implemented in sessions.py
- [x] `n_reposts` / `n_likes` / `n_ignores` per session — implemented
- [x] `empty_timeline_exit` flag — implemented
- [ ] Burstiness of actions within a session vs backlog — query from sessions
- [ ] Correlation: posts seen per session vs session duration — query from sessions
- [ ] QQ-plot: session duration distribution — query from sessions
- ⛔ Intended Pareto duration not in traces (needs Zig change)

## out_user_sessions.parquet 🔧
Can be derived from `out_sessions.parquet` via group_by, no reprocessing.

- [ ] Per-user: `n_sessions`, `total_online_time`, `mean_session_duration`
- [ ] Per-user: `pct_sessions_empty_exit` (boredom ratio)
- [ ] Per-user: `total_actions`, `total_reposts`, `total_posts_created`
- [ ] Variance across users: do some consistently starve while others thrive?
- [ ] Correlation: user repost frequency vs session duration

## Lifetimes and Scale ✅ (mostly)

- [x] Batch means of `gamma_reposts` → invariant ~1.73
- [x] `lifetime_raw` distribution (mean, median, percentiles) for posts with/without reposts
- [x] `lifetime_norm` (= lifetime_raw, since Δp=1)
- [x] `time_to_peak_50` distribution
- [x] `burstiness_B` distribution, mean=-0.16 to -0.21 (anti-bursty)
- [ ] Scatter plot: `lifetime_norm` vs `total_reposts` → need to generate
- [ ] Does a post need to get big to live long, or can small posts persist? → from scatter

### Add to out_posts.parquet 🔧
- [ ] `n_likes` — total likes per post
- [ ] `n_ignores` — total ignores per post  
- [ ] `n_impressions` — total timeline pops (= likes+reposts+ignores)

## Cascades Analysis

### Batch means ✅
- [x] Mean/median/max `cascade_size` across all runs → 5.3, 6.1, 6.3
- [x] Mean/median/max `cascade_depth` → 2.9, 3.3, 3.6
- [x] Mean/median/max `struct_virality` → 1.90, 2.05, 2.10
- [x] Mean/median/max `max_out_degree`
- [x] % viral (size ≥ 10): ~13.6% constant across scales
- [x] % viral (size ≥ 20): 1.0% → 3.3% → 3.9% (grows with scale)
- [x] % viral (size ≥ 50): 0.02% → 0.22% → 0.47%
- [x] % branching (max_out ≥ 2): 46% → 42% → 36% (DECREASES with scale!)
- [ ] Histograms per metric across runs → need per-run aggregation

### Depth vs size correlation ✅
- [x] Depth grows sub-linearly with cascade size
- [x] Size 3-9: depth 2.8, Size 50-99: depth 18.7, Size 500+: depth 47.7
- [x] Largest cascades branch wide, not deep (max_out=317 for 500+)

### Virality distribution ✅
- [x] 40% of cascades are minimal (ν ≤ 1.34 = pure chain)
- [x] Mean ν=2.1 overall, ν=4.4 for size≥10, ν=10.3 for size≥100
- [x] Virality distribution per size bucket → done
- [ ] For cascades with branching (max_out≥2): mean ν=2.6-2.9

### Influencer effect ✅
- [x] Author degree has NO effect on cascade metrics
- [x] Mean cascade_size: 5.21 (zero followers) vs 5.42 (10K+ followers)
- [x] All degree buckets have nearly identical depth, virality, max_out
- [ ] Gini coefficient of cascade sizes → not needed (no influencer effect to measure)

### Add to out_cascades.parquet 🔧
- [ ] `n_likes` — total likes per cascade
- [ ] `n_ignores` — total ignores per cascade
- [ ] `n_impressions` — total timeline pops

## Micro-Macro Coupling

### Pace ratio ρ ✅
- [x] ρ = inter_action_mean / inter_repost_mean = 0.012
- [x] Users interact 83× more often than they repost
- [x] Purely driven by p_repost=0.012

### Session persistence π
- [x] π = mean_post_lifetime / mean_session_duration
- [x] 1M: 1107/115 = 9.6, 500K: 984/129 = 7.6
- [x] Posts outlive sessions by 8-10×
- [ ] Batch means of π across all runs → ✅ sessions now available

### Saturation σ
- [x] σ = avg_time_between_reposts / mean_time_offline
- [x] 1M: mean offline gap = 450 ticks
- [x] σ << 1 → content arrives slower than users return → starvation
- [ ] Batch means of σ across all runs → ✅ sessions now available

---

## Pipeline additions needed

### out_sessions.parquet ✅ (implemented, running)
One row per session during steady state. Pipeline done.

### out_user_sessions.parquet 🔧
One row per user per run. Can be derived from `out_sessions.parquet` with
`group_by(sim_id, user_id).agg(...)` — no re-processing needed.

### Add columns to out_posts.parquet 🔧
- `n_likes` i64 — trivial groupby on action_trace
- `n_ignores` i64
- `n_impressions` i64

### Add columns to out_cascades.parquet 🔧
- `n_likes` i64 — same as above
- `n_ignores` i64
- `n_impressions` i64
