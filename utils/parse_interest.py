from pathlib import Path
from utils.gem5_parser import Gem5StatsParser

def auto_discover_benchmarks(raw_dir: Path):
    entries = []
    if not raw_dir.exists():
        return entries

    for item in raw_dir.iterdir():
        if not item.is_dir():
            continue

        stats_file = item / "stats.txt"
        if not stats_file.exists():
            continue

        if "_" not in item.name:
            continue

        benchmark, config = item.name.split("_", 1)
        entries.append({
            "benchmark": benchmark,
            "config": config,
            "stats_file": stats_file
        })

    return entries


def parse_all_raw(
    raw_dir: Path,
    parsed_dir: Path,
    interest_file: Path,
    verbose: bool = True
):
    parser = Gem5StatsParser(str(interest_file))
    entries = auto_discover_benchmarks(raw_dir)

    parsed_dir.mkdir(parents=True, exist_ok=True)

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
