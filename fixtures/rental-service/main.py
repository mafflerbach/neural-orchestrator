# Base: Python FastAPI
# Features:
# - Receives structured requests
# - Logs to /shared/logs/trace.log with correlation ID and fake JWT
# - Simple deterministic responses

from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import os
import json
from datetime import datetime

app = FastAPI()

LOG_PATH = "/shared/logs/trace.log"

# Utilities
def log_event(service: str, correlation_id: str, request_data: dict, response_data: dict, jwt: dict):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": service,
        "correlation_id": correlation_id,
        "jwt": jwt,
        "request": request_data,
        "response": response_data
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as log_file:
        log_file.write(json.dumps(event) + "\n")

# -------- Rental Service --------
rental_app = FastAPI()

class RentalRequest(BaseModel):
    location: str
    start_date: str
    end_date: str

@rental_app.post("/availability")
async def check_availability(req: RentalRequest, request: Request):
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    fake_jwt = json.loads(request.headers.get("X-JWT", "{}"))
    response = {
        "vehicles": [
            {"type": "SUV", "available": True},
            {"type": "Sedan", "available": True}
        ]
    }
    log_event("rental-service", correlation_id, req.dict(), response, fake_jwt)
    return response

