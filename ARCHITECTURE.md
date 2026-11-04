# SES Architecture

## Core Flow
`Discover → Quote → Pay → Retrieve → Cite → Receipt`

## Interfaces
- **Hosted:** `ses_sdk.SESClient` for agent-payable API calls.
- **Local:** `ses.agent.RAG` for offline dev and local embedded memory.

## Components
1. **Core:** Document chunking, local embeddings, retrieval strategies.
2. **Payment Middleware:** Handles the HTTP 402/x402-style flows, quoting, and transaction receipts.
3. **Curation Engine (Upcoming):** Creates versioned, quality-scored namespaces.
4. **FastAPI Gateway:** Exposes endpoints for agent interaction.
