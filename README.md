
# 🤖 Agent Demo – Autonomous Microservice PoC

## 🧠 Purpose

Demonstrate a working prototype of an agent-based architecture using semantically discoverable services and capability-based delegation. This PoC sets the foundation for explainable, traceable, and eventually adaptive systems.

---

## 🧱 Architecture Overview

```
                     +------------------+
                     |  CoordinatorAgent|
                     +------------------+
                              |
           +------------------+------------------+
           |                  |                  |
     +-------------+    +--------------+   +---------------+
     |CustomerAgent|    |RentalAgent   |   |PricingAgent   |
     +-------------+    +--------------+   +---------------+
           |                  |                  |
     +-------------+    +--------------+   +---------------+
     |CustomerSvc  |    |RentalSvc     |   |PricingSvc     |
     +-------------+    +--------------+   +---------------+
```

Discovery is powered by **ChromaDB**, where both agents and fixture services register themselves semantically.
Traceability is achieved via a shared log file with correlation IDs.

---

## 🚀 Getting Started

### ✅ Prerequisites

* Docker + Docker Compose
* Python 3.11+ if testing bootstrap scripts manually

### 🔧 Start Everything

```bash
docker-compose up --build
```

This will:

* Launch 3 fixture services
* Start two ChromaDBs: `agents` and `services`
* Automatically bootstrap ChromaDBs with semantic metadata
* Make everything accessible on local ports

### 🌍 Access Ports

| Component              | URL / Port                                     |
| ---------------------- | ---------------------------------------------- |
| rental-service         | [http://localhost:7001](http://localhost:7001) |
| pricing-service        | [http://localhost:7002](http://localhost:7002) |
| customer-service       | [http://localhost:7003](http://localhost:7003) |
| chroma-agents UI (TBD) | [http://localhost:8001](http://localhost:8001) |
| chroma-services UI     | [http://localhost:8002](http://localhost:8002) |

---

## 📦 Directory Layout

```
agentDemo/
├── fixtures/
│   ├── customer-service/
│   ├── pricing-service/
│   └── rental-service/
├── chroma-agents-init/
│   ├── bootstrap/agents/*.json
│   ├── bootstrap_chroma.py
│   └── Dockerfile
├── chroma-services-init/
│   ├── bootstrap/services/*.json
│   ├── bootstrap_chroma.py
│   └── Dockerfile
├── logs/                      # Shared log mount
├── docker-compose.yml
```

---

## 🧪 Sample Goal (future agent)

```json
{
  "goal": "Prepare rental offer for customer 123456 in location MUC from 2025-05-14 to 2025-05-16",
  "correlation_id": "abc-123"
}
```

This goal will eventually be handled by a **Coordinator Agent** that:

* Discovers agent capabilities via Chroma
* Delegates sub-queries
* Aggregates results
* Logs a trace

---

## 🔍 Traceability (log format)

```json
{
  "timestamp": "...",
  "service": "pricing-service",
  "correlation_id": "abc-123",
  "jwt": { ... },
  "request": {...},
  "response": {...}
}
```

These entries will be parsed later by a `trace-observer` container for visualization and debugging.

---

## 🛣️ Roadmap

* [x] Fixture services + shared logging
* [x] ChromaDB with semantic bootstrap
* [ ] CoordinatorAgent with delegation
* [ ] TraceObserver with Mermaid diagram export
* [ ] JWT delegation validation
* [ ] Adaptive agent chaining

---

## 🧩 Why It Matters

This PoC introduces:

* 🔍 Discoverable agents instead of hardcoded service trees
* 🧠 Goal-based execution instead of REST chains
* 📊 Visual traceability via correlation IDs
* 🧱 Clean separation of logic, capability, and data

Designed for future extensions like secure-by-design delegation, adaptive behavior, and self-documenting infrastructure.

