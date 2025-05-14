### 🧱 Fixture Services: rental-service, pricing-service, customer-service
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

# -------- Pricing Service --------
pricing_app = FastAPI()

class PricingRequest(BaseModel):
    vehicle_type: str
    days: int
    customer_tier: str

@pricing_app.post("/pricing")
async def get_pricing(req: PricingRequest, request: Request):
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    fake_jwt = json.loads(request.headers.get("X-JWT", "{}"))
    base_price = 50 if req.vehicle_type == "SUV" else 30
    multiplier = 0.8 if req.customer_tier == "platinum" else 1.0
    total_price = req.days * base_price * multiplier
    response = {"price": total_price}
    log_event("pricing-service", correlation_id, req.dict(), response, fake_jwt)
    return response

