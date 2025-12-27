import pandas as pd
from pathlib import Path
from typing import List
import logging
import re

logger = logging.getLogger(__name__)

METRIC_RULES = {

    # =====================================================
    # CPU IPC
    # =====================================================
    "cpu_ipc": {
        "patterns": [
            r"^system\.cpu\d+\.ipc$",
        ],
        "op": "identity",   # 单向量：保持
        "desc": "mean IPC across CPU cores",
    },

    # =====================================================
    # CPU committed IPC
    # =====================================================
    "cpu_committed_ipc": {
        "patterns": [
            r"^system\.cpu\d+\.commitStats\d+\.ipc$",
        ],
        "op": "identity",
        "desc": "mean committed IPC across CPU cores",
    },

    # =====================================================
    # GPU IPC (CUs)
    # =====================================================
    "gpu_ipc": {
        "patterns": [
            r"^system\.cpu\d+\.CUs\d+\.ipc$",
        ],
        "op": "identity",
        "desc": "mean IPC across GPU compute units",
    },

    # =====================================================
    # L3 Cache Hit Rate
    # =====================================================
    "L3_cache_hit_rate": {
        "patterns": [
            r"^L3CacheMemory\.m_demand_hits$",
            r"^L3CacheMemory\.m_demand_accesses$",
        ],
        "op": "ratio",   # pattern0 / pattern1
        "desc": "L3 cache hit rate",
    },
}


# ============================================================
# ParamGrouper
# ============================================================

class ParamGrouper:
    @staticmethod
    def build_vectors(df: pd.DataFrame, patterns: List[str]):
        vectors = []
        for pat in patterns:
            cols = [c for c in df.columns if re.match(pat, c)]
            if not cols:
                vectors.append(None)
            else:
                vectors.append(df[cols].mean(axis=1))
        return vectors

    @staticmethod
    def apply_op(vectors, op):
        if op == "identity":
            return vectors[0]

        if op == "ratio" and len(vectors) == 2:
            return vectors[0] / vectors[1]

        if isinstance(op, tuple) and op[0] == "scale":
            return vectors[0] * op[1]

        return None

    @staticmethod
    def compute_metric(df: pd.DataFrame, rule: dict) -> float:
        vectors = ParamGrouper.build_vectors(df, rule["patterns"])
        if any(v is None for v in vectors):
            return float("nan")

        final_vec = ParamGrouper.apply_op(vectors, rule["op"])
        if final_vec is None:
            return float("nan")

        # 对时间/样本维度取均值 → scalar
        return float(final_vec.mean())




# ============================================================
# Analyzer
# ============================================================
class Gem5Analyzer:
    """gem5分析器 - 使用独立的绘图模块"""
    
    def __init__(self):
        self.raw_data = pd.DataFrame()
        self.grouped_data = pd.DataFrame()
        self.metric_executor = ParamGrouper()
        self.metadata = {}
    
    def load_results(self, results_dir: str):
        results_dir = Path(results_dir)
        records = []

        for csv_file in results_dir.glob("*.csv"):
            df = pd.read_csv(csv_file)

            # benchmark / config
            benchmark = csv_file.stem.split("_")[0]
            config = "default"

            record = {
                "benchmark": benchmark,
                "config": config,
            }

            for metric, rule in METRIC_RULES.items():
                try:
                    record[metric] = self.metric_executor.compute_metric(df, rule)
                except Exception as e:
                    logger.error(f"Failed to compute {metric} for {csv_file}: {e}")
                    record[metric] = float("nan")

            records.append(record)

        if not records:
            return

        self.grouped_data = pd.DataFrame.from_records(records)
        self._create_metadata()

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    def _create_metadata(self):
        self.metadata = {
            "num_benchmarks": self.grouped_data["benchmark"].nunique(),
            "num_configs": self.grouped_data["config"].nunique(),
            "num_metrics": len(
                [c for c in self.grouped_data.columns if c not in ("benchmark", "config")]
            ),
        }

    # --------------------------------------------------------
    # Query APIs
    # --------------------------------------------------------

    def list_benchmarks(self):
        return sorted(self.grouped_data["benchmark"].unique().tolist())

    def list_configs(self):
        return sorted(self.grouped_data["config"].unique().tolist())

    def list_metrics(self):
        meta = {"benchmark", "config"}
        return sorted([c for c in self.grouped_data.columns if c not in meta])

    def select(
        self,
        metric: str,
        benchmarks: List[str],
        configs: List[str],
        agg: str = "mean",
    ):
        df = self.grouped_data
        if df.empty:
            return pd.DataFrame()

        if metric not in df.columns:
            raise ValueError(f"metric '{metric}' not found")

        df = df[df["benchmark"].isin(benchmarks)]
        df = df[df["config"].isin(configs)]

        if df.empty:
            return pd.DataFrame()

        if len(benchmarks) > 1 and len(configs) == 1:
            return df.groupby("benchmark")[metric].agg(agg).to_frame(metric)

        if len(benchmarks) == 1 and len(configs) > 1:
            return df.groupby("config")[metric].agg(agg).to_frame(metric)

        if len(benchmarks) > 1 and len(configs) > 1:
            return df.pivot_table(
                index="benchmark",
                columns="config",
                values=metric,
                aggfunc=agg,
            )

        return pd.DataFrame()