from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict
import os, json
from datetime import datetime

app = FastAPI()

LOG_PATH = "/shared/logs/trace.log"

class PricingRequest(BaseModel):
    vehicle_type: str
    customer_tier: str

def log_event(service: str, correlation_id: str, request_data: dict, response_data: dict, jwt: dict):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": service,
        "correlation_id": correlation_id,
        "jwt": jwt,
        "request": request_data,
        "response": response_data
    }
    print(json.dumps(event) + "\n")
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")

@app.post("/pricing")
async def get_pricing(req: PricingRequest, request: Request):
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    fake_jwt = json.loads(request.headers.get("X-JWT", "{}"))

    # Load fixture
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture.json")
    with open(fixture_path, "r") as f:
        fixture = json.load(f)

    # Find base price for vehicle type
    match = next((item for item in fixture if item["type"].lower() == req.vehicle_type.lower()), None)
    if not match:
        return {"error": f"vehicle type '{req.vehicle_type}' not found in fixture"}

    base_price = match["base_price"]

    # Determine multiplier
    tier_multiplier = {
        "platinum": 0.5,
        "gold": 0.7,
        "premium": 0.8,
        "under_18": 1.2
    }
    multiplier = tier_multiplier.get(req.customer_tier.lower(), 1.0)

    total_price = 1 * base_price * multiplier

    response = {
        "vehicle_type": req.vehicle_type,
        "days": 1,
        "customer_tier": req.customer_tier,
        "base_price": base_price,
        "multiplier": multiplier,
        "total_price": total_price
    }

    log_event("pricing-service", correlation_id, req.dict(), response, fake_jwt)
    return response
