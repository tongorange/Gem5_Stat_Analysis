#!/usr/bin/env python3
import os
import json
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import time

from utils.analyzer import Gem5Analyzer
from utils.parse_interest import parse_all_raw


RAW_DIR = Path(__file__).resolve().parent / "results" / "raw"
PARSED_DIR = Path(__file__).resolve().parent / "results" / "parsed"
INTEREST_FILE = Path(__file__).resolve().parent / "configs" / "interest.csv"
PRESET_FILE = Path(__file__).resolve().parent / "presets.json"


@st.cache_data(show_spinner=False, ttl=10)
def load_parsed():
    analyzer = Gem5Analyzer()
    analyzer.load_results(str(PARSED_DIR))
    return analyzer.grouped_data.copy()


def parse_raw():
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    success, total = parse_all_raw(
        raw_dir=RAW_DIR,
        parsed_dir=PARSED_DIR,
        interest_file=INTEREST_FILE,
        verbose=False,
    )
    st.success(f"Parsed {success}/{total} runs")


def load_presets():
    if not PRESET_FILE.exists():
        return {}
    try:
        with PRESET_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("presets", {})
    except Exception:
        return {}


def save_presets(presets):
    payload = {"presets": presets}
    with PRESET_FILE.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def extract_tags(df):
    tags = {
        "cpu_bench": set(),
        "gpu_bench": set(),
        "scenario": set(),
        "bloom": set(),
        "gate": set(),
        "gate_pct": set(),
    }
    run_map = {}
    run_tags = {}

    for _, row in df[["benchmark", "config"]].drop_duplicates().iterrows():
        bench = row["benchmark"]
        config = row["config"]

        config_tokens = [t for t in re.split(r"_+", config) if t]
        display_config = config
        if "wo-bloom" in config_tokens and "gate-" in display_config:
            display_config = re.sub(r"_gate-[^_]+", "", display_config)

        label = f"{bench}/{display_config}"
        run_map[label] = (bench, config)

        t = {
            "cpu_bench": set(),
            "gpu_bench": set(),
            "scenario": set(),
            "bloom": set(),
            "gate": set(),
            "gate_pct": set(),
        }
        for token in config_tokens:
            if token in ("cpu-only", "gpu-only", "cpu-gpu", "hetero"):
                t["scenario"].add(token)
                tags["scenario"].add(token)
            elif token in ("with-bloom", "wo-bloom", "bloom-on", "bloom-off"):
                t["bloom"].add(token)
                tags["bloom"].add(token)
            elif token.startswith("gate-"):
                if "wo-bloom" not in config_tokens:
                    if token == "gate-off":
                        t["gate"].add("gate-off")
                        tags["gate"].add("gate-off")
                    else:
                        t["gate"].add("gate-on")
                        tags["gate"].add("gate-on")
                        m = re.match(r"gate-(\\d+)p", token)
                        if m:
                            pct = m.group(1) + "%"
                            t["gate_pct"].add(pct)
                            tags["gate_pct"].add(pct)
            else:
                t["scenario"].add(token)
                tags["scenario"].add(token)

        if "+" in bench:
            cpu_bench, gpu_bench = bench.split("+", 1)
            t["cpu_bench"].add(cpu_bench)
            t["gpu_bench"].add(gpu_bench)
            tags["cpu_bench"].add(cpu_bench)
            tags["gpu_bench"].add(gpu_bench)
        else:
            if "cpu-only" in t["scenario"]:
                t["cpu_bench"].add(bench)
                tags["cpu_bench"].add(bench)
            elif "gpu-only" in t["scenario"]:
                t["gpu_bench"].add(bench)
                tags["gpu_bench"].add(bench)
            else:
                t["gpu_bench"].add(bench)
                tags["gpu_bench"].add(bench)

        run_tags[label] = t

    tags = {k: sorted(v) for k, v in tags.items()}
    return tags, run_map, run_tags


st.set_page_config(page_title="gem5 Results", layout="wide")

st.sidebar.title("gem5 Results")

if st.sidebar.button("Parse raw stats"):
    parse_raw()
    st.cache_data.clear()


try:
    df = load_parsed()
except Exception:
    df = pd.DataFrame()

if df.empty:
    st.info("No parsed data. Click 'Parse raw stats'.")
    st.stop()

tags, run_map, run_tags = extract_tags(df)

presets = load_presets()
st.sidebar.subheader("Presets")
preset_names = ["(none)"] + sorted(presets.keys())
selected_preset = st.sidebar.selectbox("Preset", preset_names)
if st.sidebar.button("Apply preset") and selected_preset != "(none)":
    preset = presets[selected_preset]
    st.session_state["cpu_bench_sel"] = preset.get("cpu_bench", [])
    st.session_state["gpu_bench_sel"] = preset.get("gpu_bench", [])
    st.session_state["scenario_sel"] = preset.get("scenario", [])
    st.session_state["bloom_sel"] = preset.get("bloom", [])
    st.session_state["gate_sel"] = preset.get("gate", [])
    st.session_state["gate_pct_sel"] = preset.get("gate_pct", [])
    st.session_state["metric_sel"] = preset.get("metric", "")

