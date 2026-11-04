# SES Development Guide

## Environment Setup
1. Clone the repository.
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment.
4. Install dependencies:
   ```bash
   pip install -e ".[dev,server]"
   ```
5. Copy `.env.example` to `.env` and edit the values. Set `DEBUG=true` only
   for local development with simulated payments; the example defaults to
   `DEBUG=false`.

## Running the Server
`ses serve` reads the process environment; it does not automatically load `.env`.
From the repository root, load your trusted `.env` before starting SES
(Bash; quote values containing spaces):

```bash
set -a
. ./.env
set +a
ses serve
```

Configuration in [`ses/config.py`](ses/config.py) is resolved at import time,
so restart the process after changing environment values. The CLI defaults to
`http://127.0.0.1:8000`; override `SES_HOST` and `SES_PORT` to change the bind
address (see [`ses/server/__main__.py`](ses/server/__main__.py)).

For Docker, follow the [README quickstart](README.md#docker-quickstart-verificado).
Compose uses `.env` for interpolation of the variables explicitly declared in
[`docker-compose.yml`](docker-compose.yml), not as a blanket container
environment file. Its published gateway port is `8001`.

## Running Tests
Ensure you run all unit tests before committing:
```bash
pytest
```

For coverage:
```bash
pytest --cov=ses --cov-report=term-missing
```

Critical modules (Fase 0 focus): parsers, chunking, embeddings, rag, payments/*, server/*.
Run specific:
```bash
pytest tests/test_embeddings.py tests/test_parsers.py tests/test_payments.py -q
```

Load / perf:
```bash
python tests/performance/benchmark.py
```
