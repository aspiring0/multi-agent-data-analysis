"""
DataParser Agent V2 - 数据解析专家

使用 MCP 服务器进行数据加载。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from src.agents.base import BaseAgent, AgentContext, register_agent

logger = logging.getLogger(__name__)

# 支持的文件格式
SUPPORTED_FORMATS = {".csv", ".tsv", ".xlsx", ".xls", ".json"}


@register_agent
class DataParserAgent(BaseAgent):
    """
    数据解析 Agent

    从 AGENT.md 加载定义，使用 MCP 加载数据。
    """

    name = "data_parser"

    async def run(self, context: AgentContext) -> dict[str, Any]:
        """
        执行数据解析

        工作流:
        1. 从状态中提取文件路径
        2. 通过 MCP 加载数据
        3. 生成数据集元信息
        4. 返回更新后的状态
        """
        state = context.state
        mcp_client = context.mcp_client

        # 提取文件路径
        file_path = self._extract_file_path(state)
        if not file_path:
            return {
                "messages": [AIMessage(content="❌ 未找到文件路径。请提供要分析的数据文件路径。")],
                "error": "未提供文件路径",
            }

        # 验证文件
        path = Path(file_path)
        if not path.exists():
            return {
                "messages": [AIMessage(content=f"❌ 文件不存在: `{file_path}`")],
                "error": f"文件不存在: {file_path}",
            }

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return {
                "messages": [AIMessage(
                    content=f"❌ 不支持的文件格式: `{suffix}`\n支持: {', '.join(SUPPORTED_FORMATS)}"
                )],
                "error": f"不支持的格式: {suffix}",
            }

        # 通过 MCP 加载数据
        try:
            if mcp_client:
                result = await mcp_client.call(
                    "mcp-data",
                    self._get_mcp_tool(suffix),
                    file_path=str(path.absolute()),
                    encoding="utf-8-sig",  # BOM 处理
                )

                if not result.success:
                    return {
                        "messages": [AIMessage(content=f"❌ 数据加载失败: {result.error}")],
                        "error": result.error,
                    }

                # 从 MCP 结果构建 DatasetMeta
                meta = self._build_meta_from_mcp(result.data, path)
            else:
                # Fallback: 直接加载（无 MCP）
                meta = await self._load_directly(path)

            # 更新数据集列表
            datasets = list(state.get("datasets", []))
            datasets.append(meta)

            # 生成摘要
            summary = self._generate_summary(meta)

            logger.info(f"Data parsed: {meta['file_name']} ({meta['num_rows']} rows)")

            return {
                "datasets": datasets,
                "active_dataset_index": len(datasets) - 1,
                "messages": [AIMessage(content=summary)],
            }

        except Exception as e:
            logger.error(f"Data parsing failed: {e}")
            return {
                "messages": [AIMessage(content=f"❌ 数据解析失败: {str(e)}")],
                "error": str(e),
            }

    def _extract_file_path(self, state: dict) -> str | None:
        """从状态中提取文件路径"""
        import re

        messages = state.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", "") or ""
            # 匹配文件路径
            patterns = [
                r'["\']?([/\\]?(?:[\w.\-]+[/\\])*[\w.\-]+\.(?:csv|tsv|xlsx|xls|json))["\']?',
                r'`([^`]+\.(?:csv|tsv|xlsx|xls|json))`',
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)

        # 检查 uploads 目录
        from configs.settings import settings
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

    def _get_mcp_tool(self, suffix: str) -> str:
        """根据文件后缀获取 MCP 工具名"""
        return {
            ".csv": "load_csv",
            ".tsv": "load_csv",
            ".xlsx": "load_excel",
            ".xls": "load_excel",
            ".json": "load_json",
        }.get(suffix, "load_csv")

    def _build_meta_from_mcp(self, mcp_result: dict, path: Path) -> dict:
        """从 MCP 结果构建 DatasetMeta"""
        info = mcp_result.get("dataframe_info", {})
        return {
            "file_name": path.name,
            "file_path": str(path.absolute()),
            "num_rows": info.get("row_count", 0),
            "num_cols": info.get("column_count", 0),
            "columns": info.get("columns", []),
            "dtypes": info.get("dtypes", {}),
            "preview": mcp_result.get("preview", []),
            "missing_info": {},  # 从 validate_data 获取
            "dataset_id": mcp_result.get("dataset_id"),
        }

    async def _load_directly(self, path: Path) -> dict:
        """直接加载（无 MCP 时的 fallback）"""
        import pandas as pd

        suffix = path.suffix.lower()

        # 尝试多种编码
        if suffix in {".csv", ".tsv"}:
            for encoding in ["utf-8-sig", "utf-8", "gbk"]:
                try:
                    df = pd.read_csv(path, encoding=encoding, sep="\t" if suffix == ".tsv" else ",")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                df = pd.read_csv(path, encoding="latin-1")
        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(path)
        else:
            df = pd.read_json(path)

        # 清理 BOM
        df.columns = [c.replace("\ufeff", "") if isinstance(c, str) else c for c in df.columns]

        # 构建元信息
        missing = df.isnull().sum()
        return {
            "file_name": path.name,
            "file_path": str(path.absolute()),
            "num_rows": len(df),
            "num_cols": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(5).to_string(index=False),
            "missing_info": {col: int(count) for col, count in missing.items() if count > 0},
        }

    def _generate_summary(self, meta: dict) -> str:
        """生成数据摘要"""
        lines = [
            f"📊 **数据集解析完成**: `{meta['file_name']}`",
            f"",
            f"**基本信息:**",
            f"- 行数: {meta['num_rows']:,}",
            f"- 列数: {meta['num_cols']}",
            f"- 列名: {', '.join(meta['columns'])}",
        ]

        if meta.get("missing_info"):
            lines.append(f"\n**缺失值:**")
            for col, count in meta["missing_info"].items():
                pct = count / meta["num_rows"] * 100
                lines.append(f"  - {col}: {count} ({pct:.1f}%)")
        else:
            lines.append(f"\n**缺失值:** 无缺失值 ✅")

        return "\n".join(lines)


# 兼容性别名
DataParser = DataParserAgent