import re
import csv
from pathlib import Path
from utils.analyzer import METRIC_RULES

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

class Gem5Stat():
    def __init__(self, line: str):
        line = line.strip()

        if "|" in line:
            parts = line.split("#", 1)
            self.name = line.split()[0]
            self.value = None
            self.description = parts[1].strip() if len(parts) > 1 else ""

        elif match := re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+|nan|inf)\s+# (.*)', line):
            self.name = match.group(1)
            self.value = parse_value(match.group(2))
            self.description = match.group(3)

        elif match := re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+)\s+([-+]?[0-9.eE]+)%\s+([-+]?[0-9.eE]+)%\s*# (.*)', line):
            self.name = match.group(1)
            self.value = parse_value(match.group(2))
            self.percentage = parse_value(match.group(3))
            self.percentage_cumulative = parse_value(match.group(4))
            self.description = match.group(5)
        
        elif match := re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+)\s+\(.*\)', line):
            self.name = match.group(1)
            self.value = parse_value(match.group(2))
            self.description = "(Unspecified)"

        elif match := re.match(
            r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+)\s+([-+]?[0-9.eE]+)%\s+([-+]?[0-9.eE]+)%\s+\(.*\)', line
        ):
            self.name = match.group(1)
            self.value = parse_value(match.group(2))
            self.percentage = parse_value(match.group(3))
            self.percentage_cumulative = parse_value(match.group(4))
            self.description = "(Unspecified)"

        else:
            raise ValueError(f"Cannot parse string into gem5 stat: {line}")


def parse_gem5_stats(file_path: str) -> "list[dict[str, Gem5Stat]]":
    with open(file_path, 'r') as f:
        lines = f.readlines()

    stat_instances = []
    current_stat_instance = {}

    in_stat_instance = False

    for line in lines:
        if line.strip() == '---------- Begin Simulation Statistics ----------':
            in_stat_instance = True
            current_stat_instance = {}
        elif line.strip() == '---------- End Simulation Statistics   ----------':
            in_stat_instance = False
            stat_instances.append(current_stat_instance)
        elif in_stat_instance:
            if line == "\n":
                continue
            try:
                stat = Gem5Stat(line)
                current_stat_instance[stat.name] = stat
            except ValueError as e:
                print(f"[INFO] Skipping unparsable stat line: {line.strip()}")

    return stat_instances


def main():
    # === 路径设置 ===
    stats_path = Path("../raw_data/stats.txt")
    output_csv = Path("../parsed/pre_stats.csv")
    patterns = []
    for rule in METRIC_RULES.values():
        patterns.extend(rule.get("patterns", []))
    compiled = [re.compile(p) for p in patterns if p]

    # === Step 2: 解析 gem5 的统计文件 ===
    all_stats = parse_gem5_stats(str(stats_path))
    if not all_stats:
        print("[ERROR] 未解析到任何统计数据，请检查 stats.txt 文件内容。")
        return
    stats = all_stats[-1]  # 取最后一个统计块（通常是最终结果）

    # === Step 3: 提取数据 - 改为包含匹配 ===
    results = []
    for stat_name, stat_obj in stats.items():
        for pattern in compiled:
            if pattern.match(stat_name):
                results.append({
                    "stat_name": stat_name,
                    "value": stat_obj.value
                })
                break

    # === Step 4: 写入 CSV 文件 ===
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["stat_name", "value"])
        writer.writeheader()
        writer.writerows(results)

    print(f"[OK] 已将解析结果写入 {output_csv}")
    print(f"[INFO] 匹配到的总参数数量: {len(results)}")


if __name__ == "__main__":
    main()
