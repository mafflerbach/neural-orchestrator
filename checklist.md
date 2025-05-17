
# 🛠️ AgentDemo Bring-Up Checklist

A live PoC of a **Semantic Agent Orchestrator** with ChromaDB, FastAPI fixtures, and dynamic AI-based coordination. This checklist walks through setup and key components.

---

## ✅ 1. Pre-flight File Check

* [x] Fixture services exist in `./fixtures/<service-name>/` (rental, pricing, customer, insurance)
* [x] Each has:

  * [x] `main.py`, `Dockerfile`, `requirements.txt`
  * [x] Logs written to `./logs/trace.log`
* [x] Bootstrap services for Chroma:

  * [x] `chroma-agents-init/` and `chroma-services-init/`
  * [x] Contain `bootstrap/` JSONs and `bootstrap_chroma.py`
* [x] `logs/trace.log` exists:

```bash
mkdir -p logs
: > logs/trace.log
```

---

## 🧱 2. Build All Images

```bash
docker-compose build
```

Includes:

* 4 fixture services: rental, pricing, customer, insurance
* 1 Chroma bootstrap init containers
* Coordinator agent
* Frontend React app

---

## 🚀 3. Start Services

```bash
docker-compose up -d
```

Boots:

* All services with health checks
* Coordinator + React UI
* Chroma DB and bootstrapper

---

## 📡 4. Verify Fixture Services

Each responds to POSTs with dummy fixture logic and logs traces.

Example:

```bash
curl -X POST http://localhost:7002/pricing \
  -H 'Content-Type: application/json' \
  -H 'X-Correlation-ID: test-001' \
  -d '{"vehicle_type":"SUV","days":3,"customer_tier":"platinum"}'
```

Confirm log output appears in `logs/trace.log`.

---

## 🧠 5. Chroma + Metadata

Chroma stores:

* Service descriptions
* Contract input/output schemas
* Default values
* Tags, capabilities, endpoints

Verify services collection:

```bash
curl http://localhost:8002/api/v1/collections/services
```

---

## 🧪 6. Orchestration Flow

The coordinator:

* Uses semantic embedding to fetch top services via `/api/search`
* Calls `/api/dispatch` to:

  * Rerank services using LLM
  * Resolve inputs from prior results (chaining)
  * Send fan-out requests
  * Return merged results

Logs each step to the trace file.

---

## 🔍 7. UI: Semantic Orchestrator + Trace Viewer

Open `http://localhost:3000/`:

### Semantic Agent Orchestrator

* Type a request:
  `i need a car in muc and i am customer 1234 with prices`
* See matching services
* Run coordination
* View merged response

### Trace Viewer

* Open `/trace` view (or use embedded component)
* See:

  * All steps by correlation ID
  * Query + reason for each service
  * Request/response payloads
  * Contract input/output per service
  * Auto-refresh to monitor in real time

---

## 🎯 Next Steps

* [ ] Chain responses into downstream service calls
* [ ] Auto-infer inputs from contract + prior results
* [ ] Add aggregation contract support for "composed" responses
* [ ] Visual trace graph with `react-flow` or `visx/network`
* [ ] First autonomous agent (reads Chroma, builds plan, executes)

