FROM python:3.12.8 AS builder

WORKDIR /app

COPY dist/agent_support-*-py3-none-any.whl ./

RUN pip install --no-cache-dir agent_support-*-py3-none-any.whl

FROM python:3.12.8-slim

ARG TAG=unknown

LABEL owner="sangram@aicraft.io" \
      group-owner="developer@aicraft.io" \
      name="pilotx-agent-support-service" \
      version=${TAG}

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY service /app/service
COPY resources /app/resources
COPY api_service.py /app/api_service.py

ENV CONFIG_SCHEMA_PATH=/app/resources/config-schema.yaml \
    CONFIG_PATH=/app/resources/config/dev.yaml \
    LOG_CONFIG=/app/resources/log-config.yaml \
    LOG_LEVEL=INFO \
    BUILD_VERSION=${TAG}

VOLUME ["/app/data"]

EXPOSE 8000

ENTRYPOINT ["uvicorn", "api_service:app", "--host", "0.0.0.0", "--port", "8000"]