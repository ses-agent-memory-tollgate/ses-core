import os
import sys

# Ensure SDK is in path if run from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ses_agent_sdk")))

from ses_sdk.client import SESClient, WalletPolicy

import uuid
def simulated_wallet(amount_usdc, quote):
    print(f"\n[SDK TRIGGER] 402 Payment Required detected!")
    print(f"[WALLET] Authorizing payment of {amount_usdc} USDC for operation: {quote.get('operation')}...")
    return f"simulated-{uuid.uuid4().hex}"

client = SESClient(
    agent_id="demo-agent",
    api_url="http://localhost:8001",
    payment_provider=simulated_wallet,
    wallet_policy=WalletPolicy(
        max_per_request=0.005,
        max_daily_spend=0.05,
    ),
)

print("Querying public:ses-docs namespace...")
response = client.query(
    "How does SES handle HTTP 402 payments?",
    namespace="public:ses-docs",
)

print("ANSWER:")
print(response.get("answer"))

print("\nCITATIONS:")
import json
print(json.dumps(response.get("citations"), indent=2))

print("\nRECEIPT:")
print(json.dumps(response.get("receipt"), indent=2))

print("\nVALUE PROOF:")
print(json.dumps(response.get("value_proof"), indent=2))

client.close()
