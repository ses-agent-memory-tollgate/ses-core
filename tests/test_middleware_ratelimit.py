import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from ses.server.middleware import PaymentRequiredMiddleware
from ses.server.ratelimit import RateLimiter
from ses.payments.receipts import ReceiptLedger
from ses.payments.keys import KeyStore

def test_credit_middleware_rate_limits_by_ip():
    app = FastAPI()

    @app.get("/v1/balance")
    async def balance():
        return {"status": "ok"}

    ledger = ReceiptLedger()
    keystore = KeyStore()
    # 0 tokens means immediately block
    ratelimiter = RateLimiter(requests_per_minute=0, burst_limit=0)

    app.add_middleware(PaymentRequiredMiddleware, ledger=ledger, keystore=keystore, rate_limiter=ratelimiter)

    client = TestClient(app)

    # Needs to fail with 429
    response = client.get("/v1/balance", headers={"X-API-Key": "some-key"})
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limit_exceeded"

def test_credit_middleware_rate_limits_by_key():
    app = FastAPI()

    @app.get("/v1/stats")
    async def stats():
        return {"status": "ok"}

    ledger = ReceiptLedger()
    keystore = KeyStore()
    key_id, secret = keystore.create_key()

    # Will allow IP (weight 1), then fail on key (weight 1) because burst limit is 1
    ratelimiter = RateLimiter(requests_per_minute=60, burst_limit=1)

    app.add_middleware(PaymentRequiredMiddleware, ledger=ledger, keystore=keystore, rate_limiter=ratelimiter)

    client = TestClient(app)

    # 1. First IP check happens, consumes 1 token. key is "ip:testclient"
    # 2. Key check happens, consumes 1 token. key is "key:..."
    response = client.get("/v1/stats", headers={"X-API-Key": secret})
    assert response.status_code == 200

    # Same request again - IP limit should block it because IP already consumed its 1 token
    response2 = client.get("/v1/stats", headers={"X-API-Key": secret})
    assert response2.status_code == 429

def test_credit_middleware_rate_limits_ingest_by_payload_size():
    app = FastAPI()

    @app.post("/v1/ingest")
    async def ingest():
        return {"status": "ok"}

    ledger = ReceiptLedger()
    keystore = KeyStore()
    key_id, secret = keystore.create_key()

    ratelimiter = RateLimiter(requests_per_minute=60, burst_limit=5)

    app.add_middleware(PaymentRequiredMiddleware, ledger=ledger, keystore=keystore, rate_limiter=ratelimiter)

    from ses.payments.solana_pay import SolanaPay
    from unittest.mock import MagicMock
    app.state.solana = MagicMock(spec=SolanaPay)

    client = TestClient(app)

    # Small payload, content_length = 5
    import uuid
    response = client.post("/v1/ingest", headers={"X-API-Key": secret, "X-Payment-Proof": f"simulated-{uuid.uuid4().hex}"}, content=b"hello")
    assert response.status_code == 200

    # Large payload, content_length = 100000 -> 100000 // 102400 = 0 -> weight 1 -> won't fail with burst limit 5
    # Very Large payload, content_length = 1000000 -> weight 9
    import uuid
    response2 = client.post("/v1/ingest", headers={"X-API-Key": secret, "Content-Length": "1000000", "X-Payment-Proof": f"simulated-{uuid.uuid4().hex}"}, content=b"a"*1000000)
    assert response2.status_code == 429
    assert "Payload too large" in response2.json()["error"]
