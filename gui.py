import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import re

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import pandas as pd

from utils.analyzer import Gem5Analyzer
from utils.plotter import plotter
from utils.parse_interest import parse_all_raw


class Gem5PlotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("gem5 Plot GUI")
        self.root.geometry("1000x720")
        self.root.minsize(900, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # ===== Analyzer =====
        self.analyzer = Gem5Analyzer()
        try:
            self.analyzer.load_results("results/parsed")
        except Exception:
            pass

        # ===== Data =====
        self._sync_data(rebuild_vars=True)

        # ===== UI =====
        self._build_ui()

        # ===== Plot state =====
        self.figure = None
        self.figure_canvas = None

        if self.analyzer.grouped_data.empty:
            messagebox.showinfo(
                "No parsed data",
                "No parsed data found. Please click 'Parse raw stats'.",
            )

    # -------------------------------------------------
    # Close
    # -------------------------------------------------
    def on_close(self):
        plt.close("all")
        self.root.destroy()

    # -------------------------------------------------
    # Data sync
    # -------------------------------------------------
    def _sync_data(self, rebuild_vars=False):
        df = self.analyzer.grouped_data

        if df.empty:
            self.benchmarks = []
            self.configs = []
            self.run_labels = []
            self.run_map = {}
            self.run_tags = {}
            self.tag_categories = {
                "bench": [],
                "scenario": [],
                "bloom": [],
            }
            self.metrics = []
            self.plot_types = plotter.supported_plot_types()
            if rebuild_vars:
                self.tag_vars = {
                    "bench": {},
                    "scenario": {},
                    "bloom": {},
                }
            return

        self.benchmarks = sorted(df["benchmark"].unique())
        self.configs = sorted(df["config"].unique())
        self.run_labels = []
        self.run_map = {}
        self.run_tags = {}
        category_tags = {
            "bench": set(),
            "scenario": set(),
            "bloom": set(),
        }
        pairs = df[["benchmark", "config"]].drop_duplicates()
        pairs = pairs.sort_values(["benchmark", "config"])
        for _, row in pairs.iterrows():
            label = f"{row['benchmark']}/{row['config']}"
            self.run_labels.append(label)
            self.run_map[label] = (row["benchmark"], row["config"])
            tags = {
                "bench": set(),
                "scenario": set(),
                "bloom": set(),
            }
            for token in re.split(r"[+/ ]+", row["benchmark"]):
                if token:
                    tags["bench"].add(token)
                    category_tags["bench"].add(token)

            for token in re.split(r"_+", row["config"]):
                if not token:
                    continue
                if token in ("cpu-only", "gpu-only", "cpu-gpu", "hetero"):
                    tags["scenario"].add(token)
                    category_tags["scenario"].add(token)
                elif token in ("with-bloom", "wo-bloom", "bloom-on", "bloom-off"):
                    tags["bloom"].add(token)
                    category_tags["bloom"].add(token)
                else:
                    tags["scenario"].add(token)
                    category_tags["scenario"].add(token)

            self.run_tags[label] = tags

        self.tag_categories = {
            "bench": sorted(category_tags["bench"]),
            "scenario": sorted(category_tags["scenario"]),
            "bloom": sorted(category_tags["bloom"]),
        }
        self.metrics = [
            c for c in df.columns if c not in ("benchmark", "config")
        ]
        self.plot_types = plotter.supported_plot_types()

        if rebuild_vars:
            self.tag_vars = {
                "bench": {
                    t: tk.BooleanVar(master=self.root, value=False)
                    for t in self.tag_categories["bench"]
                },
                "scenario": {
                    t: tk.BooleanVar(master=self.root, value=False)
                    for t in self.tag_categories["scenario"]
                },
                "bloom": {
                    t: tk.BooleanVar(master=self.root, value=False)
                    for t in self.tag_categories["bloom"]
                },
            }

    # -------------------------------------------------
    # UI build
    # -------------------------------------------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        self._build_left_panel(main)
        self._build_right_panel(main)

    # ---------------- Left panel ----------------
    def _build_left_panel(self, parent):
        left = ttk.Frame(parent)
        left.pack(side="left", fill="y", padx=10)
        left.config(width=320)
        left.pack_propagate(False)

        self._build_tag_panel(left)
        self._build_run_panel(left)
        self._build_metric_panel(left)
        self._build_action_panel(left)

    def _build_tag_panel(self, parent):
        ttk.Label(parent, text="Tags (per-category OR, across categories AND)").pack(anchor="w")
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)
        self.tag_frame = ttk.Frame(frame)
        self.tag_frame.pack(fill="x")
        self._refresh_tag_panel()

    def _build_run_panel(self, parent):
        ttk.Label(parent, text="Runs (filtered)").pack(anchor="w")

        frame = ttk.Frame(parent)
        frame.pack(fill="both", pady=5)

        self.run_list = tk.Listbox(
            frame, selectmode="extended", height=10
        )
        self.run_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.run_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.run_list.config(yscrollcommand=scrollbar.set)

        self.run_checked = set()
        self._refresh_run_list()
        self.run_list.bind("<Button-1>", self._on_run_list_click, add=True)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(
            btn_frame, text="Select All", command=self._select_all_runs
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            btn_frame, text="Clear", command=self._clear_all_runs
        ).pack(side="left", fill="x", expand=True)

    def _build_metric_panel(self, parent):
        ttk.Label(parent, text="Metric").pack(anchor="w")
        default_metric = self.metrics[0] if self.metrics else ""
        self.metric_var = tk.StringVar(value=default_metric)
        self.metric_combo = ttk.Combobox(
            parent,
            textvariable=self.metric_var,
            values=self.metrics,
            state="readonly",
        )
        self.metric_combo.pack(fill="x", pady=5)

        ttk.Label(parent, text="Plot Type").pack(anchor="w")
        default_plot = self.plot_types[0] if self.plot_types else ""
        self.plot_type_var = tk.StringVar(value=default_plot)
        self.plot_type_combo = ttk.Combobox(
            parent,
            textvariable=self.plot_type_var,
            values=self.plot_types,
            state="readonly",
        )
        self.plot_type_combo.pack(fill="x", pady=5)

    def _build_action_panel(self, parent):
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)

        frame = ttk.Frame(parent)
        frame.pack(fill="x")

        ttk.Button(
            frame, text="Parse raw stats", command=self.parse_raw_results
        ).pack(fill="x", pady=5)

        ttk.Button(
            frame, text="Draw Plot", command=self.draw_plot
        ).pack(fill="x", pady=5)

        ttk.Button(
            frame, text="Save Plot", command=self.save_plot
        ).pack(fill="x", pady=5)

    # ---------------- Right panel ----------------
    def _build_right_panel(self, parent):
        right = ttk.Frame(parent)
        right.pack(side="right", fill="both", expand=True)

        self.plot_frame = ttk.Frame(right)
        self.plot_frame.pack(fill="both", expand=True)

        self.log = tk.Text(right, height=10)
        self.log.pack(fill="x")
        self._log("GUI ready.")

    # -------------------------------------------------
    # Plot logic
    # -------------------------------------------------
    def draw_plot(self):
        plot_data = self._collect_plot_data()
        if plot_data is None:
            return
        self._render_plot(plot_data)

    def _collect_plot_data(self):
        if not self.run_list:
            messagebox.showwarning("Warning", "No runs available")
            return None

        selected = sorted(self.run_checked)
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one run")
            return None

        metric = self.metric_var.get()
        df = self.analyzer.grouped_data
        if df.empty:
            messagebox.showwarning("Warning", "No data to plot")
            return None

        values = {}
        for label in selected:
            bench, config = self.run_map[label]
            match = df[(df["benchmark"] == bench) & (df["config"] == config)]
            if match.empty or metric not in match.columns:
                values[label] = float("nan")
            else:
                values[label] = float(match.iloc[0][metric])

        return pd.Series(values, name=metric)

    def _render_plot(self, plot_data):
        self._clear_plot()

        self.root.update_idletasks()
        dpi = 100
        w = max(self.plot_frame.winfo_width() / dpi, 6)
        h = max(self.plot_frame.winfo_height() / dpi, 4)

        self.figure = plotter.plot(
            plot_type=self.plot_type_var.get(),
            data=plot_data,
            title=self.metric_var.get(),
            figsize=(w, h),
        )

        self.figure_canvas = FigureCanvasTkAgg(
            self.figure, master=self.plot_frame
        )
        self.figure_canvas.draw()
        self.figure_canvas.get_tk_widget().pack(fill="both", expand=True)

        self._log("Plot updated.")

    def _clear_plot(self):
        if self.figure_canvas:
            self.figure_canvas.get_tk_widget().destroy()
            self.figure_canvas = None
        if self.figure:
            plt.close(self.figure)
            self.figure = None

    # -------------------------------------------------
    # Save
    # -------------------------------------------------
    def save_plot(self):
        if not self.figure:
            messagebox.showwarning("Warning", "No plot to save")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
            ],
        )
        if not file_path:
            return

        self.figure.savefig(file_path, dpi=300)
        self._log(f"Saved plot to {file_path}")

    # -------------------------------------------------
    # Parse
    # -------------------------------------------------
    def parse_raw_results(self):
        try:
            base_dir = Path(__file__).resolve().parent
            success, total = parse_all_raw(
                raw_dir=base_dir / "results" / "raw",
                parsed_dir=base_dir / "results" / "parsed",
                interest_file=base_dir / "configs" / "interest.csv",
                verbose=False,
            )

            messagebox.showinfo(
                "Parse finished", f"Parsed {success}/{total} runs"
            )

            self.analyzer.load_results(str(base_dir / "results" / "parsed"))
            self._sync_data(rebuild_vars=False)
            self._refresh_tag_panel()
            self._refresh_run_list()
            self._refresh_metric_controls()
            self._log(f"Reloaded parsed data ({success}/{total})")

        except Exception as e:
            messagebox.showerror("Parse error", str(e))

    # -------------------------------------------------
    # Utils
    # -------------------------------------------------
    def _toggle_all(self, vars_dict, all_var):
        value = all_var.get()
        for v in vars_dict.values():
            v.set(value)

    def _update_all_state(self, vars_dict, all_var):
        if not vars_dict:
            all_var.set(False)
            return
        all_var.set(all(v.get() for v in vars_dict.values()))

    def _log(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _refresh_metric_controls(self):
        if not hasattr(self, "metric_combo") or not hasattr(self, "plot_type_combo"):
            return
        self.metric_combo["values"] = self.metrics
        self.plot_type_combo["values"] = self.plot_types
        self.metric_var.set(self.metrics[0] if self.metrics else "")
        self.plot_type_var.set(self.plot_types[0] if self.plot_types else "")

    def _refresh_tag_panel(self):
        if not hasattr(self, "tag_frame"):
            return
        for child in self.tag_frame.winfo_children():
            child.destroy()
        if not hasattr(self, "tag_vars"):
            self.tag_vars = {"bench": {}, "scenario": {}, "bloom": {}}

        for category in ("bench", "scenario", "bloom"):
            ttk.Label(self.tag_frame, text=category.capitalize()).pack(anchor="w", pady=(6, 0))
            if category not in self.tag_vars:
                self.tag_vars[category] = {}
            for tag in self.tag_categories.get(category, []):
                if tag not in self.tag_vars[category]:
                    self.tag_vars[category][tag] = tk.BooleanVar(master=self.root, value=False)
                cb = ttk.Checkbutton(
                    self.tag_frame,
                    text=tag,
                    variable=self.tag_vars[category][tag],
                    command=self._refresh_run_list,
                )
                cb.pack(anchor="w")

    def _refresh_run_list(self):
        if not self.run_list:
            return
        self.run_list.delete(0, "end")
        self.run_checked = set()

        active_tags = {
            "bench": [t for t, v in self.tag_vars.get("bench", {}).items() if v.get()],
            "scenario": [t for t, v in self.tag_vars.get("scenario", {}).items() if v.get()],
            "bloom": [t for t, v in self.tag_vars.get("bloom", {}).items() if v.get()],
        }
        for label in self.run_labels:
            tags = self.run_tags.get(label, {})
            if active_tags["bench"]:
                if not set(active_tags["bench"]).intersection(tags.get("bench", set())):
                    continue
            if active_tags["scenario"]:
                if not set(active_tags["scenario"]).intersection(tags.get("scenario", set())):
                    continue
            if active_tags["bloom"]:
                if not set(active_tags["bloom"]).intersection(tags.get("bloom", set())):
                    continue
            bench, config = self.run_map[label]
            self.run_list.insert("end", f"[ ] {bench}/{config}")
        self._sync_run_index()

    def _set_run_checked(self, label, checked):
        if label not in self.run_map:
            return
        bench, config = self.run_map[label]
        text = f"[{'x' if checked else ' '}] {bench}/{config}"
        idx = self.run_index.get(label)
        if idx is not None:
            self.run_list.delete(idx)
            self.run_list.insert(idx, text)
        if checked:
            self.run_checked.add(label)
        else:
            self.run_checked.discard(label)

    def _toggle_run_checked(self, label):
        checked = label in self.run_checked
        self._set_run_checked(label, not checked)

    def _select_all_runs(self):
        for label in self._visible_run_labels():
            self._set_run_checked(label, True)

    def _clear_all_runs(self):
        for label in list(self.run_checked):
            self._set_run_checked(label, False)

    def _sync_run_index(self):
        self.run_index = {}
        for idx, text in enumerate(self.run_list.get(0, "end")):
            if text.startswith("[ ] ") or text.startswith("[x] "):
                label = text[4:]
                if label in self.run_map:
                    self.run_index[label] = idx

    def _visible_run_labels(self):
        labels = []
        for text in self.run_list.get(0, "end"):
            if text.startswith("[ ] ") or text.startswith("[x] "):
                label = text[4:]
                if label in self.run_map:
                    labels.append(label)
        return labels

    def _on_run_list_click(self, event):
        idx = self.run_list.nearest(event.y)
        if idx < 0:
            return
        text = self.run_list.get(idx)
        if not (text.startswith("[ ] ") or text.startswith("[x] ")):
            return
        label = text[4:]
        if label in self.run_map:
            self._toggle_run_checked(label)
            return "break"


def main():
    root = tk.Tk()
    Gem5PlotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
