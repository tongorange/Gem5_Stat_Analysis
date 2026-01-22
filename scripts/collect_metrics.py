#!/usr/bin/env python3
import argparse
import csv
import os
import re


TRAFFIC_FILTER = re.compile(
    r"(dir_cntrl|tcc_cntrl|cp_cntrl|bloom_cntrl).*m_msg_count"
)


def parse_stats(path):
    stats = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            try:
                value = float(parts[1])
            except ValueError:
                continue
            stats[name] = value
    return stats


def avg(stats, pattern):
    rgx = re.compile(pattern)
    vals = [v for k, v in stats.items() if rgx.match(k)]
    if not vals:
        return ""
    return sum(vals) / len(vals)


def parse_dir_name(name):
    parts = name.split("_")
    if len(parts) < 3:
        return None
    scenario = parts[-2]
    bloom = parts[-1]
    if scenario not in ("cpu_only", "gpu_only", "cpu_gpu"):
        return None
    if bloom not in ("bloom_on", "bloom_off"):
        return None
    run_id = "_".join(parts[:-2]) or "run"
    return run_id, scenario, bloom


def find_runs(root):
    runs = []
    for dirpath, _, filenames in os.walk(root):
        if "stats.txt" in filenames:
            stats_path = os.path.join(dirpath, "stats.txt")
            rel = os.path.relpath(dirpath, root)
            parts = rel.split(os.sep)
            if len(parts) >= 3:
                run_id, scenario, bloom = parts[0], parts[1], parts[2]
                runs.append((run_id, scenario, bloom, stats_path))
                continue
            parsed = parse_dir_name(parts[0])
            if parsed:
                run_id, scenario, bloom = parsed
                runs.append((run_id, scenario, bloom, stats_path))
    return sorted(runs)


def main():
    ap = argparse.ArgumentParser(description="Collect experiment metrics")
    ap.add_argument(
        "--runs-root",
        default="stats_analysis/experiments/runs",
        help="Root directory of runs",
    )
    ap.add_argument(
        "--out-dir",
        default="stats_analysis/experiments/summary",
        help="Output directory for CSVs",
    )
    args = ap.parse_args()

    runs = find_runs(args.runs_root)
    os.makedirs(args.out_dir, exist_ok=True)

    metrics_path = os.path.join(args.out_dir, "metrics.csv")
    traffic_path = os.path.join(args.out_dir, "traffic.csv")

    metrics_fields = [
        "run_id",
        "scenario",
        "bloom",
        "cpu_ipc_avg",
        "cpu_siminsts_avg",
        "cpu_numcycles_avg",
        "bloomTotalReadChecks",
        "bloomBypassReads",
        "bloomNonBypassReads",
        "dirtyLineTransitions",
        "dirtyToCleanTransitions",
        "bloomCounterIncTotal",
        "bloomCounterDecTotal",
    ]

    with open(metrics_path, "w", newline="", encoding="utf-8") as mf, open(
        traffic_path, "w", newline="", encoding="utf-8"
    ) as tf:
        metrics_writer = csv.DictWriter(mf, fieldnames=metrics_fields)
        traffic_writer = csv.DictWriter(
            tf, fieldnames=["run_id", "scenario", "bloom", "stat", "value"]
        )
        metrics_writer.writeheader()
        traffic_writer.writeheader()

        for run_id, scenario, bloom, stats_path in runs:
            stats = parse_stats(stats_path)
            row = {
                "run_id": run_id,
                "scenario": scenario,
                "bloom": bloom,
                "cpu_ipc_avg": avg(stats, r"^system\.cpu\d+\.ipc$"),
                "cpu_siminsts_avg": avg(stats, r"^system\.cpu\d+\.simInsts$"),
                "cpu_numcycles_avg": avg(stats, r"^system\.cpu\d+\.numCycles$"),
                "bloomTotalReadChecks": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.bloomTotalReadChecks", ""
                ),
                "bloomBypassReads": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.bloomBypassReads", ""
                ),
                "bloomNonBypassReads": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.bloomNonBypassReads",
                    "",
                ),
                "dirtyLineTransitions": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.dirtyLineTransitions", ""
                ),
                "dirtyToCleanTransitions": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.dirtyToCleanTransitions",
                    "",
                ),
                "bloomCounterIncTotal": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.bloomCounterIncTotal", ""
                ),
                "bloomCounterDecTotal": stats.get(
                    "system.ruby.dir_cntrl0.BloomFilter.bloomCounterDecTotal", ""
                ),
            }
            metrics_writer.writerow(row)

            for name, value in stats.items():
                if TRAFFIC_FILTER.search(name):
                    traffic_writer.writerow(
                        {
                            "run_id": run_id,
                            "scenario": scenario,
                            "bloom": bloom,
                            "stat": name,
                            "value": value,
                        }
                    )

    print(f"[INFO] Wrote: {metrics_path}")
    print(f"[INFO] Wrote: {traffic_path}")


if __name__ == "__main__":
    main()
