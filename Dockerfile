# ai-agent-ops — production image
# Build: docker build -t ai-agent-ops .
# (lihat docker-compose.yml untuk jalankan app + PostgreSQL sekaligus)
FROM python:3.12-slim

WORKDIR /app

# Depedensi dulu (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Aplikasi
COPY app/ ./app/
COPY agent_config.yaml seed.py run_eval.py tests/ ./
COPY tests ./tests

# Non-root (keamanan dasar container)
RUN useradd -m agent && chown -R agent /app
USER agent

ENV AGENT_INTERVAL_SEC=3600 \
    AGENT_ENABLED=1

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
