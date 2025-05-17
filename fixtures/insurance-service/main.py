from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
import os, json

app = FastAPI()
LOG_PATH = "/shared/logs/trace.log"

# Define input model
class InsuranceRequest(BaseModel):
    vehicle_type: str
    customer_tier: str

# Basic fake calculation table
tier_base = {
    "platinum": 10,
    "gold": 15,
    "premium": 20,
    "basic": 30,
    "under_18": 50
}
vehicle_mult = {
    "SUV": 2.0,
    "Sedan": 1.5,
    "Golf": 1.2
}

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
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")

@app.post("/insurance")
async def get_insurance(req: InsuranceRequest, request: Request):
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    fake_jwt = json.loads(request.headers.get("X-JWT", "{}"))

    base = tier_base.get(req.customer_tier.lower(), 25)
    mult = vehicle_mult.get(req.vehicle_type, 1.5)
    cost = round(base * mult, 2)

    response = {
        "vehicle_type": req.vehicle_type,
        "customer_tier": req.customer_tier,
        "insurance_cost": cost
    }

    log_event("insurance-service", correlation_id, req.dict(), response, fake_jwt)
    return response
