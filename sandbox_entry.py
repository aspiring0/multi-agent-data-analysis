#!/usr/bin/env python3
"""
Docker沙箱容器入口脚本
从stdin读取代码和数据，执行后返回结果到stdout
"""
import sys
import os
import json
import traceback
import warnings
from pathlib import Path

# 忽略警告
warnings.filterwarnings("ignore")

# 图表保存目录
OUTPUT_DIR = Path("/sandbox/outputs")
DATA_DIR = Path("/sandbox/data")

# 存储生成的图表路径
_figure_paths = []


def setup_matplotlib():
    """配置matplotlib为非交互模式并拦截show()"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    original_show = plt.show

    def patched_show(*args, **kwargs):
        """拦截plt.show()，自动保存图表"""
        import uuid
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            fig_path = OUTPUT_DIR / f"fig_{uuid.uuid4().hex[:8]}.png"
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            _figure_paths.append(str(fig_path))
            print(f"[FIGURE_SAVED]{fig_path}", file=sys.stdout)
        plt.close("all")

    plt.show = patched_show
    return plt


def load_datasets(datasets: list[dict]) -> dict:
    """加载数据集到pandas DataFrame"""
    import pandas as pd

    loaded = {}
    for i, ds in enumerate(datasets or []):
        name = ds.get("name", f"dataset_{i}")
        file_path = ds.get("path", "")

        if not file_path or not Path(file_path).exists():
            print(f"[WARNING] 数据集 {name} 不存在: {file_path}", file=sys.stderr)
            continue

        try:
            suffix = Path(file_path).suffix.lower()
            if suffix in (".csv", ".tsv"):
                loaded[name] = pd.read_csv(file_path, encoding="utf-8-sig")
            elif suffix in (".xlsx", ".xls"):
                loaded[name] = pd.read_excel(file_path)
            elif suffix == ".json":
                loaded[name] = pd.read_json(file_path)
            else:
                print(f"[WARNING] 不支持的文件格式: {suffix}", file=sys.stderr)
        except Exception as e:
            print(f"[WARNING] 加载 {name} 失败: {e}", file=sys.stderr)

    return loaded


def save_remaining_figures(plt):
    """保存未通过plt.show()关闭的图表"""
    remaining = plt.get_fignums()
    if remaining:
        import uuid
        for fig_num in remaining:
            fig = plt.figure(fig_num)
            fig_path = OUTPUT_DIR / f"fig_{uuid.uuid4().hex[:8]}.png"
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            _figure_paths.append(str(fig_path))
            print(f"[FIGURE_SAVED]{fig_path}", file=sys.stdout)
        plt.close("all")


def execute_code(code: str, datasets: list[dict]) -> dict:
    """
    执行用户代码并返回结果

    Args:
        code: 要执行的Python代码
        datasets: 数据集列表

    Returns:
        包含执行结果的字典
    """
    # 设置matplotlib
    plt = setup_matplotlib()

    # 加载数据集
    dataframes = load_datasets(datasets)

    # 准备执行环境
    exec_globals = {
        "__builtins__": __builtins__,
        "pd": __import__("pandas"),
        "np": __import__("numpy"),
        "plt": plt,
    }

    # 注入数据集到执行环境
    if len(dataframes) == 1:
        # 单数据集时直接赋值给df
        exec_globals["df"] = list(dataframes.values())[0]
    elif len(dataframes) > 1:
        # 多数据集时按名称暴露
        exec_globals.update(dataframes)

    # 执行代码
    stdout_capture = []
    stderr_capture = []

    try:
        # 捕获stdout
        from io import StringIO
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        try:
            exec(code, exec_globals)

            # 获取捕获的输出
            stdout_capture.append(sys.stdout.getvalue())
            stderr_capture.append(sys.stderr.getvalue())
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # 保存剩余图表
        save_remaining_figures(plt)

        return {
            "success": True,
            "stdout": "".join(stdout_capture),
            "stderr": "".join(stderr_capture),
            "figures": _figure_paths,
            "dataframes": {},
        }

    except Exception as e:
        return {
            "success": False,
            "stdout": "".join(stdout_capture),
            "stderr": f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            "figures": _figure_paths,
            "dataframes": {},
        }


def main():
    """主入口"""
    try:
        # 从stdin读取输入
        input_data = json.loads(sys.stdin.read())

        code = input_data.get("code", "")
        datasets = input_data.get("datasets", [])
        timeout = input_data.get("timeout", 30)

        # 确保输出目录存在
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 执行代码
        result = execute_code(code, datasets)

        # 返回结果
        print(json.dumps(result, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "stdout": "",
            "stderr": f"JSON解析错误: {e}",
            "figures": [],
            "dataframes": {},
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "stdout": "",
            "stderr": f"入口脚本错误: {type(e).__name__}: {e}",
            "figures": [],
            "dataframes": {},
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
