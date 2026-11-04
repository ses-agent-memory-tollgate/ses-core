import os
import uvicorn
import threading
import time
import socket
import pytest
import hashlib
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import base58

# Global state for the server double
SERVER_STATE = {
    "payment_mode": "simulated",  # 'simulated', 'solana-devnet', 'solana-mainnet'
    "rpc_unreachable": False,
    "always_402": False,
    "unsupported_protocol": False,
    "query_cost": 0.001,
    "search_cost": 0.0001,
    "ingest_cost": 0.001,
    "idempotency_store": {},  # idempotency_key -> (request_hash, response_dict, timestamp)
    "seen_signatures": {},    # tx_signature -> request_hash
    "keys_store": {
        "key-123": {"key_id": "key-123", "status": "active", "wallet_address": "wallet-123"}
    },
    "key_rotate_count": 0,
    "solana_merchant_secret": os.getenv("SOLANA_MERCHANT_SECRET"),
    "solana_rpc_url": os.getenv("SOLANA_RPC_URL"),
}

app = FastAPI()

# Helper to normalize request body whitespace
def normalize_body(body: bytes) -> str:
    if not body:
        return ""
    try:
        data = json.loads(body.decode("utf-8"))
        # Normalize JSON by sorting keys and removing extraneous spaces
        return json.dumps(data, sort_keys=True, separators=(',', ':'))
    except Exception:
        return body.decode("utf-8").strip()

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def is_valid_solana_signature(sig: str) -> bool:
    try:
        decoded = base58.b58decode(sig)
        return len(decoded) == 64
    except Exception:
        return False

