"""
Skill 注册体系测试
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.skills.base import (
    Skill, SkillMeta, SkillCategory, SkillRegistry, get_registry,
)
from src.skills.builtin_skills import register_builtin_skills


class TestSkillRegistry:
    """测试 Skill 注册表"""

    def test_register_and_get(self):
        """注册后应能获取 Skill"""
        registry = SkillRegistry()
        skill = Skill(
            meta=SkillMeta(
                name="test_skill",
                display_name="测试技能",
                description="测试用",
                category=SkillCategory.UTILITY,
            ),
            generate_code=lambda: "print('test')",
        )
        registry.register(skill)
        assert registry.get("test_skill") is not None
        assert registry.get("test_skill").meta.name == "test_skill"

    def test_get_nonexistent(self):
        """获取不存在的 Skill 应返回 None"""
        registry = SkillRegistry()
        assert registry.get("nonexistent") is None

    def test_list_all(self):
        """应能列出所有 Skill"""
        registry = SkillRegistry()
        for i in range(3):
            registry.register(Skill(
                meta=SkillMeta(
                    name=f"skill_{i}",
                    display_name=f"技能{i}",
                    description=f"描述{i}",
                    category=SkillCategory.ANALYSIS,
                ),
                generate_code=lambda: "pass",
            ))
        assert len(registry.list_all()) == 3

    def test_list_by_category(self):
        """应能按分类过滤"""
        registry = SkillRegistry()
        registry.register(Skill(
            meta=SkillMeta(name="a", display_name="A", description="", category=SkillCategory.ANALYSIS),
            generate_code=lambda: "pass",
        ))
        registry.register(Skill(
            meta=SkillMeta(name="v", display_name="V", description="", category=SkillCategory.VISUALIZATION),
            generate_code=lambda: "pass",
        ))
        assert len(registry.list_by_category(SkillCategory.ANALYSIS)) == 1
        assert len(registry.list_by_category(SkillCategory.VISUALIZATION)) == 1

    def test_search(self):
        """应能模糊搜索"""
        registry = SkillRegistry()
        registry.register(Skill(
            meta=SkillMeta(
                name="correlation_analysis",
                display_name="相关性分析",
                description="计算Pearson相关系数",
                category=SkillCategory.ANALYSIS,
                tags=["相关性", "pearson"],
            ),
            generate_code=lambda: "pass",
        ))
        assert len(registry.search("相关性")) == 1
        assert len(registry.search("pearson")) == 1
        assert len(registry.search("不存在")) == 0

    def test_version_override(self):
        """同名 Skill 注册应覆盖旧版"""
        registry = SkillRegistry()
        skill_v1 = Skill(
            meta=SkillMeta(name="s", display_name="S", description="v1", category=SkillCategory.UTILITY, version="1.0"),
            generate_code=lambda: "v1",
        )
        skill_v2 = Skill(
            meta=SkillMeta(name="s", display_name="S", description="v2", category=SkillCategory.UTILITY, version="2.0"),
            generate_code=lambda: "v2",
        )
        registry.register(skill_v1)
        registry.register(skill_v2)
        assert registry.count == 1
        assert registry.get("s").meta.version == "2.0"

    def test_skill_descriptions(self):
        """应能生成描述文本"""
        registry = SkillRegistry()
        registry.register(Skill(
            meta=SkillMeta(name="test", display_name="测试", description="测试描述", category=SkillCategory.ANALYSIS),
            generate_code=lambda: "pass",
        ))
        desc = registry.get_skill_descriptions()
        assert "测试" in desc
        assert "测试描述" in desc


class TestBuiltinSkills:
    """测试内置 Skill"""

    def test_builtin_skills_registered(self):
        """内置 Skill 应已注册"""
        registry = get_registry()
        assert registry.count >= 5  # 至少 5 个内置 Skill

    def test_describe_statistics_generates_code(self):
        """描述统计 Skill 应能生成代码"""
        registry = get_registry()
        skill = registry.get("describe_statistics")
        assert skill is not None
        code = skill.generate_code()
        assert "describe" in code
        assert "isnull" in code or "缺失值" in code

    def test_correlation_generates_code(self):
        """相关性分析 Skill 应能生成代码"""
        registry = get_registry()
        skill = registry.get("correlation_analysis")
        assert skill is not None
        code = skill.generate_code()
        assert "corr" in code
        assert "heatmap" in code

    def test_distribution_generates_code(self):
        """分布分析 Skill 应能生成代码"""
        registry = get_registry()
        skill = registry.get("distribution_analysis")
        assert skill is not None
        code = skill.generate_code()
        assert "hist" in code
        assert "skew" in code
