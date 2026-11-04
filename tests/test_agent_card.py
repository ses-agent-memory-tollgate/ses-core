from ses.discovery.card import get_agent_card
from ses.payments.pricing import cost_for

def test_agent_card_pricing_consistency():
    card = get_agent_card()
    capabilities = {c["name"]: c["price"] for c in card["capabilities"]}
    
    assert capabilities["semantic_search"] == f"{cost_for('search')} USDC"
    assert capabilities["rag_query"] == f"{cost_for('query')} USDC"
    assert capabilities["document_ingest"] == f"{cost_for('ingest')} USDC"
    assert capabilities["citation_retrieval"] == f"{cost_for('search')} USDC"
    assert capabilities["quote"] == "0 USDC"
    assert capabilities["receipt"] == "0 USDC"
