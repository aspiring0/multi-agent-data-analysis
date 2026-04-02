# 后端开发环境启动脚本

echo "🚀 启动多 Agent 数据分析平台 - 后端开发环境"

# 检查 Python 版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  警告：未检测到虚拟环境"
    echo "建议创建虚拟环境: python -m venv venv"
    echo "然后激活: source venv/bin/activate"
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 启动 PostgreSQL (Docker)
echo "🐘 启动 PostgreSQL..."
docker-compose up -d postgres

# 等待 PostgreSQL 就绪
echo "⏳ 等待 PostgreSQL 启动..."
sleep 5

# 检查 PostgreSQL 连接
echo "🔍 检查数据库连接..."
python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/langgraph')
    print('✅ PostgreSQL 连接成功')
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL 连接失败: {e}')
    exit(1)
"

# 启动 FastAPI
echo "🌐 启动 FastAPI 后端..."
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
