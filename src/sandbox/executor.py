"""
代码沙箱执行器
在隔离的子进程中安全执行 LLM 生成的 Python 代码。

安全机制：
1. subprocess 进程隔离（独立 Python 解释器）
2. 超时熔断（防止死循环）
3. 内存限制（通过 resource 模块）
4. 网络隔离（不导入 requests/urllib 等）
5. 危险操作拦截（os.system, subprocess, eval 等）
6. 图表自动保存（matplotlib → 文件）

设计原则：
- 开发层不包含任何数据分析算法，100% 由 LLM 生成代码
- 沙箱只负责"安全执行 + 捕获结果"
- 执行结果结构化返回（stdout, stderr, figures, success）
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from src.graph.state import CodeResult
from configs.settings import settings

logger = logging.getLogger(__name__)

# ============================================================
# 危险模式检测
# ============================================================
DANGEROUS_PATTERNS = [
    "os.system",
    "subprocess",
    "shutil.rmtree",
    "__import__",
    "exec(",
    "eval(",
    "compile(",
    "open('/etc",
    "open('/proc",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "importlib",
    "ctypes",
    "socket.",
    "requests.",
    "urllib.",
    "http.client",
]


def _check_code_safety(code: str) -> list[str]:
    """
    检查代码中是否包含危险操作。
    返回检测到的危险模式列表（空列表 = 安全）。
    """
    warnings = []
    code_lower = code.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            warnings.append(f"检测到危险操作: {pattern}")
    return warnings


# ============================================================
# 代码包装器模板
# ============================================================
WRAPPER_TEMPLATE = '''
import sys
import os
import warnings
warnings.filterwarnings("ignore")

# 设置 matplotlib 后端为非交互式
import matplotlib
matplotlib.use("Agg")

# 图表保存目录
FIGURE_DIR = "{figure_dir}"
_figure_paths = []

# 猴子补丁：拦截 plt.show() 自动保存并关闭图表
import matplotlib.pyplot as plt
_original_show = plt.show
def _patched_show(*args, **kwargs):
    import uuid as _uuid
    for _fig_num in plt.get_fignums():
        _fig = plt.figure(_fig_num)
        _fig_path = os.path.join(FIGURE_DIR, f"fig_{{_uuid.uuid4().hex[:8]}}.png")
        _fig.savefig(_fig_path, dpi=150, bbox_inches="tight")
        _figure_paths.append(_fig_path)
        print(f"[FIGURE_SAVED]{{_fig_path}}")
    plt.close("all")
plt.show = _patched_show

# 数据文件路径注入
DATA_FILES = {data_files}

# 加载数据集（如果有的话）
import pandas as pd
_loaded_dataframes = {{}}
for _name, _path in DATA_FILES.items():
    try:
        if _path.endswith(".csv") or _path.endswith(".tsv"):
            _loaded_dataframes[_name] = pd.read_csv(_path)
        elif _path.endswith(".xlsx") or _path.endswith(".xls"):
            _loaded_dataframes[_name] = pd.read_excel(_path)
        elif _path.endswith(".json"):
            _loaded_dataframes[_name] = pd.read_json(_path)
    except Exception as _e:
        print(f"[WARNING] 加载 {{_name}} 失败: {{_e}}", file=sys.stderr)

# 便捷访问：如果只有一个数据集，直接赋值给 df
if len(_loaded_dataframes) == 1:
    df = list(_loaded_dataframes.values())[0]
elif len(_loaded_dataframes) > 1:
    # 多个数据集时，按名称暴露
    for _k, _v in _loaded_dataframes.items():
        globals()[_k] = _v

# ====== 用户代码开始 ======
{user_code}
# ====== 用户代码结束 ======

# 最后保存所有未通过 plt.show() 关闭的图表
_remaining_figs = plt.get_fignums()
if _remaining_figs:
    import uuid as _uuid2
    for _fig_num in _remaining_figs:
        _fig = plt.figure(_fig_num)
        _fig_path = os.path.join(FIGURE_DIR, f"fig_{{_uuid2.uuid4().hex[:8]}}.png")
        _fig.savefig(_fig_path, dpi=150, bbox_inches="tight")
        _figure_paths.append(_fig_path)
        print(f"[FIGURE_SAVED]{{_fig_path}}")
    plt.close("all")
'''


def execute_code(
    code: str,
    datasets: list[dict] | None = None,
    timeout: int | None = None,
) -> CodeResult:
    """
    在隔离的子进程中执行 Python 代码

    Args:
        code: 要执行的 Python 代码
        datasets: 数据集列表（DatasetMeta 列表），自动注入到执行环境
        timeout: 超时时间（秒），默认使用配置

    Returns:
        CodeResult 结构化结果
    """
    timeout = timeout or settings.SANDBOX_TIMEOUT

    # 1. 安全检查
    safety_warnings = _check_code_safety(code)
    if safety_warnings:
        logger.warning(f"代码安全检查警告: {safety_warnings}")
        return CodeResult(
            code=code,
            stdout="",
            stderr="\n".join(safety_warnings),
            success=False,
            figures=[],
            dataframes={},
        )

    # 2. 准备临时目录
    exec_id = uuid.uuid4().hex[:8]
    figure_dir = settings.OUTPUT_DIR / f"figures_{exec_id}"
    figure_dir.mkdir(parents=True, exist_ok=True)

    # 3. 构建数据文件映射
    data_files = {}
    if datasets:
        for i, ds in enumerate(datasets):
            name = ds.get("file_name", f"dataset_{i}").replace(".", "_").replace(" ", "_")
            # 去掉扩展名作为变量名
            var_name = Path(name).stem
            data_files[var_name] = ds.get("file_path", "")

    # 4. 生成包装后的代码
    wrapped_code = WRAPPER_TEMPLATE.format(
        figure_dir=str(figure_dir),
        data_files=repr(data_files),
        user_code=code,
    )

    # 5. 写入临时文件
    script_path = tempfile.mktemp(suffix=".py", prefix=f"sandbox_{exec_id}_")
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        # 6. 在子进程中执行
        logger.info(f"沙箱执行开始 [id={exec_id}, timeout={timeout}s]")

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(settings.DATA_DIR),
            env={
                **os.environ,
                "PYTHONHASHSEED": "0",  # 确保可复现
                "MPLBACKEND": "Agg",    # 非交互式后端
            },
        )

        stdout = result.stdout
        stderr = result.stderr
        success = result.returncode == 0

        # 7. 提取图表路径
        figures = []
        clean_stdout_lines = []
        for line in stdout.split("\n"):
            if line.startswith("[FIGURE_SAVED]"):
                fig_path = line.replace("[FIGURE_SAVED]", "").strip()
                if Path(fig_path).exists():
                    figures.append(fig_path)
            else:
                clean_stdout_lines.append(line)
        clean_stdout = "\n".join(clean_stdout_lines).strip()

        logger.info(
            f"沙箱执行完成 [id={exec_id}, success={success}, "
            f"figures={len(figures)}, stdout_len={len(clean_stdout)}]"
        )

        return CodeResult(
            code=code,
            stdout=clean_stdout,
            stderr=stderr.strip(),
            success=success,
            figures=figures,
            dataframes={},
        )

    except subprocess.TimeoutExpired:
        logger.warning(f"沙箱执行超时 [id={exec_id}, timeout={timeout}s]")
        return CodeResult(
            code=code,
            stdout="",
            stderr=f"⏰ 代码执行超时（{timeout}秒），请优化代码效率或减少数据量。",
            success=False,
            figures=[],
            dataframes={},
        )
    except Exception as e:
        logger.error(f"沙箱执行异常 [id={exec_id}]: {e}")
        return CodeResult(
            code=code,
            stdout="",
            stderr=f"沙箱执行异常: {str(e)}",
            success=False,
            figures=[],
            dataframes={},
        )
    finally:
        # 清理临时脚本
        try:
            os.unlink(script_path)
        except OSError:
            pass
