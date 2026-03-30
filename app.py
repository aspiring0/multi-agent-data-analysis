"""
🤖 自驱型多 Agent 数据分析平台 — Streamlit 前端

布局：ChatGPT 风格
- 左侧：会话列表 + 文件上传
- 中间：聊天对话区
- 右侧：代码预览 + 图表展示面板
"""
import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

# 确保项目根目录在 sys.path 中
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.builder import get_graph
from src.agents.data_parser import load_dataframe, build_dataset_meta
from configs.settings import settings

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="多 Agent 数据分析平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 自定义 CSS
# ============================================================
st.markdown("""
<style>
    /* 缩小 Streamlit 默认 padding */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }

    /* 侧边栏样式 */
    .sidebar-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .session-item {
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        margin: 0.2rem 0;
        cursor: pointer;
        font-size: 0.85rem;
    }
    .session-item:hover { background-color: rgba(151, 166, 195, 0.15); }
    .session-active { background-color: rgba(80, 140, 250, 0.15); font-weight: 600; }

    /* 右面板 */
    .code-panel {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border-radius: 8px;
        padding: 0.8rem;
        font-family: 'Fira Code', monospace;
        font-size: 0.8rem;
        overflow-x: auto;
        max-height: 400px;
        overflow-y: auto;
    }

    /* 聊天消息 */
    .stChatMessage { max-width: 100%; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State 初始化
# ============================================================
if "sessions" not in st.session_state:
    st.session_state.sessions = {}

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "graph" not in st.session_state:
    st.session_state.graph = None


def create_new_session(name: str = None) -> str:
    """创建新会话"""
    session_id = uuid.uuid4().hex[:8]
    ts = datetime.now().strftime("%H:%M")
    name = name or f"对话 {ts}"
    st.session_state.sessions[session_id] = {
        "name": name,
        "messages": [],
        "datasets": [],
        "figures": [],
        "current_code": "",
        "report": "",
        "thread_id": session_id,
        "created_at": datetime.now().isoformat(),
    }
    st.session_state.current_session_id = session_id
    return session_id


def get_current_session() -> dict | None:
    """获取当前会话"""
    sid = st.session_state.current_session_id
    if sid and sid in st.session_state.sessions:
        return st.session_state.sessions[sid]
    return None


def ensure_graph():
    """确保 Graph 已初始化"""
    if st.session_state.graph is None:
        with st.spinner("正在初始化分析引擎..."):
            st.session_state.graph = get_graph(with_checkpointer=True)


# ============================================================
# 左侧边栏：会话管理 + 文件上传
# ============================================================
with st.sidebar:
    st.markdown("### 🤖 数据分析平台")
    st.caption("自驱型多 Agent 自动化分析")

    st.divider()

    # 新建会话按钮
    if st.button("➕ 新建对话", use_container_width=True):
        create_new_session()
        st.rerun()

    # 会话列表
    if st.session_state.sessions:
        st.markdown("**会话列表**")
        for sid, session in reversed(list(st.session_state.sessions.items())):
            is_active = sid == st.session_state.current_session_id
            label = f"{'▶ ' if is_active else ''}{session['name']}"
            if st.button(
                label,
                key=f"session_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_session_id = sid
                st.rerun()

    st.divider()

    # 文件上传
    st.markdown("**📁 上传数据文件**")
    uploaded_files = st.file_uploader(
        "支持 CSV / Excel / JSON",
        type=["csv", "tsv", "xlsx", "xls", "json"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        session = get_current_session()
        if session is None:
            create_new_session("数据分析")
            session = get_current_session()

        for uploaded_file in uploaded_files:
            # 检查是否已上传过
            existing_names = [ds.get("file_name") for ds in session["datasets"]]
            if uploaded_file.name in existing_names:
                continue

            # 保存文件
            save_path = settings.UPLOAD_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 解析文件
            df, err = load_dataframe(str(save_path))
            if df is not None:
                meta = build_dataset_meta(df, uploaded_file.name, str(save_path))
                session["datasets"].append(meta)
                st.success(f"✅ {uploaded_file.name} ({meta['num_rows']}行 × {meta['num_cols']}列)")
            else:
                st.error(f"❌ {uploaded_file.name}: {err}")

    # 显示已加载数据集
    session = get_current_session()
    if session and session["datasets"]:
        st.divider()
        st.markdown("**📊 已加载数据集**")
        for ds in session["datasets"]:
            st.caption(f"• {ds['file_name']} ({ds['num_rows']}行)")

    # 底部信息
    st.divider()
    st.caption("Powered by LangGraph + DeepSeek V3")


# ============================================================
# 主区域：聊天 + 右面板
# ============================================================

# 如果没有会话，显示欢迎页
session = get_current_session()
if session is None:
    st.markdown("## 🤖 欢迎使用多 Agent 数据分析平台")
    st.markdown("""
    **开始使用：**
    1. 点击左侧 **➕ 新建对话** 创建新会话
    2. 上传 CSV / Excel / JSON 数据文件
    3. 用自然语言告诉我你想做什么分析

    **示例指令：**
    - 📊 *"帮我做一个数据概览"*
    - 📈 *"画一个销售额随时间变化的折线图"*
    - 🔍 *"分析各产品的相关性"*
    - 📄 *"生成分析报告"*
    """)
    st.stop()

# 有会话时显示聊天界面
# 使用两列布局：左侧聊天(7)，右侧面板(3)
chat_col, panel_col = st.columns([7, 3])

# ---- 聊天区 ----
with chat_col:
    # 显示历史消息
    for msg in session["messages"]:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if hasattr(msg, "content") else str(msg)
        with st.chat_message(role):
            st.markdown(content)

    # 输入框
    if prompt := st.chat_input("输入你的分析需求..."):
        # 添加用户消息
        user_msg = HumanMessage(content=prompt)
        session["messages"].append(user_msg)

        with st.chat_message("user"):
            st.markdown(prompt)

        # 确保 Graph 初始化
        ensure_graph()

        # 调用 LangGraph
        with st.chat_message("assistant"):
            with st.spinner("正在分析..."):
                try:
                    graph = st.session_state.graph

                    # 构建 State 输入
                    state_input = {
                        "messages": session["messages"],
                        "datasets": session["datasets"],
                        "figures": session["figures"],
                        "active_dataset_index": 0,
                        "retry_count": 0,
                    }

                    # 调用 Graph
                    result = graph.invoke(
                        state_input,
                        config={"configurable": {"thread_id": session["thread_id"]}},
                    )

                    # 提取结果
                    new_messages = result.get("messages", [])
                    if new_messages:
                        # 获取最后的 AI 回复
                        last_msg = new_messages[-1]
                        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                        st.markdown(content)
                        session["messages"].append(last_msg)

                    # 更新 session 数据
                    if result.get("figures"):
                        session["figures"] = result["figures"]
                    if result.get("current_code"):
                        session["current_code"] = result["current_code"]
                    if result.get("report"):
                        session["report"] = result["report"]
                    if result.get("datasets"):
                        session["datasets"] = result["datasets"]

                except Exception as e:
                    error_msg = f"❌ 系统错误: {str(e)}"
                    st.error(error_msg)
                    session["messages"].append(AIMessage(content=error_msg))
                    logging.error(f"Graph invoke error: {e}", exc_info=True)

# ---- 右面板：代码 + 图表 ----
with panel_col:
    st.markdown("#### 📋 分析面板")

    # 标签页切换
    tab_code, tab_charts, tab_report = st.tabs(["💻 代码", "📈 图表", "📄 报告"])

    with tab_code:
        code = session.get("current_code", "")
        if code:
            st.code(code, language="python", line_numbers=True)
        else:
            st.caption("执行分析后，生成的代码将在此显示")

    with tab_charts:
        figures = session.get("figures", [])
        if figures:
            for i, fig_path in enumerate(figures):
                if Path(fig_path).exists():
                    st.image(fig_path, caption=f"图表 {i+1}", use_container_width=True)
        else:
            st.caption("生成图表后将在此显示")

    with tab_report:
        report = session.get("report", "")
        if report:
            st.markdown(report)
            # 下载按钮
            st.download_button(
                label="📥 下载报告 (.md)",
                data=report,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
            )
        else:
            st.caption("输入'生成报告'后将在此显示")

    # 数据预览
    if session["datasets"]:
        st.divider()
        st.markdown("#### 📊 数据预览")
        for ds in session["datasets"]:
            with st.expander(f"{ds['file_name']}", expanded=False):
                st.text(ds.get("preview", "无预览"))
                st.caption(
                    f"行: {ds.get('num_rows', '?')} | "
                    f"列: {ds.get('num_cols', '?')} | "
                    f"类型: {', '.join(set(ds.get('dtypes', {}).values()))}"
                )
