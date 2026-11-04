"""
Lightweight HTTP client for SES Agentic Gateway.

Implements the x402 payment retry flow automatically.

Usage (as an AI agent would write it):

    from ses_sdk import SESClient

    api = SESClient(agent_id="my-agent-1", payment_provider=my_crypto_wallet)
    results = api.search("How to deploy SES?")
    answer = api.query("Summarize the docs")
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
PaymentProvider = Callable[[float, Dict[str, Any]], Any]


@dataclass
class WalletPolicy:
    max_per_request: float = 0.005
    max_daily_spend: float = 0.1
    current_daily_spend: float = 0.0


class SESClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 30.0,
        payment_provider: Optional[PaymentProvider] = None,
        transport: Optional[httpx.BaseTransport] = None,
        wallet_policy: Optional[WalletPolicy] = None,
    ):
        self.api_url = (api_url or os.getenv("SES_API_URL", BASE_URL)).rstrip("/")
        self._payment_provider = payment_provider

        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        if agent_id:
            headers["X-Agent-Id"] = agent_id

        self._http = httpx.Client(
            timeout=timeout,
            headers=headers,
            transport=transport,
        )
        self.wallet_policy = wallet_policy or WalletPolicy()

    def search(self, query: str, namespace: str = "default", top_k: int = 5) -> Dict[str, Any]:
        return self._post("/v1/search", {
            "query": query, "namespace": namespace, "top_k": top_k,
        })

    def ingest(self, content: str, filename: str = "document.txt",
               namespace: str = "default", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        return self._post("/v1/ingest", {
            "content": content, "filename": filename,
            "namespace": namespace, "metadata": metadata or {},
        })

    def query(self, question: str, namespace: str = "default", top_k: int = 5) -> Dict[str, Any]:
        return self._post("/v1/query", {
            "question": question, "namespace": namespace, "top_k": top_k,
        })

    def capabilities(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/capabilities")

    def pricing(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/pricing")

    def stats(self, namespace: str = "default") -> Dict[str, Any]:
        return self._request("GET", "/v1/stats", params={"namespace": namespace})

    def create_key(self, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        body = {"wallet_address": wallet_address} if wallet_address else {}
        return self._request("POST", "/v1/keys", json=body)

    def list_keys(self, status: str = "active") -> Dict[str, Any]:
        return self._request("GET", "/v1/keys", params={"status": status})

    def rotate_key(self, key_id: str) -> Dict[str, Any]:
        return self._request("PUT", f"/v1/keys/{key_id}/rotate")

    def revoke_key(self, key_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/v1/keys/{key_id}")

    def close(self) -> None:
        self._http.close()

    def _post(self, path: str, body: Dict) -> Dict[str, Any]:
        return self._request("POST", path, json=body)

    def _request(self, method: str, path: str, headers: Optional[Dict] = None, **kwargs: Any) -> Dict[str, Any]:
        req_headers = headers or {}
        resp = self._http.request(method, f"{self.api_url}{path}", headers=req_headers, **kwargs)

        # x402 auto-payment flow
        if resp.status_code == 402:
            data = resp.json()
            if data.get("payment_protocol") == "x402":
                amount = float(data.get("amount", 0))

                if amount > self.wallet_policy.max_per_request:
                    raise RuntimeError(f"Requested amount {amount} exceeds max_per_request {self.wallet_policy.max_per_request}")

                if self.wallet_policy.current_daily_spend + amount > self.wallet_policy.max_daily_spend:
                    raise RuntimeError("Daily spend limit exceeded")

                if not self._payment_provider:
                    raise RuntimeError("Payment required (402) but no payment provider configured")

                proof = self._payment_provider(amount, data)
                tx_signature = self._extract_tx_signature(proof)

                self.wallet_policy.current_daily_spend += amount
                logger.info("x402 Auto-paid: %.4f USDC for %s", amount, path)

                req_headers["X-Payment-Proof"] = tx_signature
                resp = self._http.request(method, f"{self.api_url}{path}", headers=req_headers, **kwargs)
            else:
                raise RuntimeError(f"Unsupported payment protocol or missing x402 fields: {data}")

        if resp.status_code == 401:
            raise RuntimeError(f"Identity/Auth Error: {resp.text}")
        if resp.status_code >= 400:
            raise RuntimeError(f"API Error {resp.status_code}: {resp.text}")

        return resp.json()

    @staticmethod
    def _extract_tx_signature(proof: Any) -> str:
        if isinstance(proof, str) and proof.strip():
            return proof
        if isinstance(proof, dict):
            signature = proof.get("tx_signature")
            if isinstance(signature, str) and signature.strip():
                return signature
        raise ValueError("Payment provider must return a transaction signature")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
