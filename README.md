# Gem5 Stat Analysis

**Gem5 Stat Analysis** 是一个面向 **gem5 仿真结果后处理** 的分析与可视化工具，提供从原始 `stats.txt` 到可视化图表的一体化流程，并通过图形界面（GUI）支持交互式分析。

该工具主要面向 **体系结构研究与实验评估场景**，用于在不同 `benchmark` 与 `config` 下，对性能指标进行统一计算、对比和可视化，避免反复编写一次性分析脚本。

---

## 功能特性

- **统一的分析流程**
  - 解析 `gem5` 原始 `stats.txt`
  - 基于规则提取感兴趣指标
  - 按 `benchmark` / `config` 进行聚合与对比

- **交互式图形界面（GUI）**
  - 通过复选框选择 `benchmark` 与 `config`
  - 自由选择指标 `metric` 与绘图类型 `plot type`

- **多种绘图类型（可扩展）**
  - 条形图（Bar）
  - 折线图（Line）
  - 热力图（Heatmap）
  - 箱线图（Box）

- **结果导出**
  - 支持导出 PNG / PDF / SVG

---

## 项目结构

```text
Gem5_Stat_Analysis/
├── gui.py                  # GUI 主入口
├── utils/
│   ├── analyzer.py         # 派生指标计算
│   ├── plotter.py          # 绘图管理与绘图后端
│   ├── parse_interest.py   # gem5 原始 stats 解析与初步提取
│   └── ...
├── configs/
│   └── interest.csv        # 感兴趣指标定义
├── results/
│   ├── raw/                # gem5 原始输出，由 run.sh 重定向至此
│   ├── parsed/             # 解析后的 CSV 数据
│   └── analysis/           # 生成图表
├── LICENSE
└── README.md
```
## 如何使用

### 环境配置
本项目可以由 `miniconda` 直接生成环境，通过 `environment.yaml` 生成可以运行该项目的环境。

```bash
conda env create -f environment.yaml
conda activate stat
```

### `stats.txt` 父文件夹重定向与命名
- 通过 `run.sh` 将输出定向到 `results/raw`
- 父文件夹命名为 `benchmark_config`
    - 比如：`bfs_L1-16KB`，`btree_default`

### 启动 GUI
启动 `conda` 的 `stat` 环境后，运行以下命名：
```python
python gui.py
```

即可打开交互平台，如下图所示：
![alt text](figures/image.png)

- 点击 `Parse raw stats`，生成解析后的 `CSV` 数据，存储在 `results/parsed` 路径下
- 选择 `benchmark` 与 `config`
    - 可单独选择，也可使用 `Select All`
- 选择指标与绘图类型
- 绘制图像，图像直接显示在 GUI 中
- 保存图像，支持 PNG / PDF / SVG 格式

## 扩展

### 指标扩展
指标通过基于模式匹配的规则进行定义，相关逻辑位于：
- `configs/interest.csv`
- `utils/analyzer.py`

指标规则规定如下：
本工具通过 **规则驱动（rule-based）** 的方式定义和派生性能指标，所有可分析指标均由 `METRIC_RULES` 描述，其定义位于：

- `utils/analyzer.py`

每一条指标规则包含以下字段：

- `patterns`  
  用于匹配 gem5 `stats.txt` 中的统计项，支持正则表达式  
- `op`  
  指标的计算方式（如保持原值、比值计算等）
- `desc`  
  指标语义说明（用于文档与理解）

这是规则示例：

```python
METRIC_RULES = {

    # CPU IPC
    "cpu_ipc": {
        "patterns": [
            r"^system\.cpu\d+\.ipc$",
        ],
        "op": "identity",
        "desc": "mean IPC across CPU cores",
    },

    # L3 Cache Hit Rate
    "L3_cache_hit_rate": {
        "patterns": [
            r"^L3CacheMemory\.m_demand_hits$",
            r"^L3CacheMemory\.m_demand_accesses$",
        ],
        "op": "ratio",
        "desc": "L3 cache hit rate",
    },
}
```
支持的计算操作（op）
- identity：对匹配到的统计项直接进行聚合（如对多核取均值）
- ratio：对多个统计项执行比值计算
    - patterns[0] / patterns[1]
    - 常用于命中率、利用率等派生指标


### 图像类型扩展
图像绘制定义在 `utils/plotter.py` 下，如果想要扩展绘制的图像类型，可以仿照已有的代码进行扩展

## LICENSE
本项目采用 GPL-3.0 license，详见 LICENSE 文件。