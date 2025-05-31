
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from jsonschema import validate, ValidationError
from typing import List, Dict, Any
from typing import Set

import json
import os, requests, json, uuid
import re



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


from typing import Tuple

def resolve_with_sources(
    props: Dict[str, Any],
    context: Dict[str, Any],
    extracted: Dict[str, Any],
    prior_responses: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    resolved = {}
    sources = {}

    for key in props:
        if key in context:
            resolved[key] = context[key]
            sources[key] = "context"
        elif key in extracted:
            resolved[key] = extracted[key]
            sources[key] = "llm"
        else:
            for resp in prior_responses.values():
                if isinstance(resp, dict) and key in resp:
                    resolved[key] = resp[key]
                    sources[key] = "previous"
                    break

    return resolved, sources


def load_prompt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt from {path}: {e}")

def parse_inputs(field):
    if isinstance(field, str):
        return [x.strip() for x in field.split(",")]
    return field or []

def extract_json_like(content: str) -> str:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else "{}"

def allow_nulls(schema):
    """Recursively update the schema to allow null values for all properties."""
    if not isinstance(schema, dict):
        return schema

    if schema.get("type") == "object" and "properties" in schema:
        for key, prop in schema["properties"].items():
            if "type" in prop:
                current_type = prop["type"]
                if isinstance(current_type, str):
                    prop["type"] = [current_type, "null"]
                elif isinstance(current_type, list) and "null" not in current_type:
                    prop["type"].append("null")
            schema["properties"][key] = allow_nulls(prop)

    if schema.get("type") == "array" and "items" in schema:
        schema["items"] = allow_nulls(schema["items"])

    return schema

def extract(prompt: str, schema: dict) -> dict:
    """
    Extract structured JSON from a prompt using an LLM, matching the given schema.
    All fields should be considered optional and returned as null if not extractable.
    """

    # Log incoming prompt and schema
    print("\n[extract()] Prompt to LLM:")
    print(prompt)
    print("\n[extract()] Schema used:")
    print(json.dumps(schema, indent=2))

    system_prompt = f"""You are a strict JSON extractor.

    Your task is to extract only explicitly stated or clearly implied values from the user's input, based on the following JSON schema:

    {json.dumps(schema, indent=2)}

    Guidelines:
    - Prefer extracting values over returning null if the user's intent is reasonably clear and matches the schema type.
    - For example: "I am user 2345" → "customer_id": 2345 is valid.
    - Normalize common variants if unambiguous (e.g., German city names like "Munic" → "MUC", or dates like "4. Mai 2025" → "2025-05-04").

    Rules:
    - Do NOT guess or fabricate values.
    - Do NOT infer unstated values (e.g., don't assume vehicle type unless mentioned).
    - Return a single valid JSON object only. No text, markdown, code blocks, or explanations.

    Important:
    - If a value is missing, ambiguous, or not explicitly derivable, return null.
    - Return only fields defined in the schema. Ignore irrelevant content.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    print("\n[extract()] SYSTEM Prompt to LLM:")
    print(system_prompt)

    try:
        response = requests.post(FULL_URL, json={
            "model": chat_model,
            "messages": messages,
            "temperature": 0.0,
        }, timeout=request_timeout)

        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        print("\n[extract()] LLM raw response:")
        print(content)

        result = json.loads(content)

        # Validate
        try:
            validate(instance=result, schema=schema)
        except ValidationError as e:
            print(f"\n[extract()] ❌ Validation failed:\n{e}")
            raise

        return result

    except Exception as e:
        print(f"\n[extract()] ❌ LLM extraction failed: {e}")
        return {k: None for k in schema.get("properties", {}).keys()}



def get_collection_id() -> str:
    resp = requests.get(f"{chroma_services_url}/api/v1/collections", timeout=request_timeout)
    resp.raise_for_status()
    for col in resp.json():
        if col.get("name") == collection:
            return col["id"]
    raise runtimeerror(f"collection '{collection}' not found")

def log_event(correlation_id: str, service: Dict[str, Any], req: Dict, res: Dict, reason: str = "", query: str = ""):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "coordinator-agent",
        "correlation_id": correlation_id,
        "jwt": {},
        "request": req,
        "response": res,
        "target_service": service["id"],
        "target_url": service["metadata"].get("url") or service["metadata"].get("endpoint"),
        "reason": reason,
        "query": query,
        "contract_input": service["metadata"].get("contract_input"),
        "contract_output": service["metadata"].get("contract_output"),
    }
    print(json.dumps(event) + "\n")
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


def resolve_fields(
    props: Dict[str, Any],
    context: Dict[str, Any],
    extracted: Dict[str, Any],
    prior_responses: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Attempts to resolve all fields defined in `props` using:
    1. the current context (cumulative state),
    2. extracted LLM results,
    3. prior service responses.

    Returns a dict of resolved fields.
    """
    resolved = {}

    for key in props:
        if key in context:
            resolved[key] = context[key]
        elif key in extracted:
            resolved[key] = extracted[key]
            context[key] = extracted[key]
        else:
            # Try fallback to previous service results
            for resp in prior_responses.values():
                if isinstance(resp, dict) and key in resp:
                    resolved[key] = resp[key]
                    context[key] = resp[key]
                    break

    return resolved



def build_candidates_section(candidates: List[Dict]) -> str:
    def build_line(c):
        m = c["metadata"]
        provides = ", ".join(m.get("provides", []))
        tags     = ", ".join(m.get("tags", []))
        inputs   = ", ".join(json.loads(m.get("contract_input", "{}")).get("properties", {}).keys())
        outputs  = ", ".join(json.loads(m.get("contract_output", "{}")).get("properties", {}).keys())
        return (
            f"{c['id']}:\n"
            f"  description: {c['document']}\n"
            f"  provides: {provides}\n"
            f"  inputs: {inputs}\n"
            f"  outputs: {outputs}\n"
            f"  tags: {tags}\n"
            f"  endpoint: {m.get('endpoint')}"
        )
    return "\n\n".join(build_line(c) for c in candidates)


def topo_sort_services(pickids: List[str], service_contracts: Dict[str, Dict[str, Any]], known_fields: Set[str]) -> List[str]:
    print(f"[TOPO ORDER] pickids: '{pickids}'")
    print(f"[TOPO ORDER] known fields: '{known_fields}'")

    remaining = set(pickids)
    order = []
    available_fields = set(known_fields)

    inputs_map = {
        sid: set(service_contracts[sid]["input"].get("required", []))
        for sid in pickids
    }

    outputs_map = {
        sid: set(service_contracts[sid]["output"].get("properties", {}).keys())
        for sid in pickids
    }

    while remaining:
        progress = False
        for sid in list(remaining):
            if inputs_map[sid].issubset(available_fields):
                order.append(sid)
                available_fields.update(outputs_map[sid])
                remaining.remove(sid)
                progress = True

        if not progress:
            raise RuntimeError(f"Dependency resolution failed. Unresolved services: {remaining}. Known fields: {available_fields}")

    return order


def is_resolvable(contract_input: dict, context: dict) -> bool:
    props = contract_input.get("properties", {})
    raw_required = contract_input.get("required")
    required = raw_required or [
        k for k, v in props.items()
        if not (isinstance(v.get("type"), list) and "null" in v["type"])
    ]
    return all(
        k in context and context[k] is not None and str(context[k]).lower() != "null"
        for k in required
    )