# Administrative / Test routes to manage server double state
@app.post("/v1/test/set_mode")
def set_mode(data: Dict[str, str]):
    mode = data.get("mode", "simulated")
    if mode not in ["simulated", "solana-devnet", "solana-mainnet"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    SERVER_STATE["payment_mode"] = mode
    return {"status": "ok", "mode": mode}

@app.post("/v1/test/set_rpc_unreachable")
def set_rpc_unreachable(data: Dict[str, bool]):
    unreachable = data.get("unreachable", False)
    SERVER_STATE["rpc_unreachable"] = unreachable
    return {"status": "ok", "rpc_unreachable": unreachable}

@app.post("/v1/test/set_always_402")
def set_always_402(data: Dict[str, bool]):
    SERVER_STATE["always_402"] = data.get("always_402", False)
    return {"status": "ok", "always_402": SERVER_STATE["always_402"]}

@app.post("/v1/test/set_unsupported_protocol")
def set_unsupported_protocol(data: Dict[str, bool]):
    SERVER_STATE["unsupported_protocol"] = data.get("unsupported_protocol", False)
    return {"status": "ok", "unsupported_protocol": SERVER_STATE["unsupported_protocol"]}

@app.post("/v1/test/set_cost")
def set_cost(data: Dict[str, Any]):
    # Set costs, potentially negative for boundary tests
    if "query" in data:
        SERVER_STATE["query_cost"] = float(data["query"])
    if "search" in data:
        SERVER_STATE["search_cost"] = float(data["search"])
    if "ingest" in data:
        SERVER_STATE["ingest_cost"] = float(data["ingest"])
    return {"status": "ok", "costs": data}

@app.post("/v1/test/set_config")
def set_config(data: Dict[str, Any]):
    SERVER_STATE["solana_merchant_secret"] = data.get("solana_merchant_secret")
    SERVER_STATE["solana_rpc_url"] = data.get("solana_rpc_url")
    return {"status": "ok"}

@app.post("/v1/test/clear")
def clear_state():
    SERVER_STATE["idempotency_store"].clear()
    SERVER_STATE["seen_signatures"].clear()
    SERVER_STATE["keys_store"] = {
        "key-123": {"key_id": "key-123", "status": "active", "wallet_address": "wallet-123"}
    }
    SERVER_STATE["key_rotate_count"] = 0
    SERVER_STATE["payment_mode"] = "simulated"
    SERVER_STATE["rpc_unreachable"] = False
    SERVER_STATE["always_402"] = False
    SERVER_STATE["unsupported_protocol"] = False
    SERVER_STATE["query_cost"] = 0.001
    SERVER_STATE["search_cost"] = 0.0001
    SERVER_STATE["ingest_cost"] = 0.001
    SERVER_STATE["solana_merchant_secret"] = None
    SERVER_STATE["solana_rpc_url"] = None
    return {"status": "ok"}

# Public free endpoints
@app.get("/v1/health")
def health():
    return {"status": "healthy"}

@app.get("/v1/capabilities")
def capabilities():
    return {"capabilities": ["search", "query", "ingest"]}

@app.get("/v1/pricing")
def pricing():
    return {
        "query": SERVER_STATE["query_cost"],
        "search": SERVER_STATE["search_cost"],
        "ingest": SERVER_STATE["ingest_cost"]
    }

@app.get("/v1/stats")
def stats(namespace: str = "default"):
    return {"total_documents": 3, "namespace": namespace}

# Key Management Endpoints (Free, should not trigger 402)
@app.post("/v1/keys")
def create_key(data: Dict[str, Any]):
    key_id = f"key-{uuid.uuid4().hex[:8]}"
    wallet_address = data.get("wallet_address", "wallet-unknown")
    SERVER_STATE["keys_store"][key_id] = {
        "key_id": key_id,
        "status": "active",
        "wallet_address": wallet_address
    }
    return SERVER_STATE["keys_store"][key_id]

@app.get("/v1/keys")
def list_keys(status: str = "active"):
    res = [k for k in SERVER_STATE["keys_store"].values() if k["status"] == status]
    return res

@app.put("/v1/keys/{key_id}/rotate")
def rotate_key(key_id: str):
    if key_id not in SERVER_STATE["keys_store"]:
        raise HTTPException(status_code=404, detail="Key not found")
    SERVER_STATE["key_rotate_count"] += 1
    new_key_id = f"key-rotated-{SERVER_STATE['key_rotate_count']}"
    k = SERVER_STATE["keys_store"].pop(key_id)
    k["key_id"] = new_key_id
    SERVER_STATE["keys_store"][new_key_id] = k
    return k

@app.delete("/v1/keys/{key_id}")
def revoke_key(key_id: str):
    if key_id not in SERVER_STATE["keys_store"]:
        raise HTTPException(status_code=404, detail="Key not found")
    SERVER_STATE["keys_store"][key_id]["status"] = "revoked"
    return {"status": "revoked"}

# Helper to process payments and handle 402/409/Idempotency
async def process_payment_flow(request: Request, operation: str, cost: float):
    # Check RPC status
    if SERVER_STATE["rpc_unreachable"]:
        return JSONResponse(status_code=503, content={"error": "RPC node unreachable"})

    # Check for negative cost boundary condition
    if cost < 0:
        return JSONResponse(status_code=400, content={"error": "Negative cost rejected"})

    # Read body and compute normalized hash
    body_bytes = await request.body()
    normalized_str = normalize_body(body_bytes)
    req_hash = compute_hash(normalized_str)

    idempotency_key = request.headers.get("Idempotency-Key")
    payment_proof = request.headers.get("X-Payment-Proof")

    # Enforce Idempotency check first
    if idempotency_key:
        if idempotency_key in SERVER_STATE["idempotency_store"]:
            stored_hash, cached_response, cached_time = SERVER_STATE["idempotency_store"][idempotency_key]
            # Check if this was a failure. Failed requests are not cached.
            # In our mock server, we only cache successful responses (status 200).
            # But let's verify if the request body is different
            if stored_hash != req_hash:
                # If body is different with same idempotency key, return 409 Conflict
                return JSONResponse(status_code=409, content={"error": "Idempotency key body mismatch"})
            return cached_response

    # If no payment proof provided, or always_402 is enabled, return HTTP 402
    if SERVER_STATE["always_402"] or not payment_proof:
        proto = "invalid_proto" if SERVER_STATE["unsupported_protocol"] else "x402"
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment required",
                "code": "payment_required",
                "next_action": "pay_and_retry",
                "payment_protocol": proto,
                "amount": str(cost),
                "asset": "USDC",
                "network": "solana",
                "operation": operation,
                "retry": {
                    "method": request.method,
                    "path": request.url.path,
                    "required_headers": [
                        "X-Payment-Proof",
                        "Idempotency-Key"
                    ]
                }
            }
        )

    # Validate payment proof according to mode
    mode = SERVER_STATE["payment_mode"]
    if mode == "simulated":
        # Accepts 'simulated' or 'simulated-*'
        if not (payment_proof == "simulated" or payment_proof.startswith("simulated-")):
            return JSONResponse(status_code=402, content={"error": "Invalid simulated payment proof"})
    elif mode == "solana-devnet":
        # Reject simulated
        if payment_proof == "simulated" or payment_proof.startswith("simulated-"):
            return JSONResponse(status_code=402, content={"error": "Simulated signature rejected in devnet mode"})
        # Must be valid Solana signature
        if not is_valid_solana_signature(payment_proof):
            return JSONResponse(status_code=402, content={"error": "Invalid devnet Solana signature"})
    elif mode == "solana-mainnet":
        # Must have explicit config
        # Let's check config requirements:
        if not SERVER_STATE["solana_merchant_secret"] or not SERVER_STATE["solana_rpc_url"]:
            # Mainnet initialization or execution fails without explicit configuration
            return JSONResponse(status_code=500, content={"error": "Mainnet requires SOLANA_RPC_URL and SOLANA_MERCHANT_SECRET"})
        # Reject simulated or devnet signatures
        if payment_proof == "simulated" or payment_proof.startswith("simulated-") or "devnet" in payment_proof:
            return JSONResponse(status_code=402, content={"error": "Devnet/Simulated signature rejected on mainnet"})
        # Must be valid Solana signature
        if not is_valid_solana_signature(payment_proof):
            return JSONResponse(status_code=402, content={"error": "Invalid mainnet Solana signature"})

    # Check for replay attack: same transaction signature, different body (request hash)
    if payment_proof in SERVER_STATE["seen_signatures"]:
        stored_hash = SERVER_STATE["seen_signatures"][payment_proof]
        if stored_hash != req_hash:
            return JSONResponse(status_code=409, content={"error": "Replay attack: signature reused for different request body"})
        # If it is the same body, let's treat it as a replay, but wait:
        # If there is no matching idempotency key, reuse of payment proof for a different request should be rejected.
        # But if body is identical, and idempotency key matches or is absent, let's return the same cached response
        # (or return 200).

    # Record the signature and body hash
    SERVER_STATE["seen_signatures"][payment_proof] = req_hash

    # Generate operation-specific canonical response
    response_payload = {}
    
    if operation == "query":
        # Read question from body
        try:
            req_json = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            req_json = {}
        question = req_json.get("question", "empty question")
        namespace = req_json.get("namespace", "default")
        
        answer = f"Simulated answer for question: {question}"
        resp_hash = compute_hash(answer)
        
        # Determine citations based on question (to test empty citations)
        if "empty_citations" in question or "missing_context" in question:
            citations = []
        else:
            citations = [
                {
                    "chunk_id": "chunk-1",
                    "doc_id": "doc-1",
                    "source_title": "Source Title 1",
                    "source_path": "/docs/source1.pdf",
                    "citation_anchor": "Section 1.2",
                    "source_hash": "hash123",
                    "score": 0.95,
                    "freshness_score": 0.9,
                    "quality_score": 0.85
                }
            ]
            
        # Support scores null handling test:
        if "null_scores" in question:
            citations[0]["score"] = None
            citations[0]["freshness_score"] = None
            citations[0]["quality_score"] = None

        # Support large response payload test:
        if "large_payload" in question:
            citations = [
                {
                    "chunk_id": f"chunk-{i}",
                    "doc_id": f"doc-{i}",
                    "source_title": f"Source Title {i}",
                    "source_path": f"/docs/source{i}.pdf",
                    "citation_anchor": f"Section {i}",
                    "source_hash": f"hash{i}",
                    "score": 0.9,
                    "freshness_score": 0.9,
                    "quality_score": 0.9
                } for i in range(1000)
            ]

        # Support special characters in anchor test:
        if "special_char" in question:
            citations[0]["citation_anchor"] = "Section 1.2 #$%&/()=?"

        # Support malformed pydantic schema test:
        if "malformed_schema" in question:
            # We return invalid types for citations, score must be float but we return string
            citations[0]["score"] = "invalid_score"

        receipt = {
            "receipt_id": f"receipt-{uuid.uuid4().hex[:12]}",
            "operation": "query",
            "amount_paid": cost,
            "asset": "USDC",
            "network": "solana",
            "tx_signature": payment_proof,
            "request_hash": req_hash,
            "response_hash": resp_hash,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        value_proof = {
            "namespace": namespace,
            "namespace_version": "1.0",
            "freshness_score": 0.9,
            "retrieved_chunks": len(citations),
            "source_trust": 0.95,
            "estimated_steps_saved": 5,
            "infrastructure_avoided": 2,
            "reason_to_pay": "High quality memory match",
            "price_paid": cost
        }
        
        namespace_info = {
            "id": namespace,
            "version": "1.0",
            "type": "semantic"
        }
        
        usage = {
            "retrieved_chunks": len(citations),
            "processing_time_ms": 15
        }
        
        response_payload = {
            "answer": answer,
            "citations": citations,
            "receipt": receipt,
            "value_proof": value_proof,
            "namespace": namespace_info,
            "usage": usage
        }

    elif operation == "search":
        try:
            req_json = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            req_json = {}
        query_val = req_json.get("query", "")
        namespace = req_json.get("namespace", "default")
        
        # Support malformed pydantic schema:
        if "malformed_schema" in query_val:
            response_payload = {
                "results": "not a list",
                "total_documents": "not an int",
                "processing_time_ms": "not an int"
            }
        else:
            response_payload = {
                "results": [{"document_id": "doc-1", "score": 0.95}],
                "total_documents": 1,
                "processing_time_ms": 5
            }

    elif operation == "ingest":
        try:
            req_json = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            req_json = {}
        content_val = req_json.get("content", "")
        
        if "malformed_schema" in content_val:
            response_payload = {
                "status": 12345, # not a string
                "document_id": 9999,
                "processing_time_ms": "not an int"
            }
        else:
            response_payload = {
                "status": "success",
                "document_id": f"doc-{uuid.uuid4().hex[:8]}",
                "processing_time_ms": 25
            }

    # If idempotency key is provided, cache the success response
    if idempotency_key:
        SERVER_STATE["idempotency_store"][idempotency_key] = (req_hash, response_payload, datetime.utcnow())

    return response_payload

@app.post("/v1/query")
async def query_endpoint(request: Request):
    return await process_payment_flow(request, "query", SERVER_STATE["query_cost"])

@app.post("/v1/search")
async def search_endpoint(request: Request):
    return await process_payment_flow(request, "search", SERVER_STATE["search_cost"])

@app.post("/v1/ingest")
async def ingest_endpoint(request: Request):
    return await process_payment_flow(request, "ingest", SERVER_STATE["ingest_cost"])


# Threading helper to run the server double in background
class UvicornServerThread(threading.Thread):
    def __init__(self, port: int):
        super().__init__()
        self.port = port
        self.config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        self.server = uvicorn.Server(self.config)
        self.daemon = True

    def run(self):
        self.server.run()

    def shutdown(self):
        self.server.should_exit = True

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture(scope="session", autouse=True)
def run_simulated_server():
    # If the user explicitly wants to bypass or a real URL is already configured, we respect it.
    api_url = os.getenv("SES_API_URL")
    use_simulated = os.getenv("E2E_USE_SIMULATED_SERVER", "true").lower() in ("true", "1", "yes")
    
    if api_url and not use_simulated:
        # Use real target server
        yield api_url
        return
        
    port = find_free_port()
    server_thread = UvicornServerThread(port)
    server_thread.start()
    
    # Wait for server to boot
    time.sleep(1.0)
    
    target_url = f"http://127.0.0.1:{port}"
    os.environ["SES_API_URL"] = target_url
    
    yield target_url
    
    server_thread.shutdown()
    server_thread.join()
