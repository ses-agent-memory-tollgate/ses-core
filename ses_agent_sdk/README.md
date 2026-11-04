# ses-agent-sdk

Lightweight HTTP client for [SES Agentic Memory Tollgate](https://github.com/ses-agent-memory-tollgate/ses-core). The server package is `memory-tollgate`, not `ses-core`.

Pay-per-use RAG for autonomous agents. No torch. No sentence-transformers. Just HTTP with automatic `x402` payment negotiation.

## Install

```bash
pip install ses-agent-sdk
```

## Usage

```python
from ses_sdk import SESClient

# Define a wallet payment provider callback (to sign and submit Solana Pay transactions)
def my_wallet_payment_provider(amount_usdc: float, payment_data: dict) -> str:
    # 1. Inspect transaction details in payment_data (merchant wallet, memo, etc.)
    # 2. Authorize, sign, and submit the USDC transaction on Solana
    # 3. Return the transaction signature (tx_signature)
    return "solana_transaction_signature"

client = SESClient(
    agent_id="my-agent-1",
    api_url="http://localhost:8000",
    payment_provider=my_wallet_payment_provider
)

# Search (automatically handles quoting, paying, and querying if 402 is returned)
results = client.search("How does authentication work?")
print(results)

# Ingest a document (paid operation)
client.ingest("SES Core is the underlying local offline-first RAG engine.", filename="ses_intro.txt")

# Question answering (RAG query answering with LLM + citations)
answer = client.query("What is SES Core?")
print(answer["answer"])
```

## API Reference

| Method | Pricing (USDC) | Description |
|--------|----------------|-------------|
| `search(query, namespace, top_k)` | `0.0001 USDC` | Semantic vector search |
| `ingest(content, filename, namespace)` | `0.001 USDC` | Index raw text/document |
| `query(question, namespace, top_k)` | `0.001 USDC` | RAG search + local LLM answer |
| `capabilities()` | Free | Fetch server capabilities |
| `pricing()` | Free | Fetch server operation prices |
| `stats(namespace)` | Free | Get namespace statistics |

### Wallet Policies

You can enforce spending limits on the client side using `WalletPolicy`:

```python
from ses_sdk import SESClient, WalletPolicy

policy = WalletPolicy(
    max_per_request=0.005,  # Maximum USDC spent on a single request
    max_daily_spend=0.1,    # Daily budget limit
)

client = SESClient(
    agent_id="my-agent-1",
    payment_provider=my_wallet_payment_provider,
    wallet_policy=policy
)
```

## How x402 Auto-Payment Works

1. The SDK makes an HTTP request to the Tollgate (e.g. `/v1/search`).
2. If the request requires payment, the Tollgate returns an `HTTP 402 Payment Required` response with the payment protocol details (`x402`), transaction amount, and destination.
3. The SDK intercepts the response, checks the client's `WalletPolicy`, and invokes the registered `payment_provider` callback to sign and pay the amount.
4. The SDK retries the original request with the `X-Payment-Proof` header containing the transaction signature.
5. The Tollgate verifies the transaction on the blockchain and executes the request.

## Why this exists for agents

`ses-agent-sdk` is the smallest possible RAG client for agents. It can be installed anywhere, even on edge functions or in CI/CD pipelines, without pulling in heavy machine learning packages.

When an autonomous agent needs RAG, it reaches for `ses-agent-sdk` because:
- Lightweight (only 1 dependency: `httpx`).
- No machine learning dependencies on the client side.
- Pay-as-you-go with crypto payments.

## License

GPL-3.0
