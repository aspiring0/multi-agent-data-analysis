"""
全局 AnalysisState 定义
这是整个多 Agent 系统的数据流转核心，所有 Node 通过读写 State 来通信。

设计原则：
1. 强类型 TypedDict，编辑器可推断字段类型
2. 使用 Annotated + reducer 管理 messages 的追加语义
3. 每个字段都有明确的职责，避免"万能字段"
"""
from __future__ import annotations

from typing import Annotated, Any, Literal
from typing_extensions import TypedDict
from langgraph.graph import add_messages


# ============================================================
# 数据集元信息
# ============================================================
class DatasetMeta(TypedDict, total=False):
    """单个数据集的元信息"""
    file_name: str           # 原始文件名
    file_path: str           # 存储路径
    num_rows: int            # 行数
    num_cols: int            # 列数
    columns: list[str]       # 列名列表
    dtypes: dict[str, str]   # 列名 -> 数据类型
    preview: str             # 前几行的字符串预览
    missing_info: dict[str, int]  # 列名 -> 缺失值数量


# ============================================================
# 代码执行结果
# ============================================================
class CodeResult(TypedDict, total=False):
    """一次代码执行的结果"""
    code: str                # 执行的代码
    stdout: str              # 标准输出
    stderr: str              # 标准错误
    success: bool            # 是否成功
    figures: list[str]       # 生成的图表路径列表
    dataframes: dict[str, str]  # 名称 -> DataFrame 的 CSV 字符串


# ============================================================
# 全局 State
# ============================================================
class AnalysisState(TypedDict, total=False):
    """
    多 Agent 数据分析平台的全局状态

    字段分组：
    - messages: 对话历史（LangGraph 原生 add_messages reducer）
    - intent / task_type: 调度层的意图识别结果
    - datasets: 已上传/已解析的数据集
    - current_code / code_result: 代码生成与执行
    - report: 最终报告
    - error: 错误信息
    """

    # ---- 对话历史 ----
    messages: Annotated[list, add_messages]

    # ---- 调度层 ----
    intent: str              # 用户意图的自然语言描述
    task_type: Literal[
        "upload",            # 上传文件
        "parse",             # 解析数据
        "explore",           # 探索性分析
        "visualize",         # 可视化
        "clean",             # 数据清洗
        "model",             # 建模/预测
        "report",            # 生成报告
        "chat",              # 普通对话
    ]
    next_agent: str          # 下一个要执行的 Agent 名称

    # ---- 数据层 ----
    datasets: list[DatasetMeta]     # 所有已加载的数据集
    active_dataset_index: int       # 当前活跃数据集的索引

    # ---- 代码执行层 ----
    current_code: str               # 当前生成的代码
    code_result: CodeResult         # 代码执行结果
    retry_count: int                # 代码修复重试次数

    # ---- 输出层 ----
    report: str                     # Markdown 格式的分析报告
    figures: list[str]              # 所有生成的图表路径

    # ---- 错误处理 ----
    error: str                      # 最近一次错误信息
