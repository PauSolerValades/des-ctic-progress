"""Cascade Morphology — Table 1: out_cascades.parquet

Characterises the structural shape and virality of information spread.
One row per post with cascade size N >= 2.

Metrics:
    - cascade_size: total number of distinct users who engaged (repost+like, not ignore)
    - cascade_depth: longest path from root to leaf in the propagation tree
    - struct_virality: Wiener index (average pairwise distance) of the tree
    - max_out_degree: maximum number of direct children for any node in the tree
    - author_degree: in-degree (follower count) of the post's author
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import polars as pl

from .network import get_author_degree

CASCADE_COLUMNS = [
    "sim_id",
    "post_id",
    "author_degree",
    "cascade_size",
    "cascade_depth",
    "struct_virality",
    "max_out_degree",
]


# ---------------------------------------------------------------------------
# BATCH tree reconstruction (the performance-critical path)
# ---------------------------------------------------------------------------
def _build_cascade_trees_batch(
    repost_by_post: Dict[int, List[Tuple[int, float]]],
    prop_by_post: Dict[int, List[Tuple[int, float]]],
    authors_by_post: Dict[int, int],
    post_ids: List[int],
) -> Dict[int, Optional[Dict[int, List[int]]]]:
    """Build cascade trees for multiple posts in a single batch.

    For each post:
      - Author is root.
      - For each reposter, find the parent: the most recent propagator whose
        propagate time < repost time (with small float tolerance).
      - Both reposts and propagates are already sorted by time.

    Returns {post_id: tree | None}, where tree is {node: [children]}.
    """
    trees: Dict[int, Optional[Dict[int, List[int]]]] = {}

    for pid in post_ids:
        reposters = repost_by_post.get(pid, [])
        props = prop_by_post.get(pid, [])
        author = authors_by_post.get(pid)

        if author is None or len(reposters) < 2:
            trees[pid] = None
            continue

        tree: Dict[int, List[int]] = {author: []}

        # Walk both sorted lists in tandem — O(n_reposts + n_props)
        pi = 0
        for reposter_uid, repost_time in reposters:
            best_parent = author
            while pi < len(props) and props[pi][1] < repost_time - 1e-9:
                best_parent = props[pi][0]
                pi += 1

            tree.setdefault(best_parent, []).append(reposter_uid)
            if reposter_uid not in tree:
                tree[reposter_uid] = []

        trees[pid] = tree

    return trees


# ---------------------------------------------------------------------------
# Single-tree metrics
# ---------------------------------------------------------------------------
def _compute_depth(tree: Dict[int, List[int]], root: int) -> int:
    """BFS to find maximum tree depth (longest path from root to leaf)."""
    if not tree:
        return 0
    max_depth = 0
    queue: deque[Tuple[int, int]] = deque([(root, 0)])
    while queue:
        node, depth = queue.popleft()
        max_depth = max(max_depth, depth)
        for child in tree.get(node, []):
            queue.append((child, depth + 1))
    return max_depth


def _compute_wiener(tree: Dict[int, List[int]], root: int) -> float:
    """Wiener index normalised as average pairwise distance (struct_virality).

    Computed via post-order DFS size aggregation.
    """
    n = len(tree)
    if n <= 1:
        return 0.0

    subtree_size: Dict[int, int] = {}

    def dfs(node: int) -> int:
        size = 1
        for child in tree.get(node, []):
            size += dfs(child)
        subtree_size[node] = size
        return size

    dfs(root)

    wiener = 0
    for parent, children in tree.items():
        for child in children:
            sz = subtree_size[child]
            wiener += sz * (n - sz)

    pairs = n * (n - 1) / 2.0
    if pairs == 0:
        return 0.0
    return wiener / pairs


def _compute_max_out_degree(tree: Dict[int, List[int]]) -> int:
    """Maximum number of direct children for any node in the tree."""
    if not tree:
        return 0
    return max(len(children) for children in tree.values())


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def compute_cascades(
    sim_id: str,
    creates_df: pl.DataFrame,
    actions_df: pl.DataFrame,
    propagates_df: pl.DataFrame,
    indegree_map: Dict[int, int],
) -> pl.DataFrame:
    """Produce the out_cascades DataFrame for a single simulation run.

    Only posts with cascade_size >= 2 are included (space-saving per spec).
    """
    t0 = time.perf_counter()

    # --- Step 1: identify posts with cascade_size >= 2 ---
    # cascade_size = 1 (author) + number_of_distinct_reposters
    # Only include posts with >= 2 reposts (= cascade_size >= 3)
    repost_counts = (
        actions_df.filter(pl.col("type") == "repost")
        .group_by("post_id")
        .agg(pl.col("user_id").n_unique().alias("num_reposters"))
        .filter(pl.col("num_reposters") >= 2)
    )

    if repost_counts.height == 0:
        return pl.DataFrame(
            schema={
                "sim_id": pl.Utf8,
                "post_id": pl.Int64,
                "author_degree": pl.Int64,
                "cascade_size": pl.Int64,
                "cascade_depth": pl.Int64,
                "struct_virality": pl.Float64,
                "max_out_degree": pl.Int64,
            }
        )

    # --- Step 2: get author per post ---
    author_df = creates_df.select(
        [pl.col("post_id"), pl.col("user_id").alias("author")]
    )
    meta = repost_counts.join(author_df, on="post_id", how="inner")
    post_ids = meta["post_id"].to_list()
    # cascade_size = author + distinct reposters
    cascade_sizes = {
        pid: cnt + 1
        for pid, cnt in zip(
            meta["post_id"].to_list(), meta["num_reposters"].to_list()
        )
    }
    authors_by_post = dict(
        zip(meta["post_id"].to_list(), meta["author"].to_list())
    )

    # --- Step 3: batch-index reposts and propagates by post_id ---
    reposts = (
        actions_df.filter(pl.col("type") == "repost")
        .select(["post_id", "user_id", "time"])
        .sort(["post_id", "time"])
    )
    props = (
        propagates_df.rename({"type": "post_id"})
        .select(["post_id", "user_id", "time"])
        .sort(["post_id", "time"])
    )

    repost_by_post: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for row in reposts.iter_rows(named=True):
        repost_by_post[row["post_id"]].append((row["user_id"], row["time"]))

    prop_by_post: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for row in props.iter_rows(named=True):
        prop_by_post[row["post_id"]].append((row["user_id"], row["time"]))

    # --- Step 4: batch-build all cascade trees ---
    trees = _build_cascade_trees_batch(
        repost_by_post, prop_by_post, authors_by_post, post_ids
    )

    # --- Step 5: compute per-tree metrics ---
    rows = []
    for pid in post_ids:
        author = authors_by_post[pid]
        tree = trees.get(pid)

        if tree is None:
            depth = 0
            wiener = 0.0
            max_out = 0
        else:
            depth = _compute_depth(tree, author)
            wiener = _compute_wiener(tree, author)
            max_out = _compute_max_out_degree(tree)

        rows.append(
            {
                "sim_id": sim_id,
                "post_id": pid,
                "author_degree": get_author_degree(indegree_map, author),
                "cascade_size": cascade_sizes[pid],
                "cascade_depth": depth,
                "struct_virality": wiener,
                "max_out_degree": max_out,
            }
        )

    result = pl.DataFrame(
        rows,
        schema={
            "sim_id": pl.Utf8,
            "post_id": pl.Int64,
            "author_degree": pl.Int64,
            "cascade_size": pl.Int64,
            "cascade_depth": pl.Int64,
            "struct_virality": pl.Float64,
            "max_out_degree": pl.Int64,
        },
    )
    print(f"  [cascades] {result.height} rows in {time.perf_counter() - t0:.1f}s")
    return result
