import re
import csv
from pathlib import Path

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
    interest_csv = Path("../configs/interest.csv")
    output_csv = Path("../parsed/pre_stats.csv")

    # === Step 1: 读取感兴趣的参数名 ===
    with open(interest_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        interest_names = [row["name"].strip() for row in reader if row["name"].strip()]

    # === Step 2: 解析 gem5 的统计文件 ===
    all_stats = parse_gem5_stats(str(stats_path))
    if not all_stats:
        print("[ERROR] 未解析到任何统计数据，请检查 stats.txt 文件内容。")
        return
    stats = all_stats[-1]  # 取最后一个统计块（通常是最终结果）

    # === Step 3: 提取数据 - 改为包含匹配 ===
    results = []
    for interest_name in interest_names:
        matched = False
        for stat_name, stat_obj in stats.items():
            # 使用包含匹配而不是完全匹配
            if interest_name in stat_name:
                matched = True
                value = stat_obj.value
                # 每个匹配到的参数都单独记录，去掉description字段
                results.append({
                    "interest_name": interest_name,  # 原始的兴趣名称
                    "stat_name": stat_name,         # 匹配到的统计参数名
                    "value": value
                })
        
        # 如果没有任何匹配，记录一条未匹配的信息
        if not matched:
            results.append({
                "interest_name": interest_name,
                "stat_name": "NO_MATCH",
                "value": "N/A"
            })

    # === Step 4: 写入 CSV 文件 ===
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["interest_name", "stat_name", "value"])
        writer.writeheader()
        writer.writerows(results)

    # 统计信息
    total_interest = len(interest_names)
    total_matched_params = sum(1 for r in results if r["value"] != "N/A")
    matched_interest = len(set(r["interest_name"] for r in results if r["value"] != "N/A"))
    
    print(f"[OK] 已将解析结果写入 {output_csv}")
    print(f"[INFO] 兴趣参数数量: {total_interest}")
    print(f"[INFO] 匹配到参数的兴趣名称数量: {matched_interest}")
    print(f"[INFO] 匹配到的总参数数量: {total_matched_params}")
    
    # 如果有未匹配的兴趣名称，显示它们
    unmatched = set(r["interest_name"] for r in results if r["value"] == "N/A")
    if unmatched:
        print(f"[WARNING] 以下兴趣名称未匹配到任何参数:")
        for name in sorted(unmatched):
            print(f"  - {name}")


if __name__ == "__main__":
    main()