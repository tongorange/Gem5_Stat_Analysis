import re
from typing import Dict, List, Optional, Any
import pandas as pd

class Gem5Stat:
    """gem5统计项类"""
    def __init__(self, line: str):
        self.parse_line(line)
    
    def parse_line(self, line: str):
        line = line.strip()
        
        if "|" in line:
            parts = line.split("#", 1)
            self.name = line.split()[0]
            self.value = None
        elif match := re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+|nan|inf)\s+# (.*)', line):
            self.name = match.group(1)
            self.value = self._parse_value(match.group(2))
        elif match := re.match(r'([\w.:\-+]+)\s+([-+]?[0-9.eE]+)\s+\(.*\)', line):
            self.name = match.group(1)
            self.value = self._parse_value(match.group(2))
        else:
            raise ValueError(f"Cannot parse line: {line}")
    
    def _parse_value(self, val: str) -> Optional[Any]:
        if val == "nan":
            return None
        elif val == "inf":
            return 1e99
        elif "%" in val:
            return float(val.strip("%"))
        elif "." in val:
            return float(val)
        elif val.lstrip('-').isdigit():
            return int(val)
        else:
            try:
                return float(val)
            except:
                return str(val)

class Gem5StatsParser:
    """gem5统计解析器"""

    def __init__(self, interest_patterns: List[str]):
        self.interest_patterns = [re.compile(p) for p in interest_patterns if p]
    
    def parse_stats_file(self, stats_file: str) -> Dict[str, Any]:
        """解析单个stats.txt文件"""
        with open(stats_file, 'r') as f:
            lines = f.readlines()
        
        stats = {}
        in_stat_instance = False
        
        for line in lines:
            if line.strip() == '---------- Begin Simulation Statistics ----------':
                in_stat_instance = True
                stats = {}
            elif line.strip() == '---------- End Simulation Statistics   ----------':
                in_stat_instance = False
                break  # 只取第一个统计块
            elif in_stat_instance and line.strip():
                try:
                    stat = Gem5Stat(line)
                    stats[stat.name] = stat.value
                except ValueError:
                    continue
        
        return stats
    
    def extract_interest_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """从统计中提取感兴趣的参数（正则匹配）"""
        results = {}

        for stat_name, stat_value in stats.items():
            for pattern in self.interest_patterns:
                if pattern.match(stat_name):
                    results[stat_name] = stat_value
                    break

        return results
    
    def parse_and_extract(self, stats_file: str) -> pd.DataFrame:
        """解析并提取统计数据，返回DataFrame"""
        stats = self.parse_stats_file(stats_file)
        interest_stats = self.extract_interest_stats(stats)
        
        return pd.DataFrame([interest_stats])
