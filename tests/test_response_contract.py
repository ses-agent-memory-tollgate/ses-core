import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from ses.payments.keys import KeyStore
from ses.payments.receipts import ReceiptLedger
from ses.payments.solana_pay import VerificationResult
from ses.server.app import create_app
from ses.server.models import QueryResponse, SearchResponse, Citation, Receipt, ValueProof, NamespaceRef, UsageInfo

def make_test_gateway(tmp_path):
    engine = MagicMock()
    engine.embedded = True
    engine.get_stats = AsyncMock(return_value={"total_documents": 10})
    
    # Mocking standard search result format that OfflineRAGEngine returns
    mock_results = [
        {
            "id": "test-chunk-id-1",
            "score": 0.85,
            "text": "sample text chunk contents",
            "text_snippet": "sample text chunk contents",
            "indexed_at": 1718841600.0,
            "metadata": {
                "parent_document_id": "test-doc-id-1",
                "filename": "sample.pdf",
                "source_path": "/path/to/sample.pdf",
                "content_hash": "hash123",
                "chunk_index": 2,
                "citation_anchor": "chunk_2"
            }
        }
    ]
    engine.search = AsyncMock(return_value={"results": mock_results, "total_documents": 10})
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

def provision_key(client):
    response = client.post("/v1/keys", json={})
    assert response.status_code == 200
    return response.json()["key_id"], response.json()["secret"]

def test_search_response_contract(tmp_path):
    app, engine, keys, ledger = make_test_gateway(tmp_path)
    with TestClient(app) as client:
        key_id, secret = provision_key(client)
        
        response = client.post(
            "/v1/search",
            headers={"X-API-Key": secret, "X-Payment-Proof": "simulated-tx-1"},
            json={"query": "test query", "namespace": "test_ns"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify that data matches the Pydantic SearchResponse
        parsed = SearchResponse(**data)
        assert len(parsed.results) == 1
        citation = parsed.results[0]
        assert isinstance(citation, Citation)
        assert citation.chunk_id == "test-chunk-id-1"
        assert citation.doc_id == "test-doc-id-1"
        assert citation.source_title == "sample.pdf"
        assert citation.source_path == "/path/to/sample.pdf"
        assert citation.citation_anchor == "chunk_2"
        assert citation.source_hash == "hash123"
        assert citation.score == 0.85
        assert isinstance(citation.freshness_score, float)
        assert isinstance(citation.quality_score, float)
        
        assert parsed.total_documents == 10
        
        # Check Receipt
        assert parsed.receipt is not None
        assert isinstance(parsed.receipt, Receipt)
        assert parsed.receipt.tx_signature == "simulated-tx-1"
        assert parsed.receipt.operation == "search"
        assert parsed.receipt.amount_paid == "0.0001"
        assert parsed.receipt.request_hash != ""
        assert parsed.receipt.response_hash != ""
        assert parsed.receipt.created_at != ""
        
        # Check ValueProof
        assert parsed.value_proof is not None
        assert isinstance(parsed.value_proof, ValueProof)
        assert parsed.value_proof.namespace == "test_ns"
        assert parsed.value_proof.retrieved_chunks == 1
        assert parsed.value_proof.price_paid == "0.0001"
        
        # Check NamespaceRef
        assert parsed.namespace is not None
        assert isinstance(parsed.namespace, NamespaceRef)
        assert parsed.namespace.id == "test_ns"
        
        # Check UsageInfo
        assert parsed.usage is not None
        assert isinstance(parsed.usage, UsageInfo)
        assert parsed.usage.retrieved_chunks == 1
        assert isinstance(parsed.usage.processing_time_ms, float)

def test_query_response_contract(tmp_path):
    app, engine, keys, ledger = make_test_gateway(tmp_path)
    with TestClient(app) as client:
        key_id, secret = provision_key(client)
        
        response = client.post(
            "/v1/query",
            headers={"X-API-Key": secret, "X-Payment-Proof": "simulated-tx-2"},
            json={"question": "test question", "namespace": "test_ns_query"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify that data matches the Pydantic QueryResponse
        parsed = QueryResponse(**data)
        assert parsed.answer != ""
        assert len(parsed.citations) == 1
        citation = parsed.citations[0]
        assert citation.chunk_id == "test-chunk-id-1"
        
        assert parsed.receipt is not None
        assert parsed.receipt.tx_signature == "simulated-tx-2"
        assert parsed.receipt.operation == "query"
        assert parsed.receipt.amount_paid == "0.001"
        
        assert parsed.value_proof is not None
        assert parsed.value_proof.namespace == "test_ns_query"
        assert parsed.value_proof.price_paid == "0.001"
        
        assert parsed.namespace is not None
        assert parsed.namespace.id == "test_ns_query"
        
        assert parsed.usage is not None
        assert parsed.usage.retrieved_chunks == 1
