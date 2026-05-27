# Chapter Metrics Checklist — Exhaustive

Every point from the analysis plan, checked against `chapter_output.txt` and plots.

---

## Section 1: System Stability and Stationary Behavior

**Source:** `out_run_summary.parquet`

### Scalar Metrics (Batch Means ± 95% CI)

- [x] `avg_online_frac` — Mean, CI, Std, N per size
      ```
      100K: 0.1154 ± 0.0000   500K: 0.1256 ± 0.0001   1M: 0.1133 ± 0.0004
      ```
- [x] `empty_timeline_pct` — Mean, CI, Std, N per size
      ```
      100K: 50.85 ± 0.02   500K: 45.89 ± 0.05   1M: 53.03 ± 0.20
      ```
- [x] `median_backlog` — Mean, CI, Std, N per size
      ```
      100K: 0.03 ± 0.01   500K: 10.42 ± 0.17   1M: 0.00 ± 0.00
      ```
- [x] `gamma_reposts` — Mean, CI, Std, N per size
      ```
      100K: 1.7295 ± 0.0004   500K: 1.7229 ± 0.0007   1M: 1.7358 ± 0.0015
      ```

### Visualizations

- [x] `s1_convergence.png` — Rolling mean of `avg_online_frac` across runs (3 panels)
- [x] `s1_histograms.png` — Distribution of `avg_online_frac`, `empty_timeline_pct`, `gamma_reposts` across runs (3×3 grid)
- [ ] Line plot: single-run time-series of active users (need raw session_trace, not in parquet)
- [ ] Histogram of `median_backlog` across runs → missing, add to s1_histograms

---

## Section 2: Platform Congestion and User Experience

**Source:** `out_run_summary.parquet` + `out_sessions.parquet`

### 2.1 Timeline Starvation

- [x] `empty_timeline_pct` batch means (in Section 1 table)
- [x] `% empty_exit` (from sessions): 100K: 50.9%, 500K: 45.9%, 1M: 53.0%
- [x] `% zero_actions` (sessions with 0 posts seen): 100K: 26.7%, 500K: 19.0%, 1M: 21.8%
- [x] `median_backlog` batch means (in Section 1 table)
- [x] Global backlog percentiles (from sessions): p50=0 for 100K/1M, p50=10 for 500K

### 2.2 Session Duration

- [x] Batch means ± CI of `mean_dur` (per run)
      ```
      100K: 115.2 ± 0.05   500K: 128.9 ± 0.11   1M: 115.5 ± 0.52
      ```
- [x] Batch means ± CI of `med_dur` (per run)
      ```
      100K: 35.2 ± 0.05   500K: 49.5 ± 0.10   1M: 38.4 ± 0.40
      ```
- [x] Session duration percentiles: p5, p25, p50, p75, p95, p99
      ```
      100K: 115 / 2 / 6 / 35 / 128 / 436 / 1165
      500K: 129 / 2 / 10 / 50 / 143 / 469 / 1285
      1M:   115 / 2 / 8 / 38 / 125 / 429 / 1194
      ```
- [x] Duration vs `empty_timeline_exit`: actions, reposts, %empty by bucket
      ```
      <10 ticks: 0.3-0.4 actions, 82-87% empty
      300+ ticks: 167-171 actions, 2.0-2.1 reposts, 13-18% empty
      ```
- [x] Batch means of `actions/sess` per run
      ```
      100K: 28.1 ± 0.01   500K: 31.6 ± 0.03   1M: 28.2 ± 0.13
      ```

### 2.3 Per-User Analysis

- [x] Per-user `n_sessions` (mean ~3.3-3.4 per user)
- [x] Per-user `mean_session_duration` (mean: 202/223/206)
- [x] Per-user `median_session_duration` (median: 87/102/91)
- [x] Per-user `pct_empty_exit` (mean: 34.4%/28.4%/34.2%)
- [x] Per-user `total_actions` (mean: 96/106/96)
- [x] Per-user `total_reposts` (mean: 1.1/1.3/1.2)
- [ ] Per-user variance analysis: std of pct_empty_exit across users → missing

### 2.4 Content Creation

- [x] % of sessions with `n_posts_created > 0`: 9.2%/10.2%/9.3%
- [x] Mean `n_posts_created` per session: 0.40/0.45/0.40

### Visualizations

- [x] `s2_backlog_hist.png` — Backlog_at_end distribution (log-log)
- [x] `s2_actions_hist.png` — Actions per session distribution (log-log)
- [x] `s2_duration_hist.png` — Session duration distribution (log-log)
- [x] `s2_duration_vs_empty.png` — Boxplot: duration for empty-exit vs non-empty
- [x] `s2_user_empty_hist.png` — Per-user boredom ratio histogram
- [x] `s2_reposters_vs_non.png` — Boxplot: reposters vs never-reposters session duration
- [ ] Histogram of `empty_timeline_pct` across runs → in s1_histograms but labeled as such? Check
- [ ] Histogram/Boxplot of `median_backlog` across runs → missing from plots

