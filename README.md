# 🧠 chroma-agent-orchestrator

A lightweight multi-agent orchestration system using LLMs, JSON contracts, and service chaining with semantic discovery via ChromaDB.

---

## 🎯 Executive Summary

This project demonstrates a **modular, AI-assisted orchestration system** for service execution and automation.

### 🌐 What it does  
It allows users—whether human or machine—to express their goals in plain language. The system then:
1. **Understands the request** using a language model
2. **Identifies relevant backend services**
3. **Figures out what needs to run, in what order**
4. **Executes the services automatically**
5. **Returns the complete result, with full traceability**

Think of it as an **AI-powered dispatcher** that builds just-in-time service pipelines from natural language.

---

### 💡 Why this matters

This project is a **Proof of Concept (PoC)** for:
- **Agentic systems** — the future of automation and orchestration
- **LLM-enhanced backends** — turning vague input into structured system behavior
- **Composable services** — everything is defined by contracts, making reuse and chaining trivial
- **Intelligent observability** — every step is logged and traceable

It enables **business logic composition at runtime**, rather than through pre-defined pipelines or hardcoded integrations.

---

### 📈 Potential Use Cases
- **Customer Support**: Automatically trigger workflows based on customer messages
- **Sales Automation**: Assemble service responses based on intent ("Give me a leasing offer for an SUV")
- **DevOps**: Self-healing systems triggered by natural language alerts
- **Internal Tools**: Dynamic dashboards that reconfigure based on stakeholder prompts

---

### 🧭 Strategic Relevance

This prototype supports experimentation with:
- **Autonomous software agents**
- **Declarative backend composition**
- **Service governance via contracts**
- **AI-driven integration without traditional middleware**

It's aligned with modern trends in:
- **AI Ops & Developer Experience**
- **Composable Business Architectures**
- **Digital Transformation through ML-assisted orchestration**

---

### 🛠️ Tech Stack (non-exhaustive)
| Component      | Purpose                               |
|----------------|----------------------------------------|
| FastAPI        | API orchestration                     |
| LM Studio (LLM)| Natural language understanding         |
| ChromaDB       | Semantic service registry              |
| Docker         | Easy local and cloud deployments       |
| JSON Schema    | Structured contracts for validation    |

---

## 🧰 Components

### 1. `coordinator_agent/`
The main orchestrator service. Handles:
- Query interpretation via LLM
- Dynamic JSON schema generation
- Topological sorting of services based on contract dependencies
- Service execution and response aggregation

#### Key files:
- `main.py`: The `/dispatch` endpoint, request routing, LLM-based extraction, and execution loop.
- `utils.py`: Everything from LLM prompting to contract validation, topo sorting, and logging.
- `requirements.txt`: FastAPI + requests + jsonschema.

### 2. `chroma-agents/`
Utility module for bootstrapping service definitions into ChromaDB.

#### Key files:
- `bootstrap_chroma.py`: Uploads JSON service definitions (with metadata + contracts) into Chroma.
- `*.json`: Service definition files (e.g., `customer.json`, `pricing.json`) including ID, description, endpoint, input/output contracts.
- `Dockerfile`: Runs the bootstrapper with required deps (`chromadb[server]`, `requests`).

### 3. `frontend/` (optional, stubbed)
Likely intended for visualization or user input. Currently has just static files.

---

## 📡 Flow Overview

```plaintext
User Query (natural language)
    ↓
LLM (via LM Studio)
    → Extract structured JSON based on aggregated schema from service contracts
    ↓
ChromaDB Lookup
    → Find candidate services and their metadata/contracts
    ↓
Dependency Resolver
    → Sort services using topological sort based on input/output contract
    ↓
Service Execution Loop
    → Inject resolved values, POST to services, update shared context
    ↓
Logging
    → Each execution (or skip) is logged to a shared trace log
```

---

## 🚀 Getting Started

### 1. Bootstrapping ChromaDB

```bash
cd chroma-agents
docker build -t chroma-bootstrap .
docker run --rm -v $PWD:/app chroma-bootstrap \
    --source /app \
    --host <chroma-host> \
    --port 8000 \
    --collection services
```

Or locally:

```bash
python bootstrap_chroma.py --source . --host localhost --port 8000 --collection services
```

### 2. Coordinator Agent (FastAPI)

Make sure LM Studio is running with the correct `/v1/chat/completions` and embedding endpoint exposed.

```bash
cd coordinator_agent
uvicorn main:app --reload --host 0.0.0.0 --port 7000
```

Environment variables:
```env
LMSTUDIO_URL=http://localhost:1234
chat_model=swe-dev-32b-i1
embed_model=text-embedding-all-minilm-l12-v2
CHROMA_AGENTS_URL=http://chroma-services:8000
SERVICE_SELECTION_SYSTEM_PROMPT=coordinator_agent/prompts/serviceSelectionSystem.txt
SERVICE_SELECTION_USER_PROMPT=coordinator_agent/prompts/serviceSelectionUser.txt
```

---

## 🛠 Example Request

POST `/dispatch`:

```json
{
  "query": "Find me an SUV for a premium customer in Munich",
  "candidates": [
    {
      "id": "rental-service",
      "document": "Rental service provides vehicle availability.",
      "metadata": {
        "endpoint": "http://rental:7001/availability",
        "contract_input": "{...}",
        "contract_output": "{...}"
      }
    }
  ]
}
```

---

## 📎 Trace Example

```json
{
  "timestamp": "2025-05-18T13:05:26.635900",
  "service": "coordinator-agent",
  "correlation_id": "abc-123",
  "request": {
    "location": "MUC"
  },
  "response": {
    "vehicle_type": "SUV"
  },
  "target_service": "rental-service",
  "reason": "executed after dependency resolution",
  "query": "Find me an SUV..."
}
```

---

## 📦 Future Ideas

- [ ] Frontend Trace Viewer with Mermaid or JSON diff
- [ ] Semantic service recommendation
- [ ] Streaming or step-by-step service execution visualization
- [ ] Model switching support

---

## 🧾 License

MIT, or whatever license you're planning.
