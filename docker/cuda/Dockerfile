# ── Stage 1: Build ──────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

WORKDIR /app

# 先拷贝依赖声明，利用 Docker 缓存
COPY pyproject.toml uv.lock .python-version ./

# 安装 CUDA 版本依赖（--extra cuda）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra cuda --no-dev

# 拷贝项目源码
COPY . .

# 重新同步以确保项目本身也被安装
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra cuda --no-dev

# ── Stage 2: Runtime ──────────────────────────────────────
FROM nvidia/cuda:13.0.0-runtime-ubuntu24.04 AS runtime

# 安装运行时系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3.13 python3.13-venv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 拷贝虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 拷贝项目代码
COPY --from=builder /app /app

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

EXPOSE 8111

# 使用 uvicorn 启动 FastAPI 服务
CMD ["uvicorn", "detector.server:app", "--host", "0.0.0.0", "--port", "8111"]