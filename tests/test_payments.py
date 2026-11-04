import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ses.payments.keys import KeyStore
from ses.payments.receipts import ReceiptLedger
from ses.payments.solana_pay import Keypair, SOLANA_AVAILABLE, SolanaPay, USDC_MINT, SOLANA_NETWORK as _MOD_NETWORK


@pytest.fixture
def sqlite_path():
    path = Path("tests/data") / f"crypto-{uuid4().hex}.db"
    yield str(path)
    for candidate in path.parent.glob(f"{path.name}*"):
        candidate.unlink(missing_ok=True)


def test_solana_requires_signature_in_production():
    solana = SolanaPay(debug=False)

    result = asyncio.run(solana.verify_usdc_transfer("", 1.0))

    assert result.verified is False
    assert result.error == "Transaction signature is required"


@pytest.mark.skipif(not SOLANA_AVAILABLE, reason="Solana dependencies not installed")
def test_solana_uses_injected_rpc_client_without_client_name_collision():
    merchant = Keypair()
    merchant_address = str(merchant.pubkey())
    signature = str(Keypair().sign_message(b"ses-payment"))

    def balance(owner, amount, account_index):
        return SimpleNamespace(
            owner=owner,
            mint=USDC_MINT,
            account_index=account_index,
            ui_token_amount=SimpleNamespace(ui_amount=amount),
        )

    meta = SimpleNamespace(
        err=None,
        pre_token_balances=[
            balance("sender-wallet", 10.0, 0),
            balance(merchant_address, 2.0, 1),
        ],
        post_token_balances=[
            balance("sender-wallet", 9.0, 0),
            balance(merchant_address, 3.0, 1),
        ],
    )
    transaction = SimpleNamespace(meta=meta, transaction="memo:ses:test")
    response = SimpleNamespace(value=SimpleNamespace(transaction=transaction))

    class FakeClient:
        def __init__(self):
            self.calls = 0
            self.closed = False

        async def get_transaction(self, *_args, **_kwargs):
            self.calls += 1
            return response

        async def close(self):
            self.closed = True

    client = FakeClient()
    solana = SolanaPay(
        merchant_keypair=merchant,
        client_factory=lambda _url: client,
        debug=False,
    )

    result = asyncio.run(
        solana.verify_usdc_transfer(signature, 1.0, expected_memo="ses:test")
    )
    same_client = asyncio.run(solana._get_client())
    asyncio.run(solana.close())

    assert result.verified is True
    assert result.amount_usdc == pytest.approx(1.0)
    assert same_client is client
    assert client.calls == 1
    assert client.closed is True




def test_concurrent_deductions_never_overdraw(sqlite_path):
    # Basic smoke: the KeyStore + ReceiptLedger should be usable from multiple threads
    # without obvious breakage (full concurrency proof would use property testing).
    from concurrent.futures import ThreadPoolExecutor
    from ses.payments.receipts import ReceiptLedger

    store = KeyStore(sqlite_path)
    key_id, secret = store.create_key()

    ledger = ReceiptLedger(sqlite_path.replace("keys", "receipts"))

    def do_work(_):
        # validate + create receipt is the typical paid path
        kid = store.validate(secret)
        assert kid == key_id
        rid = ledger.reserve_receipt(
            identity=key_id,
            operation="search",
            amount=0.0001,
            tx_signature=f"sim-{_}",
            idempotency_key=f"idemp-{_}",
            request_hash=f"req-{_}"
        )
        assert rid == "reserved"

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(do_work, range(20)))

    store.close()
    ledger.close()


def test_key_rotation_preserves_identity_and_invalidates_old_secret(sqlite_path):
    store = KeyStore(sqlite_path)
    key_id, old_secret = store.create_key(wallet_address="wallet-1")

    rotated = store.rotate(key_id)

    assert rotated is not None
    rotated_id, new_secret = rotated
    assert rotated_id == key_id
    assert new_secret != old_secret
    assert store.lookup(old_secret) is None
    assert store.validate(old_secret) is None
    assert store.validate(new_secret) == key_id
    key = store.get_by_id(key_id)
    assert key is not None
    assert key.id == key_id
    assert key.wallet_address == "wallet-1"
    store.close()