preset_name = st.sidebar.text_input("Save preset name", value="")
if st.sidebar.button("Save preset"):
    name = preset_name.strip()
    if not name:
        st.sidebar.error("Preset name required")
    else:
        presets[name] = {
            "cpu_bench": st.session_state.get("cpu_bench_sel", []),
            "gpu_bench": st.session_state.get("gpu_bench_sel", []),
            "scenario": st.session_state.get("scenario_sel", []),
            "bloom": st.session_state.get("bloom_sel", []),
            "gate": st.session_state.get("gate_sel", []),
            "gate_pct": st.session_state.get("gate_pct_sel", []),
            "metric": st.session_state.get("metric_sel", ""),
        }
        save_presets(presets)
        st.sidebar.success(f"Saved preset: {name}")

st.sidebar.subheader("Filters")
st.sidebar.caption("Group OR within category, AND across categories")

if "cpu_bench_sel" not in st.session_state:
    st.session_state["cpu_bench_sel"] = []
if "gpu_bench_sel" not in st.session_state:
    st.session_state["gpu_bench_sel"] = []
if "scenario_sel" not in st.session_state:
    st.session_state["scenario_sel"] = []
if "bloom_sel" not in st.session_state:
    st.session_state["bloom_sel"] = []
if "gate_sel" not in st.session_state:
    st.session_state["gate_sel"] = []
if "gate_pct_sel" not in st.session_state:
    st.session_state["gate_pct_sel"] = []

selected_cpu = st.sidebar.multiselect(
    "CPU Bench",
    tags["cpu_bench"],
    key="cpu_bench_sel",
)  # OR

gpu_select_all = st.sidebar.checkbox("Select all GPU benches", value=False)
if gpu_select_all:
    st.session_state["gpu_bench_sel"] = tags["gpu_bench"]
selected_gpu = st.sidebar.multiselect(
    "GPU Bench",
    tags["gpu_bench"],
    key="gpu_bench_sel",
)  # OR

selected_scenario = st.sidebar.multiselect(
    "Scenario",
    tags["scenario"],
    key="scenario_sel",
)  # OR
selected_bloom = st.sidebar.multiselect(
    "Bloom",
    tags["bloom"],
    key="bloom_sel",
)  # OR

selected_gate = st.sidebar.multiselect(
    "Gate",
    tags["gate"],
    key="gate_sel",
)  # OR
st.sidebar.caption("Gate filters only apply to with-bloom runs")

selected_gate_pct = st.sidebar.multiselect(
    "Gate Threshold",
    tags["gate_pct"],
    key="gate_pct_sel",
)  # OR

metrics = [c for c in df.columns if c not in ("benchmark", "config")]
if "metric_sel" not in st.session_state:
    st.session_state["metric_sel"] = metrics[0] if metrics else ""
metric = st.sidebar.selectbox("Metric", metrics, key="metric_sel")

# Build filtered run list
filtered_runs = []
for label, (bench, config) in run_map.items():
    t = run_tags[label]
    if selected_cpu and not set(selected_cpu).intersection(t["cpu_bench"]):
        continue
    if selected_gpu and not set(selected_gpu).intersection(t["gpu_bench"]):
        continue
    if selected_scenario and not set(selected_scenario).intersection(t["scenario"]):
        continue
    if selected_bloom and not set(selected_bloom).intersection(t["bloom"]):
        continue

    has_wo = "wo-bloom" in t["bloom"]
    has_with = "with-bloom" in t["bloom"] or "bloom-on" in t["bloom"]

    # Gate filtering rules:
    # - wo-bloom is never filtered out by gate selection.
    # - if both with-bloom and wo-bloom selected and no gate chosen, keep only gate-off for with-bloom.
    gate_sel = set(selected_gate)
    pct_sel = set(selected_gate_pct)
    if pct_sel and "gate-on" not in gate_sel:
        gate_sel.add("gate-on")

    if gate_sel:
        if has_with and not gate_sel.intersection(t["gate"]):
            continue
        if has_with and "gate-on" in gate_sel and pct_sel:
            if not pct_sel.intersection(t["gate_pct"]):
                continue
    else:
        if has_with and ("wo-bloom" in selected_bloom):
            if "gate-off" not in t["gate"]:
                continue

    filtered_runs.append(label)

st.sidebar.subheader("Runs")
filtered_benches = sorted({run_map[label][0] for label in filtered_runs})
run_select_all = st.sidebar.checkbox("Select all runs (benches)", value=False)
if "bench_sel" not in st.session_state:
    st.session_state["bench_sel"] = []
