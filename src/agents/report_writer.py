"""
ReportWriter Agent — 报告撰写专家
职责：
1. 汇总当前会话中的所有分析结果（文本输出 + 图表 + 代码）
2. 调用 LLM 生成结构化 Markdown 分析报告
3. 报告可下载为 .md 文件

核心原则：报告文字由 LLM 生成，开发层只负责组装上下文和格式化输出。
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from src.graph.state import AnalysisState
from src.utils.llm import get_llm
from configs.settings import settings

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """你是一个专业的数据分析报告撰写专家。

## 你的职责
根据数据分析的过程和结果，撰写一份结构完整、专业的 Markdown 分析报告。

## 报告结构要求
1. **标题** — 清晰的报告标题
2. **摘要** — 3-5 句话概述关键发现
3. **数据概览** — 数据集基本信息（来源、行列数、字段描述）
4. **分析过程** — 做了哪些分析、用了什么方法
5. **关键发现** — 重要的数据洞察（用编号列表）
6. **可视化说明** — 对生成的图表进行解读
7. **结论与建议** — 基于分析给出可行建议
8. **附录** — 数据概况表、执行的代码片段

## 写作规范
- 使用中文
- 专业但易懂，避免过多术语
- 数据要具体（给出实际数字）
- 每个发现都要有数据支撑
- 合理使用 Markdown 表格、列表、加粗

## 分析上下文
{analysis_context}
"""


def _build_analysis_context(state: AnalysisState) -> str:
    """从 State 中提取所有分析上下文"""
    parts = []

    # 数据集信息
    datasets = state.get("datasets", [])
    if datasets:
        parts.append("## 数据集信息")
        for i, ds in enumerate(datasets):
            parts.append(
                f"### 数据集 {i+1}: {ds.get('file_name', '未知')}\n"
                f"- 行数: {ds.get('num_rows', '?')}\n"
                f"- 列数: {ds.get('num_cols', '?')}\n"
                f"- 列名: {', '.join(ds.get('columns', []))}\n"
                f"- 缺失值: {ds.get('missing_info', {})}\n"
                f"- 预览:\n```\n{ds.get('preview', '无')}\n```"
            )

    # 对话历史中的分析结果
    messages = state.get("messages", [])
    analysis_outputs = []
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        # 提取包含分析结果的 AI 消息
        if any(kw in content for kw in ["统计", "分析", "相关", "分布", "执行结果", "✅"]):
            # 截断过长的内容
            if len(content) > 1500:
                content = content[:1500] + "\n... (已截断)"
            analysis_outputs.append(content)

    if analysis_outputs:
        parts.append("\n## 分析结果摘要")
        for i, output in enumerate(analysis_outputs[-5:]):  # 最近 5 条
            parts.append(f"\n### 分析输出 {i+1}\n{output}")

    # 当前代码和执行结果
    current_code = state.get("current_code", "")
    if current_code:
        parts.append(f"\n## 最近执行的代码\n```python\n{current_code[:2000]}\n```")

    code_result = state.get("code_result", {})
    if code_result.get("stdout"):
        stdout = code_result["stdout"][:2000]
        parts.append(f"\n## 最近的代码输出\n```\n{stdout}\n```")

    # 图表信息
    figures = state.get("figures", [])
    if figures:
        parts.append(f"\n## 生成的图表\n共 {len(figures)} 张图表")

    return "\n\n".join(parts) if parts else "暂无分析数据"


def report_writer_node(state: AnalysisState) -> dict[str, Any]:
    """
    ReportWriter Node：生成 Markdown 分析报告

    工作流程：
    1. 收集 State 中的所有分析结果
    2. 构建上下文提示词
    3. 调用 LLM 生成报告
    4. 保存为 .md 文件
    5. 返回报告内容和文件路径

    读取：state["messages"], state["datasets"], state["code_result"], state["figures"]
    写入：state["report"], state["messages"]
    """
    datasets = state.get("datasets", [])

    if not datasets:
        return {
            "messages": [
                AIMessage(
                    content="❌ 暂无分析数据。请先上传数据并进行分析，然后再生成报告。"
                )
            ],
            "error": "无数据集",
        }

    llm = get_llm()

    # 构建分析上下文
    analysis_context = _build_analysis_context(state)

    system_prompt = REPORT_SYSTEM_PROMPT.format(
        analysis_context=analysis_context,
    )

    # 提取用户的报告需求（最近消息）
    messages = state.get("messages", [])
    user_request = "请根据以上分析结果，生成一份完整的数据分析报告。"
    for msg in reversed(messages[-3:]):
        content = msg.content if hasattr(msg, "content") else str(msg)
        if hasattr(msg, "type") and msg.type == "human":
            user_request = content
            break

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request),
        ])

        report_content = response.content.strip()

        # 保存报告文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = settings.OUTPUT_DIR / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"report_{timestamp}.md"
        report_path.write_text(report_content, encoding="utf-8")

        logger.info(f"报告已生成: {report_path} ({len(report_content)} 字符)")

        # 构建回复
        figures = state.get("figures", [])
        reply = (
            f"📄 **分析报告已生成**\n\n"
            f"报告包含 {len(report_content)} 字符"
        )
        if figures:
            reply += f"，引用了 {len(figures)} 张图表"
        reply += f"\n\n📁 已保存到: `{report_path}`\n\n"
        reply += "---\n\n"
        reply += report_content

        return {
            "messages": [AIMessage(content=reply)],
            "report": report_content,
        }

    except Exception as e:
        logger.error(f"ReportWriter 调用失败: {e}")
        return {
            "messages": [AIMessage(content=f"❌ 报告生成失败: {str(e)}")],
            "error": str(e),
        }
