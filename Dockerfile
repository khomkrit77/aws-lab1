FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DB_PATH=/data/maze-munch.sqlite3

WORKDIR /app
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /data \
    && chown app:app /data
COPY --chown=app:app server.py index.html ./

USER app
EXPOSE 8000
CMD ["python", "server.py"]
