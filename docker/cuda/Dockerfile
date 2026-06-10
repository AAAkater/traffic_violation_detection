# ── Stage 1: Build ──────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Ensure bytecode compilation & copy-mode for multi-stage compatibility
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120

WORKDIR /app

# Copy dependency declarations first — maximizes Docker layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies using PyTorch CUDA 13.0 wheel index
RUN uv sync --frozen --index https://download.pytorch.org/whl/cu130 --no-dev

# Copy project source code
COPY . .

# Re-sync to install the project package itself
RUN uv sync --frozen --index https://download.pytorch.org/whl/cu130 --no-dev

# ── Stage 2: Runtime ──────────────────────────────────────
FROM nvidia/cuda:13.0.0-runtime-ubuntu24.04 AS runtime

# Install runtime system dependencies in a single layer (no Python from apt!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy uv binary from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Install Python 3.13 via uv (standalone build, no deadsnakes PPA needed)
RUN uv python install 3.13

WORKDIR /app

# Copy virtual environment & source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Re-link venv Python symlink to the local uv-managed Python 3.13
# (keeps all installed packages intact, only updates interpreter link)
RUN uv venv --python 3.13 --allow-existing /app/.venv

# Environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

EXPOSE 4321

# Use FastAPI CLI (production: fastapi run; dev: fastapi dev)
CMD ["fastapi", "dev", "./main.py", "--host", "0.0.0.0", "--port", "4321"]