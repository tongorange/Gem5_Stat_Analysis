"""
绘图工具模块 - 专门负责各种图表绘制
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 设置matplotlib样式
plt.style.use('default')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300

class PlotFormatter:
    """图表格式化器"""
    
    @staticmethod
    def format_value(val: float) -> str:
        """根据数值大小智能格式化数字"""
        if pd.isna(val) or val == 0:
            return "0"
        
        abs_val = abs(val)
        if abs_val < 0.001:
            return f"{val:.1e}"
        elif abs_val >= 1e9:
            return f"{val/1e9:.1f}B"
        elif abs_val >= 1e6:
            return f"{val/1e6:.1f}M"
        elif abs_val >= 1000:
            return f"{val/1000:.1f}K"
        elif abs_val < 1:
            return f"{val:.3f}"
        else:
            return f"{val:.2f}"
    
    @staticmethod
    def create_annot_matrix(data: pd.DataFrame) -> np.ndarray:
        """创建注解矩阵"""
        annot_matrix = np.empty_like(data.values, dtype=object)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                annot_matrix[i, j] = PlotFormatter.format_value(data.iat[i, j])
        return annot_matrix
    
    @staticmethod
    def set_chinese_font():
        """设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass

class HeatmapPlotter:

    def __init__(self):
        self.formatter = PlotFormatter()

    def create_heatmap(
        self,
        data: pd.DataFrame,
        title: str = "Performance Heatmap",
        figsize=(14, 10),
        cmap="YlOrRd",
        show_values=True,
        rotate_x_labels=True,
        save: bool = False,
        output_file: Optional[str] = None,
    ):
        if data.empty:
            logger.warning("没有数据可以绘制热力图")
            return None

        plot_data = data.fillna(0)

        fig, ax = plt.subplots(figsize=figsize)

        annot = self.formatter.create_annot_matrix(plot_data) if show_values else None

        sns.heatmap(
            plot_data,
            annot=annot,
            fmt="",
            cmap=cmap,
            linewidths=0.5,
            linecolor="gray",
            cbar_kws={"shrink": 0.8, "label": "Value"},
            annot_kws={"size": 9},
            ax=ax,
        )

        ax.set_title(title, fontsize=14, pad=20)
        ax.set_xlabel("Metrics")
        ax.set_ylabel("Benchmarks")

        if rotate_x_labels:
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")

        fig.tight_layout()

        if save:
            if not output_file:
                raise ValueError("output_file required when save=True")
            fig.savefig(output_file, dpi=300, bbox_inches="tight")

        return fig


class BarPlotter:

    @staticmethod
    def create_bar_chart(
        data: pd.DataFrame,
        title="Performance Comparison",
        figsize=(12, 6),
        stacked=False,
        show_values=True,
        rotation=45,
        save: bool = False,
        output_file: Optional[str] = None,
    ):
        if data.empty:
            logger.warning("没有数据可以绘制条形图")
            return None

        fig, ax = plt.subplots(figsize=figsize)

        if isinstance(data, pd.Series):
            data.plot(kind="bar", ax=ax, color="steelblue")
        else:
            data.plot(kind="bar", stacked=stacked, ax=ax)

        ax.set_title(title, fontsize=14, pad=20)
        ax.set_ylabel("Value")

        if rotation:
            ax.set_xticklabels(ax.get_xticklabels(), rotation=rotation, ha="right")

        if show_values:
            if isinstance(data, pd.Series):
                for i, v in enumerate(data):
                    ax.text(i, v, PlotFormatter.format_value(v), ha="center", va="bottom")
            else:
                for c in ax.containers:
                    ax.bar_label(c, fmt=lambda x: PlotFormatter.format_value(x))

        if not isinstance(data, pd.Series):
            ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        fig.tight_layout()

        if save:
            if not output_file:
                raise ValueError("output_file required when save=True")
            fig.savefig(output_file, dpi=300, bbox_inches="tight")

        return fig


class LinePlotter:

    @staticmethod
    def create_line_chart(
        data: pd.DataFrame,
        title="Performance Trend",
        figsize=(12, 6),
        marker="o",
        grid=True,
        save: bool = False,
        output_file: Optional[str] = None,
    ):
        if data.empty:
            return None

        fig, ax = plt.subplots(figsize=figsize)

        if isinstance(data, pd.Series):
            ax.plot(data.index, data.values, marker=marker, label=data.name)
        else:
            for col in data.columns:
                ax.plot(data.index, data[col], marker=marker, label=col)

        ax.set_title(title)
        ax.set_ylabel("Value")
        ax.legend()

        if grid:
            ax.grid(True, linestyle="--", alpha=0.6)

        fig.tight_layout()

        if save:
            if not output_file:
                raise ValueError("output_file required when save=True")
            fig.savefig(output_file, dpi=300, bbox_inches="tight")

        return fig