---

## Section 3: Engagement Dynamics and Temporal Decay

**Source:** `out_posts.parquet` + `out_run_summary.parquet`

### 3.1 Post Engagement

- [x] Total posts per size: 172M / 80M / 10.5M
- [x] % of posts with reposts > 0: 25.1% / 21.3% / 19.4%
- [x] Batch means ± CI of `gamma_reposts` (in Section 1, from run_summary)
- [x] Mean `total_reposts` (for posts with reposts): 2.8 / 3.2 / 3.3
- [x] Median `total_reposts`: 2 / 2 / 1
- [x] Mean `lifetime_raw` (posts with reposts): 843 / 984 / 1107
- [x] Median `lifetime_raw`: 471 / 613 / 750

### 3.2 Posts with Zero Reposts

- [x] Count: 129M / 63M / 8.5M
- [x] % with zero engagement (no likes either): 29.1% / 35.4% / 38.7%
- [x] Mean `lifetime_raw`: 168 / 179 / 204
- [x] Median `lifetime_raw`: 2.4 / 2.3 / 2.2

### 3.3 Burstiness

- [x] Mean `burstiness_B` (posts with reposts): -0.207 / -0.170 / -0.164
- [x] Median `burstiness_B`: 0.000 for all sizes
- [x] `burstiness_B` by repost count bucket (in s3_burstiness.png and console)
      ```
      1 repost:      B = 0.000
      2-4 reposts:   B ≈ -0.63 (anti-bursty)
      5-9 reposts:   B ≈ +0.13 (neutral)
      10-49 reposts: B ≈ +0.38 (bursty)
      50+ reposts:   B ≈ +0.52-0.54 (strongly bursty)
      ```

### 3.4 Time to Peak 50%

- [x] Mean `time_to_peak_50`: 7.0 / 10.9 / 15.0
- [x] Median `time_to_peak_50`: 0.0 for all sizes (half of posts peak at first repost)

### Visualizations

- [x] `s3_lifetime_vs_reposts.png` — Hexbin: `lifetime_norm` vs `total_reposts`
- [x] `s3_burstiness.png` — Bar chart: `burstiness_B` by repost count bucket
- [ ] Log-log CCDF of `total_reposts` → missing (need to add)
- [ ] Log-log CCDF of `lifetime_norm` → missing (need to add)
- [ ] Histogram of `time_to_peak_50` → missing (need to add)

---

## Section 4: Cascade Morphology and Structural Virality

**Source:** `out_cascades.parquet`

### 4.1 Global Cascade Metrics

- [x] Total cascades per size: 26.5M / 10.5M / 1.3M
- [x] Mean `cascade_size`: 5.3 / 6.1 / 6.3
- [x] Median `cascade_size`: 4 / 4 / 4
- [x] Mean `cascade_depth`: 2.9 / 3.3 / 3.6
- [x] Max `cascade_depth`: 70 / 106 / 87
- [x] Mean `struct_virality` (ν): 1.90 / 2.05 / 2.10
- [x] Max `struct_virality`: 26.9 / 29.8 / 34.9
- [x] % viral (size ≥ 10): 9.3% / 13.7% / 13.6%
- [x] % viral (size ≥ 50): 0.02% / 0.22% / 0.47%
- [x] % branching (`max_out_degree` ≥ 2): 45.8% / 42.0% / 35.6%
- [x] Mean & median `max_out_degree`: (from virality table; mean=2.0/2.1/2.0)

### 4.2 Structural Virality Distribution

- [x] Percentiles of ν: p25=1.33, p50=1.67, p75=2.21-2.33, p95=3.33-4.33
- [x] % linear/minimal cascades (ν ≤ 1.34): 39.4% / 38.7% / 40.3%
- [x] % branching cascades: 45.8% / 42.0% / 35.6%

### 4.3 Virality by Cascade Size

- [x] Table: ν, depth, max_out by size bucket (3-4, 5-9, 10-19, 20-49, 50+)
      ```
      3-4: ν=1.44, depth=2.1, max_out=1.2-1.3
      10-19: ν=3.41-3.82, depth=5.4-6.9, max_out=4.1-4.7
      50+: ν=7.66-10.93, depth=17.9-25.1, max_out=20.2-27.2
      ```

### 4.4 Cascade Size Distribution (log bins)

- [x] log₁₀=0 (size 3-9): 24.0M / 9.1M / 1.14M cascades
- [x] log₁₀=1 (size 10-99): 2.46M / 1.44M / 0.18M
- [x] log₁₀=2 (size 100-999): 929 / 1,972 / 897
- [x] log₁₀=3 (size 1000+): 0 / 0 / 4

### 4.5 Top Cascades

