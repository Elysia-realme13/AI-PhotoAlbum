# 后端 Dockerfile
# bookworm = 锁定 Debian 12，避免基础镜像底层 OS 漂移
FROM python:3.12-slim-bookworm

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 复制依赖描述和锁文件（先复制锁文件层，利用 Docker 缓存）
COPY pyproject.toml uv.lock ./

# 严格按 uv.lock 安装，不重新解析版本
RUN uv sync --no-dev --frozen

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/uploads /app/data/thumbnails /app/data/logs /app/data/models

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
