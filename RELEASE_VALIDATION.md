# Gate 5.5 Release Validation

Date: 2026-06-26

Branch under validation: `gate-5-5-release-readiness`

Status: **not production ready**. Do not claim alpha release candidate status until every required Gate 5.5 check passes in a fully provisioned environment.

## Results

| Check | Command | Result | Notes |
|---|---|---:|---|
| Clean Python environment | `python3 -m venv .venv` | **Pass** | Virtual environment creation succeeded. |
| Install toolchain | `python -m pip install --upgrade pip setuptools wheel` | **Blocked** | Package index access failed with repeated proxy `403 Forbidden` responses while resolving `setuptools`. |
| Install package | `python -m pip install -e ".[dev,server]"` | **Blocked** | Could not complete because dependency resolution needs package index access in this environment. |
| Pytest | `pytest` | **Blocked** | Full suite collection cannot run here without server/payment dev dependencies (`fastapi`, `base58`) and `pytest-asyncio`; package installation is blocked by index access. |
| Curation build | `DEBUG=true EMBEDDED_MODE=true ses curate build public:ses-docs --base-dir .` | **Pass** | Built version `2026-06-26.1` with 31 chunks. |
| Curation validate | `DEBUG=true EMBEDDED_MODE=true ses curate validate public:ses-docs --base-dir .` | **Pass** | Freshness and quality validation passed. |
| Curation publish | `DEBUG=true EMBEDDED_MODE=true ses curate publish public:ses-docs --base-dir .` | **Pass** | Published version `2026-06-26.1` and indexed 31 chunks in embedded mode. The environment could not download the SentenceTransformers model and used deterministic local hash embeddings. |
| Public docs demo | `python examples/03_query_public_ses_docs.py` | **Blocked** | Requires a running local SES gateway with server dependencies installed; server dependencies are unavailable in this environment. |
| Gateway local embedded | `DEBUG=true EMBEDDED_MODE=true ses serve` | **Blocked** | Requires `fastapi`/`uvicorn` server dependencies; package installation is blocked by index access. |
| Docker embedded | `docker compose up -d --build gateway` and `curl http://127.0.0.1:8001/v1/health` | **Blocked** | Docker is not installed in this environment (`docker: command not found`). |
| Docker full/Qdrant | `EMBEDDED_MODE=false docker compose --profile full up -d --build` and `curl http://127.0.0.1:8001/v1/health` | **Blocked** | Docker is not installed in this environment (`docker: command not found`). |
| Security scan | `bandit -r ses/ -ll --format txt` | **Blocked** | `bandit` is not installed and package installation is blocked. |
| Dependency scan | `safety check` | **Blocked** | `safety` is not installed and package installation is blocked. |
| Targeted curation regression subset | `python3 -m pytest -q tests/test_curation_chunk_ids.py tests/test_curation_registry.py tests/test_curation_manifest.py tests/test_curation_validators.py tests/test_milestone2_robustness.py tests/test_curation_stress.py` | **Pass** | 50 passed. This is not a substitute for full `pytest`. |

## Fixes Applied During Validation

- `ses curate ...` can now load without importing FastAPI server dependencies first.
- Local embedded curation publish no longer fails solely because the embedding model cannot be downloaded; it falls back to deterministic local hash embeddings unless `SES_ALLOW_HASH_EMBEDDINGS=false` is set.
- The development extra now includes `pytest-asyncio`, which is required by the async tests.
- Curation source fetching now raises `PermissionError` for files with no read permission bits, including when tests run as root.

## Blockers Before Gate 5.5 Can Be Claimed Passing

The following checks still need to pass in a fully provisioned environment:

1. `python -m pip install --upgrade pip setuptools wheel`
2. `python -m pip install -e ".[dev,server]"`
3. `pytest`
4. `DEBUG=true EMBEDDED_MODE=true ses serve`
5. `python examples/03_query_public_ses_docs.py`
6. Docker embedded build and health check.
7. Docker full/Qdrant build and health check.
8. `bandit -r ses/ -ll --format txt`
9. `safety check`

Do **not** claim production readiness. Do **not** claim alpha release candidate status until pytest, curation publish, the public docs demo script, Docker embedded, Docker full/Qdrant, and security scans all pass in the same fully provisioned validation environment.
