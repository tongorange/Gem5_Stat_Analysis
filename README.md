# Gem5 Stats Analysis
这是一个针对 `Gem5` 模拟运行的输出文件 `stats.txt` 的分析工具，支持以下功能：
- 自动扫描指定路径下的输出文件
- 提取感兴趣的指标
- 根据自定义规则生成派生指标，比如 `IPC` 的均值，`Cache Hit Rate`等
- 