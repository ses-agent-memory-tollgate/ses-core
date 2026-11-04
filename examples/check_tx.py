import asyncio
import os
from ses.payments.solana_pay import SolanaPay

async def main():
    merchant_secret = os.getenv("SOLANA_MERCHANT_SECRET")
    sp = SolanaPay()
    # verify
    res = await sp.verify_usdc_transfer('3KAcNLwm3sXLXmNRQv5fcFJBdDW68JsR3tB72wWUXycxVaDDt4bmER8sAHgkJT9zVk4Dpruc3mUut81xdR8cG4We', 0.001)
    print("Verification result:", res)
    
    # get details
    details = await sp.get_transaction_details('3KAcNLwm3sXLXmNRQv5fcFJBdDW68JsR3tB72wWUXycxVaDDt4bmER8sAHgkJT9zVk4Dpruc3mUut81xdR8cG4We')
    print("Details:", details)

asyncio.run(main())
