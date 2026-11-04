import json

import httpx
import pytest

from ses_agent_sdk.ses_sdk.client import SESClient, WalletPolicy


API_URL = "https://ses.test"


def response(status_code=200, payload=None):
    return httpx.Response(status_code, json=payload or {})


def test_stats_uses_get_with_namespace():
    requests = []

    def handler(request):
        requests.append(request)
        return response(payload={"total_documents": 3})

    client = SESClient(
        api_key="sk-test",
        api_url=API_URL,
        transport=httpx.MockTransport(handler),
    )

    assert client.stats("legal") == {"total_documents": 3}
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/v1/stats"
    assert requests[0].url.params["namespace"] == "legal"
    client.close()


def test_x402_auto_pay_without_provider_raises_error():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/v1/search":
            return response(402, {"payment_protocol": "x402", "amount": 0.0001})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = SESClient(
        api_key="sk-test",
        api_url=API_URL,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="Payment required \\(402\\) but no payment provider configured"):
        client.search("contract")

    assert [request.url.path for request in requests] == ["/v1/search"]
    client.close()


def test_x402_auto_pay_uses_payment_provider_signature():
    requests = []
    provider_calls = []

    pay_response = {"payment_protocol": "x402", "amount": "0.0001", "retry": {"method": "POST"}}

    def handler(request):
        requests.append(request)
        if request.url.path == "/v1/search":
            if "X-Payment-Proof" in request.headers:
                return response(payload={"results": [], "total_documents": 0, "processing_time_ms": 1})
            return response(402, pay_response)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    def payment_provider(amount_usdc, requirements):
        provider_calls.append((amount_usdc, requirements))
        return {"tx_signature": "paid-on-solana"}

    client = SESClient(
        api_key="sk-test",
        api_url=API_URL,
        payment_provider=payment_provider,
        transport=httpx.MockTransport(handler),
    )

    client.search("contract")

    assert provider_calls[0][0] == 0.0001
    assert provider_calls[0][1] == pay_response
    assert requests[-1].headers["X-Payment-Proof"] == "paid-on-solana"
    client.close()


def test_x402_respects_wallet_policy():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/v1/search":
            return response(402, {"payment_protocol": "x402", "amount": "0.01"}) # Requires more than max_per_request
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = SESClient(
        api_key="sk-test",
        api_url=API_URL,
        wallet_policy=WalletPolicy(max_per_request=0.005),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="exceeds max_per_request"):
        client.search("contract")

    client.close()

def test_key_management_methods_follow_http_contract():
    requests = []

    def handler(request):
        requests.append(request)
        return response(payload={"status": "ok"})

    client = SESClient(
        api_key="sk-test",
        api_url=API_URL,
        transport=httpx.MockTransport(handler),
    )

    client.list_keys("revoked")
    client.create_key("wallet-address")
    client.rotate_key("key-123")
    client.revoke_key("key-123")

    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/v1/keys"),
        ("POST", "/v1/keys"),
        ("PUT", "/v1/keys/key-123/rotate"),
        ("DELETE", "/v1/keys/key-123"),
    ]
    assert requests[0].url.params["status"] == "revoked"
    assert json.loads(requests[1].content) == {"wallet_address": "wallet-address"}
    client.close()
