"""
内置 Skill 集合
预注册的常用数据分析技能。

每个 Skill 提供：
1. 元信息（名称、描述、标签）
2. 代码模板（供 CodeGenerator 参考和直接使用）
"""
from __future__ import annotations

import logging

from src.skills.base import (
    Skill, SkillMeta, SkillCategory, SkillRegistry, get_registry
)

logger = logging.getLogger(__name__)


# ============================================================
# 分析类 Skills
# ============================================================

def _gen_describe_stats(columns: str = "None", **kwargs) -> str:
    """生成描述性统计代码"""
    return f'''
# 描述性统计分析
print("=" * 60)
print("📊 描述性统计分析")
print("=" * 60)

cols = {columns}
target = df[cols] if cols else df.select_dtypes(include=["number"])

print("\\n【基本统计量】")
print(target.describe().round(2).to_string())

print("\\n【数据类型分布】")
print(df.dtypes.value_counts().to_string())

print("\\n【缺失值统计】")
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
missing_df = pd.DataFrame({{"缺失数": missing, "缺失率(%)": missing_pct}})
print(missing_df[missing_df["缺失数"] > 0].to_string() if missing.sum() > 0 else "无缺失值 ✅")

print("\\n【唯一值统计】")
for col in df.columns:
    print(f"  {{col}}: {{df[col].nunique()}} 个唯一值")
'''


def _gen_distribution_analysis(**kwargs) -> str:
    """生成分布分析代码"""
    return '''
# 数据分布分析
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
n_cols = len(numeric_cols)

if n_cols == 0:
    print("没有数值型列，无法进行分布分析")
else:
    # 直方图
    n_rows = (n_cols + 2) // 3
    fig, axes = plt.subplots(n_rows, min(3, n_cols), figsize=(5 * min(3, n_cols), 4 * n_rows))
    if n_cols == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for i, col in enumerate(numeric_cols):
        if i < len(axes):
            ax = axes[i]
            df[col].dropna().hist(bins=30, ax=ax, edgecolor="black", alpha=0.7)
            ax.set_title(col)
            ax.set_xlabel("")

    # 隐藏多余子图
    for j in range(n_cols, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle("数值特征分布直方图", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.show()

    # 偏度和峰度
    print("\\n【偏度和峰度】")
    for col in numeric_cols:
        skew = df[col].skew()
        kurt = df[col].kurtosis()
        print(f"  {col}: 偏度={skew:.3f}, 峰度={kurt:.3f}")
'''


def _gen_correlation_analysis(**kwargs) -> str:
    """生成相关性分析代码"""
    return '''
# 相关性分析
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

numeric_df = df.select_dtypes(include=["number"])

if numeric_df.shape[1] < 2:
    print("数值列不足 2 列，无法计算相关性")
else:
    corr = numeric_df.corr().round(3)

    print("【Pearson 相关系数矩阵】")
    print(corr.to_string())

    # 热力图
    fig, ax = plt.subplots(figsize=(max(8, numeric_df.shape[1]), max(6, numeric_df.shape[1] * 0.8)))
    sns.heatmap(corr, annot=True, cmap="RdBu_r", center=0, fmt=".2f",
                square=True, linewidths=0.5, ax=ax)
    ax.set_title("相关性热力图")
    plt.tight_layout()
    plt.show()

    # 高相关性警告
    print("\\n【高相关性特征对 (|r| > 0.7)】")
    high_corr = []
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            if abs(corr.iloc[i, j]) > 0.7:
                high_corr.append((corr.columns[i], corr.columns[j], corr.iloc[i, j]))
    if high_corr:
        for c1, c2, r in high_corr:
            print(f"  {c1} ↔ {c2}: r = {r:.3f}")
    else:
        print("  无高相关性特征对")
'''


