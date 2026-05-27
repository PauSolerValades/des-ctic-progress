# Results — CTIC Simulation Trace Analysis

All numbers are from the existing `output/{size}/out_*.parquet` files.
No re-processing needed.

---

## 1. Stationary Behaviour

Batch means across all runs for each network size.

| Metric | 100K (n=1600) | 500K (n=136) | 1M (n=10) |
|--------|---------------|--------------|-----------|
| avg_online_frac | 11.54% ± 0.10% | **12.56%** ± 0.06% | 11.33% ± 0.07% |
| empty_timeline_pct | 50.85% ± 0.41% | **45.89%** ± 0.29% | 53.03% ± 0.33% |
| median_backlog | 0.03 ± 0.23 | **10.42** ± 1.00 | 0.00 ± 0.00 |
| γ_reposts | 1.729 ± 0.009 | 1.723 ± 0.004 | 1.736 ± 0.002 |

**Interpretation:**
- **500K is the healthiest**: highest online fraction, lowest empty timeline %, non-zero backlog.
- **γ is scale-invariant** (~1.73). The power-law exponent of repost cascades is a fundamental property of the model + policy weights, not the network size.
- std decreases with more runs (1600 at 100K → γ CI is tightest).
- All three show severe content starvation: ~50% of sessions end with empty timeline.

---

## 2. Cascade Morphology

### 2.1 Overall cascade stats

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| Total cascades (N≥3) | 26.5M | 10.5M | 1.3M |
| Mean cascade_size | 5.3 | 6.1 | 6.3 |
| Median cascade_size | 4 | 4 | 4 |
| Max cascade_size | 217 | 953 | 1632 |
| Mean depth | 2.9 | 3.3 | 3.6 |
| Max depth | 70 | 106 | 87 |
| Mean virality (ν) | 1.90 | 2.05 | 2.10 |
| Max virality | 26.9 | 29.8 | 34.9 |
| % branching | 45.8% | 42.0% | 35.6% |

### 2.2 Viral post percentages (batch means)

| Threshold | 100K | 500K | 1M |
|-----------|------|------|-----|
| % with size ≥ 10 | 13.6% | 13.7% | 13.6% |
| % with size ≥ 20 | 1.0% | 3.3% | 3.9% |
| % with size ≥ 50 | 0.02% | 0.22% | 0.47% |

**Interpretation:**
- The percentage of viral cascades (size ≥ 10) is constant at ~13.6% across scales.
- BUT the tail gets fatter with network size: size≥50 goes from 0.02% → 0.22% → 0.47%.
- Larger networks enable larger maximum cascades (217 → 953 → 1632) because there are more users to propagate through.
- ~55-64% of cascades have NO branching (max_out_degree=1): most are linear chains.

### 2.3 Cascade size distribution (log bins)

| log₁₀(size) | 100K | 500K | 1M |
|-------------|------|------|-----|
| 0 (3-9) | 86.4% | 86.3% | 86.4% |
| 1 (10-99) | 13.6% | 13.7% | 13.6% |
| 2 (100-999) | 0.02% | 0.02% | 0.07% |
| 3 (1000+) | 0% | 0% | 0.0003% |

### 2.4 Depth vs size (1M sample)

| Size bucket | N cascades | Mean depth | Mean virality | Mean max_out |
|-------------|-----------|------------|---------------|-------------|
| 3-9 | 1,137,600 | 2.8 | 1.7 | 1.4 |
| 10-49 | 173,457 | 7.9 | 4.3 | 5.5 |
| 50-99 | 5,297 | 18.7 | 8.1 | 22.3 |
| 100-499 | 878 | 28.4 | 10.3 | 49.6 |
| 500+ | 23 | 47.7 | 9.8 | 317.2 |

**Depth grows sub-linearly with size.** The largest cascades (500+ nodes) have depth ~48 hops but max_out_degree of 317 — they are wide-branching, not deep.

---

## 3. Post Lifetimes

### 3.1 Posts with reposts > 0

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| % of all posts | 25.1% | 21.3% | 19.4% |
| Mean reposts | 2.8 | 3.2 | 3.3 |
| Median reposts | 2 | 2 | 1 |
| Mean lifetime_raw | 843 | 984 | 1107 |
| Median lifetime_raw | — | 613 | 750 |
| Mean burstiness_B | -0.207 | -0.170 | -0.164 |
| Mean time_to_peak_50 | 7.0 | 10.9 | 15.0 |

