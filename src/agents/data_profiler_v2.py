"""
DataProfiler Agent V2 - 数据探索分析专家

使用动态 Skill 发现和 MCP 集成。
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from src.agents.base import BaseAgent, AgentContext, register_agent
from src.skills.selector import SkillSelector, build_data_context_from_state
from src.skills.validator import SkillValidator

logger = logging.getLogger(__name__)


@register_agent
class DataProfilerAgent(BaseAgent):
    """
    数据探索分析 Agent

    从 AGENT.md 加载定义，动态选择 Skills 执行分析。
    """

    name = "data_profiler"

    async def run(self, context: AgentContext) -> dict[str, Any]:
        """
        执行数据探索分析

        工作流:
        1. 构建数据上下文
        2. 使用 SkillSelector 选择相关 Skills
        3. 验证并执行 Skills
        4. 汇总结果
        """
        state = context.state

        # 获取数据集
        datasets = state.get("datasets", [])
        if not datasets:
            return {
                "messages": [AIMessage(content="❌ 请先加载数据文件。")],
                "error": "无数据集",
            }

        # 获取意图
        intent = state.get("intent", "探索性分析")

        # 构建数据上下文
        data_context = build_data_context_from_state(state)

        # 动态选择 Skills
        selector = SkillSelector()
        selected_skills = selector.select_skills_for_intent(
            intent=intent,
            data_context=data_context,
            max_skills=self.get_guardrail("max_skills_per_run", 5),
        )

        if not selected_skills:
            return {
                "messages": [AIMessage(content="⚠️ 没有找到适合的分析技能。")],
                "error": "无匹配技能",
            }

        # 验证 Skills
        validator = SkillValidator()
        executable, rejected = validator.validate_batch(selected_skills, data_context)

        if rejected:
            logger.info(f"Rejected skills: {[r[0].meta.name for r in rejected]}")

        if not executable:
            return {
                "messages": [AIMessage(content="⚠️ 当前数据不满足任何分析技能的要求。")],
                "error": "无可用技能",
            }

        # 执行 Skills
        results = []
        execution_log = []

        for skill in executable:
            try:
                # 生成代码
                code = skill.generate_code()

                # 执行代码
                from src.sandbox.executor import execute_code
                result = execute_code(code=code, datasets=datasets)

                skill_result = {
                    "skill": skill.meta.name,
                    "display_name": skill.meta.display_name,
                    "success": result.get("success", False),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "figures": result.get("figures", []),
                }

                results.append(skill_result)
                execution_log.append({
                    "skill": skill.meta.name,
                    "status": "success" if result.get("success") else "failed",
                })

                logger.info(f"Executed skill: {skill.meta.name}")

            except Exception as e:
                logger.error(f"Skill {skill.meta.name} failed: {e}")
                execution_log.append({
                    "skill": skill.meta.name,
                    "status": "error",
                    "error": str(e),
                })

        # 汇总结果
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        # 构建响应消息
        parts = ["📊 **数据探索分析完成**\n"]
        parts.append(f"执行了 {len(results)} 个分析技能 ({len(successful)} 成功)\n")

        for r in successful:
            parts.append(f"\n### {r['display_name']}")
            if r["stdout"]:
                parts.append(f"```\n{r['stdout'][:1000]}\n```")
            if r["figures"]:
                parts.append(f"📈 生成了 {len(r['figures'])} 张图表")

        if failed:
            parts.append(f"\n⚠️ {len(failed)} 个技能执行失败")

        return {
            "messages": [AIMessage(content="\n".join(parts))],
            "profile_result": {
                "successful_skills": [r["skill"] for r in successful],
                "failed_skills": [r["skill"] for r in failed],
                "total_figures": sum(len(r["figures"]) for r in successful),
            },
            "selected_skills": [s.meta.name for s in selected_skills],
            "execution_log": execution_log,
        }


# 兼容性别名
DataProfiler = DataProfilerAgent