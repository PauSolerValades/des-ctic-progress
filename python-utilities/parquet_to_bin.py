#!/usr/bin/env python3
"""Convert BlueSky network parquet files to a flat binary file.

Expected parquet files in the input folder:
    nodes.parquet         – columns: did (string), int_id (u32)
    induced_edges.parquet – columns: actor_id (u32), subject_id (u32)

Binary layout (little-endian, no header):
    u32  num_users
    u32  user_ids[num_users]
    u32  num_induced
    u32  induced_edges[num_induced * 2]   (actor_id, subject_id interleaved)

Usage:
    uv run --with pyarrow,numpy parquet_to_bin.py <input_folder> [-o <output_dir>]
"""

import os
import sys

EXPECTED = ("nodes.parquet", "induced_edges.parquet")


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def col_to_numpy(folder: str, filename: str, col: str):
    """Read a single parquet column as a numpy uint32 array."""
    import pyarrow.parquet as pq
    t = pq.read_table(os.path.join(folder, filename), columns=[col])
    return t.column(col).to_numpy().astype("<u4", copy=False)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(f"Usage: {sys.argv[0]} <input_folder> [-o <output_dir>]", file=sys.stderr)
        sys.exit(1)

    inp = args[0]
    out = None

    i = 1
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        else:
            die(f"unknown option: {args[i]}")

    if not os.path.isdir(inp):
        die(f"'{inp}' is not a directory")

    missing = [f for f in EXPECTED if not os.path.isfile(os.path.join(inp, f))]
    if missing:
        die(f"missing files in '{inp}': {missing}")

    if out is None:
        parent = os.path.dirname(os.path.abspath(inp))
        name = os.path.basename(os.path.abspath(inp))
        out = os.path.join(parent, f"{name}_binary")

    os.makedirs(out, exist_ok=True)

    print(f"Reading: {inp}  ->  {out}")

    users = col_to_numpy(inp, "nodes.parquet", "int_id")
    actors = col_to_numpy(inp, "induced_edges.parquet", "actor_id")
    subjects = col_to_numpy(inp, "induced_edges.parquet", "subject_id")

    num_users = len(users)
    num_edges = len(actors)
    print(f"  users: {num_users}  induced: {num_edges}")

    # Interleave actors + subjects into a single uint32 array
    import numpy as np
    edges_flat = bytearray(actors.nbytes * 2)
    flat = np.frombuffer(edges_flat, dtype="<u4").reshape(-1, 2)
    flat[:, 0] = actors
    flat[:, 1] = subjects

    out_path = os.path.join(out, "network.bin")
    with open(out_path, "wb") as f:
        import struct
        f.write(struct.pack("<I", num_users))
        f.write(users.tobytes())
        f.write(struct.pack("<I", num_edges))
        f.write(edges_flat)

    del edges_flat, flat, actors, subjects, users

    total = 4 + num_users * 4 + 4 + num_edges * 8
    print(f"  wrote: {out_path}  ({total:,} bytes)")


if __name__ == "__main__":
    main()
