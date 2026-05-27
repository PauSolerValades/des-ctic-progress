#!/usr/bin/env bash
set -euo pipefail

BINARY="./zig-out/bin/bskysim-release"
DATA="data/1M/network.bin"
RUNS=8
NAME="batch-1M"

mkdir -p traces

for ((i=1; i<=RUNS; i++)); do
    echo "=== Run $i/$RUNS ==="
    "$BINARY" "$DATA" 1 -n "${NAME}-${i}"
done

echo "=== All $RUNS runs complete ==="