def _gen_categorical_analysis(**kwargs) -> str:
    """生成分类变量分析代码"""
    return '''
# 分类变量分析
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

if not cat_cols:
    print("没有分类变量列")
else:
    for col in cat_cols:
        print(f"\\n【{col} 的值分布】")
        vc = df[col].value_counts()
        print(vc.head(15).to_string())

        if len(vc) <= 20:
            fig, ax = plt.subplots(figsize=(10, 5))
            vc.plot(kind="bar", ax=ax, edgecolor="black", alpha=0.7)
            ax.set_title(f"{col} 值分布")
            ax.set_xlabel(col)
            ax.set_ylabel("数量")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.show()
'''


def _gen_outlier_detection(**kwargs) -> str:
    """生成异常值检测代码"""
    return '''
# 异常值检测 (IQR 方法)
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

if not numeric_cols:
    print("没有数值型列")
else:
    print("【IQR 异常值检测】")
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower) | (df[col] > upper)]
        pct = len(outliers) / len(df) * 100
        print(f"  {col}: {len(outliers)} 个异常值 ({pct:.1f}%), 范围=[{lower:.2f}, {upper:.2f}]")

    # 箱线图
    n_cols = len(numeric_cols)
    fig, axes = plt.subplots(1, min(n_cols, 5), figsize=(4 * min(n_cols, 5), 5))
    if n_cols == 1:
        axes = [axes]
    for i, col in enumerate(numeric_cols[:5]):
        axes[i].boxplot(df[col].dropna())
        axes[i].set_title(col)
    plt.suptitle("箱线图 (异常值检测)", fontsize=13)
    plt.tight_layout()
    plt.show()
'''


# ============================================================
# 注册所有内置 Skill
# ============================================================

def register_builtin_skills(registry: SkillRegistry | None = None) -> SkillRegistry:
    """注册所有内置 Skill 到注册表"""
    reg = registry or get_registry()

    skills = [
        Skill(
            meta=SkillMeta(
                name="describe_statistics",
                display_name="描述性统计分析",
                description="对数据集进行全面的描述性统计，包括均值、标准差、分位数、缺失值和唯一值统计",
                category=SkillCategory.ANALYSIS,
                tags=["统计", "描述", "概览", "缺失值", "mean", "std", "describe"],
                input_description="DataFrame",
                output_description="统计摘要文本",
            ),
            generate_code=_gen_describe_stats,
        ),
        Skill(
            meta=SkillMeta(
                name="distribution_analysis",
                display_name="数据分布分析",
                description="分析数值特征的分布情况，生成直方图，计算偏度和峰度",
                category=SkillCategory.ANALYSIS,
                tags=["分布", "直方图", "偏度", "峰度", "histogram", "skew"],
            ),
            generate_code=_gen_distribution_analysis,
        ),
        Skill(
            meta=SkillMeta(
                name="correlation_analysis",
                display_name="相关性分析",
                description="计算数值特征间的 Pearson 相关系数，生成热力图，识别高相关性特征对",
                category=SkillCategory.ANALYSIS,
                tags=["相关性", "热力图", "correlation", "heatmap", "pearson"],
            ),
            generate_code=_gen_correlation_analysis,
        ),
        Skill(
            meta=SkillMeta(
                name="categorical_analysis",
                display_name="分类变量分析",
                description="统计分类变量的值分布，生成条形图",
                category=SkillCategory.ANALYSIS,
                tags=["分类", "类别", "value_counts", "bar chart"],
            ),
            generate_code=_gen_categorical_analysis,
        ),
        Skill(
            meta=SkillMeta(
                name="outlier_detection",
                display_name="异常值检测",
                description="使用 IQR 方法检测数值特征中的异常值，生成箱线图",
                category=SkillCategory.ANALYSIS,
                tags=["异常值", "离群点", "IQR", "boxplot", "outlier"],
            ),
            generate_code=_gen_outlier_detection,
        ),
    ]

    for skill in skills:
        reg.register(skill)

    logger.info(f"已注册 {len(skills)} 个内置 Skill")
    return reg


# 模块导入时自动注册
register_builtin_skills()