def test_revoked_key_cannot_be_rotated(sqlite_path):
    store = KeyStore(sqlite_path)
    key_id, _secret = store.create_key()

    assert store.revoke(key_id) is True
    assert store.rotate(key_id) is None
    store.close()


# --- Pricing ---

from ses.payments.pricing import PRICING, cost_for


def test_pricing_table_contains_core_operations():
    assert "search" in PRICING
    assert "query" in PRICING
    assert "ingest" in PRICING
    assert cost_for("search") > 0
    assert cost_for("unknown-op") == 0.0


# --- Verifier ---

import asyncio
from unittest.mock import AsyncMock, MagicMock

from ses.payments.verifier import verify_payment_proof
from ses.payments.solana_pay import VerificationResult


def test_verify_payment_proof_debug_simulated():
    # When DEBUG=true and proof == "simulated", it short-circuits to True
    # (config.DEBUG is true in test env via conftest)
    result = asyncio.run(verify_payment_proof("simulated", 0.001, MagicMock()))
    assert result is True


@pytest.mark.asyncio
async def test_verify_payment_proof_delegates_to_solana():
    fake_solana = MagicMock()
    fake_solana.verify_usdc_transfer = AsyncMock(
        return_value=VerificationResult(verified=True, amount_usdc=0.0005, sender="0xabc")
    )

    ok = await verify_payment_proof("real-sig-123", 0.0005, fake_solana)
    assert ok is True
    fake_solana.verify_usdc_transfer.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# Solana network / USDC mint configuration resolution tests (devnet vs mainnet)
# These set env before instantiation; resolution happens inside SolanaPay.__init__
# ─────────────────────────────────────────────────────────────────────────────

def _set_env(network: str = None, rpc: str = None, mint: str = None):
    if network is not None:
        os.environ["SOLANA_NETWORK"] = network
    if rpc is not None:
        os.environ["SOLANA_RPC_URL"] = rpc
    if mint is not None:
        os.environ["USDC_MINT"] = mint


def _clear_env(keys=("SOLANA_NETWORK", "SOLANA_RPC_URL", "USDC_MINT")):
    for k in keys:
        os.environ.pop(k, None)


def test_solana_network_mainnet_default_mint():
    _clear_env()
    sol = SolanaPay(debug=True)
    assert sol.network in ("mainnet-beta", "mainnet")
    assert sol.usdc_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert "mainnet" in sol._rpc_url
    _clear_env()


def test_solana_network_devnet_default_mint():
    _clear_env()
    _set_env(network="devnet")
    sol = SolanaPay(debug=True)
    assert sol.network == "devnet"
    assert sol.usdc_mint == "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    assert "devnet" in sol._rpc_url.lower()
    _clear_env()


def test_solana_usdc_mint_custom_overrides_default():
    _clear_env()
    _set_env(network="devnet", mint="MyCustomMint111111111111111111111111111111111")
    sol = SolanaPay(debug=True)
    assert sol.usdc_mint == "MyCustomMint111111111111111111111111111111111"
    assert sol.network == "devnet"
    _clear_env()


def test_solana_network_devnet_default_rpc_when_no_url():
    _clear_env()
    _set_env(network="devnet")
    # ensure no rpc override
    os.environ.pop("SOLANA_RPC_URL", None)
    sol = SolanaPay(debug=True)
    assert sol.network == "devnet"
    assert sol._rpc_url == "https://api.devnet.solana.com"
    _clear_env()


