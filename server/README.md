# 后端服务 (server)

基于 FastAPI 的交通违法检测与判定服务。

## 本地开发

```bash
cd server

# 1. 安装依赖（需要 Python 3.13 + NVIDIA GPU）
uv sync --index https://download.pytorch.org/whl/cu130

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，配置数据库和对象存储连接

# 3. 启动依赖服务（PostgreSQL + RustFS）
docker compose -f ../docker/cuda/docker-compose.yaml up -d postgres rustfs

# 4. 启动开发服务器
uv run fastapi dev main.py --host 0.0.0.0 --port 8000
```

### API 端点

| 方法   | 路径          | 说明                      |
| ------ | ------------- | ------------------------- |
| `POST` | `/v1/detect`  | 上传图片，YOLO 检测       |
| `POST` | `/v1/judge`   | 对已检测图片执行 LLM 判定 |
| `GET`  | `/v1/history` | 分页查询历史记录          |
| `GET`  | `/v1/health`  | 健康检查                  |

### 开发工具

```bash
uv run ruff format   # 格式化
uv run ruff check    # Lint
uv run pytest        # 测试
```
