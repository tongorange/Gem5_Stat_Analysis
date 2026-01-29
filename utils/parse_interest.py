from pathlib import Path
from utils.gem5_parser import Gem5StatsParser
from utils.analyzer import METRIC_RULES

def auto_discover_benchmarks(raw_dir: Path):
    entries = []
    if not raw_dir.exists():
        return entries

    for item in raw_dir.iterdir():
        if not item.is_dir():
            continue

        # New layout: raw/bench/config/stats.txt
        stats_file = item / "stats.txt"
        if stats_file.exists():
            entries.append({
                "benchmark": item.name,
                "config": "default",
                "stats_file": stats_file
            })
            continue

        for sub in item.iterdir():
            if not sub.is_dir():
                continue
            stats_file = sub / "stats.txt"
            if not stats_file.exists():
                continue
            entries.append({
                "benchmark": item.name,
                "config": sub.name,
                "stats_file": stats_file
            })
            continue

        # Legacy layout: raw/bench_config/stats.txt
        if "_" in item.name:
            stats_file = item / "stats.txt"
            if stats_file.exists():
                benchmark, config = item.name.split("_", 1)
                entries.append({
                    "benchmark": benchmark,
                    "config": config,
                    "stats_file": stats_file
                })

    return entries


def _collect_interest_patterns():
    patterns = []
    for rule in METRIC_RULES.values():
        patterns.extend(rule.get("patterns", []))
    return patterns


def parse_all_raw(
    raw_dir: Path,
    parsed_dir: Path,
    verbose: bool = True
):
    parser = Gem5StatsParser(_collect_interest_patterns())
    entries = auto_discover_benchmarks(raw_dir)

    parsed_dir.mkdir(parents=True, exist_ok=True)
    for csv_file in parsed_dir.glob("*.csv"):
        csv_file.unlink()

    success = 0
    for e in entries:
        df = parser.parse_and_extract(str(e["stats_file"]))
        if df.empty:
            continue

        df["benchmark"] = e["benchmark"]
        df["config"] = e["config"]

        out = parsed_dir / f'{e["benchmark"]}_{e["config"]}.csv'
        df.to_csv(out, index=False)
        success += 1

        if verbose:
            print(f"[OK] {out}")

    return success, len(entries)
