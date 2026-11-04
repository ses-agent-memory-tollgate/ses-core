#!/usr/bin/env python3
"""
SES Merchant Key Generator
==========================

This script generates a Solana keypair suitable for use as the SES merchant wallet.

It produces:
- The public address (where agents will send USDC)
- The SOLANA_MERCHANT_SECRET value (base58) that SES expects
- A merchant.json file compatible with the Solana CLI

Usage:
    python generate_merchant_key.py

Requirements:
    pip install solders base58
"""

import json
import os
import sys
from datetime import datetime

try:
    from solders.keypair import Keypair
    import base58
except ImportError as e:
    import sys
    print("❌ Missing dependencies for THIS Python interpreter.")
    print(f"   Python being used: {sys.executable}")
    print()
    print("   Install using the SAME Python:")
    print(f"   {sys.executable} -m pip install solders base58")
    print()
    print("   Then run the script again with the same Python:")
    print(f"   {sys.executable} scripts/generate_merchant_key.py")
    print()
    print("   Or run this one-liner directly:")
    print(f'   {sys.executable} -c "')
    print('   from solders.keypair import Keypair')
    print('   import base58, json, datetime')
    print('   kp = Keypair()')
    print('   secret = base58.b58encode(bytes(kp)).decode()')
    print('   pub = str(kp.pubkey())')
    print('   print(\"PUBLIC ADDRESS:\", pub)')
    print('   print(\"SOLANA_MERCHANT_SECRET=\", secret)')
    print('   with open(\"merchant.json\", \"w\") as f: json.dump(list(bytes(kp)), f)')
    print('   print(\"Saved merchant.json\")')
    print('   "')
    sys.exit(1)


def generate_merchant_keypair():
    print("=" * 70)
    print("SES MERCHANT KEYPPAIR GENERATOR")
    print("For Solana Pay / USDC payments (Devnet recommended first)")
    print("=" * 70)
    print()

    # Generate fresh keypair
    kp = Keypair()
    pubkey = str(kp.pubkey())
    secret_bytes = bytes(kp)

    # This is the format SES expects in SOLANA_MERCHANT_SECRET
    secret_base58 = base58.b58encode(secret_bytes).decode()

    # Also save in standard Solana CLI JSON format (array of bytes)
    json_path = "merchant.json"
    with open(json_path, "w") as f:
        json.dump(list(secret_bytes), f)

    # Also create a nice .env snippet
    env_snippet = f"""# === SES Merchant Configuration (add to your .env) ===
DEBUG=false
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_MERCHANT_SECRET={secret_base58}
# For production use mainnet:
# SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
"""

    print("✅ Keypair generated successfully!\n")

    print("PUBLIC ADDRESS (Merchant Address):")
    print(f"   {pubkey}")
    print()
    print("SOLANA_MERCHANT_SECRET (copy this exactly):")
    print(f"   {secret_base58}")
    print()

    print(f"📁 Files created:")
    print(f"   - {json_path}          (for Solana CLI)")
    print()

    # Save a helper file with the env vars
    env_file = "merchant.env"
    with open(env_file, "w") as f:
        f.write(env_snippet)
    print(f"   - {env_file}          (ready to copy into your .env)\n")

    print("=" * 70)
    print("NEXT STEPS: FUND THE WALLET ON DEVNET")
    print("=" * 70)
    print()

    print("1. Install Solana CLI (if you don't have it):")
    print("   Windows (PowerShell):")
    print("     irm https://release.solana.com/stable/install.ps1 | iex")
    print()
    print("   macOS / Linux:")
    print("     sh -c \"$(curl -sSfL https://release.solana.com/stable/install)\"")
    print()

    print("2. Add the Solana CLI to your PATH and restart your terminal.")
    print()

    print("3. Airdrop SOL (needed for transaction fees) on Devnet:")
    print(f"   solana airdrop 2 {pubkey} --url https://api.devnet.solana.com")
    print()
    print("   You can run it multiple times if needed (max ~2 SOL per request).")
    print()

    print("4. Get Devnet USDC (the token agents will pay with):")
    print("   Option A - Use the official Solana Faucet (easy):")
    print("      → Go to: https://faucet.solana.com/")
    print(f"      → Paste this address: {pubkey}")
    print("      → Select Devnet + request USDC (or SOL first, then swap)")
    print()
    print("   Option B - Using Solana CLI (if you have SPL token installed):")
    print("      # First make sure you have the devnet USDC mint")
    print("      spl-token create-account --url https://api.devnet.solana.com EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
    print(f"      # Then ask someone to send you test USDC or use a devnet faucet")
    print()

    print("5. Verify your balances:")
    print(f"   solana balance {pubkey} --url https://api.devnet.solana.com")
    print(f"   spl-token accounts --url https://api.devnet.solana.com")
    print()

    print("=" * 70)
    print("HOW TO USE WITH SES")
    print("=" * 70)
    print()
    print("Option A - Local .env file:")
    print(f"   Copy the contents of {env_file} into your project's .env")
    print()
    print("Option B - Docker Compose:")
    print("   Add to your environment or .env:")
    print(f"   SOLANA_MERCHANT_SECRET={secret_base58}")
    print(f"   SOLANA_RPC_URL=https://api.devnet.solana.com")
    print()
    print("Option C - Run the server directly:")
    print(f"   DEBUG=false \\")
    print(f"   SOLANA_RPC_URL=https://api.devnet.solana.com \\")
    print(f"   SOLANA_MERCHANT_SECRET={secret_base58} \\")
    print("   python -m ses.server")
    print()

    print("6. Verify the merchant is correctly loaded:")
    print("   python -c \"")
    print("   from ses.payments.solana_pay import SolanaPay")
    print("   s = SolanaPay()")
    print("   print(s.get_merchant_info())")
    print("   \"")
    print()

    print("=" * 70)
    print("SECURITY WARNING")
    print("=" * 70)
    print("• This key controls any USDC sent to it.")
    print("• NEVER commit merchant.json or the secret to git.")
    print("• For production, use a different keypair on mainnet.")
    print("• Consider using a secrets manager (GitHub Secrets, Docker secrets, etc).")
    print()
    print("Generated at:", datetime.now().isoformat())
    print("=" * 70)

    return pubkey, secret_base58


if __name__ == "__main__":
    generate_merchant_keypair()
