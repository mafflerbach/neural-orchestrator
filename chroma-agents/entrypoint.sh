#!/bin/bash
set -e

echo "[INIT] Starting Chroma (uvicorn) in background..."
uvicorn chromadb.app:app --host 0.0.0.0 --port 8000 &
CHROMA_PID=$!

 echo "[WAIT] Waiting for Chroma to become ready…"
 until curl -sf http://localhost:8000/api/v1/heartbeat; do
   echo "[WAIT] retrying in 3s…"
   sleep 3
 done
 echo "[READY] Chroma is up!"

echo "[BOOTSTRAP] Adding services..."
python3 bootstrap_chroma.py \
  --source /app/bootstrap/agents \
  --host localhost \
  --port 8000 \
  --collection services

echo "[DONE] Tail Chroma logs..."
wait $CHROMA_PID
