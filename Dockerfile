# Pipeline image: ingest -> dbt build -> export. Same image runs on DuckDB (CI) and BigQuery (prod).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    # dbt writes compiled SQL and logs here, so the container can run as any user id
    DBT_TARGET_PATH=/tmp/dbt/target \
    DBT_LOG_PATH=/tmp/dbt/logs \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pipeline/ pipeline/
COPY dbt/ dbt/

# Landing files, the DuckDB file and BI extracts are mounted at run time, not baked in.
RUN mkdir -p data/landing warehouse exports && chmod -R a+rwX warehouse exports
USER 10001

ENTRYPOINT ["python", "-m", "pipeline"]
CMD ["run"]
