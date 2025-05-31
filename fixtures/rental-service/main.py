from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import os
import json
from datetime import datetime
from typing import List

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

class RentalRequest(BaseModel):
    location: str
    start_date: str
    end_date: str

@app.post("/availability")
async def check_availability(req: RentalRequest, request: Request):
    correlation_id = request.headers.get("X-Correlation-ID", "none")
    fake_jwt = json.loads(request.headers.get("X-JWT", "{}"))

    path = os.path.join(os.path.dirname(__file__), "fixture.json")
    with open(path, "r") as f:
        vehicles = json.load(f)


    log_event("rental-service", correlation_id, req.dict(), vehicles, fake_jwt)
    return { "vehicles": vehicles }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
