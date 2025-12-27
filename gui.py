import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from utils.analyzer import Gem5Analyzer
from utils.plotter import plotter
from utils.parse_interest import parse_all_raw


class Gem5PlotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("gem5 Plot GUI")
        self.root.geometry("900x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # ===== Analyzer =====
        self.analyzer = Gem5Analyzer()
        self.analyzer.load_results("results/parsed")

        if self.analyzer.grouped_data.empty:
            messagebox.showerror("Error", "No parsed data found")
            root.destroy()
            return

        # ===== Data =====
        self._sync_data(rebuild_vars=True)

        # ===== UI =====
        self._build_ui()

        # ===== Plot state =====
        self.figure = None
        self.figure_canvas = None

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

        self.benchmarks = sorted(df["benchmark"].unique())
        self.configs = sorted(df["config"].unique())
        self.metrics = [
            c for c in df.columns if c not in ("benchmark", "config")
        ]
        self.plot_types = plotter.supported_plot_types()

        if rebuild_vars:
            self.benchmark_vars = {
                b: tk.BooleanVar(master=self.root, value=False) for b in self.benchmarks
            }
            self.config_vars = {
                c: tk.BooleanVar(master=self.root, value=False) for c in self.configs
            }
            self.benchmark_all_var = tk.BooleanVar(master=self.root, value=False)
            self.config_all_var = tk.BooleanVar(master=self.root, value=False)

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

        self._build_benchmark_panel(left)
        self._build_config_panel(left)
        self._build_metric_panel(left)
        self._build_action_panel(left)

    def _build_benchmark_panel(self, parent):
        ttk.Label(parent, text="Benchmark").pack(anchor="w")

        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            frame,
            text="Select All",
            variable=self.benchmark_all_var,
            command=lambda: self._toggle_all(
                self.benchmark_vars, self.benchmark_all_var
            ),
        ).pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=3)

        for b, var in self.benchmark_vars.items():
            ttk.Checkbutton(frame, text=b, variable=var).pack(anchor="w")
            var.trace_add(
                "write",
                lambda *_: self._update_all_state(
                    self.benchmark_vars, self.benchmark_all_var
                ),
            )

    def _build_config_panel(self, parent):
        ttk.Label(parent, text="Config").pack(anchor="w")

        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            frame,
            text="Select All",
            variable=self.config_all_var,
            command=lambda: self._toggle_all(
                self.config_vars, self.config_all_var
            ),
        ).pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=3)

        for c, var in self.config_vars.items():
            ttk.Checkbutton(frame, text=c, variable=var).pack(anchor="w")
            var.trace_add(
                "write",
                lambda *_: self._update_all_state(
                    self.config_vars, self.config_all_var
                ),
            )

    def _build_metric_panel(self, parent):
        ttk.Label(parent, text="Metric").pack(anchor="w")
        self.metric_var = tk.StringVar(value=self.metrics[0])
        ttk.Combobox(
            parent,
            textvariable=self.metric_var,
            values=self.metrics,
            state="readonly",
        ).pack(fill="x", pady=5)

        ttk.Label(parent, text="Plot Type").pack(anchor="w")
        self.plot_type_var = tk.StringVar(value=self.plot_types[0])
        ttk.Combobox(
            parent,
            textvariable=self.plot_type_var,
            values=self.plot_types,
            state="readonly",
        ).pack(fill="x", pady=5)

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
        selected_benchmarks = [
            b for b, v in self.benchmark_vars.items() if v.get()
        ]
        selected_configs = [
            c for c, v in self.config_vars.items() if v.get()
        ]

        if not selected_benchmarks:
            messagebox.showwarning("Warning", "Please select at least one benchmark")
            return None

        if not selected_configs:
            messagebox.showwarning("Warning", "Please select at least one config")
            return None

        try:
            data = self.analyzer.select(
                metric=self.metric_var.get(),
                benchmarks=selected_benchmarks,
                configs=selected_configs,
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return None

        if data.empty:
            messagebox.showwarning("Warning", "No data to plot")
            return None

        return data

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
            success, total = parse_all_raw(
                raw_dir=Path("results/raw"),
                parsed_dir=Path("results/parsed"),
                interest_file=Path("configs/interest.csv"),
                verbose=False,
            )

            messagebox.showinfo(
                "Parse finished", f"Parsed {success}/{total} runs"
            )

            self.analyzer.load_results("results/parsed")
            self._sync_data(rebuild_vars=False)
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


def main():
    root = tk.Tk()
    Gem5PlotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
