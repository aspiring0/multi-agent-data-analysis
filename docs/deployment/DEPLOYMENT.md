# 部署指南

## 部署方式概览

| 方式 | 适用场景 | 复杂度 | 成本 |
|------|---------|--------|------|
| **本地运行** | 开发/演示 | ⭐ | 免费 |
| **Docker 容器** | 团队共享/测试环境 | ⭐⭐ | 低 |
| **云服务器** | 生产环境 | ⭐⭐⭐ | 中 |
| **Streamlit Cloud** | 快速上线演示 | ⭐ | 免费 |

---

## 方式 1：本地运行（开发/演示）

```bash
# 1. 克隆仓库
git clone https://github.com/aspiring0/multi-agent-data-analysis.git
cd multi-agent-data-analysis

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 5. 运行测试
python -m pytest tests/ -v

# 6. 启动 Web 界面
streamlit run app.py
```

---

## 方式 2：Docker 容器

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（matplotlib 中文字体）
RUN apt-get update && apt-get install -y \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true"]
```

### 构建和运行

```bash
# 构建
docker build -t multi-agent-analysis .

# 运行
docker run -d \
  --name analysis-platform \
  -p 8501:8501 \
  -e DEEPSEEK_API_KEY=your_key_here \
  -v $(pwd)/data:/app/data \
  multi-agent-analysis
```

### docker-compose.yml（推荐）

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## 方式 3：云服务器部署

### 推荐配置

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB SSD |
| 系统 | Ubuntu 22.04 | Ubuntu 22.04 |

### 部署步骤（以 Ubuntu 为例）

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 克隆代码
git clone https://github.com/aspiring0/multi-agent-data-analysis.git
cd multi-agent-data-analysis

# 3. 配置环境变量
echo "DEEPSEEK_API_KEY=your_key" > .env

# 4. 启动
docker compose up -d

# 5. 配置 Nginx 反向代理（可选）
# /etc/nginx/sites-available/analysis
# server {
#     listen 80;
#     server_name your-domain.com;
#     location / {
#         proxy_pass http://localhost:8501;
#         proxy_http_version 1.1;
#         proxy_set_header Upgrade $http_upgrade;
#         proxy_set_header Connection "upgrade";
#         proxy_set_header Host $host;
#     }
# }
```

---

## 方式 4：Streamlit Cloud（最快上线）

1. Fork 仓库到你的 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 选择仓库 → 分支 `main` → 入口文件 `app.py`
4. 在 Secrets 中配置：
   ```toml
   DEEPSEEK_API_KEY = "your_key_here"
   ```
5. 点击 Deploy

---

## 生产化清单

### 安全
- [ ] DEEPSEEK_API_KEY 通过环境变量注入，不写入代码
- [ ] 沙箱已拦截 os.system/subprocess/eval 等危险操作
- [ ] HITL 审批已启用（生产环境设 `auto_approve=False`）
- [ ] 文件上传大小限制（Streamlit 默认 200MB）

### 可靠性
- [ ] 错误恢复：LLM 调用指数退避重试（已实现）
- [ ] 沙箱超时熔断：30 秒（可配置）
- [ ] Debugger 最多 3 次自修复（防无限循环）
- [ ] 全局异常捕获（已实现）

### 性能
- [ ] 长会话消息压缩（已实现，滑动窗口 + 摘要）
- [ ] 异步任务队列（已实现，3 并发线程）
- [ ] 社区 Skill Progressive Disclosure（按需加载）

### 数据
- [ ] SQLite 会话持久化（已实现）
- [ ] 跨会话记忆系统（已实现）
- [ ] 定期清理过期记忆和临时文件

### 监控
- [ ] 日志级别可配置（LOG_LEVEL 环境变量）
- [ ] 任务队列状态可查询
- [ ] 考虑接入 Prometheus + Grafana（长期）

---

## 环境变量参考

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | - | `deepseek-chat` | 模型名称 |
| `DEEPSEEK_BASE_URL` | - | `https://api.deepseek.com` | API 地址 |
| `LLM_TEMPERATURE` | - | `0` | 生成温度 |
| `SANDBOX_TIMEOUT` | - | `30` | 沙箱超时（秒） |
| `LOG_LEVEL` | - | `INFO` | 日志级别 |
