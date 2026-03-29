"""
多 Agent 数据分析平台 — 命令行入口
用于快速验证整个 Graph 是否正常工作。

用法：
    python main.py
"""
import sys
import logging
from pathlib import Path

# 将项目根目录加入 Python 路径
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from configs.settings import settings
from src.graph.builder import build_analysis_graph

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    """交互式命令行入口"""
    # 验证配置
    errors = settings.validate()
    if errors:
        for e in errors:
            logger.error(f"配置错误: {e}")
        print("\n⚠️  请先在 .env 文件中设置 DEEPSEEK_API_KEY")
        print("   cp .env.example .env && vim .env")
        return

    # 构建 Graph
    print("🔧 正在构建分析工作流...\n")
    graph = build_analysis_graph(with_checkpointer=True, debug=False)
    print("✅ 工作流构建成功！\n")

    # 打印欢迎信息
    print("=" * 60)
    print("  🤖 多 Agent 数据分析平台 v0.1.0")
    print("  输入自然语言指令，开始数据分析之旅")
    print("  输入 'quit' 退出")
    print("=" * 60)
    print()

    # 会话配置（支持多轮对话）
    config = {"configurable": {"thread_id": "session-001"}}

    while True:
        try:
            user_input = input("📝 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("\n👋 再见！")
            break

        # 调用 Graph
        try:
            result = graph.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )

            # 提取最后一条 AI 消息
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                print(f"\n🤖 助手: {content}\n")
            else:
                print("\n🤖 助手: (无响应)\n")

            # 显示路由信息（调试用）
            intent = result.get("intent", "")
            task_type = result.get("task_type", "")
            next_agent = result.get("next_agent", "")
            if intent:
                logger.debug(f"[调度] intent={intent}, task_type={task_type}, agent={next_agent}")

        except Exception as e:
            logger.error(f"执行出错: {e}", exc_info=True)
            print(f"\n❌ 出错了: {e}\n")


if __name__ == "__main__":
    main()
