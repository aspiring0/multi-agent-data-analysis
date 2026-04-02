"""
后端 API 验证测试

在开始前端开发前，验证后端所有功能是否正常工作。
"""
import sys
import subprocess
import time
import json
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 测试配置
BASE_URL = "http://localhost:8000"
SESSION_NAME = "验证测试会话"


def test_prerequisites():
    """测试 1: 检查前置条件"""
    print("\n" + "="*60)
    print("测试 1: 检查前置条件")
    print("="*60)

    # 检查 PostgreSQL
    print("🐘 检查 PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            "postgresql://postgres:postgres@localhost:5432/langgraph"
        )
        print("✅ PostgreSQL 连接成功")
        conn.close()
    except ImportError:
        print("❌ psycopg2 未安装，运行: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
        print("请确保 PostgreSQL 已启动:")
        print("  docker-compose up -d postgres")
        return False

    # 检查后端是否运行
    print("\n🌐 检查后端服务...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 后端服务异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务")
        print("请启动后端:")
        print("  python -m uvicorn backend.api.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def test_session_management():
    """测试 2: 会话管理"""
    print("\n" + "="*60)
    print("测试 2: 会话管理")
    print("="*60)

    # 创建会话
    print("📝 创建会话...")
    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"name": SESSION_NAME},
        timeout=5
    )

    if response.status_code != 200:
        print(f"❌ 创建会话失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return None

    session_data = response.json()
    session_id = session_data.get("id")
    print(f"✅ 会话创建成功")
    print(f"   会话 ID: {session_id}")
    print(f"   名称: {session_data.get('name')}")
    print(f"   创建时间: {session_data.get('created_at')}")

    # 列出所有会话
    print("\n📋 列出所有会话...")
    response = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
    if response.status_code == 200:
        sessions = response.json()
        print(f"✅ 找到 {len(sessions)} 个会话")
        for s in sessions:
            print(f"   - {s.get('id')}: {s.get('name')}")
    else:
        print(f"❌ 获取会话列表失败: {response.status_code}")

    # 获取会话详情
    print("\n🔍 获取会话详情...")
    response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
    if response.status_code == 200:
        session_detail = response.json()
        print(f"✅ 会话详情获取成功")
        print(f"   消息数: {len(session_detail.get('messages', []))}")
        print(f"   数据集数: {len(session_detail.get('datasets', []))}")
        print(f"   图表数: {len(session_detail.get('figures', []))}")
    else:
        print(f"❌ 获取会话详情失败: {response.status_code}")

    return session_id


def test_chat_api(session_id: str):
    """测试 3: 聊天 API"""
    print("\n" + "="*60)
    print("测试 3: 聊天 API")
    print("="*60)

    test_message = "你好，这是测试消息"

    print(f"💬 发送测试消息: '{test_message}'")
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "session_id": session_id,
            "message": test_message
        },
        timeout=30  # 给足处理时间
    )

    if response.status_code != 200:
        print(f"❌ 聊天请求失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False

    result = response.json()
    print(f"✅ 聊天请求成功")
    print(f"   回复: {result.get('response', '')[:100]}...")

    # 验证消息已保存
    print("\n🔍 验证消息已保存...")
    response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
    if response.status_code == 200:
        session_detail = response.json()
        messages = session_detail.get('messages', [])
        print(f"✅ 消息已保存，当前消息数: {len(messages)}")
        if messages:
            last_msg = messages[-1]
            print(f"   最新消息: role={last_msg.get('role')}, content={last_msg.get('content')[:50]}...")
    else:
        print(f"⚠️ 无法验证消息保存")

    return True


def test_file_upload(session_id: str):
    """测试 4: 文件上传"""
    print("\n" + "="*60)
    print("测试 4: 文件上传")
    print("="*60)

    # 创建测试 CSV 文件
    print("📄 创建测试 CSV 文件...")
    test_csv = """name,age,score
Alice,25,95
Bob,30,87
Charlie,28,92
"""

    test_file_path = Path("test_data.csv")
    try:
        with open(test_file_path, 'w') as f:
            f.write(test_csv)
        print(f"✅ 测试文件已创建: {test_file_path}")
    except Exception as e:
        print(f"❌ 创建测试文件失败: {e}")
        return False

    # 上传文件
    print(f"\n📤 上传文件到会话 {session_id}...")
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path.name, f, 'text/csv')}
            response = requests.post(
                f"{BASE_URL}/api/upload/{session_id}",
                files=files,
                timeout=10
            )

        if response.status_code != 200:
            print(f"❌ 文件上传失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

        result = response.json()
        print(f"✅ 文件上传成功")
        print(f"   文件名: {result.get('file_name')}")
        print(f"   行数: {result.get('num_rows')}")
        print(f"   列数: {result.get('num_cols')}")
        print(f"   列名: {result.get('columns')}")

        # 验证数据集已保存
        print("\n🔍 验证数据集已保存...")
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
        if response.status_code == 200:
            session_detail = response.json()
            datasets = session_detail.get('datasets', [])
            print(f"✅ 数据集已保存，当前数据集数: {len(datasets)}")
            if datasets:
                for ds in datasets:
                    print(f"   - {ds.get('file_name')}: {ds.get('num_rows')}行 × {ds.get('num_cols')}列")

    except Exception as e:
        print(f"❌ 文件上传测试失败: {e}")
        return False
    finally:
        # 清理测试文件
        if test_file_path.exists():
            test_file_path.unlink()
            print(f"\n🧹 清理测试文件: {test_file_path}")

    return True


def test_websocket(session_id: str):
    """测试 5: WebSocket 连接"""
    print("\n" + "="*60)
    print("测试 5: WebSocket 连接")
    print("="*60)

    import asyncio
    import websockets

    async def test_ws():
        try:
            uri = f"ws://localhost:8000/ws/chat/{session_id}"
            print(f"🔌 连接到 WebSocket: {uri}")
            async with websockets.connect(uri) as ws:
                print("✅ WebSocket 连接成功")

                # 等待连接确认
                msg = await ws.recv()
                if json_parse(msg):
                    data = json_parse(msg)
                    if data.get('type') == 'connected':
                        print(f"   收到: {data}")

                # 发送测试消息
                test_msg = {
                    "type": "message",
                    "message": "WebSocket 测试消息"
                }
                print(f"\n💬 发送测试消息...")
                await ws.send(json.dumps(test_msg))

                # 接收响应（简化版，只收前几条）
                chunk_count = 0
                max_chunks = 5

                while chunk_count < max_chunks:
                    msg = await ws.recv()
                    data = json_parse(msg)
                    if not data:
                        continue

                    msg_type = data.get('type')
                    if msg_type == 'start':
                        print("   收到: start")
                    elif msg_type == 'chunk':
                        content = data.get('content', '')[:50]
                        print(f"   收到 chunk: {content}...")
                        chunk_count += 1
                    elif msg_type == 'done':
                        print("   收到: done")
                        break
                    elif msg_type == 'error':
                        error_msg = data.get('message', '')
                        print(f"❌ 收到 error: {error_msg}")
                        return False

                print(f"✅ WebSocket 测试完成，收到 {chunk_count} 个 chunks")
                return True

        except Exception as e:
            print(f"❌ WebSocket 测试失败: {e}")
            return False

    # 运行异步测试
    try:
        result = asyncio.run(test_ws())
        return result
    except ImportError:
        print("❌ websockets 未安装，跳过 WebSocket 测试")
        print("   安装: pip install websockets")
        return None  # 不算失败，只是跳过


def json_parse(text: str):
    """简单的 JSON 解析（避免依赖）"""
    import json
    try:
        return json.loads(text)
    except:
        return None


def test_integration():
    """测试 6: 集成测试"""
    print("\n" + "="*60)
    print("测试 6: 集成测试")
    print("="*60)

    print("🔗 测试与现有 LangGraph 的集成...")

    try:
        # 导入测试
        from src.graph.builder import get_graph

        print("✅ LangGraph 导入成功")

        # 测试 Graph 构建
        graph = get_graph(with_checkpointer=False)
        print("✅ Graph 构建成功")

        # 测试 Graph 节点
        nodes = graph.nodes
        print(f"✅ Graph 节点: {list(nodes)}")

        return True

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """运行所有验证测试"""
    print("\n" + "="*60)
    print("🚀 后端 API 验证测试")
    print("="*60)
    print("说明: 这个测试会验证后端的所有核心功能")
    print("预计耗时: 2-3 分钟")

    # 暂停一下，确保用户准备好了
    input("\n按 Enter 键开始测试...")

    # 运行测试
    results = {}

    # 测试 1: 前置条件
    if not test_prerequisites():
        print("\n❌ 前置条件检查失败，请先解决上述问题后再试")
        return

    results['prerequisites'] = True

    # 测试 2: 会话管理
    session_id = test_session_management()
    if session_id:
        results['session_id'] = session_id
        results['session_management'] = True
    else:
        results['session_management'] = False

    if not session_id:
        print("\n❌ 会话管理测试失败，无法继续")
        return

    # 测试 3: 聊天 API
    results['chat_api'] = test_chat_api(session_id)

    # 测试 4: 文件上传
    results['file_upload'] = test_file_upload(session_id)

    # 测试 5: WebSocket
    results['websocket'] = test_websocket(session_id)

    # 测试 6: 集成测试
    results['integration'] = test_integration()

    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        test_display = {
            'prerequisites': '前置条件检查',
            'session_id': '会话管理',
            'session_management': '会话管理',
            'chat_api': '聊天 API',
            'file_upload': '文件上传',
            'websocket': 'WebSocket',
            'integration': '集成测试',
        }
        print(f"{status} - {test_display.get(test_name, test_name)}")

    print(f"\n总计: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！后端功能正常，可以开始前端开发。")
        print("\n下一步: 创建 Next.js 前端项目")
    else:
        print(f"\n⚠️  有 {failed_tests} 个测试失败，请先解决后再继续。")
        print("\n常见问题解决方案:")
        print("1. PostgreSQL 未启动: docker-compose up -d postgres")
        print("2. 后端未启动: python -m uvicorn backend.api.main:app --reload")
        print("3. 依赖缺失: pip install -r requirements.txt")
        print("4. 端口被占用: 检查 8000 端口是否被占用")


if __name__ == "__main__":
    main()
