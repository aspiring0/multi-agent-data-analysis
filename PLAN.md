# Docker沙箱隔离 - 开发计划

## 问题描述

当前沙箱使用 `subprocess` 进程隔离，存在以下安全问题：
1. **内存限制未实际实现** - 配置了`SANDBOX_MAX_MEMORY_MB`但代码未使用
2. **无CPU限制** - CPU密集型代码可能占满资源
3. **文件系统隔离弱** - 代码可访问`DATA_DIR`内所有文件
4. **无系统调用过滤** - 无seccomp/AppArmor保护
5. **黑名单可绕过** - 通过编码技巧可能绕过危险模式检测

## 当前状态分析

### 现有实现 (`src/sandbox/executor.py`)
```python
# 当前使用subprocess
result = subprocess.run(
    [sys.executable, "-X", "utf8", script_path],
    capture_output=True,
    ...
)
```

### 安全措施
- ✅ 危险模式检测（黑名单）
- ✅ 超时熔断（30秒）
- ❌ 内存限制（配置存在但未实现）
- ❌ CPU限制
- ❌ 文件系统隔离
- ❌ 网络命名空间

## 技术方案

### 方案A: Docker容器沙箱（推荐）

**架构**:
```
┌─────────────────────────────────────────────────────────┐
│  Host System                                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  FastAPI Backend                                  │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │  Sandbox Service                           │  │   │
│  │  │  ┌───────────┐  ┌───────────┐              │  │   │
│  │  │  │ Container │  │ Container │  ...         │  │   │
│  │  │  │ (执行代码) │  │ (执行代码) │              │  │   │
│  │  │  └───────────┘  └───────────┘              │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**容器配置**:
- 只读文件系统（ro）
- 无网络访问（--network none）
- 内存限制（--memory）
- CPU限制（--cpus）
- 用户命名空间（--user）
- Seccomp配置

### 方案B: gVisor增强（更安全）

在Docker基础上使用gVisor运行时：
- 用户态内核
- 系统调用拦截
- 更强的隔离

### 方案C: Firecracker微VM（最安全）

- 轻量级虚拟机
- 极快启动（<125ms）
- 硬件级隔离

**决定**: 采用方案A (Docker容器沙箱)，后续可升级到gVisor

## 开发任务

### Phase 1: Docker Sandbox基础

#### 任务 1.1: 创建Sandbox容器镜像
```dockerfile
# Dockerfile.sandbox
FROM python:3.11-slim

# 安装数据分析依赖
RUN pip install --no-cache-dir \
    pandas==2.0.0 \
    numpy==1.24.0 \
    matplotlib==3.7.0 \
    plotly==5.15.0 \
    seaborn==0.12.0

# 创建非root用户
RUN useradd -m -u 1000 sandbox

# 设置工作目录
WORKDIR /sandbox
RUN chown sandbox:sandbox /sandbox

USER sandbox

# 入口脚本
COPY sandbox_entry.py /sandbox/entry.py
ENTRYPOINT ["python", "/sandbox/entry.py"]
```

#### 任务 1.2: 创建Sandbox入口脚本
```python
# sandbox_entry.py
import sys
import json
import os

