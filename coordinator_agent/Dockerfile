FROM python:3.11-slim

# 1. Set working dir
WORKDIR /app

# 2. Copy and install dependencies
COPY coordinator_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy your package
COPY coordinator_agent/ ./coordinator_agent

# 4. (Optional) Create shared log dir
RUN mkdir -p /shared/logs

# 5. Default command
CMD ["uvicorn", "coordinator_agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
