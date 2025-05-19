from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from jsonschema import validate, ValidationError
from typing import List, Dict, Any

import json
import os, requests, json, uuid
import re
import logging


app = FastAPI()

# ── config ───────────────────────────────────────────────────────────────────────
chroma_services_url = os.getenv("CHROMA_AGENTS_URL", "http://chroma-services:8000")
lmstudio_url      = os.getenv("LMSTUDIO_URL")
if not lmstudio_url:
    raise runtimeerror("missing lmstudio_url env var")

embed_path    = os.getenv("lmstudio_embed_path", "/v1/embeddings")
chat_path     = os.getenv("lmstudio_chat_path",  "/v1/chat/completions")
embed_model   = os.getenv("embed_model",   "text-embedding-all-minilm-l12-v2")
chat_model    = os.getenv("chat_model",    "swe-dev-32b-i1")
collection        = "services"
log_path          = "/shared/logs/trace.log"
request_timeout   = (2, 60)   # connect, read timeouts

SYSTEM_PROMPT_PATH = os.getenv("SERVICE_SELECTION_SYSTEM_PROMPT", "coordinator_agent/prompts/serviceSelectionSystem.txt")
USER_PROMPT_PATH   = os.getenv("SERVICE_SELECTION_USER_PROMPT", "coordinator_agent/prompts/serviceSelectionUser.txt")

FULL_URL = lmstudio_url.rstrip("/") + chat_path
# ────────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger("coordinator")
logger.setLevel(logging.INFO)


from coordinator_agent.utils import (
    build_candidates_section,
    load_prompt,
    parse_inputs,
    extract_json_like,
    extract,
    get_collection_id,
    log_event,
    topo_sort_services,
    resolve_inputs,
    resolve_fields,
    is_resolvable,
    resolve_with_sources,
    allow_nulls
)




@app.get("/api/search")
def semantic_search(q: str, k: int = 5):
    # 1) embed via lm studio
    embed_url = lmstudio_url.rstrip("/") + embed_path
    try:
        r = requests.post(
            embed_url,
            json={"model": embed_model, "input": [q]},
            timeout=request_timeout
        )
        r.raise_for_status()
        body = r.json()
        # handle both openai and lm studio shapes
        if "data" in body:
            emb = body["data"][0]["embedding"]
        elif "embedding" in body:
            emb = body["embedding"]
        else:
            raise runtimeerror(f"no embedding in response: keys={List(body.keys())}")
    except exception as e:
        raise httpexception(502, detail=f"embedding error: {e}")

    # 2) query chroma
    try:
        coll_id = get_collection_id()
    except exception as e:
        raise httpexception(502, detail=f"chroma error: {e}")

    query_url = f"{chroma_services_url}/api/v1/collections/{coll_id}/query"
    payload = {
        "query_embeddings": [emb],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"]
    }
    r2 = requests.post(query_url, json=payload, timeout=request_timeout)
    if r2.status_code != 200:
        raise httpexception(502, detail=f"vector search error: {r2.text}")
    data = r2.json()

    # 3) format the results
    results = []
    ids       = data.get("ids", [[]])[0]
    metadatas = data.get("metadatas", [[]])[0]
    distances = data.get("distances", [[]])[0]
    for i, aid in enumerate(ids):
        results.append({
            "id":       aid,
            "metadata": metadatas[i],
            "distance": distances[i]
        })
    return results



@app.post("/api/rerank")
def rerank(body: Dict):
    q = body.get("query")
    candidates = body.get("candidates", [])
    if not q or not candidates:
        raise HTTPException(400, detail="require 'query' and 'candidates'")

    system_prompt = load_prompt(SYSTEM_PROMPT_PATH)
    user_template = load_prompt(USER_PROMPT_PATH)
    # --- 1. Build candidate description block ---
    user_prompt = user_template \
        .replace("{{query}}", q) \
        .replace("{{candidates}}", build_candidates_section(candidates))

    # --- 2. Build and send LLM request ---
    chat_url = lmstudio_url.rstrip("/") + chat_path
    payload = {
        "model": chat_model,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user",   "content": user_prompt }
        ],
        "temperature": 0
    }

    try:

        r = requests.post(chat_url, json=payload, timeout=request_timeout)
        r.raise_for_status()
        content = r.json().get("choices", [])[0].get("message", {}).get("content", "")

        try:
            picked = json.loads(content)
        except json.JSONDecodeError:
            picked = json.loads(extract_json_like(content))

        pickids: List[str] = picked.get("pickids", [])
        order: List[str] = picked.get("order", pickids)
        reasons: Dict[str, str] = picked.get("reasons", {})

        if not pickids:
            raise RuntimeError("no pickids returned")

    except Exception as e:
        raise HTTPException(502, detail=f"rerank error: {e}")

    return {
        "pickids": pickids,
        "order": order,
        "reasons": reasons,
        "raw_response": content
    }

