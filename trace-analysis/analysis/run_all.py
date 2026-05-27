#!/usr/bin/env python3
"""Master script: runs all 4 analysis sections and writes chapter_output.txt."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPTS = ["stationary.py", "congestion.py", "lifetimes_cascades.py", "coupling.py"]
OUT = HERE / "chapter_output.txt"

def main():
    with open(OUT, "w") as f:
        for script in SCRIPTS:
            name = script.replace(".py", "").replace("_", " ").title()
            f.write(f"\n{'='*70}\n")
            f.write(f"  {name}\n")
            f.write(f"{'='*70}\n\n")
            try:
                result = subprocess.run(
                    [sys.executable, str(HERE / script)],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(HERE.parent)
                )
                f.write(result.stdout)
                if result.stderr and "UserWarning" not in result.stderr:
                    f.write(f"\n[stderr]\n{result.stderr}\n")
            except subprocess.TimeoutExpired:
                f.write(f"[TIMEOUT after 300s]\n")
            except Exception as e:
                f.write(f"[ERROR: {e}]\n")
    print(f"Done → {OUT}")


if __name__ == "__main__":
    main()
