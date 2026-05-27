"""Read network.bin files and provide in-degree (follower count) lookups.

Binary format (little-endian, no header):
    u32  num_users
    u32  user_ids[num_users]           (internal_id → parquet int_id mapping)
    u32  num_edges
    u32  edges[num_edges * 2]          (actor_id, subject_id interleaved)

Actor = follower, subject = followed user. Both use parquet int_id values.
In-degree of a user = number of actors following them.

The simulation traces use internal IDs (0 .. num_users-1).  This module
provides a two-level lookup: internal_id → parquet int_id → indegree.
"""

import struct
from pathlib import Path
from typing import Dict, List

import numpy as np

# Cache: keyed by absolute path, value = (id_map: list[int], indegree: dict)
_CACHE: Dict[str, Dict[int, int]] = {}


def load_indegree(network_bin_path: Path) -> Dict[int, int]:
    """Return {internal_user_id: follower_count} for the simulation.

    Results are cached by absolute path.
    """
    key = str(network_bin_path.resolve())
    if key in _CACHE:
        return _CACHE[key]

    with open(network_bin_path, "rb") as fh:
        # num_users: u32
        num_users = struct.unpack("<I", fh.read(4))[0]

        # user_ids — mapping from internal_id → parquet int_id
        fmt = "<" + "I" * num_users
        user_ids: List[int] = list(struct.unpack(fmt, fh.read(num_users * 4)))

        # num_edges: u32
        num_edges = struct.unpack("<I", fh.read(4))[0]

        # Read all edges as raw bytes → numpy
        edge_bytes = fh.read(num_edges * 8)

    # Edges: [actor0, subject0, actor1, subject1, ...] as u32
    edges = np.frombuffer(edge_bytes, dtype=np.uint32).reshape(-1, 2)

    # subjects = column 1 (parquet int_id of the user being followed)
    subjects = edges[:, 1]

    # Count using bincount (parquet int_ids can be up to ~27M, that fits)
    max_id = int(subjects.max()) if len(subjects) > 0 else 0
    counts = np.bincount(subjects, minlength=max_id + 1)

    # Build internal_id → follower_count mapping
    result: Dict[int, int] = {}
    nonzero = np.flatnonzero(counts)
    # Build reverse map: parquet_id → indegree
    parquet_to_indegree = {int(uid): int(counts[uid]) for uid in nonzero}

    for internal_id, parquet_id in enumerate(user_ids):
        deg = parquet_to_indegree.get(parquet_id, 0)
        if deg > 0:
            result[internal_id] = deg

    _CACHE[key] = result
    return result


def get_author_degree(indegree_map: Dict[int, int], user_id: int) -> int:
    """Safely look up follower count by internal user ID."""
    return indegree_map.get(user_id, 0)
