# Jinja2 MCP Server Dockerfile
# 简化版本，避免复杂的系统依赖

FROM python:3.12-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    MCP_TRANSPORT=stdio \
    MCP_PORT=8123

# 配置pip使用清华大学镜像源 (中国大陆优化)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip config set global.timeout 120

# 创建非root用户
RUN groupadd -r jinja && useradd -r -g jinja -s /bin/false jinja

# 创建工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY examples/ ./examples/
COPY run_server.py ./
COPY env.example ./

# 创建配置目录并设置权限
RUN mkdir -p /app/config /app/logs /app/templates && \
    chown -R jinja:jinja /app

# 切换到非root用户
USER jinja

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.jinja_mcp_server; print('OK')" || exit 1

# 暴露端口
EXPOSE 8123

# 设置入口点
ENTRYPOINT ["python", "run_server.py"]

# 默认参数 - stdio模式
CMD ["--transport", "stdio"] 