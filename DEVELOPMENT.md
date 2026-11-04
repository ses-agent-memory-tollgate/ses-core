# SES Development Guide

## Environment Setup
1. Clone the repository.
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment.
4. Install dependencies:
   ```bash
   pip install -e ".[dev,server]"
   ```
5. Copy `.env.example` to `.env`.

## Running the Server
```bash
ses serve
```

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