### 3.2 Posts with 0 reposts

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| Count | 129M | 62.8M | 8.5M |
| Mean lifetime | 168 | 179 | 204 |
| Median lifetime | 2.4 | 2.3 | 2.2 |
| % zero engagement | 29.1% | 35.4% | 38.7% |

**Interpretation:**
- Only 19-25% of posts get any reposts. 75-80% die alone.
- Of those that get 0 reposts, 29-39% get NO engagement at all (not even a like). They're created and instantly forgotten.
- Burstiness is negative on average (-0.16 to -0.21): reposts tend to be spread out rather than clustered.
- time_to_peak_50 is very small (7-15 ticks) because most cascades are small — the first repost often IS the 50% mark.
- Larger networks have longer mean lifetimes (843→984→1107) — content survives longer when there are more users to see it.

---

## 4. Influencer Effect (Author Degree vs Cascade)

Cascade metrics are **nearly identical across all author degree buckets**:

| Degree bucket | Mean size (100K) | Mean depth (100K) | Mean virality (100K) |
|---------------|-----------------|------------------|---------------------|
| zero | 5.21 | 2.87 | 1.89 |
| 1-9 | 5.27 | 2.90 | 1.91 |
| 10-99 | 5.29 | 2.91 | 1.91 |
| 100-999 | 5.24 | 2.89 | 1.90 |
| 1K-10K | 5.26 | 2.89 | 1.90 |
| 10K+ | 5.42 | 2.97 | 1.94 |

**The "influencer effect" is nearly zero.** A post from a user with 10K+ followers has mean cascade_size=5.42 vs 5.21 for a zero-follower user. The cascade doesn't care who started it — it only cares about the repost probability (p=0.012) of whoever encounters it downstream.

This is expected: the simulation uses homogeneous behavioral policies for all users. The initial follower count gives a larger first-hop audience, but with p_repost=0.012, only ~1.2% of those followers will repost. The cascade dies or lives based on the subsequent propagation structure, not the seed.

---

## 5. Micro-Macro Coupling Ratios

### 5.1 Pace ratio ρ = inter_action_mean / inter_repost_mean

```
ρ = 3.0 / (3.0 / 0.012) = 0.012
```

Users interact 83× more frequently than they repost. This is purely a consequence of the policy weights: p_repost=0.012 means one repost per ~83 timeline encounters.

### 5.2 Session persistence π = mean_post_lifetime / mean_online_per_session

| Network | Mean post lifetime | Mean session duration | π |
|---------|-------------------|-----------------------|---|
| 1M (1 run) | 1107 | 115 | 9.6 |
| 500K (1 run) | 984 | 129 | 7.6 |

**Posts outlive sessions by 8-10×.** A user logs in, scrolls for ~2 minutes, logs out — but the post they just liked continues getting engagement for ~16-18 more minutes. Content has inertia that sessions don't.

### 5.3 Saturation σ = avg_time_between_reposts / mean_time_offline

Computing correctly requires session-level data (offline gaps). From sample run:

| Network | Mean offline gap | 
|---------|-----------------|
| 1M | 450 ticks |
| 500K | 454 ticks |

Global repost rate is very sparse (0.012 per action × 3 ticks per action = one repost per ~250 ticks per online user). With only ~11% of users online, the global inter-repost interval is much larger than the offline gap. **σ << 1**: content arrives slower than users return → starvation.

---

## 6. Key Takeaways

1. **The simulation is content-starved at all network sizes.** ~50% of sessions end with empty timeline. 23% of sessions have zero actions. The boredom mechanism (exit on empty timeline) dominates session termination.

2. **γ ≈ 1.73 is a universal constant** of this model configuration. It's independent of network size, number of runs, and sampling variance.

3. **Cascades are mostly linear chains** (55-64% have no branching). The policy (p_repost=0.012) makes each repost a rare, isolated event.

4. **There is no influencer effect.** Author follower count matters for the first hop only; downstream propagation is driven by reposters' behavior, which is homogeneous.

5. **500K is the healthiest network size** — highest engagement, lowest starvation. Both 100K (too little content) and 1M (content dilution) perform worse.

6. **Posts outlive sessions by 8-10×.** Content persists far longer than individual user attention spans.
