from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import os
import json
from datetime import datetime

app = FastAPI()
LOG_PATH = "/shared/logs/trace.log"

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
    with open(LOG_PATH, "a") as log_file:
        log_file.write(json.dumps(event) + "\n")

class CustomerResponse(BaseModel):
    customer_tier: str
    preferences: dict


@app.post("/customer/{customer_id}")
async def get_customer(customer_id: int):
    # Load all fixtures
    with open("fixture.json", "r") as f:
        all_data = json.load(f)

    customer = next((c for c in all_data["customers"] if int(c["id"]) == customer_id), None)

    if not customer:
        return {"error": "Customer not found"}

    return customer

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
