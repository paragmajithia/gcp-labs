FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY demo.py ./
COPY chroma_db/ ./chroma_db/

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "exec python demo.py serve --host 0.0.0.0 --port ${PORT:-8080}"]
