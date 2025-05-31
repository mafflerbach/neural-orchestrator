# 📐 Architecture of Chroma Agent Orchestrator

## Overview

The Chroma Agent Orchestrator is a proof-of-concept system for dynamic, language-driven orchestration of composable services. It’s designed to simulate how AI agents could build workflows on the fly using semantic metadata and contract-driven execution.

---

## Key Design Elements

### 🧠 LLM-Driven Planning

The system uses a local LLM to:
- Parse natural language input
- Extract a structured representation of the task
- Select appropriate services based on semantic similarity

This happens through `coordinator_agent/main.py` and customizable prompts in the `prompts/` folder.

---

### 🧬 ChromaDB-Powered Service Discovery

ChromaDB stores services as documents enriched with:
- Descriptions
- Endpoint metadata
- Future support for contract schemas

It acts as a lightweight vector search index to retrieve relevant services.

---

### 🔀 Topological Service Sorting

Once the relevant services are identified, they are sorted by dependencies. This:
- Ensures data is available before it’s needed
- Enables parallelism in future versions
- Avoids circular dependencies

Dependency resolution is performed using logic in `utils.py`.

---

### 🧪 Execution Engine

The orchestrator executes services one by one, passing results into a shared context dictionary:
- Input contracts are validated (future feature)
- Execution is skipped if preconditions are unmet
- Trace logs are emitted per step

Each step includes reason annotations for observability.

---

### 🖥️ Frontend (WIP)

A `TraceViewer.jsx` file is stubbed in the `frontend/src/`, planned to:
- Display execution chains
- Provide JSON diff of states
- Replay or simulate steps

---

## Data Flow

```plaintext
User Query
   ↓
LLM (Structured JSON Plan)
   ↓
Service Discovery (ChromaDB)
   ↓
Dependency Sort (Topo Sort)
   ↓
Service Execution (with validation)
   ↓
Trace Output (logged & frontend-visible)
```

---

## Future Architecture Improvements

- Full schema-based validation per contract
- Context snapshotting for auditability
- Parallel DAG-based execution model
- Frontend integration with Chroma for live queries