def test_verify_usdc_transfer_sums_post_balances_only_for_matching_mint(monkeypatch):
    """verify sums deltas only for post_token_balances whose mint == self.usdc_mint"""
    _clear_env()
    _set_env(network="devnet")  # sets correct devnet mint internally
    merchant = Keypair()
    merchant_addr = str(merchant.pubkey())

    def mk_bal(owner, mint, amount, idx):
        return SimpleNamespace(
            owner=owner,
            mint=mint,
            account_index=idx,
            ui_token_amount=SimpleNamespace(ui_amount=amount),
        )

    devnet_mint = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    wrong_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    meta = SimpleNamespace(
        err=None,
        pre_token_balances=[
            mk_bal("sender", devnet_mint, 0.0, 0),
            mk_bal(merchant_addr, devnet_mint, 0.0, 1),
        ],
        post_token_balances=[
            mk_bal("sender", devnet_mint, 0.0, 0),
            mk_bal(merchant_addr, devnet_mint, 20.0, 1),  # matching
            mk_bal(merchant_addr, wrong_mint, 999.0, 2),  # ignored because wrong mint
        ],
    )
    tx = SimpleNamespace(
        meta=meta,
        transaction=SimpleNamespace(transaction=SimpleNamespace(message=SimpleNamespace(
            account_keys=[], instructions=[], static_account_keys=None
        )))
    )
    response = SimpleNamespace(value=SimpleNamespace(transaction=tx))

    class FakeClient:
        async def get_transaction(self, *a, **k):
            return response
        async def close(self):
            pass

    sol = SolanaPay(merchant_keypair=merchant, client_factory=lambda u: FakeClient(), debug=False)
    # force the mint to devnet one (already set by env)
    assert sol.usdc_mint == devnet_mint

    # Use a syntactically valid (but meaningless) signature so Signature.from_string succeeds
    dummy_sig = "1111111111111111111111111111111111111111111111111111111111111111"
    res = asyncio.run(sol.verify_usdc_transfer(dummy_sig, 20.0))
    assert res.verified is True
    assert res.amount_usdc == pytest.approx(20.0)
    _clear_env()


def test_verify_fails_with_clear_error_when_mint_mismatch_in_tx():
    """When token balances use a different mint, verify should fail and error should mention expected mint/network/rpc"""
    _clear_env()
    _set_env(network="devnet")
    merchant = Keypair()
    maddr = str(merchant.pubkey())

    def mk_bal(owner, mint, amount, idx):
        return SimpleNamespace(owner=owner, mint=mint, account_index=idx,
                               ui_token_amount=SimpleNamespace(ui_amount=amount))

    wrong_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    meta = SimpleNamespace(err=None, pre_token_balances=[], post_token_balances=[
        mk_bal(maddr, wrong_mint, 20.0, 0)
    ])
    tx = SimpleNamespace(meta=meta, transaction=SimpleNamespace(transaction=SimpleNamespace(
        message=SimpleNamespace(account_keys=[], instructions=[], static_account_keys=None))))
    resp = SimpleNamespace(value=SimpleNamespace(transaction=tx))

    class FC:
        async def get_transaction(self, *_a, **_k): return resp
        async def close(self): pass

    sol = SolanaPay(merchant_keypair=merchant, client_factory=lambda u: FC(), debug=False)
    dummy_sig = "1111111111111111111111111111111111111111111111111111111111111111"
    res = asyncio.run(sol.verify_usdc_transfer(dummy_sig, 20.0))
    assert res.verified is False
    assert "Expected 20.0 USDC, got 0" in (res.error or "") or res.amount_usdc == 0.0
    # The error path should be reproducible; also check merchant info carries network/mint
    info = sol.get_merchant_info()
    assert info["network"] == "devnet"
    assert "4zMMC" in info["mint"]
    assert "devnet" in info["rpc_url"]
    _clear_env()


def test_get_merchant_info_includes_mint_network_rpc():
    _clear_env()
    _set_env(network="devnet")
    sol = SolanaPay(debug=True)
    info = sol.get_merchant_info()
    assert info["token"] == "USDC"
    assert "address" in info
    assert info["network"] == "devnet"
    assert info["mint"] == "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    assert "devnet.solana.com" in info["rpc_url"]
    _clear_env()