def main():
    # 从stdin读取代码和配置
    input_data = json.loads(sys.stdin.read())
    code = input_data["code"]
    timeout = input_data.get("timeout", 30)

    # 执行代码并返回结果
    exec_globals = {"__builtins__": __builtins__}
    try:
        exec(code, exec_globals)
        print(json.dumps({"success": True}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    main()
```

#### 任务 1.3: 创建Docker Sandbox服务
```python
# src/sandbox/docker_executor.py

import docker
import json
import tempfile
from pathlib import Path

class DockerSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "multiagent-sandbox:latest"

    def execute(
        self,
        code: str,
        datasets: list[dict],
        timeout: int = 30,
        memory_mb: int = 512,
        cpu_quota: float = 1.0,
    ) -> CodeResult:
        """在Docker容器中执行代码"""

        # 准备输入数据
        input_data = {
            "code": code,
            "datasets": datasets,
            "timeout": timeout
        }

        # 创建临时文件用于数据集
        volumes = {}
        for i, ds in enumerate(datasets or []):
            # 挂载数据文件为只读
            volumes[ds["file_path"]] = {
                "bind": f"/data/dataset_{i}.csv",
                "mode": "ro"
            }

        try:
            container = self.client.containers.run(
                self.image_name,
                stdin_open=True,
                detach=True,
                mem_limit=f"{memory_mb}m",
                cpu_quota=int(cpu_quota * 100000),
                network_disabled=True,  # 无网络
                read_only=True,  # 只读文件系统
                volumes=volumes,
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],  # 移除所有capabilities
                pids_limit=100,  # 限制进程数
            )

            # 发送输入并等待结果
            container_socket = container.attach_socket(
                params={'stdin': 1, 'stdout': 1, 'stream': 1}
            )
            container_socket.send(json.dumps(input_data).encode())

            # 等待完成（带超时）
            result = container.wait(timeout=timeout)
            output = container.logs().decode()

            # 清理
            container.remove()

            return self._parse_result(output, result)

        except docker.errors.ContainerError as e:
            return CodeResult(success=False, stderr=str(e))
        except Exception as e:
            return CodeResult(success=False, stderr=f"Sandbox error: {e}")
```

### Phase 2: 资源限制增强

#### 任务 2.1: 实现内存限制
```python
# 添加到容器配置
mem_limit=f"{memory_mb}m",
memswap_limit=f"{memory_mb}m",  # 禁用swap
mem_swappiness=0,
```

#### 任务 2.2: 实现CPU限制
```python
cpu_quota=int(cpu_quota * 100000),  # 1.0 CPU = 100000
cpu_period=100000,
cpu_shares=1024,
```

#### 任务 2.3: 实现PIDs限制
```python
pids_limit=100,  # 最多100个进程
```

### Phase 3: 安全配置

#### 任务 3.1: 创建Seccomp配置
```json
// seccomp.json
{
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64"],
    "syscalls": [
        {"names": ["read", "write", "exit", "mmap"], "action": "SCMP_ACT_ALLOW"},
        {"names": ["execve", "fork", "clone"], "action": "SCMP_ACT_ALLOW"},
        {"names": ["socket", "connect", "bind"], "action": "SCMP_ACT_ERRNO"}
    ]
}
```

#### 任务 3.2: 应用安全配置
```python
security_opt=[
    "no-new-privileges",
    "seccomp=seccomp.json"
],
cap_drop=["ALL"],
cap_add=["CHOWN", "SETUID", "SETGID"],  # 仅必需的capabilities
```

### Phase 4: 镜像管理

#### 任务 4.1: 添加镜像构建到Docker Compose
```yaml
# docker-compose.yml
services:
  sandbox:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    image: multiagent-sandbox:latest
    # 不运行，仅用于构建镜像
```

#### 任务 4.2: 预热容器池（可选）
```python
# src/sandbox/container_pool.py

class ContainerPool:
    """预创建容器池，减少启动延迟"""

    def __init__(self, pool_size=5):
        self.pool = []
        self._initialize_pool(pool_size)

    def get_container(self) -> Container:
        if self.pool:
            return self.pool.pop()
        return self._create_container()

    def return_container(self, container):
        # 重置容器状态
        container.restart()
        self.pool.append(container)
```

### Phase 5: 统一接口

#### 任务 5.1: 创建Sandbox工厂
```python
# src/sandbox/factory.py

from configs.settings import settings

def get_sandbox():
    """根据配置返回沙箱实现"""
    if settings.SANDBOX_TYPE == "docker":
        from .docker_executor import DockerSandbox
        return DockerSandbox()
    else:
        from .executor import execute_code
        return execute_code  # 保持向后兼容
```

#### 任务 5.2: 更新配置
```python
# configs/settings.py
class Settings:
    SANDBOX_TYPE: str = "docker"  # "subprocess" 或 "docker"
    SANDBOX_MEMORY_MB: int = 512
    SANDBOX_CPU_QUOTA: float = 1.0
    SANDBOX_TIMEOUT: int = 30
```

## 对比

| 特性 | subprocess（当前） | Docker（目标） |
|------|-------------------|----------------|
| 内存限制 | ❌ 未实现 | ✅ cgroups |
| CPU限制 | ❌ 无 | ✅ cgroups |
| 文件系统隔离 | ❌ 弱 | ✅ 只读+卷挂载 |
| 网络隔离 | ❌ 仅黑名单 | ✅ --network none |
| 系统调用过滤 | ❌ 无 | ✅ seccomp |
| 用户隔离 | ❌ 同用户 | ✅ 非root用户 |
| 进程隔离 | ⚠️ 同namespace | ✅ 容器namespace |

## 验收标准

- [ ] Sandbox镜像可正常构建
- [ ] 简单Python代码可在容器中执行
- [ ] 内存超限代码被正确终止
- [ ] CPU超限代码被正确限制
- [ ] 网络请求被阻止
- [ ] 文件系统为只读
- [ ] 执行超时被正确处理
- [ ] 图表正常生成和保存
- [ ] 性能延迟在可接受范围（<2s启动开销）

## 开发提示词

```
请帮我将当前的subprocess沙箱升级为Docker容器沙箱。

当前状态：
- src/sandbox/executor.py 使用subprocess.run执行代码
- 内存限制未实际实现
- 无真正的资源隔离

需求：
1. 创建 Dockerfile.sandbox 构建沙箱镜像
   - 基于python:3.11-slim
   - 包含pandas/numpy/matplotlib/plotly/seaborn
   - 非root用户运行

2. 创建 src/sandbox/docker_executor.py
   - DockerSandbox类管理容器生命周期
   - 实现内存/CPU/PIDs限制
   - 无网络访问
   - 只读文件系统
   - Seccomp安全配置

3. 创建 src/sandbox/factory.py 支持配置切换
4. 更新 docker-compose.yml 添加sandbox镜像构建
5. 添加 seccomp.json 安全配置

请确保向后兼容，通过配置开关选择沙箱类型。
```

## 性能优化

- 使用容器池减少启动延迟
- 镜像精简减少拉取时间
- 考虑使用Kata Containers或gVisor增强安全

## 风险

- Docker daemon需在宿主机运行
- Windows/Mac上Docker性能差异
- 容器启动开销（可通过池化优化）