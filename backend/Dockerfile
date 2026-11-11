FROM python:3.12-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create dedicated non-root user and group (UID/GID 1000)
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -d /app -s /bin/sh appuser

# Copy project manifest and locks for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and install application
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Copy entrypoint script
COPY --chown=appuser:appgroup entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Ensure application ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Expose internal FastAPI port
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
