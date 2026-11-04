#!/usr/bin/env python3
"""Debug helper to inspect a tx's token data (run from project root)."""

import os
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if len(sys.argv) < 2:
    print("Usage: python scripts/debug_tx.py <signature>")
    sys.exit(1)

sig = sys.argv[1]

project_root = Path(__file__).resolve().parent
env_path = project_root / "merchant.env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

os.environ["DEBUG"] = "false"

from ses.payments.solana_pay import SolanaPay

async def main():
    solana = SolanaPay()
    print("Merchant:", solana.merchant_address)
    details = await solana.get_transaction_details(sig)
    print(json.dumps(details, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