if run_select_all:
    st.session_state["bench_sel"] = filtered_benches
selected_benches = st.sidebar.multiselect("Select benches", filtered_benches, key="bench_sel")

st.title("gem5 Results")

if not selected_benches:
    st.info("Select runs on the left to plot.")
    st.stop()

st.subheader("Command Generator")
def _bench_to_gpu(name):
    if "+" in name:
        return name.split("+", 1)[1]
    return name

gpu_benches = sorted({_bench_to_gpu(b) for b in selected_benches})
bench_cmds = []
scenario_arg = ",".join(selected_scenario) if selected_scenario else ""
bloom_arg = ",".join(selected_bloom) if selected_bloom else ""
gate_items = []
if "gate-off" in selected_gate:
    gate_items.append("off")
gate_on = "gate-on" in selected_gate
if selected_gate_pct:
    gate_on = True
    gate_items.extend(selected_gate_pct)
elif gate_on:
    default_pcts = tags["gate_pct"] if tags["gate_pct"] else ["10%", "30%", "50%", "70%"]
    gate_items.extend(default_pcts)
gate_arg = ",".join(gate_items) if gate_items else ""

for b in gpu_benches:
    cmd_lines = [
        f"BENCH={b}",
        f"SCENARIO_LIST={scenario_arg}" if scenario_arg else "",
        f"BLOOM_LIST={bloom_arg}" if bloom_arg else "",
        f"GATE_LIST={gate_arg}" if gate_arg else "",
        "./run_bloom_experiments.sh",
    ]
    bench_cmds.append(" ".join([c for c in cmd_lines if c]))

cmd = "\n".join(bench_cmds)
st.code(cmd, language="bash")
st.caption("Run the command above in a terminal. After it finishes, click 'Parse raw stats'.")

selected_runs = [
    label for label in filtered_runs
    if run_map[label][0] in selected_benches
]

values = {}
for label in selected_runs:
    bench, config = run_map[label]
    match = df[(df["benchmark"] == bench) & (df["config"] == config)]
    if match.empty or metric not in match.columns:
        values[label] = float("nan")
    else:
        values[label] = float(match.iloc[0][metric])

benches = sorted({run_map[l][0] for l in selected_runs})
configs = sorted({run_map[l][1] for l in selected_runs})

st.subheader(metric)

if len(benches) > 1 or len(configs) > 1:
    data = pd.DataFrame(index=benches, columns=configs, dtype=float)
    for label in selected_runs:
        bench, config = run_map[label]
        data.loc[bench, config] = values[label]
    st.dataframe(data)
    fig, ax = plt.subplots(figsize=(10, 4))
    cols = list(data.columns)
    idx = list(data.index)
    n_groups = len(idx)
    n_cols = len(cols)
    width = 0.8 / max(n_cols, 1)
    base_color = ["#614099", "#FABB6E", "#FC8002"]
    highlight = "#000000"

    for j, col in enumerate(cols):
        x = [i + j * width for i in range(n_groups)]
        vals = [data.loc[idx[i], col] for i in range(n_groups)]
        colors = []
        for i, v in enumerate(vals):
            row = data.loc[idx[i]]
            row_max = row.max()
            if pd.notna(v) and pd.notna(row_max) and v == row_max:
                colors.append(base_color[j % len(base_color)])
            else:
                colors.append(base_color[j % len(base_color)])
        bars = ax.bar(
            x,
            vals,
            width=width,
            color=colors,
            label=col,
        )

    ax.set_xticks([i + width * (n_cols - 1) / 2 for i in range(n_groups)])
    ax.set_xticklabels(idx, rotation=45, ha="right")
    # mark max bar in each group
    for i in range(n_groups):
        row = data.loc[idx[i]]
        if row.isna().all():
            continue
        max_col = row.idxmax()
        j = cols.index(max_col)
        x = i + j * width
        y = row[max_col]
        ax.scatter([x], [y], marker="^", color=highlight, zorder=5)
    ax.set_ylabel(metric)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    if leg:
        for lh in leg.legend_handles:
            lh.set_linewidth(0.0)
            lh.set_edgecolor("none")
    fig.tight_layout()
    st.pyplot(fig)
else:
    s = pd.Series(values, name=metric)
    st.dataframe(s)
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = []
    max_val = s.max()
    for v in s.values:
        colors.append("#614099")
    ax.bar(s.index, s.values, color=colors)
    if pd.notna(max_val):
        max_idx = s.idxmax()
        ax.scatter([max_idx], [max_val], marker="^", color=highlight, zorder=5)
    ax.set_xticklabels(s.index, rotation=45, ha="right")
    ax.set_ylabel(metric)
    st.pyplot(fig)
