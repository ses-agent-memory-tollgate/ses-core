import os
import time
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from spl.token.instructions import transfer_checked, TransferCheckedParams, get_associated_token_address, create_associated_token_account
from solders.instruction import Instruction
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.system_program import transfer, TransferParams

DEVNET_RPC = "https://api.devnet.solana.com"
USDC_MINT = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

def setup_agent_wallet():
    merchant_secret = os.getenv("SOLANA_MERCHANT_SECRET")
    if not merchant_secret:
        print("Need SOLANA_MERCHANT_SECRET to fund the agent")
        return
        
    merchant_kp = Keypair.from_base58_string(merchant_secret)
    agent_kp = Keypair()
    
    print(f"Merchant: {merchant_kp.pubkey()}")
    print(f"Agent generated: {agent_kp.pubkey()}")
    print(f"Agent secret: {base58.b58encode(bytes(agent_kp)).decode()}")
    
    client = Client(DEVNET_RPC)
    
    # 1. Transfer SOL for gas
    sol_ix = transfer(TransferParams(
        from_pubkey=merchant_kp.pubkey(),
        to_pubkey=agent_kp.pubkey(),
        lamports=10000000 # 0.01 SOL
    ))
    
    # 2. Create ATA for agent
    ata_ix = create_associated_token_account(
        payer=merchant_kp.pubkey(),
        owner=agent_kp.pubkey(),
        mint=USDC_MINT
    )
    
    # 3. Transfer 0.05 USDC
    merchant_ata = get_associated_token_address(merchant_kp.pubkey(), USDC_MINT)
    agent_ata = get_associated_token_address(agent_kp.pubkey(), USDC_MINT)
    
    usdc_ix = transfer_checked(
        TransferCheckedParams(
            program_id=TOKEN_PROGRAM_ID,
            source=merchant_ata,
            mint=USDC_MINT,
            dest=agent_ata,
            owner=merchant_kp.pubkey(),
            amount=50000, # 0.05 USDC
            decimals=6
        )
    )
    
    blockhash = client.get_latest_blockhash().value.blockhash
    msg = MessageV0.try_compile(
        payer=merchant_kp.pubkey(),
        instructions=[sol_ix, ata_ix, usdc_ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    
    tx = VersionedTransaction(msg, [merchant_kp])
    print("Sending funding tx...")
    sig = client.send_transaction(tx).value
    print(f"Funding tx: {sig}")
    
    # Wait for confirmation
    print("Waiting 15s...")
    time.sleep(15)

if __name__ == "__main__":
    setup_agent_wallet()