class BoxPlotter:

    @staticmethod
    def create_box_plot(
        data: pd.DataFrame,
        title="Performance Distribution",
        figsize=(12, 6),
        rotation=45,
        save: bool = False,
        output_file: Optional[str] = None,
    ):
        if data.empty:
            return None

        fig, ax = plt.subplots(figsize=figsize)

        data.plot(
            kind="box",
            ax=ax,
            patch_artist=True,
            boxprops=dict(facecolor="lightblue"),
            medianprops=dict(color="red"),
        )

        ax.set_title(title)

        if rotation:
            ax.set_xticklabels(ax.get_xticklabels(), rotation=rotation, ha="right")

        fig.tight_layout()

        if save:
            if not output_file:
                raise ValueError("output_file required when save=True")
            fig.savefig(output_file, dpi=300, bbox_inches="tight")

        return fig


class ScatterPlotter:
    """散点图绘制器"""
    
    @staticmethod
    def create_scatter_plot(x_data: pd.Series,
                           y_data: pd.Series,
                           title: str = "Correlation Analysis",
                           x_label: str = "X",
                           y_label: str = "Y",
                           figsize: Tuple[int, int] = (10, 6),
                           output_file: Optional[str] = None,
                           color_by: Optional[pd.Series] = None):
        """
        创建散点图
        
        Args:
            x_data: X轴数据
            y_data: Y轴数据
            title: 图表标题
            x_label: X轴标签
            y_label: Y轴标签
            figsize: 图表大小
            output_file: 输出文件路径
            color_by: 按此序列着色
        """
        if len(x_data) != len(y_data):
            logger.warning("X和Y数据长度不匹配")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制散点图
        if color_by is not None and len(color_by) == len(x_data):
            scatter = ax.scatter(x_data, y_data, c=color_by, cmap='viridis', alpha=0.7)
            plt.colorbar(scatter, ax=ax, label='Color Value')
        else:
            ax.scatter(x_data, y_data, alpha=0.7)
        
        # 添加回归线（可选）
        if len(x_data) > 1:
            try:
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                ax.plot(x_data, p(x_data), "r--", alpha=0.8, label=f'Regression: y={z[0]:.2f}x+{z[1]:.2f}')
                ax.legend()
            except:
                pass
        
        # 设置标题和标签
        ax.set_title(title, fontsize=14, pad=20)
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        
        # 显示网格
        ax.grid(True, linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"散点图已保存到: {output_file}")
        
        return fig, ax

class PlotManager:
    """绘图管理器 - 统一的绘图接口"""
    
    def __init__(self):
        self.heatmap = HeatmapPlotter()
        self.bar = BarPlotter()
        self.line = LinePlotter()
        self.box = BoxPlotter()
        self.scatter = ScatterPlotter()
    
    def save_all_figures(self, base_dir: str, prefix: str = ""):
        """保存当前所有打开的图表"""
        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        
        for i, fig in enumerate(plt.get_fignums()):
            fig_obj = plt.figure(fig)
            filename = base_path / f"{prefix}figure_{i+1}.png"
            fig_obj.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {filename}")
    
    @staticmethod
    def close_all_figures():
        """关闭所有图表"""
        plt.close('all')
        
    def __init__(self):
        self.heatmap = HeatmapPlotter()
        self.bar = BarPlotter()
        self.line = LinePlotter()
        self.box = BoxPlotter()
        self.scatter = ScatterPlotter()

        # === 给 GUI 用的注册表 ===
        self._plot_registry = {
            "bar": self._plot_bar,
            "line": self._plot_line,
            "heatmap": self._plot_heatmap,
            "box": self._plot_box,
            "scatter": self._plot_scatter,
        }

    # ========= GUI 接口 =========

    def supported_plot_types(self):
        """返回 GUI 可用的图类型"""
        return list(self._plot_registry.keys())

    def plot(self, plot_type: str, data, **kwargs):
        """
        GUI 统一调用入口

        plot_type: 'bar' | 'line' | 'heatmap' | 'box' | 'scatter'
        data: pandas DataFrame / Series
        kwargs: title, output_file 等
        """
        if plot_type not in self._plot_registry:
            raise ValueError(f"Unsupported plot type: {plot_type}")

        return self._plot_registry[plot_type](data, **kwargs)

    # ========= 内部适配层 =========

    def _plot_bar(self, data, **kwargs):
        return self.bar.create_bar_chart(data, **kwargs)

    def _plot_line(self, data, **kwargs):
        return self.line.create_line_chart(data, **kwargs)

    def _plot_heatmap(self, data, **kwargs):
        return self.heatmap.create_heatmap(data, **kwargs)

    def _plot_box(self, data, **kwargs):
        return self.box.create_box_plot(data, **kwargs)

    def _plot_scatter(self, data, **kwargs):
        # scatter 比较特殊，一般 GUI 不会直接用
        raise NotImplementedError("Scatter needs x/y data")

# 创建全局绘图管理器实例
plotter = PlotManager()