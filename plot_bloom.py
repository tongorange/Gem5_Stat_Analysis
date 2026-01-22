#!/usr/bin/env python3
"""
Quick helper to extract and visualize DRAM cache Bloom filter stats from a
gem5 stats.txt file.

Usage:
    python stats_analysis/plot_bloom.py /path/to/stats.txt
"""

import re
import sys
from pathlib import Path
from typing import Dict


def parse_stats(stats_path: Path) -> Dict[str, int]:
    fields = {
        "dramBloomBypassReads": 0,
        "dramBloomNonBypassReads": 0,
        "dramBloomIncrements": 0,
        "dramBloomDecrements": 0,
    }

    pattern = re.compile(r"^(?P<name>dramBloom\w+)\s+(?P<value>[0-9]+)")
    with stats_path.open() as fh:
        for line in fh:
            m = pattern.match(line.strip())
            if not m:
                continue
            name = m.group("name")
            if name in fields:
                fields[name] = int(m.group("value"))
    return fields


def maybe_plot(fields: Dict[str, int]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        print("matplotlib not installed; skipping plot. Values:")
        for k, v in fields.items():
            print(f"{k}: {v}")
        return

    labels = list(fields.keys())
    values = [fields[k] for k in labels]

    plt.figure(figsize=(8, 4))
    bars = plt.bar(labels, values, color=["#4c72b0", "#dd8452", "#55a868", "#c44e52"])
    plt.title("DRAM Cache Bloom Filter Stats")
    plt.ylabel("Count")
    plt.xticks(rotation=20, ha="right")

    for bar, val in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            str(val),
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.show()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    stats_path = Path(sys.argv[1])
    if not stats_path.exists():
        raise SystemExit(f"stats file not found: {stats_path}")

    fields = parse_stats(stats_path)
    maybe_plot(fields)


if __name__ == "__main__":
    main()
