# Simulation Audit: Key Findings & Open Questions

## 1. Configuration Discovery

The actual config used by the simulation is `release-v4/src/config.zig`, NOT
`release-v4/simconfs/all1.json` (which was a stale test file).

| Parameter | all1.json (stale) | config.zig (actual) |
|-----------|-------------------|---------------------|
| p_ignore | 0.50 | **0.80** |
| p_like | 0.30 | **0.188** |
| p_repost | 0.20 | **0.012** |
| inter_action | Exp(3.0) | Exp(3.0) ✓ |
| session_duration | Exp(60) | **Pareto(shape, scale) per user** |

The Pareto parameters are in `release-v4/params/session_duration_params.txt`
(one `shape scale` pair per user, fitted from real Bluesky session data).

## 2. Session Duration Analysis

### Raw Measurements (1M network, 1 run sample)

| Metric | Zero-backlog sessions | Non-zero-backlog sessions |
|--------|----------------------|--------------------------|
| Count | 1,201,085 (53.4%) | 1,049,462 (46.6%) |
| Mean duration | 56 ticks | 183 ticks |
| Median duration | 12 ticks | 105 ticks |
| Ratio | 1.0× | **3.28× longer** |

### Duration distribution (all sessions)

| Range | Count | % | Mean backlog at end | % zero-backlog |
|-------|-------|---|---------------------|----------------|
| <10 ticks | 653,130 | 29.0% | 124.6 | 85.3% |
| 10-60 | 664,563 | 29.5% | 403.8 | 63.0% |
| 60-300 | 740,166 | 32.9% | 1204.4 | 25.7% |
| 300-1000 | 162,749 | 7.2% | 2238.2 | 16.7% |
| 1000+ | 29,939 | 1.3% | 3425.2 | 29.3% |

### Key findings

1. **The boredom mechanism dominates session termination**: 53% of sessions
   end with backlog=0, and those sessions are 3× shorter (median 12 vs 105 ticks).
   The intended Pareto session duration is being overridden by empty-timeline exit.

2. **Backlog at session start is always 0** (timelines are cleared on offline).
   This means every new session starts with an empty feed. The user must wait
   for content to arrive via propagation — in the first few ticks they have
   nothing to consume, making early session exit almost guaranteed.

3. **Long sessions correlate with content availability**: sessions lasting
   60-300 ticks have only 26% zero-backlog, compared to 85% for <10-tick sessions.
   When content is flowing, users stay engaged.

4. **500K is healthier than 1M**: median duration 50 vs 38, zero-backlog 46% vs 53%.
   Fewer users → more content per user → less starvation → longer sessions.

### 3. Cascade Virality vs Real Data

| Metric | 1M | 500K |
|--------|-----|------|
| Mean virality (all) | 2.10 | 2.05 |
| Mean virality (size ≥ 10) | 4.42 | 3.99 |
| Mean virality (branching) | 2.89 | 2.64 |
| Top virality | 34.9 | 29.8 |
| % minimal (ν ≤ 1.34) | 40.3% | 38.7% |
| % with any branching | 35.6% | 42.0% |
| γ_reposts | 1.736 | 1.723 |

The virality numbers are a consequence of p_repost = 0.012:
- Only 1.2% of timeline encounters result in a repost
- 80% are ignored, 18.8% are likes
- Cascades are mostly linear chains (40% are pure chains with no branching)
- The few branching cascades (35% of total) have mean ν ≈ 2.6-2.9

With 0.012 repost probability and ~20% of posts getting any reposts, the
effective branching factor is very low.

## 4. Open Questions to Investigate

### Q1: How does the boredom mechanism shift session durations?
- Compare actual session durations against the intended Pareto distribution
- Plot a QQ-plot: intended Pareto durations vs actual durations
- Compute what fraction of sessions are "prematurely terminated" (ended by
  boredom rather than the scheduled Pareto duration)
- For each user, the Pareto(s, k) was sampled at session start. We don't have
  the scheduled duration in traces. But we can infer: if actual duration <
  typical Pareto durations for that user, boredom killed it.

### Q2: How many posts does a user see per session?
- Each action (ignore/like/repost) = one post popped from the timeline
- Count actions per user per session (between session start/end events)

**Results (sample of 500 users, 1761 sessions, 1M network):**

| Duration | Sessions | Posts/mean | Posts/med | % zero actions |
|----------|----------|------------|-----------|----------------|
| <10 ticks | 505 | 0.4 | 0 | 73% |
| 10-60 | 541 | 6.1 | 5 | 5% |
| 60-300 | 562 | 33.4 | 30 | 0% |
| 300+ | 153 | 188.9 | 128 | 0% |

| Backlog | Sessions | Posts/mean | Posts/med | Duration/med |
|---------|----------|------------|-----------|-------------|
| bl=0 | 1015 (58%) | 13.9 | 2 | 12 ticks |
| bl>0 | 746 (42%) | 49.6 | 28 | 114 ticks |

**Key findings:**
- **23% of sessions have ZERO actions**: the user comes online and
  immediately goes offline because their timeline is empty.
- Another 7% have exactly 1 action. Combined: 30% see ≤1 post.
- **73% of sessions under 10 ticks have zero actions** — these sessions
  should never have started (no content available).
- Sessions with backlog>0 at end see 3.6× more posts (50 vs 14) and
  last 9.5× longer (114 vs 12 ticks).
- The median session with bl=0 sees only 2 posts total. That's extreme
  content starvation: users log in, see 1-2 posts, and bounce.

### Q3: Is timeline clearing correct?
- The design doc says timelines are cleared on offline
- But in real life, timelines persist across sessions
- This amplifies starvation: every session starts empty
- What if timelines were NOT cleared?

### Q4: Does the 0.012 repost probability match real Bluesky data?
- Need to compare with the calibration data used to fit the categorical
- If real data shows higher repost rates, the policy weights may need
  recalibration

### Q5: Network size scaling — cross-size comparison

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| Runs | 1600 | 136 | 10 |
| avg_online_frac | 11.54% ± 0.10% | **12.56% ± 0.06%** | 11.33% ± 0.07% |
| median_backlog | 0 | **10** | 0 |
| empty_timeline_pct | 50.9% ± 0.4% | **45.9% ± 0.3%** | 53.0% ± 0.3% |
| γ_reposts | 1.730 ± 0.009 | 1.723 ± 0.004 | 1.736 ± 0.002 |
| Posts with reposts | **25.1%** | 21.3% | 19.4% |
| Cascade max depth | 70 | 106 | 87 |
| Cascade max size | 217 | 953 | 1632 |
| Cascade mean virality | 1.90 | 2.05 | 2.10 |

**500K is the Goldilocks zone.** It has the highest online fraction,
lowest empty timeline percentage, and non-zero median backlog. Users
stay engaged because content is abundant enough.

**Both extremes suffer:**
- **100K**: Absolute content volume is too low. Even though per-post
  engagement is highest (25% get reposts), each user's feed runs dry
  because there simply aren't enough posts being created.
- **1M**: Content dilution. Same total creation rate spread over 10×
  more consumers = each user sees less. The largest cascades exist
  (max size 1632) but they're rare and don't help the median user.

**γ is an invariant** (~1.72-1.74). The power-law exponent of repost
cascades is a fundamental property of the CTIC model and the policy
weights, independent of network size. Variance decreases with more
runs (1600 runs at 100K gives tighter CI).
