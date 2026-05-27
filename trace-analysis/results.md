# CTIC Simulation — Results

## 1. Stationary Behaviour

Batch means across all replications. Values shown as mean ± 1 std.

| Metric | 100K (n=1600) | 500K (n=136) | 1M (n=10) |
|--------|---------------|--------------|-----------|
| avg_online_frac | 11.54% ± 0.10% | **12.56%** ± 0.06% | 11.33% ± 0.07% |
| empty_timeline_pct | 50.85% ± 0.41% | **45.89%** ± 0.29% | 53.03% ± 0.33% |
| median_backlog | 0.03 ± 0.23 | **10.42** ± 1.00 | 0.00 ± 0.00 |
| γ_reposts | 1.729 ± 0.009 | 1.723 ± 0.004 | 1.736 ± 0.002 |

**Interpretation:**

— **500K is the healthiest network size** across every metric. Highest online
  fraction, lowest empty-timeline rate, and the only size with non-zero median
  backlog. This is the Goldilocks zone where content production and consumption
  are balanced.

— **1M is the worst**: half-empty median backlog, 53% of sessions end bored.
  Content gets diluted across too many users. Despite having the largest
  absolute cascades (max size 1632), the *median* user experience is worse.

— **100K sits in between**: slightly better than 1M but worse than 500K. The
  network is too small to generate enough content volume. The interleaving of
  posts from different users is sparser — fewer sources means fewer opportunities
  for a user's timeline to be filled by the time they log in.

— **γ is an invariant of the model**: 1.72–1.74 across all scales. The power-law
  exponent of repost cascades is a fundamental property determined by the policy
  weights and the propagation delay, not by network size.

— **Variance scales with runs**: 100K has 1600 runs → tightest CI on most metrics.
  1M has only 10 runs → wider uncertainty. But γ variance actually decreases with
  larger networks because the distribution is sampled from more nodes.

---

## 2. Cascade Morphology

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| Total cascades | 26.5M | 10.5M | 1.3M |
| Per run | 16,558 | 77,380 | 131,726 |
| Mean cascade_size | 5.3 | 6.1 | 6.3 |
| Median cascade_size | 4 | 4 | 4 |
| Max cascade_size | 217 | 953 | 1,632 |
| Mean depth | 2.88 | 3.31 | 3.55 |
| Max depth | 70 | 106 | 87 |
| Mean virality | 1.90 | 2.05 | 2.10 |
| Max virality | 26.9 | 29.8 | 34.9 |
| % viral (size ≥ 10) | 12.8% | 13.7% | 13.6% |
| % viral (size ≥ 20) | 1.0% | 3.3% | 3.9% |
| % viral (size ≥ 50) | 0.02% | 0.22% | 0.47% |
| % with branching (max_out ≥ 2) | 45.8% | 42.0% | 35.6% |
| Mean max_out_degree | 2.1 | 2.1 | 2.0 |

**Interpretation:**

— **The median cascade is tiny**: size=4 nodes (author + 3 reposters) across all
  network sizes. 87% of cascades never reach size 10. Viral events are rare.

— **Bigger networks enable bigger cascades**: max cascade size grows from 217
  (100K) to 1,632 (1M). The long tail is real — larger populations allow
  information to spread further when it does go viral. But these are extreme
  outliers, not typical behavior.

— **Branching DECREASES with network size**: 100K has 45.8% of cascades with
  any branching vs 35.6% at 1M. In larger networks, content is more diluted,
  so when someone reposts, fewer of their followers also see and repost that
  same post. The cascade becomes a chain rather than a tree.

— **Virality is structural, not engagement-based**: mean virality increases
  slightly with network size (1.90 → 2.10), but this is just because larger
  networks have a few more long chains in the tail. The 40% of cascades that
  are pure chains (ν = 1.33) dominate the mean.

— **Depth follows logarithmic scaling with size**: size 3–9 → depth ~2.7,
  size 50–99 → depth ~17, size 500+ → depth ~48. Cascades tend to be deep
  chains rather than wide trees.

---

## 3. Post Lifetimes & Engagement

| Metric | 100K | 500K | 1M |
|--------|------|------|-----|
| Total posts (SS) | 172M | 79.8M | 10.5M |
| Posts with reposts > 0 | 43.2M (25.1%) | 17.0M (21.3%) | 2.0M (19.4%) |
| Mean reposts (on posts with any) | 2.8 | 3.2 | 3.3 |
| Median reposts | 2 | 2 | 1 |
| Mean lifetime_raw (with reposts) | 843 | 984 | 1,107 |
| Median lifetime_raw (with reposts) | 441 | 613 | 750 |
| Mean burstiness_B | −0.207 | −0.170 | −0.164 |
| Posts with 0 reposts: mean lifetime | 168 | 179 | 204 |
| 0-repost posts: % no engagement at all | 29.1% | 35.4% | 38.7% |

**Interpretation:**

— **80% of posts get zero reposts**. The repost probability is 1.2% per
  encounter. With 20 followers on average, a post gets ~20 impressions,
  each with 1.2% repost chance → expected 0.24 reposts. Most posts die
  silently.

— **Lifetime grows with network size**: posts with reposts live 843 ticks
  (100K) → 1,107 ticks (1M). Bigger networks sustain engagement longer
  because there are more potential reposters downstream. A post "wakes up"
  whenever a new user discovers it.

— **Posts without reposts still die slowly**: mean lifetime of 168–204 ticks,
  driven entirely by likes. A post can get likes for hundreds of ticks without
  ever being reposted. 29–39% of these get zero engagement at all — they're
  created and immediately buried.

