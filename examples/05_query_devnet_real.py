import os
import sys
import time
import base58
import logging

# Ensure local 'ses_agent_sdk' can be found before standard installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ses_agent_sdk")))

try:
    from dotenv import load_dotenv
    # Load .env from the parent directory
    load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
except ImportError:
    pass

from ses_sdk import SESClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from spl.token.instructions import transfer_checked, TransferCheckedParams, get_associated_token_address
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.instruction import Instruction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
DEVNET_RPC = "https://api.devnet.solana.com"
USDC_MINT = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

def real_devnet_wallet_provider(amount_usdc: float, payment_data: dict) -> str:
    """
    Signs a real transaction on Solana Devnet to pay the merchant.
    This simulates an agent authorizing an on-chain transfer from its own wallet.
    """
    agent_secret = os.getenv("AGENT_SECRET")
    if not agent_secret:
        raise ValueError("AGENT_SECRET env var is required for real devnet payments.")
        
    merchant_address = payment_data.get('pay_to')
    if not merchant_address:
        raise ValueError("Merchant address ('pay_to') not provided in x402 payment data.")
        
    merchant_pubkey = Pubkey.from_string(merchant_address)
    agent_keypair = Keypair.from_base58_string(agent_secret)
    agent_pubkey = agent_keypair.pubkey()
    
    amount_raw = int(amount_usdc * 1_000_000) # USDC has 6 decimals
    
    logger.info(f"AGENT WALLET INTERCEPT: Authorizing premium payment of {amount_usdc} USDC...")
    logger.info(f"   From: {agent_pubkey}")
    logger.info(f"   To:   {merchant_address}")
    
    client = Client(DEVNET_RPC)
    
    # 1. Get Associated Token Accounts (ATA)
    agent_ata = get_associated_token_address(agent_pubkey, USDC_MINT)
    merchant_ata = get_associated_token_address(merchant_pubkey, USDC_MINT)
    
    # 2. Build SPL Token Transfer instruction
    usdc_ix = transfer_checked(
        TransferCheckedParams(
            program_id=TOKEN_PROGRAM_ID,
            source=agent_ata,
            mint=USDC_MINT,
            dest=merchant_ata,
            owner=agent_pubkey,
            amount=amount_raw,
            decimals=6
        )
    )
    
    # 4. Add binding memo
    memo_ix = Instruction(
        program_id=Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"),
        accounts=[],
        data=b"ses"
    )
    
    # 5. Build transaction
    blockhash = client.get_latest_blockhash().value.blockhash
    msg = MessageV0.try_compile(
        payer=agent_pubkey,
        instructions=[usdc_ix, memo_ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    tx = VersionedTransaction(msg, [agent_keypair])
    
    # 5. Send transaction
    logger.info(f"Sending transaction to Devnet...")
    sig_resp = client.send_transaction(tx)
    signature = str(sig_resp.value)
    logger.info(f"Transaction signed and broadcasted! Signature: {signature}")
    
    # Wait for confirmation so the backend verifier finds it successfully
    logger.info("Waiting 15 seconds for Devnet confirmation before returning to SDK...")
    time.sleep(15) 
    
    return signature

def run_real_devnet_demo():
    # 1. Check for Agent Wallet
    agent_secret = os.getenv("AGENT_SECRET")
    if not agent_secret:
        # Generate one to help the user setup
        kp = Keypair()
        pubkey = str(kp.pubkey())
        secret = base58.b58encode(bytes(kp)).decode('utf-8')
        
        print("\n" + "!"*80)
        print("NO AGENT WALLET FOUND!")
        print("To run the real Devnet end-to-end test, the agent needs a wallet funded with Devnet SOL & USDC.")
        print("\nWe generated a fresh disposable wallet for local Devnet testing only.")
        print("WARNING: This private key is DEVNET ONLY, disposable, and must never hold mainnet funds.")
        print("Do not print, share, commit, or reuse private keys outside this local Devnet setup flow.")
        print(f"  Public Key : {pubkey}")
        print("  Private Key: <generated; set AGENT_SECRET locally for this Devnet-only test>")
        print("\nINSTRUCTIONS:")
        print("1. Airdrop Devnet SOL to this address.")
        print("2. Send some Devnet USDC (SPL token: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU) to this address.")
        print("3. Run this script again with the environment variable set:")
        print("   # Set AGENT_SECRET locally to the generated disposable Devnet-only private key.")
        print(f"   python examples/05_query_devnet_real.py")
        print("\nUse only disposable funded Devnet wallets for this example; never reuse production keys.")
        print("!"*80 + "\n")
        sys.exit(1)
        
    # 2. Run Test
    # Make sure we don't accidentally enable simulated debug bypasses
    if "DEBUG" in os.environ:
        del os.environ["DEBUG"]
    
    client = SESClient(
        agent_id="autonomous-demo-agent-v3",
        api_url="http://127.0.0.1:8001",
        payment_provider=real_devnet_wallet_provider
    )
    
    print("\n" + "="*60)
    print("TEST: Querying 'premium:solana-pay' with REAL DEVNET USDC")
    print("="*60)
    
    try:
        response = client.query(
            "How do I verify a transaction with Solana Pay?", 
            namespace="premium:solana-pay"
        )
        
        print("\nSUCCESS: Premium memory acquired via REAL on-chain payment!")
        print(f"Answer: {response.get('answer')}")
        print(f"Receipt ID: {response.get('receipt', {}).get('receipt_id')}")
        print(f"Receipt Hash: {response.get('receipt', {}).get('response_hash')}")
        print("\nCitations:")
        for cit in response.get('citations', []):
            print(f" - [{cit['source_title']}] Chunk: {cit['chunk_id']} (Score: {cit['score']:.4f})")
            
    except Exception as e:
        logger.error(f"Devnet Test failed: {e}")

if __name__ == "__main__":
    run_real_devnet_demo()
