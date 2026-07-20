# 后端 Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml .

# 安装 Python 依赖
RUN uv sync --no-dev && rm -rf /root/.cache/uv

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/uploads /app/data/thumbnails /app/data/logs /app/data/models

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
