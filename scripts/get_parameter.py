import re
from pathlib import Path
import csv

def parse_value(val: str):
    if val == "nan":
        return None
    elif val == "inf":
        return 1e99
    elif "%" in val:
        return float(val.strip("%"))
    elif "." in val:
        return float(val)
    else:
        return int(val)

class Gem5Stat:
    def __init__(self, line: str):
        line = line.strip()

        if "|" in line:
            self.name = line.split()[0]
            self.value = None
            return

        m = re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+|nan|inf)\s+# (.*)', line)
        if m:
            self.name = m.group(1)
            self.value = parse_value(m.group(2))
            return

        raise ValueError(f"Cannot parse stat line: {line}")

def extract_names_from_file(file_path: str):
    names = set()

    with open(file_path, 'r') as f:
        lines = f.readlines()

    in_block = False

    for line in lines:
        t = line.strip()

        if t == '---------- Begin Simulation Statistics ----------':
            in_block = True
            continue

        if t == '---------- End Simulation Statistics ----------':
            in_block = False
            continue

        if in_block and t:
            try:
                stat = Gem5Stat(line)
                names.add(stat.name)
            except ValueError:
                pass

    return names

def main():
    stats_dir = Path("../test_stats")
    out_dir = Path("../parsed")
    out_dir.mkdir(exist_ok=True)

    all_sets = {}  # { "bfs": set(...), "btree": set(...) }

    # 提取每个 stats 的 name 集合
    for stats_file in stats_dir.glob("*.txt"):
        stem = stats_file.stem.replace("stats_", "")
        names = extract_names_from_file(str(stats_file))
        all_sets[stem] = names

        # 写各自的 all_names_xxx.txt
        out_path = out_dir / f"all_names_{stem}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            for n in sorted(names):
                f.write(n + "\n")

        print(f"[OK] {stats_file.name} → {out_path.name} ({len(names)} 个参数)")

    # === 1. 计算所有文件共有的参数 (intersection) ===
    common_all = set.intersection(*all_sets.values())
    with open(out_dir / "diff_common_all.txt", "w", encoding="utf-8") as f:
        for n in sorted(common_all):
            f.write(n + "\n")

    print(f"[INFO] 所有 stats 文件共有的参数: {len(common_all)}")

    # === 2. 计算每个 stats 文件独有的参数 ===
    with open(out_dir / "diff_unique_each.txt", "w", encoding="utf-8") as f:
        for key, name_set in all_sets.items():
            others = set.union(*(v for k, v in all_sets.items() if k != key))
            unique = name_set - others
            f.write(f"=== {key} 独有参数 ({len(unique)} 个) ===\n")
            for u in sorted(unique):
                f.write(u + "\n")
            f.write("\n")

    print(f"[INFO] 已生成每个文件独有的参数 diff_unique_each.txt")

    # === 3. 生成参数 × 文件 的矩阵 CSV ===
    all_params = sorted(set.union(*all_sets.values()))
    keys = sorted(all_sets.keys())

    with open(out_dir / "diff_summary.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["parameter"] + keys)

        for p in all_params:
            row = [p] + [(1 if p in all_sets[k] else 0) for k in keys]
            writer.writerow(row)

    print(f"[INFO] 已生成对比矩阵 diff_summary.csv")


if __name__ == "__main__":
    main()
