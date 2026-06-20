#!/usr/bin/env python3
"""Remap parquet int_ids to sequential 0..N-1 and drop orphan nodes (no edges).

Reads a source folder containing nodes.parquet, induced_edges.parquet, and
optionally burned_edges.parquet.  Outputs clean copies with monotonically
increasing int_ids into a new folder.

Usage:
    uv run --with pyarrow clean_parquet.py <source_folder> [-o <output_dir>]
    uv run --with pyarrow clean_parquet.py ~/firehose-analysis/topology/sampling-go/results/10000
    uv run --with pyarrow clean_parquet.py ~/firehose-analysis/topology/sampling-go/results/10000 -o ./clean/10K

The output folder can then be passed directly to parquet_to_bin.py.
"""

import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

EXPECTED = ("nodes.parquet", "induced_edges.parquet")
OPTIONAL = ("burned_edges.parquet",)


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(f"Usage: {sys.argv[0]} <source_folder> [-o <output_dir>]", file=sys.stderr)
        sys.exit(1)

    src = args[0]
    out_dir = None
    i = 1
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
        else:
            die(f"unknown option: {args[i]}")

    src_path = Path(src).expanduser()
    if not src_path.is_dir():
        die(f"'{src_path}' is not a directory")

    missing = [f for f in EXPECTED if not (src_path / f).is_file()]
    if missing:
        die(f"missing files in '{src_path}': {missing}")

    if out_dir is None:
        out_dir = src_path.parent / f"{src_path.name}_clean"

    out_path = Path(out_dir)
    os.makedirs(out_path, exist_ok=True)

    print(f"Source: {src_path}")
    print(f"Output: {out_path}")

    # ── 1. Read nodes ──────────────────────────────────────────────────────
    nodes = pq.read_table(src_path / "nodes.parquet")
    old_ids = nodes.column("int_id").to_pylist()

    # Deduplicate: same int_id may appear multiple times (keep first occurrence)
    seen: set[int] = set()
    keep_mask: list[bool] = []
    for oid in old_ids:
        keep = oid not in seen
        seen.add(oid)
        keep_mask.append(keep)

    unique_old = [oid for oid, k in zip(old_ids, keep_mask) if k]
    num_unique = len(unique_old)

    # ── 2. Collect all IDs referenced in edges ─────────────────────────────
    edges = pq.read_table(src_path / "induced_edges.parquet")
    e_actors = edges.column("actor_id").to_pylist()
    e_subjects = edges.column("subject_id").to_pylist()

    edge_id_set: set[int] = set(e_actors) | set(e_subjects)

    # Read burned edges if present
    burnt_actors: list[int] = []
    burnt_subjects: list[int] = []
    if (src_path / "burned_edges.parquet").is_file():
        burnt = pq.read_table(src_path / "burned_edges.parquet")
        burnt_actors = burnt.column("actor_id").to_pylist()
        burnt_subjects = burnt.column("subject_id").to_pylist()
        edge_id_set |= set(burnt_actors) | set(burnt_subjects)

    # ── 3. Build remapping: old int_id → new sequential ID ─────────────────
    # Only keep nodes that appear in edges (drop orphans)
    id_map: dict[int, int] = {}
    for oid in unique_old:
        if oid in edge_id_set:
            id_map[oid] = len(id_map)

    new_count = len(id_map)
    print(f"\n  Nodes read: {len(old_ids)} rows, {num_unique} unique IDs")
    print(f"  Edges induced: {edges.num_rows}, burnt: {len(burnt_actors)}")
    print(f"  IDs in edges: {len(edge_id_set)}")
    print(f"  Orphans dropped: {num_unique - new_count}")
    print(f"  New sequential IDs: 0 .. {new_count - 1}")

    if new_count == 0:
        die("No nodes remain after filtering — check your input")

    # ── 4. Write clean nodes.parquet ───────────────────────────────────────
    new_dids: list[str] = []
    new_ids: list[int] = []
    node_dids = nodes.column("did").to_pylist()

    for did, oid, keep in zip(node_dids, old_ids, keep_mask):
        if keep and oid in id_map:
            new_dids.append(did)
            new_ids.append(id_map[oid])

    nodes_out = pa.table(
        {"did": pa.array(new_dids, type=pa.string()),
         "int_id": pa.array(new_ids, type=pa.uint32())}
    )
    pq.write_table(nodes_out, out_path / "nodes.parquet")
    print(f"  Wrote nodes.parquet  ({len(new_ids)} rows)")

    # ── 5. Write clean induced_edges.parquet ───────────────────────────────
    new_actors = [id_map[a] for a in e_actors]
    new_subjects = [id_map[s] for s in e_subjects]
    # Keep actor_did / subject_did if present
    cols: dict[str, pa.Array] = {
        "actor_id": pa.array(new_actors, type=pa.uint32()),
        "subject_id": pa.array(new_subjects, type=pa.uint32()),
    }
    if "actor_did" in edges.column_names:
        cols["actor_did"] = edges.column("actor_did")
    if "subject_did" in edges.column_names:
        cols["subject_did"] = edges.column("subject_did")

    edges_out = pa.table(cols)
    pq.write_table(edges_out, out_path / "induced_edges.parquet")
    print(f"  Wrote induced_edges.parquet  ({len(new_actors)} rows)")

    # ── 6. Write clean burned_edges.parquet (if present) ───────────────────
    if burnt_actors:
        new_b_actors = [id_map[a] for a in burnt_actors]
        new_b_subjects = [id_map[s] for s in burnt_subjects]
        b_cols: dict[str, pa.Array] = {
            "actor_id": pa.array(new_b_actors, type=pa.uint32()),
            "subject_id": pa.array(new_b_subjects, type=pa.uint32()),
        }
        if "actor_did" in burnt.column_names:
            b_cols["actor_did"] = burnt.column("actor_did")
        if "subject_did" in burnt.column_names:
            b_cols["subject_did"] = burnt.column("subject_did")

        burnt_out = pa.table(b_cols)
        pq.write_table(burnt_out, out_path / "burned_edges.parquet")
        print(f"  Wrote burned_edges.parquet  ({len(new_b_actors)} rows)")

    print(f"\nDone. Clean parquet in: {out_path}")
    print(f"Run:  uv run --with pyarrow parquet_to_bin.py {out_path}")


if __name__ == "__main__":
    main()
