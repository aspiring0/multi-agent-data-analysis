"""
DataParser Agent — 数据解析专家
职责：
1. 接收 CSV 文件路径
2. 使用 pandas 加载并解析数据
3. 生成数据集元信息（DatasetMeta）
4. 将解析结果写入 State

设计原则：
- 纯工具型 Agent，不需要 LLM 调用
- 确保解析结果结构化、可被后续 Agent 使用
- 对常见问题做容错处理（编码、分隔符、大文件）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from langchain_core.messages import AIMessage

from src.graph.state import AnalysisState, DatasetMeta
from configs.settings import settings

logger = logging.getLogger(__name__)

# 支持的文件格式
SUPPORTED_FORMATS = {".csv", ".tsv", ".xlsx", ".xls", ".json"}

# 预览行数
PREVIEW_ROWS = 5


def _detect_encoding(file_path: str) -> str:
    """简单的编码检测：尝试常见编码（优先 utf-8-sig 处理 BOM）"""
    # utf-8-sig 优先，自动处理 BOM
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8-sig"  # fallback，优先处理 BOM


def _load_dataframe(file_path: str) -> pd.DataFrame:
    """根据文件扩展名选择合适的加载方式"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".csv", ".tsv"}:
        encoding = _detect_encoding(file_path)
        sep = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(file_path, encoding=encoding, sep=sep)
    elif suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    elif suffix == ".json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，支持: {SUPPORTED_FORMATS}")


def _build_dataset_meta(df: pd.DataFrame, file_path: str) -> DatasetMeta:
    """从 DataFrame 构建 DatasetMeta"""
    path = Path(file_path)

    # 缺失值统计
    missing = df.isnull().sum()
    missing_info = {col: int(count) for col, count in missing.items() if count > 0}

    # 数据预览（前 N 行转为字符串）
    preview = df.head(PREVIEW_ROWS).to_string(index=False)

    # 数据类型映射
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    return DatasetMeta(
        file_name=path.name,
        file_path=str(path.absolute()),
        num_rows=len(df),
        num_cols=len(df.columns),
        columns=list(df.columns),
        dtypes=dtypes,
        preview=preview,
        missing_info=missing_info,
    )


def _generate_summary(meta: DatasetMeta) -> str:
    """生成人类可读的数据摘要"""
    lines = [
        f"📊 数据集解析完成: {meta['file_name']}",
        f"",
        f"**基本信息:**",
        f"- 行数: {meta['num_rows']:,}",
        f"- 列数: {meta['num_cols']}",
        f"- 列名: {', '.join(meta['columns'])}",
        f"",
        f"**数据类型:**",
    ]
    for col, dtype in meta["dtypes"].items():
        lines.append(f"  - {col}: {dtype}")

    if meta.get("missing_info"):
        lines.append(f"")
        lines.append(f"**缺失值:**")
        for col, count in meta["missing_info"].items():
            pct = count / meta["num_rows"] * 100
            lines.append(f"  - {col}: {count} ({pct:.1f}%)")
    else:
        lines.append(f"\n**缺失值:** 无缺失值 ✅")

    lines.append(f"\n**数据预览（前 {PREVIEW_ROWS} 行）:**")
    lines.append(f"```")
    lines.append(meta["preview"])
    lines.append(f"```")

    return "\n".join(lines)


def data_parser_node(state: AnalysisState) -> dict[str, Any]:
    """
    DataParser Node：解析上传的数据文件

    工作流程：
    1. 从最近的用户消息中提取文件路径
    2. 加载并解析数据
    3. 构建 DatasetMeta
    4. 返回更新后的 state

    读取：state["messages"]
    写入：state["datasets"], state["active_dataset_index"], state["messages"]
    """
    messages = state.get("messages", [])

    # 从最近的消息中提取文件路径
    file_path = _extract_file_path(state)

    if not file_path:
        return {
            "messages": [
                AIMessage(content="❌ 未找到文件路径。请提供要分析的数据文件路径，例如：`/path/to/data.csv`")
            ],
            "error": "未提供文件路径",
        }

    # 验证文件存在
    if not Path(file_path).exists():
        return {
            "messages": [
                AIMessage(content=f"❌ 文件不存在: `{file_path}`\n请检查路径是否正确。")
            ],
            "error": f"文件不存在: {file_path}",
        }

    # 验证文件格式
    suffix = Path(file_path).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return {
            "messages": [
                AIMessage(
                    content=f"❌ 不支持的文件格式: `{suffix}`\n"
                    f"支持的格式: {', '.join(SUPPORTED_FORMATS)}"
                )
            ],
            "error": f"不支持的格式: {suffix}",
        }

    try:
        # 加载数据
        logger.info(f"开始解析文件: {file_path}")
        df = _load_dataframe(file_path)

        # 构建元信息
        meta = _build_dataset_meta(df, file_path)

        # 更新数据集列表
        existing_datasets = list(state.get("datasets", []))
        existing_datasets.append(meta)

        # 生成摘要
        summary = _generate_summary(meta)
        logger.info(f"文件解析完成: {meta['file_name']} ({meta['num_rows']} 行, {meta['num_cols']} 列)")

        return {
            "datasets": existing_datasets,
            "active_dataset_index": len(existing_datasets) - 1,
            "messages": [AIMessage(content=summary)],
        }

    except Exception as e:
        error_msg = f"数据解析失败: {str(e)}"
        logger.error(error_msg)
        return {
            "messages": [AIMessage(content=f"❌ {error_msg}")],
            "error": error_msg,
        }


def load_dataframe(file_path: str) -> tuple[pd.DataFrame | None, str | None]:
    """
    公共接口：加载数据文件

    Args:
        file_path: 数据文件路径

    Returns:
        (DataFrame, None) 成功时返回 DataFrame
        (None, error_msg) 失败时返回错误信息
    """
    try:
        df = _load_dataframe(file_path)
        return df, None
    except Exception as e:
        return None, str(e)


def build_dataset_meta(df: pd.DataFrame, file_name: str, file_path: str) -> dict:
    """
    公共接口：构建数据集元信息

    Args:
        df: pandas DataFrame
        file_name: 文件名
        file_path: 文件路径

    Returns:
        数据集元信息字典
    """
    meta = _build_dataset_meta(df, file_path)
    return dict(meta)


def _extract_file_path(state: AnalysisState) -> str | None:
    """
    从 state 中提取文件路径

    查找策略（优先级从高到低）：
    1. 最近的用户消息中包含的文件路径
    2. data/uploads 目录下最新的文件
    """
    messages = state.get("messages", [])

    # 策略 1：从消息中提取路径
    for msg in reversed(messages):
        content = ""
        if hasattr(msg, "content"):
            content = msg.content
        elif isinstance(msg, dict):
            content = msg.get("content", "")

        if not content:
            continue

        # 简单的路径提取：查找看起来像文件路径的字符串
        import re
        # 匹配常见文件路径模式
        patterns = [
            r'["\']?([/\\]?(?:[\w.\-]+[/\\])*[\w.\-]+\.(?:csv|tsv|xlsx|xls|json))["\']?',
            r'`([^`]+\.(?:csv|tsv|xlsx|xls|json))`',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

    # 策略 2：检查 uploads 目录
    upload_dir = settings.UPLOAD_DIR
    if upload_dir.exists():
        files = sorted(
            [f for f in upload_dir.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if files:
            return str(files[0])

    return None


