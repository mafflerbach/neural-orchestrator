from fastapi import FastAPI, HTTPException
import os, requests, json, uuid
from datetime import datetime
from typing import List, Dict, Any
import re


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
request_timeout   = (2, 40)   # connect, read timeouts
# ────────────────────────────────────────────────────────────────────────────────
def parse_inputs(field):
    if isinstance(field, str):
        return [x.strip() for x in field.split(",")]
    return field or []

def extract_json_like(content: str) -> str:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else "{}"


def get_collection_id() -> str:
    resp = requests.get(f"{chroma_services_url}/api/v1/collections", timeout=request_timeout)
    resp.raise_for_status()
    for col in resp.json():
        if col.get("name") == collection:
            return col["id"]
    raise runtimeerror(f"collection '{collection}' not found")

def log_event(correlation_id: str, service: Dict[str,Any], req: Dict, res: Dict, reason: str = "", query: str = ""):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "coordinator-agent",
        "correlation_id": correlation_id,
        "jwt": {},
        "request": req,
        "response": res,
        "target_service": service["id"],
        "target_url": service["metadata"].get("url") or service["metadata"].get("endpoint"),
        "reason": reason
    }
    if query:
        event["query"] = query

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(event) + "\n")


def resolve_inputs(contract_str: str, body: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        contract = json.loads(contract_str)
        required_fields = contract.get("required", [])
        properties = contract.get("properties", {})

        resolved = {}
        for field in required_fields:
            # Try from request body
            if field in body:
                resolved[field] = body[field]
            # Try from prior responses
            else:
                for result in previous_results.values():
                    if isinstance(result, dict) and field in result:
                        resolved[field] = result[field]
                        break

        if all(field in resolved for field in required_fields):
            return resolved
        else:
            return None

    except Exception as e:
        print(f"Input resolution error: {e}")
        return None


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
    q          = body.get("query")
    candidates = body.get("candidates", [])
    if not q or not candidates:
        raise httpexception(400, detail="require 'query' and 'candidates'")

    # build a multi-pick prompt
    def build_line(c):
        m = c["metadata"]
        provides = ", ".join(m.get("provides", []))
        tags     = ", ".join(m.get("tags", []))
        return (
            f"{c['id']}:\n"
            f"  description: {c['document']}\n"
            f"  provides: {provides}\n"
            f"  tags: {tags}\n"
            f"  endpoint: {m.get('endpoint')}"
        )

    lines = [build_line(c) for c in candidates]

    user_prompt = (
        f"user request: {q}\n\n"
        "candidates (id: name):\n" + "\n".join(lines) +
        "\n\nwhich of these services are required?  "
        "respond with json like:\n"
        "{\n"
        '  "pickids":["id1","id2"],\n'
        '  "reasons":{\n'
        '    "id1":"why for id1",\n'
        '    "id2":"why for id2"\n'
        "  }\n"
        "}"
    )

    chat_url = lmstudio_url.rstrip("/") + chat_path
    payload = {
        "model": chat_model,
        "messages": [
            { "role":"system", "content":"you are an service selector." },
            { "role":"user",   "content":user_prompt }
        ],
        "temperature": 0
    }
    try:
        r = requests.post(chat_url, json=payload, timeout=request_timeout)
        r.raise_for_status()
        content = r.json().get("choices",[])[0].get("message",{}).get("content","")

        try:
            picked = json.loads(content)
        except json.JSONDecodeError:
            picked = json.loads(extract_json_like(content))

        pickids: List[str] = picked.get("pickids", [])
        reasons: Dict[str,str] = picked.get("reasons", {})
        if not pickids:
            raise runtimeerror("no pickids returned")
    except exception as e:
        raise httpexception(502, detail=f"rerank error: {e}")

    return {
        "pickids": pickids,
        "reasons": reasons,
        "raw_response": content
    }


@app.post("/api/dispatch")
def dispatch(body: Dict):
    query      = body.get("query")
    candidates = body.get("candidates", [])
    if not query or not candidates:
        raise HTTPException(400, detail="require 'query' and 'candidates'")

    correlation_id = str(uuid.uuid4())

    rerank_result = rerank({"query": query, "candidates": candidates})
    pickids = rerank_result["pickids"]
    reasons = rerank_result["reasons"]
    raw_response  = rerank_result.get("raw_response", "")



    # ── 2) fan‐out calls ──────────────────────────────────────────────────────────
    responses: Dict[str, Any] = {}
    executed = set()
    responses = {}
    context = body.copy()

    while True:
        progress = False
        for pid in pickids:
            if pid in executed:
                continue

            svc = next((c for c in candidates if c["id"] == pid), None)
            if not svc:
                continue

            contract_str = svc["metadata"].get("contract_input", "{}")
            try:
                contract = json.loads(contract_str)
            except Exception:
                contract = {}

            required = contract.get("required", [])
            props = contract.get("properties", {})

            # Attempt to resolve all required fields from context or previous responses
            resolved = {}
            for key in required:
                if key in context:
                    resolved[key] = context[key]
                else:
                    # Try pulling from earlier service results
                    for r in responses.values():
                        if isinstance(r, dict) and key in r:
                            resolved[key] = r[key]
                            break

            if all(key in resolved for key in required):
                url = svc["metadata"]["endpoint"]
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
                    reason=reasons.get(pid, "inferred from contract chaining"),
                    query=query
                )
                progress = True

        if not progress:
            break

    # ── 3) return merged result ──────────────────────────────────────────────────
    return {
        "pickids":   pickids,
        "reasons":   reasons,
        "responses": responses,
        "llm_raw":   raw_response
    }


from fastapi.responses import PlainTextResponse

@app.get("/api/logs", response_class=PlainTextResponse)
def read_logs():
    try:
        with open(log_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")

