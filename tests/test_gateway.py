from unittest.mock import AsyncMock, MagicMock  # AsyncMock already imported for other tests

from fastapi.testclient import TestClient

from ses.payments.keys import KeyStore
from ses.payments.receipts import ReceiptLedger
from ses.payments.solana_pay import VerificationResult
from ses.server.app import create_app


def make_gateway(tmp_path):
    engine = MagicMock()
    engine.embedded = True
    engine.get_stats = AsyncMock(return_value={"total_documents": 0})
    engine.search = AsyncMock(return_value={"results": [], "total_documents": 0})
    engine.ingest_file = AsyncMock(
        return_value={"status": "ok", "chunks_count": 1}
    )
    engine.clear_namespace = AsyncMock()

    solana = MagicMock()
    solana.close = AsyncMock()
    solana.verify_usdc_transfer = AsyncMock(
        return_value=VerificationResult(
            verified=True,
            amount_usdc=0.0001,
            sender="agent-wallet",
        )
    )
    solana.get_merchant_info.return_value = {
        "address": "merchant",
        "token": "USDC",
        "mint": "mint",
        "network": "solana",
        "rpc_url": "https://api.devnet.solana.com",
    }

    keys = KeyStore(str(tmp_path / "keys.db"))
    ledger = ReceiptLedger(str(tmp_path / "credits.db"))
    app = create_app(
        engine=engine,
        ledger=ledger,
        keystore=keys,
        solana=solana,
    )
    return app, engine, keys, ledger


def provision(client):
    response = client.post("/v1/keys", json={})
    assert response.status_code == 200
    return response.json()["key_id"], response.json()["secret"]


def test_health_and_autonomous_key_bootstrap(tmp_path):
    app, _, _, _ = make_gateway(tmp_path)
    with TestClient(app) as client:
        assert client.get("/v1/health").status_code == 200
        key_id, secret = provision(client)

    assert key_id.startswith("key_")
    assert secret.startswith("ses_")


def test_gateway_scopes_namespaces_per_key(tmp_path):
    app, engine, _, ledger = make_gateway(tmp_path)
    with TestClient(app) as client:
        first_id, first = provision(client)
        second_id, second = provision(client)

        first_response = client.post(
            "/v1/search",
            headers={"X-API-Key": first, "X-Payment-Proof": "simulated"},
            json={"query": "auth", "namespace": "docs"},
        )
        first_namespace = engine.search.await_args.kwargs["namespace"]

        second_response = client.post(
            "/v1/search",
            headers={"X-API-Key": second, "X-Payment-Proof": "simulated-2"},
            json={"query": "auth", "namespace": "docs"},
        )
        second_namespace = engine.search.await_args.kwargs["namespace"]

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_namespace != second_namespace


def test_stats_uses_get_and_is_free(tmp_path):
    app, _, _, ledger = make_gateway(tmp_path)
    with TestClient(app) as client:
        key_id, secret = provision(client)
        response = client.get(
            "/v1/stats",
            headers={"X-API-Key": secret},
            params={"namespace": "docs"},
        )

    assert response.status_code == 200


def test_key_cannot_revoke_another_key(tmp_path):
    app, _, _, _ = make_gateway(tmp_path)
    with TestClient(app) as client:
        _, first = provision(client)
        second_id, _ = provision(client)
        response = client.delete(
            f"/v1/keys/{second_id}",
            headers={"X-API-Key": first},
        )

    assert response.status_code == 403


def test_key_rotation_preserves_namespace(tmp_path):
    app, engine, _, ledger = make_gateway(tmp_path)
    with TestClient(app) as client:
        key_id, old_secret = provision(client)
        first = client.post(
            "/v1/search",
            headers={"X-API-Key": old_secret, "X-Payment-Proof": "simulated"},
            json={"query": "auth"},
        )
        first_namespace = engine.search.await_args.kwargs["namespace"]

        rotated = client.put(
            f"/v1/keys/{key_id}/rotate",
            headers={"X-API-Key": old_secret},
        )
        new_secret = rotated.json()["secret"]
        rejected = client.post(
            "/v1/search",
            headers={"X-API-Key": old_secret},
        )
        second = client.post(
            "/v1/search",
            headers={"X-API-Key": new_secret, "X-Payment-Proof": "simulated-2"},
            json={"query": "auth"},
        )
        second_namespace = engine.search.await_args.kwargs["namespace"]

    assert first.status_code == 200
    assert rotated.status_code == 200
    assert rejected.status_code == 401
    assert second.status_code == 200
    assert first_namespace == second_namespace


def test_failed_method_does_not_charge_unknown_operation(tmp_path):
    app, _, _, ledger = make_gateway(tmp_path)
    with TestClient(app) as client:
        key_id, secret = provision(client)
        response = client.post(
            "/v1/stats",
            headers={"X-API-Key": secret},
            json={},
        )

    assert response.status_code == 405


def test_delete_document_endpoint(tmp_path):
    app, engine, _, _ = make_gateway(tmp_path)
    with TestClient(app) as client:
        _, secret = provision(client)
        # Simulate successful delete
        engine.delete_document = AsyncMock(return_value=True)

        resp = client.delete(
            "/v1/documents/doc-abc123?namespace=docs",
            headers={"X-API-Key": secret, "X-Payment-Proof": "simulated"},
        )
        assert resp.status_code == 200
        assert resp.json()["document_id"] == "doc-abc123"


def test_402_is_machine_actionable(tmp_path):
    app, _, _, _ = make_gateway(tmp_path)
    with TestClient(app) as client:
        _, secret = provision(client)
        response = client.post(
            "/v1/search",
            headers={"X-API-Key": secret},
            json={"query": "auth"},
        )

    payload = response.json()
    assert response.status_code == 402
    assert payload["code"] == "payment_required"
    assert "amount" in payload
    assert payload["retry"]["method"] == "POST"


def test_payment_is_idempotent_and_cannot_replay(tmp_path):
    app, _, _, ledger = make_gateway(tmp_path)
    with TestClient(app) as client:
        first_id, first_secret = provision(client)
        second_id, second_secret = provision(client)

        first = client.post(
            "/v1/search",
            headers={"X-API-Key": first_secret, "X-Payment-Proof": "chain-tx-1", "Idempotency-Key": "same-request"},
            json={"query": "auth"},
        )

        retry = client.post(
            "/v1/search",
            headers={"X-API-Key": first_secret, "X-Payment-Proof": "chain-tx-1", "Idempotency-Key": "same-request"},
            json={"query": "auth"},
        )

        stolen = client.post(
            "/v1/search",
            headers={"X-API-Key": second_secret, "X-Payment-Proof": "chain-tx-1", "Idempotency-Key": "different-request"},
            json={"query": "auth"},
        )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert stolen.status_code == 409


def test_failed_paid_request_does_not_spend_payment_proof(tmp_path):
    app, _, _, _ = make_gateway(tmp_path)
    with TestClient(app) as client:
        _, secret = provision(client)
        headers = {
            "X-API-Key": secret,
            "X-Payment-Proof": "chain-tx-failed-then-success",
            "Idempotency-Key": "failed-then-success",
        }

        failed = client.post("/v1/search", headers=headers, json={"bad": "body"})
        retried = client.post("/v1/search", headers=headers, json={"query": "auth"})

    assert failed.status_code == 422
    assert retried.status_code == 200
