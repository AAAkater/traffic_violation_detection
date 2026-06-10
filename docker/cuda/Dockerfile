# ── Stage 1: Build ──────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120 \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.13

WORKDIR /app

# bind mount: pyproject.toml/uv.lock 不进镜像层，源码变更不触发依赖重装
# cache mount: uv 下载缓存跨构建保留
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --index https://download.pytorch.org/whl/cu130 --no-dev

# Copy project source code
# (no second sync needed — project has no [build-system] / self-install)
COPY . .

# ── Stage 2: Runtime ──────────────────────────────────────
# base 镜像比 runtime 小 ~200 MB（少 CUDA 示例/文档等）
FROM nvidia/cuda:13.0.0-base-ubuntu24.04 AS runtime

# Install runtime system dependencies in a single layer (no Python from apt!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy standalone Python from builder — no uv needed in runtime!
COPY --from=builder /python /python

WORKDIR /app

# Only copy what's needed at runtime (not pyproject.toml, uv.lock, etc.)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/main.py /app/
COPY --from=builder /app/detector/ /app/detector/

# Environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/app/configs

EXPOSE 4321

# Use FastAPI CLI (production: fastapi run; dev: fastapi dev)
CMD ["fastapi", "run", "./main.py", "--host", "0.0.0.0", "--port", "4321"]