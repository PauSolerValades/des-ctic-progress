#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <data_file> <runs> <batch_name>"
    echo "Example: $0 data/1M/network.bin 8 batch-A"
    exit 1
fi

DATA="$1"
RUNS="$2"
BATCH_NAME="script-$(basename "$(dirname "$DATA")")-$3"
BINARY="./zig-out/bin/bskysim-release"

echo "Data:     $DATA"
echo "Runs:     $RUNS"
echo "Output:   traces/${BATCH_NAME}"

for ((i=1; i<=RUNS; i++)); do
    echo "=== Run $i/$RUNS ==="
    "$BINARY" -n "${BATCH_NAME}/${i}" "$DATA"
done

echo "=== All $RUNS runs complete ==="
