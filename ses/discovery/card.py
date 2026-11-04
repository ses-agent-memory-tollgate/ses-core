"""
A2A Agent Card definitions and endpoints.
"""

from typing import Dict, Any

import os
from ses.payments.pricing import cost_for

def get_agent_card() -> Dict[str, Any]:
    base_url = os.getenv("SES_PUBLIC_BASE_URL", "http://localhost:8000")
    return {
        "name": "SES Agent Memory Tollgate",
        "description": "Paid semantic memory and RAG retrieval for autonomous agents.",
        "capabilities": [
            {
                "name": "semantic_search",
                "description": "Returns ranked document chunks for a query.",
                "price": f"{cost_for('search')} USDC"
            },
            {
                "name": "rag_query",
                "description": "Answers questions over indexed documents with citations.",
                "price": f"{cost_for('query')} USDC"
            },
            {
                "name": "document_ingest",
                "description": "Ingests a document into the knowledge base.",
                "price": f"{cost_for('ingest')} USDC"
            },
            {
                "name": "citation_retrieval",
                "description": "Retrieves citations for a query.",
                "price": f"{cost_for('search')} USDC"
            },
            {
                "name": "quote",
                "description": "Gets a pricing quote for operations.",
                "price": "0 USDC"
            },
            {
                "name": "receipt",
                "description": "Retrieves the receipt for a transaction.",
                "price": "0 USDC"
            }
        ],
        "interfaces": {
            "http": f"{base_url}/v1"
        },
        "payment": {
            "protocols": ["x402", "solana_pay"],
            "assets": ["USDC"],
            "networks": ["solana"]
        }
    }