@app.get("/api/logs", response_class=PlainTextResponse)
def read_logs():
    try:
        with open(log_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")





@app.post("/api/dispatch")
def dispatch(body: Dict):
    query = body.get("query")
    candidates = body.get("candidates", [])
    if not query or not candidates:
        raise HTTPException(400, detail="require 'query' and 'candidates'")

    correlation_id = str(uuid.uuid4())

    rerank_result = rerank({"query": query, "candidates": candidates})
    pickids = rerank_result["pickids"]
    reasons = rerank_result["reasons"]
    raw_response = rerank_result.get("raw_response", "")

    responses: Dict[str, Any] = {}
    executed = set()
    context = body.copy()
    contract_map = {}
    merged_props = {}

    for svc in candidates:
        pid = svc["id"]
        if pid not in pickids:
            continue

        contract_input = json.loads(svc["metadata"].get("contract_input", "{}"))
        contract_output = json.loads(svc["metadata"].get("contract_output", "{}"))

        contract_map[pid] = {
            "input": contract_input,
            "output": contract_output
        }

        for k, v in contract_input.get("properties", {}).items():
            merged_props[k] = v

    schema = {"type": "object", "properties": merged_props}
    schema = allow_nulls(schema)
    result = extract(prompt=query, schema=schema)

    resolvable_services = [
        pid for pid in pickids
        if pid in contract_map and is_resolvable(contract_map[pid]["input"], context)
    ]



    cleaned_result = {
        k: v for k, v in result.items()
        if v is not None and str(v).strip().lower() != "null"
    }
    context.update(cleaned_result)

    if not cleaned_result:
        raise HTTPException(400, detail="No usable values extracted from query")


    resolvable = {
        pid for pid in pickids
        if pid in contract_map and is_resolvable(contract_map[pid]["input"], context)
    }

    try:
        order = topo_sort_services(list(resolvable), contract_map, context.keys())
    except RuntimeError as e:
        # If resolution still fails (e.g. circular deps), skip topo and rely on retry loop
        print(f"[dispatch()] Topo sort failed: {e}")
        order = list(resolvable)




    prev_ctx_keys = set(context.keys())
    retries = 0
    max_retries = 5

    while True:
        progress = False
        unresolved = []

        remaining = [pid for pid in pickids if pid not in executed]
        if not remaining:
            break

        for pid in remaining:
            if pid in executed:
                continue

            svc = next((c for c in candidates if c["id"] == pid), None)
            if not svc:
                continue

            contract = contract_map.get(pid, {})
            contract_input = contract.get("input", {})
            props = contract_input.get("properties", {})
            raw_required = contract_input.get("required")
            required = raw_required or [
                k for k, v in props.items()
                if not (isinstance(v.get("type"), list) and "null" in v["type"])
            ]

            resolved = {
                k: context[k] for k in required
                if k in context and context[k] is not None and str(context[k]).lower() != "null"
            }

            missing = [k for k in required if k not in resolved]
            if missing:
                unresolved.append((pid, missing))
                continue

            url = svc["metadata"]["endpoint"]
            for k, v in resolved.items():
                url = url.replace(f"{{{k}}}", str(v))

            headers = {
                "content-type": "application/json",
                "x-correlation-id": correlation_id,
                "x-jwt": "{}"
            }

            try:
                sub_r = requests.post(url, json=resolved, headers=headers, timeout=request_timeout)
                sub_r.raise_for_status()
                try:
                    res = sub_r.json()
                except ValueError:
                    res = {"error": "invalid JSON", "raw": sub_r.text[:200]}
            except Exception as e:
                res = {"error": str(e)}

            responses[pid] = res
            executed.add(pid)
            context.update(res)

            log_event(
                correlation_id,
                svc,
                resolved,
                res,
                reason=reasons.get(pid, "executed after dependency resolution"),
                query=query
            )

            progress = True

        current_ctx_keys = set(context.keys())

        if not progress and current_ctx_keys == prev_ctx_keys:
            retries += 1
        else:
            retries = 0

        prev_ctx_keys = current_ctx_keys

        if retries >= max_retries:
            break

        if not progress:
            try:
                initial_fields = set(context.keys())
                order = topo_sort_services(pickids, contract_map, initial_fields)
            except RuntimeError as e:
                break

    for pid, missing in unresolved:
        skip_entry = {
            "skipped": True,
            "missing_inputs": missing,
            "reason": "Unresolvable inputs after dependency resolution loop."
        }
        svc = next((c for c in candidates if c["id"] == pid), None)
        if svc:
            log_event(
                correlation_id,
                svc,
                context,
                skip_entry,
                reason=skip_entry["reason"],
                query=query
            )
        responses[pid] = skip_entry

    return {
        "pickids": pickids,
        "reasons": reasons,
        "responses": responses,
        "skipped": {k: v for k, v in responses.items() if v.get("skipped")},
        "llm_raw": raw_response
    }
