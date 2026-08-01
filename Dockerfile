# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY --from=docker:28-cli /usr/local/bin/docker /usr/local/bin/docker

COPY config ./config
COPY docker ./docker

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/logs /sandbox-shared \
    && chown -R appuser:appuser /app /sandbox-shared

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/dashboard', timeout=3).status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
