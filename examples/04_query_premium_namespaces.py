import os
import sys
import uuid
import logging

# Ensure local 'ses_agent_sdk' can be found before standard installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ses_agent_sdk")))

from ses_sdk import SESClient
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def simulated_premium_wallet_provider(amount_usdc: float, payment_data: dict) -> str:
    """
    Simulates a wallet signing a transaction for a Premium Namespace.
    In production, this would prompt the user or the agent's autonomous wallet
    to sign a transaction on Solana Mainnet targeting the merchant's address.
    """
    logger.info(f"💰 AGENT WALLET INTERCEPT: Authorizing premium payment of {amount_usdc} USDC...")
    logger.info(f"   Target Network: {payment_data.get('network')}")
    logger.info(f"   Target Asset: {payment_data.get('asset')}")
    
    # Generate a unique dummy transaction signature
    tx_signature = f"PremiumTx{uuid.uuid4().hex[:16]}"
    logger.info(f"✅ Transaction signed! Signature: {tx_signature}")
    
    return tx_signature

def run_premium_demo():
    # We must run in DEBUG mode so the backend accepts simulated signatures
    os.environ["DEBUG"] = "true"
    
    client = SESClient(
        agent_id="autonomous-demo-agent-v2",
        api_url="http://127.0.0.1:8001",
        payment_provider=simulated_premium_wallet_provider
    )
    
    # Test 1: Query Solana Pay
    print("\n" + "="*60)
    print("🚀 TEST 1: Querying 'premium:solana-pay'")
    print("="*60)
    
    try:
        response = client.query(
            "How do I verify a transaction with Solana Pay?", 
            namespace="premium:solana-pay"
        )
        
        print("\n🏆 SUCCESS: Premium memory acquired!")
        print(f"Answer: {response.get('answer')}")
        print(f"Receipt ID: {response.get('receipt', {}).get('receipt_id')}")
        print("\nCitations:")
        for cit in response.get('citations', []):
            print(f" - [{cit['source_title']}] Chunk: {cit['chunk_id']} (Score: {cit['score']:.4f})")
            
    except Exception as e:
        logger.error(f"Test 1 failed: {e}")

    # Test 2: Query Agent Frameworks
    print("\n" + "="*60)
    print("🚀 TEST 2: Querying 'premium:agent-frameworks'")
    print("="*60)
    
    try:
        response = client.query(
            "What is the difference between LangChain and LlamaIndex for agents?", 
            namespace="premium:agent-frameworks"
        )
        
        print("\n🏆 SUCCESS: Premium memory acquired!")
        print(f"Answer: {response.get('answer')}")
        print(f"Receipt ID: {response.get('receipt', {}).get('receipt_id')}")
        print("\nCitations:")
        for cit in response.get('citations', []):
            print(f" - [{cit['source_title']}] Chunk: {cit['chunk_id']} (Score: {cit['score']:.4f})")
            
    except Exception as e:
        logger.error(f"Test 2 failed: {e}")

if __name__ == "__main__":
    run_premium_demo()
