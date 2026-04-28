# Base image aligned with CI Python version
FROM python:3.12-slim AS build

#install uv from official source
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Set working directory inside the container
WORKDIR /app
# Keep Python logs unbuffered and avoid .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Copy dependency files first for faster builds
COPY pyproject.toml requirements.txt ./

# Install uv and dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev
    # Copy the rest of the project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PATH="/app:${PATH}" \
    PYTHONPATH="/app" \
    UV_LINK_MODE=copy

RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /app -s /bin/bash appuser

WORKDIR /app

COPY --from=build --chown=appuser:appgroup /app .

USER appuser
# Default command (runs the live trading entrypoint)
CMD ["python", "-m", "src.main"]
