# SES Product Specification

SES Agent Memory Tollgate provides curated paid memory namespaces for autonomous agents.

Agents pay when they need fresh, cited and verifiable context to complete a goal. SES returns answer, citations, receipt and value_proof.

## Operating Modes

### 1. Local Embedded RAG
- SQLite + numpy
- no payments
- no external vector DB
- for development, offline tests and demos

### 2. Hosted Curated Tollgate
- Qdrant
- FastAPI Gateway
- payment middleware
- curated public technical namespaces

### 3. Future Private / Marketplace
- private BYOD namespaces
- publisher marketplace
- not part of current build

## Non-Goals
- SES is not building a legal corpus in this roadmap.
- SES is not building Lex Mex API.
- SES is not opening a public marketplace yet.
- SES is not building a human dashboard yet.

## Fase 1 Status (MVP Prep)
- OpenAPI documentation improved for all /v1/* endpoints (tags, summaries, descriptions).
- Namespace quotas (MAX_*_NAMESPACE) + document delete (`DELETE /documents/{doc_id}`).
- Basic update via deterministic re-ingest.
- Solana Pay production path hardened.
- Bilingual surface: README (ES/EN), OpenAPI (English standard + Spanish summaries), error messages being unified.

## Licensing
Current license: **GPLv3** (see LICENSE).
Considerations for dual licensing (GPL + commercial-friendly license such as Apache-2.0 or custom) should be evaluated if enterprise adoption or SDK distribution requires it. No change yet — documented for review.
- SES is not adding multi-chain billing yet.
