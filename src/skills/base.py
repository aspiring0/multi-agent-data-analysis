"""
Skill 基类和注册体系
把每个分析能力封装为可注册、可版本化、可路由的 Skill 单元。

设计思路（参考 LangGraph 社区 Agent Skill 模式）：
1. 每个 Skill 是一个带有元信息的可调用单元
2. Skill Registry 负责注册、查找和路由
3. Coordinator 通过 Registry 查询可用 Skill 来增强路由决策
4. 支持版本管理，方便 A/B 测试和回滚

Skill 分类：
- analysis: 数据分析类（统计、分布、相关性）
- transform: 数据变换类（清洗、特征工程）
- visualization: 可视化类（折线图、柱状图、热力图）
- modeling: 建模类（回归、分类、预测）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """Skill 分类"""
    ANALYSIS = "analysis"
    TRANSFORM = "transform"
    VISUALIZATION = "visualization"
    MODELING = "modeling"
    UTILITY = "utility"


@dataclass
class SkillMeta:
    """
    Skill 元信息
    描述一个 Skill 的名称、功能、使用方式等。
    """
    name: str                          # 唯一标识符，如 "describe_statistics"
    display_name: str                  # 显示名称，如 "描述性统计分析"
    description: str                   # 功能描述（供 LLM 理解）
    category: SkillCategory            # 分类
    version: str = "1.0.0"            # 版本号
    tags: list[str] = field(default_factory=list)  # 标签，用于搜索
    input_description: str = ""        # 输入说明
    output_description: str = ""       # 输出说明
    code_template: str = ""            # 代码模板（供 CodeGenerator 参考）
    examples: list[str] = field(default_factory=list)  # 使用示例


@dataclass
class Skill:
    """
    一个完整的 Skill 单元
    包含元信息 + 可执行的代码生成逻辑
    """
    meta: SkillMeta

    # 代码生成函数：接收上下文参数，返回 Python 代码字符串
    generate_code: Callable[..., str] | None = None

    # 直接执行函数（某些 Skill 不需要生成代码，直接返回结果）
    execute: Callable[..., dict[str, Any]] | None = None

    def __post_init__(self):
        if self.generate_code is None and self.execute is None:
            raise ValueError(
                f"Skill '{self.meta.name}' 必须提供 generate_code 或 execute 之一"
            )


class SkillRegistry:
    """
    Skill 注册表（全局单例）
    负责 Skill 的注册、查找和路由。
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册一个 Skill"""
        name = skill.meta.name
        if name in self._skills:
            existing = self._skills[name]
            logger.info(
                f"Skill 覆盖注册: {name} "
                f"(v{existing.meta.version} → v{skill.meta.version})"
            )
        else:
            logger.info(f"Skill 注册: {name} (v{skill.meta.version})")
        self._skills[name] = skill

    def get(self, name: str) -> Skill | None:
        """按名称获取 Skill"""
        return self._skills.get(name)

    def list_all(self) -> list[SkillMeta]:
        """列出所有已注册 Skill 的元信息"""
        return [s.meta for s in self._skills.values()]

    def list_by_category(self, category: SkillCategory) -> list[SkillMeta]:
        """按分类列出 Skill"""
        return [
            s.meta for s in self._skills.values()
            if s.meta.category == category
        ]

    def search(self, query: str) -> list[SkillMeta]:
        """模糊搜索 Skill（按名称、描述、标签）"""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            meta = skill.meta
            searchable = (
                f"{meta.name} {meta.display_name} {meta.description} "
                f"{' '.join(meta.tags)}"
            ).lower()
            if query_lower in searchable:
                results.append(meta)
        return results

    def get_skill_descriptions(self) -> str:
        """
        生成所有 Skill 的描述文本（供 Coordinator 使用）
        格式适合注入到 LLM 的系统提示词中。
        """
        if not self._skills:
            return "暂无已注册的 Skill。"

        lines = ["## 可用分析技能\n"]
        by_category: dict[str, list[SkillMeta]] = {}
        for meta in self.list_all():
            cat = meta.category.value
            by_category.setdefault(cat, []).append(meta)

        for category, skills in sorted(by_category.items()):
            lines.append(f"### {category}")
            for s in skills:
                lines.append(f"- **{s.display_name}** (`{s.name}`): {s.description}")
            lines.append("")

        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._skills)


# ============================================================
# 全局单例
# ============================================================
_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """获取全局 Skill 注册表"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
