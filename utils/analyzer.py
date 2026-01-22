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
    "cpu_load_to_use_mean": {
        "patterns": [
            r"^system\.cpu\d+\.lsq0\.loadToUse::mean$",
        ],
        "op": "identity",
        "desc": "mean load-to-use latency (cycles) across CPUs",
    },
    "ruby_hit_latency_mean": {
        "patterns": [
            r"^(?:system\.ruby\.)?m_hitLatencyHistSeqr::mean$",
        ],
        "op": "identity",
        "desc": "Ruby sequencer hit latency mean",
    },
    "ruby_miss_latency_mean": {
        "patterns": [
            r"^(?:system\.ruby\.)?m_missLatencyHistSeqr::mean$",
        ],
        "op": "identity",
        "desc": "Ruby sequencer miss latency mean",
    },
    "mem_read_avg_lat": {
        "patterns": [
            r"^(?:system\.mem_ctrls\.)?requestorReadAvgLat::ruby\.dir_cntrl0$",
        ],
        "op": "identity",
        "desc": "Memory controller read avg latency (ticks)",
    },
    "mem_write_avg_lat": {
        "patterns": [
            r"^(?:system\.mem_ctrls\.)?requestorWriteAvgLat::ruby\.dir_cntrl0$",
        ],
        "op": "identity",
        "desc": "Memory controller write avg latency (ticks)",
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

    # =====================================================
    # Bloom Filter
    # =====================================================
    "bloom_total_read_checks": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?bloomTotalReadChecks$",
        ],
        "op": "identity",
        "desc": "Bloom total read checks",
    },
    "bloom_bypass_reads": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?bloomBypassReads$",
        ],
        "op": "identity",
        "desc": "Bloom bypass reads",
    },
    "bloom_non_bypass_reads": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?bloomNonBypassReads$",
        ],
        "op": "identity",
        "desc": "Bloom non-bypass reads",
    },
    "bloom_dirty_transitions": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?dirtyLineTransitions$",
        ],
        "op": "identity",
        "desc": "Bloom clean->dirty transitions",
    },
    "bloom_dirty_to_clean_transitions": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?dirtyToCleanTransitions$",
        ],
        "op": "identity",
        "desc": "Bloom dirty->clean transitions",
    },
    "bloom_counter_inc_total": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?bloomCounterIncTotal$",
        ],
        "op": "identity",
        "desc": "Bloom counter increment attempts",
    },
    "bloom_counter_dec_total": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.BloomFilter\.)?bloomCounterDecTotal$",
        ],
        "op": "identity",
        "desc": "Bloom counter decrement attempts",
    },

    # =====================================================
    # Ruby Traffic (MessageBuffer counts)
    # =====================================================
    "dir_request_in_msgs": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.)?(?:requestNetwork_in|requestFromCores)\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Dir requestNetwork_in message count",
    },
    "dir_request_out_msgs": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.)?(?:requestNetwork_out|requestToMemory)\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Dir requestNetwork_out message count",
    },
    "dir_response_in_msgs": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.)?(?:responseNetwork_in|responseFromMemory)\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Dir responseNetwork_in message count",
    },
    "dir_response_out_msgs": {
        "patterns": [
            r"^(?:system\.ruby\.dir_cntrl0\.)?(?:responseNetwork_out|responseToCore)\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Dir responseNetwork_out message count",
    },
    "bloom_req_from_cores": {
        "patterns": [
            r"^(?:system\.ruby\.)?bloom_cntrl0\.requestFromCores\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Bloom requestFromCores message count",
    },
    "bloom_req_to_dir": {
        "patterns": [
            r"^(?:system\.ruby\.)?bloom_cntrl0\.requestToDir\.m_msg_count$",
        ],
        "op": "identity",
        "desc": "Bloom requestToDir message count",
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
        if rule["op"] == "sum":
            cols = [c for c in df.columns if re.match(rule["patterns"][0], c)]
            if not cols:
                return float("nan")
            return float(df[cols].sum(axis=1).mean())

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
            if "benchmark" in df.columns and "config" in df.columns:
                benchmark = str(df["benchmark"].iloc[0])
                config = str(df["config"].iloc[0])
            else:
                parts = csv_file.stem.split("_", 1)
                benchmark = parts[0]
                config = parts[1] if len(parts) > 1 else "default"

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
