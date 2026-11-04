# SES Security

SES deals with agent payments and verifiable technical context.

## Payment Integrity
SES requires payment verification via HTTP 402 flows. 
- Signatures and payload contents are strictly validated.
- All transactions maintain an immutable cryptographic receipt.
- A successful payment proof is bound to a normalized request hash and cannot be transplanted to a different request.
- Failed route executions are marked `failed` and do not consume the payment proof; the proof can be retried until a successful response commits it.

## Idempotency and Replay Protection
- SES employs request hashing and idempotency keys to ensure that a single payment cannot be abused for multiple different requests, preventing replay attacks and duplicate spending.

## Sandbox Mode
- Simulated payments and solana-devnet modes are available and should only be used for local tests and non-production environments to avoid unintended losses.
- `DEBUG=true` accepts simulated payment proofs. It must never be used in a production tollgate.
- `docker compose config` can print environment-expanded secrets such as `SOLANA_MERCHANT_SECRET`; do not paste that output into public logs.

## API Security Review (Fase 0)
### Authentication & Authorization
- All paid/privileged endpoints require either `X-API-Key` (validated via `KeyStore.validate`, SHA-256 hashed storage) or `X-Agent-Id`.
- Invalid/revoked keys return 401 immediately in `PaymentRequiredMiddleware`.
- Keys are self-service only: a key can only revoke/rotate itself (`routes.py`).
- Namespace scoping: private keys derive deterministic hashed namespaces (`_namespace_from_key_id`); public namespaces are explicitly prefixed `public:*`.

### CORS
- Configurable via `CORS_ALLOW_ORIGINS`. Defaults to restrictive list in non-DEBUG mode.
- `allow_credentials` is disabled outside DEBUG to avoid browser security issues with wildcard origins.
- Recommendation: Set explicit origins in production deployments.

### Rate Limiting
- Multi-layer token-bucket implemented in `RateLimiter`:
  - Per-IP
  - Per-identity (key or agent)
  - Payload-size weighted for `/v1/ingest`
- Middleware short-circuits with 429 before payment or heavy processing.
- Tests cover burst, replenish, and weight behavior.

### CSRF
- Not applicable to token/API-key authenticated JSON APIs (no session cookies used for auth).
- Protection comes from requiring secret API keys + payment proofs.

### Other Recommendations (current state)
- Run with `DEBUG=false` in any non-local environment.
- Remote/managed Qdrant must use `QDRANT_API_KEY`; remote/managed Redis must use `REDIS_PASSWORD`.
- Local Docker full mode (`QDRANT_URL=http://qdrant:6333`, `REDIS_HOST=redis`) is for integration validation and is not production hardening by itself.
- File uploads (ingest) should be further bounded by reverse proxy (size, content-type).
- Consider adding request signing / nonce for high-value operations in future versions.
- The current Rust acceleration path (`core_rs`) is optional; fallback is pure Python + numpy.
- `SentenceTransformer` may contact Hugging Face to download models when not cached. Pin/cache model artifacts for controlled production deployments.
- If Ollama is unavailable, the local LLM provider may return fallback answers over retrieved citations. That is acceptable for development checks but not proof of production answer quality.

### Static Analysis
- CI runs blocking `bandit` (Python security) + `safety` (dependency vulnerability) checks on every push/PR to release branches.

## Reporting
Report issues privately to the maintainers. See repository SECURITY policy.
