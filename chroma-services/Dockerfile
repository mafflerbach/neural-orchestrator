FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y curl && \
    pip install --no-cache-dir "chromadb[server]==0.4.13" requests tqdm && \
    chmod +x /app/entrypoint.sh
RUN pip uninstall -y chromadb && \
    pip install --no-cache-dir "chromadb[server]==0.4.13"

ENTRYPOINT ["/app/entrypoint.sh"]
