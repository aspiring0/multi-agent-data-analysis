"""
异常值检测代码生成器

使用IQR方法生成异常值检测代码，包括统计和箱线图。
"""

def generate_code(**kwargs) -> str:
    """
    生成异常值检测代码

    Returns:
        str: 生成的Python代码字符串
    """
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
