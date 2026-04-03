"""
DataProfiler Agent — 数据探索专家
职责：
1. 根据 Skill Registry 中的分析技能，自动生成数据探索代码
2. 在沙箱中执行代码
3. 汇总分析结果返回给用户

核心特点：
- 不硬编码任何分析逻辑，通过 Skill 生成代码
- 代码在沙箱中安全执行
- 结果包含文本输出 + 可视化图表
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from src.graph.state import AnalysisState
from src.sandbox.executor import execute_code
from src.skills.base import get_registry

logger = logging.getLogger(__name__)


def data_profiler_node(state: AnalysisState) -> dict[str, Any]:
    """
    DataProfiler Node：自动运行数据探索分析

    工作流程：
    1. 检查是否有已加载的数据集
    2. 从 Skill Registry 获取分析 Skill
    3. 生成并执行分析代码（描述统计 + 分布 + 相关性）
    4. 返回结果

    读取：state["datasets"], state["active_dataset_index"]
    写入：state["messages"], state["code_result"], state["figures"]
    """
    datasets = state.get("datasets", [])
    active_idx = state.get("active_dataset_index", 0)

    if not datasets:
        return {
            "messages": [
                AIMessage(
                    content="❌ 暂无数据集。请先上传数据文件，然后我才能进行探索分析。\n"
                    "例如：`请帮我分析 /path/to/data.csv`"
                )
            ],
            "error": "无数据集",
        }

    # 当前活跃数据集
    active_ds = datasets[min(active_idx, len(datasets) - 1)]

    # 获取 Skill Registry
    registry = get_registry()

    # 选择要执行的 Skill（默认做全套探索）
    skill_names = [
        "describe_statistics",
        "distribution_analysis",
        "correlation_analysis",
    ]

    all_results = []
    all_figures = []
    all_codes = []
    failed_skills = []  # 跟踪失败的 Skill
    accumulated_stderr = []  # 收集所有错误信息

    for skill_name in skill_names:
        skill = registry.get(skill_name)
        if skill is None or skill.generate_code is None:
            logger.warning(f"Skill 不存在或无代码生成器: {skill_name}")
            continue

        # 生成代码
        code = skill.generate_code()
        all_codes.append(f"# === {skill.meta.display_name} ===\n{code}")

        # 在沙箱中执行
        result = execute_code(
            code=code,
            datasets=datasets,
        )

        if result["success"]:
            output = result.get("stdout", "").strip()
            if output:
                all_results.append(f"### {skill.meta.display_name}\n\n```\n{output}\n```")
            figures = result.get("figures", [])
            all_figures.extend(figures)
            if figures:
                all_results.append(f"📈 生成了 {len(figures)} 张图表")
        else:
            stderr = result.get("stderr", "未知错误")
            all_results.append(
                f"### {skill.meta.display_name}\n\n⚠️ 执行出现问题: {stderr[:200]}"
            )
            failed_skills.append(skill_name)
            accumulated_stderr.append(f"[{skill_name}] {stderr}")

    # 汇总结果
    if all_results:
        summary = (
            f"## 🔍 数据探索分析: {active_ds['file_name']}\n\n"
            + "\n\n".join(all_results)
        )
    else:
        summary = "分析未产生结果，请检查数据集格式。"

    # 如果有失败，添加提示
    if failed_skills:
        summary += f"\n\n---\n⚠️ 有 {len(failed_skills)} 个分析任务失败，正在尝试修复..."

    # 构建完整代码记录
    full_code = "\n\n".join(all_codes)

    # 判断是否需要触发 Debugger
    has_failures = len(failed_skills) > 0
    combined_stderr = "\n".join(accumulated_stderr) if accumulated_stderr else ""

    return {
        "messages": [AIMessage(content=summary)],
        "current_code": full_code,
        "code_result": {
            "code": full_code,
            "stdout": "\n".join(all_results),
            "stderr": combined_stderr,
            "success": not has_failures,  # 只有没有失败时才算成功
            "figures": all_figures,
            "dataframes": {},
        },
        "figures": list(state.get("figures", [])) + all_figures,
        "needs_debug": has_failures,  # 新增：标记是否需要修复
        "retry_count": 0 if has_failures else state.get("retry_count", 0),
    }
