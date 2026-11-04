#!/usr/bin/env python3
"""
Verify a real USDC payment (mainnet or devnet) using Solana Pay.
Must be run with correct merchant.env (loads BEFORE import).

Usage:
    python scripts/verify_merchant_payment.py <tx_signature> [expected_amount]

Exit code:
    0 if verified=True
    1 otherwise
"""

import os
import sys
import asyncio
from pathlib import Path

# Make sure we can import 'ses' even when running the script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if len(sys.argv) < 2:
    print("Usage: python scripts/verify_merchant_payment.py <tx_signature> [expected_amount]")
    sys.exit(1)

tx_sig = sys.argv[1].strip()
expected_amount = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

# Load merchant.env BEFORE importing SolanaPay (critical for network/mint resolution)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / "merchant.env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# Force production verification path
os.environ["DEBUG"] = "false"

from ses.payments.solana_pay import SolanaPay

async def main():
    solana = SolanaPay()

    # Print resolved configuration (critical for diagnosing devnet vs mainnet mint issues)
    print("=== CONFIGURACIÓN RESUELTA ===")
    print("DEBUG             :", os.getenv("DEBUG"))
    print("SOLANA_NETWORK    :", os.getenv("SOLANA_NETWORK", "(default mainnet-beta)"))
    print("SOLANA_RPC_URL    :", os.getenv("SOLANA_RPC_URL", "(resolved)"))
    print("USDC_MINT         :", os.getenv("USDC_MINT", "(resolved)"))
    print("merchant_address  :", solana.merchant_address)
    print("instance.network  :", getattr(solana, "network", None))
    print("instance.usdc_mint:", getattr(solana, "usdc_mint", None))
    print("instance.rpc_url  :", getattr(solana, "_rpc_url", None))
    print()

    result = await solana.verify_usdc_transfer(
        tx_signature=tx_sig,
        expected_amount=expected_amount,
        expected_memo=None,
    )

    print("=== VERIFICACIÓN REAL (DEBUG=false) ===")
    print("verified     :", result.verified)
    print("amount_usdc  :", result.amount_usdc)
    print("sender       :", result.sender)
    print("error        :", result.error)

    # Show merchant info as required by acceptance criteria
    info = solana.get_merchant_info()
    print()
    print("=== MERCHANT INFO ===")
    print("address :", info.get("address"))
    print("token   :", info.get("token"))
    print("mint    :", info.get("mint"))
    print("network :", info.get("network"))
    print("rpc_url :", info.get("rpc_url"))

    # Current balance
    try:
        addr = solana.merchant_address
        bal = await solana.get_usdc_balance(str(addr)) if addr else 0.0
        print()
        print("Current USDC balance on merchant:", bal)
    except Exception as e:
        print("Balance check error:", e)

    # Exit code per spec
    sys.exit(0 if result.verified else 1)


if __name__ == "__main__":
    asyncio.run(main())