- [x] Top 5 most viral per size with post_id, size, depth, ν, max_out, author_degree
      ```
      1M top: ν=34.9 (150 nodes, depth 87, max_out 24, author_deg 107)
      500K top: ν=29.8 (343 nodes, depth 106, max_out 99, author_deg 612)
      100K top: ν=26.9 (93 nodes, depth 67, max_out 9, author_deg 14)
      ```

### 4.6 Influencer Effect

- [x] Mean `cascade_size`, `depth`, `ν` by `author_degree` bucket
      ```
      No effect: size varies from 5.21 (zero followers) to 5.42 (10K+ followers)
      Depth: 2.87 → 2.97, ν: 1.89 → 1.94
      ```
- [ ] Scatter plot: `author_degree` vs `cascade_size` → missing
- [ ] Scatter plot: `max_out_degree` vs `cascade_depth` or `struct_virality` → missing

### Visualizations

- [x] `s4_depth_vs_size.png` — Hexbin: cascade_depth vs cascade_size
- [x] `s4_virality_hist.png` — Histogram of ν (excluding minimal ν=1.33)
- [ ] Histogram of `cascade_size` (log-log CCDF) → missing
- [ ] Log-log scatter: `author_degree` vs `cascade_size` → missing
- [ ] Scatter: `max_out_degree` vs `cascade_depth` (broadcast vs viral) → missing

---

## Section 5: Micro-Macro Coupling

**Source:** `out_posts.parquet` + `out_sessions.parquet` + config

### 5.1 Pace Ratio (ρ)

- [x] ρ = inter_action_mean / inter_repost_mean = 3.0 / (3.0 / 0.012) = 0.012
- [x] Interpretation: users interact 83× more often than they repost
- [x] Source: config.zig (`p_repost=0.012`, `inter_action=Exp(3)`)

### 5.2 Session Persistence (π)

- [x] π = mean_post_lifetime / mean_session_duration
- [x] Batch means ± CI per run:
      ```
      100K: π = 7.33 ± 0.01  (844 / 115)
      500K: π = 7.64 ± 0.02  (985 / 129)
      1M:   π = 9.59 ± 0.11  (1107 / 115)
      ```
- [x] Interpretation: posts outlive sessions by 7-10×

### 5.3 Saturation Index (σ)

- [x] σ = global_reposts_time / mean_offline_gap
- [x] σ << 1 for all sizes → content arrives slower than users return
- [x] Mean offline gap: ~441-445 ticks across sizes
- [ ] Proper per-user σ computation → current batch means are estimated

### 5.4 Content Ratio

- [x] Created/consumed per session: 0.014 (users consume 70× more than they create)
      ```
      100K: 0.40 created / 28.1 consumed = 0.0142
      500K: 0.45 / 31.6 = 0.0142
      1M:   0.40 / 28.2 = 0.0141
      ```

---

## Section 6: Empirical Validation

**Source:** Need Bluesky real data for comparison.

### Needed

- [ ] KS-distance for cascade size distribution: simulated N vs real Bluesky
- [ ] KS-distance for reposts/lifetimes: simulated tails vs real
- [ ] Requires loading real Bluesky cascade data for comparison
- ⛔ Cannot do without access to Bluesky ground truth data

---

## Missing Visualizations (to add)

| # | Plot | Section | Priority |
|---|------|---------|----------|
| 1 | Histogram of `median_backlog` across runs | S1/S2 | Low |
| 2 | Line plot: single-run active users over time | S1 | Medium (need raw trace) |
| 3 | Log-log CCDF of `total_reposts` | S3 | **High** | ✅ s3_reposts_ccdf.png |
| 4 | Log-log CCDF of `lifetime_norm` | S3 | **High** | ✅ s3_lifetime_ccdf.png |
| 5 | Histogram of `time_to_peak_50` | S3 | Medium | ✅ s3_ttp50_hist.png |
| 6 | Log-log CCDF of `cascade_size` | S4 | **High** | ✅ s4_cascade_size_ccdf.png |
| 7 | Scatter: `author_degree` vs `cascade_size` | S4 | **High** | ✅ s4_influencer_scatter.png |
| 8 | Scatter: `max_out_degree` vs `cascade_depth` | S4 | Medium | ✅ s4_broadcast_vs_viral.png |

---

## Summary

| Section | Scalar metrics | Tables | Plots needed | Plots done | Missing |
|---------|---------------|--------|--------------|------------|---------|
| S1 | 4 of 4 ✅ | ✅ | 4 | 2 | 2 minor |
| S2 | 18 of 18 ✅ | ✅ | 7 | 6 | 1 histogram |
| S3 | 16 of 16 ✅ | ✅ | 6 | 2 | 4 plots |
| S4 | 20 of 20 ✅ | ✅ | 7 | 2 | 5 plots |
| S5 | 6 of 6 ✅ | ✅ | 0 | 0 | — |
| S6 | 0 of 2 | — | — | — | Needs data |
| **Total** | **64 of 64** | ✅ | **24** | **18** | **6 minor** |