— **Burstiness is slightly anti-bursty** (mean ~−0.17): reposts tend to
  arrive more regularly than Poisson. This is the propagation delay doing
  its job — each hop takes Δ_p = 1 tick, so reposts can't all happen at once.
  But small cascades (2–4 reposts) are strongly anti-bursty (B ≈ −0.63),
  while large cascades (50+) are bursty (B ≈ +0.52). Viral events cluster.

— **Time to peak is fast**: median time_to_peak_50 = 0 across all sizes
  (the first repost is already 50% of most cascades). Only for larger
  cascades does it become meaningful.

---

## 4. Influencer Effect

Cascade metrics by author's follower count (in-degree):

| Degree bucket | 100K n | mean_size | mean_depth | 500K n | mean_size | 1M n | mean_size |
|---------------|--------|-----------|------------|--------|-----------|------|-----------|
| zero | 579K | 5.21 | 2.87 | 192K | 6.08 | 28K | 6.22 |
| 1–9 | 3.2M | 5.27 | 2.90 | 1.1M | 6.06 | 181K | 6.16 |
| 10–99 | 7.1M | 5.29 | 2.91 | 2.9M | 6.07 | 446K | 6.34 |
| 100–999 | 8.1M | 5.24 | 2.89 | 4.0M | 6.11 | 484K | 6.34 |
| 1K–10K | 7.3M | 5.26 | 2.89 | 2.1M | 6.16 | 167K | 6.29 |
| 10K+ | 289K | 5.42 | 2.97 | 160K | 6.10 | 12K | 6.21 |

**Interpretation:**

— **Follower count has essentially ZERO effect on cascade size**. A user with
  0 followers gets cascades of mean size 5.2; a user with 10K+ followers gets
  5.4. The difference is negligible. This is the most striking negative result
  of the simulation.

— **Why?** The CTIC model treats every user identically — same policy weights,
  same content creation rate. Followers only matter for the *first hop* of the
  cascade. After someone reposts, the cascade continues through *their* followers,
  not the original author's. The network's homogeneity washes out any influencer
  effect within 1–2 hops.

— **Implication**: viral content in this model is NOT about who posts it, but
  about the stochastic chain of reposts it triggers. Luck, not influence,
  determines cascade size.

---

## 5. Micro-Macro Coupling Ratios

### Pace ratio ρ

ρ = mean_inter_action_time / mean_inter_repost_time
  = 3.0 / (3.0 / 0.012)
  = **0.012**

Users interact 83× more often than they repost. The platform is a scrolling
machine, not a sharing machine. Content is consumed but rarely propagated.

### Session persistence π (sample estimates)

| | 100K | 500K | 1M |
|--------|------|------|-----|
| Mean session duration | ~115* | 129 | 115 |
| Mean post lifetime (with reposts) | 843 | 984 | 1,107 |
| π | ~7.3 | **7.6** | **9.6** |

A post with any reposts outlives an average session by 7–10×. Posts persist
across multiple user sessions. The content ecosystem has long memory relative
to individual attention spans.

_* 100K estimate from interpolation, not directly measured._

### Saturation σ (sample estimates)

σ = avg_time_between_reposts / mean_time_offline

The per-user inter-repost time is ~250 ticks (3.0 / 0.012). Global inter-repost
time across all users is much smaller (1M users × reposts/user ≈ continuous stream).
Mean offline gap is ~450 ticks.

σ << 1: reposts arrive much faster than users return from being offline.
Content piles up while users are away. But since timelines are CLEARED on
offline (session end), this piling up is wasted — users never see it.

---

## 6. Summary Assessment

### What the simulation gets right

1. **γ ≈ 1.73 is stable** — the repost cascade power-law exponent is an emergent
   invariant of the model, independent of network size. This matches real social
   media data where cascade size distributions are heavy-tailed.

2. **The boredom mechanism is self-consistent** — users leave when they run out
   of content. This creates a natural content-consumption cycle.

3. **Cascade depth scaling** — depth grows sublinearly with size, consistent
   with real diffusion trees that tend to be chains, not explosive stars.

### What the simulation gets wrong / concerning

1. **Influencer effect is absent**. In real social media, follower count is the
   strongest predictor of cascade size. Here it explains nothing. The model
   needs *content heterogeneity*: not all posts are equally shareable. A post
   quality parameter (e.g. sampled from a distribution, baked into the repost
   probability) would make some posts naturally more viral. Users with many
   followers who happen to create high-quality posts would drive large cascades.
   This is the single most important missing ingredient.

2. **Content starvation at 1M scale**. Without content quality variation, all
   posts have identical (low) repost probability. At larger scales, each user's
   timeline fills with uniformly mediocre content. Real networks have viral
   posts that act as "content anchors" — they spread widely and fill many
   timelines simultaneously, keeping users engaged across sessions.

3. **p_repost = 0.012 is a consequence of homogeneity**. With uniform content,
   the only way to prevent every post from going viral is a low baseline repost
   rate. If posts had varying quality, the baseline could be higher because
   only the good ones would actually spread. The 1.2% rate is an artifact of
   assuming all content is equally (un)interesting.

4. **29–39% of posts get zero engagement**. These are posts that arrive in
   timelines but are never seen before the user's session ends. Combined with
   the boredom exit, this creates a self-reinforcing cycle: mediocre content →
   quick sessions → less content seen → worse engagement. Better content
   breaks this cycle.

5. **80% ignore rate reflects content homogeneity, not user behavior**. Users
   ignore 4 out of 5 posts because every post has the same 80% ignore
   probability baked in. In reality, users ignore boring posts but engage
   with interesting ones. Content quality variation would naturally vary
   engagement rates across posts.
