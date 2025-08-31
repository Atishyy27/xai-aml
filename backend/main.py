# backend/main.py
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any

app = FastAPI(
    title="XAI-AML Detection API",
    description="API for detecting and explaining money laundering networks.",
    version="1.0.0"
)

# --- MOCK DATABASE ---
# This hardcoded data unblocks frontend development.
# It will be replaced by calls to the AI Core and Neo4j later.

MOCK_SUSPICIOUS_NETWORKS = [
    {
        "network_id": "net_smurf_01",
        "risk_score": 0.95,
        "pattern_type": "Smurfing",
        "involved_accounts": 21,
        "total_amount_inr": 850000.00
    },
    {
        "network_id": "net_layer_01",
        "risk_score": 0.92,
        "pattern_type": "Layering",
        "involved_accounts": 7,
        "total_amount_inr": 5500000.00
    },
    {
        "network_id": "net_mule_01",
        "risk_score": 0.88,
        "pattern_type": "Cash-Out Mule",
        "involved_accounts": 15,
        "total_amount_inr": 1200000.00
    }
]

MOCK_GRAPH_DATA = {
    "net_layer_01": {
        "nodes": [
            {"id": "source_acct_A"},
            {"id": "middle_acct_B"},
            {"id": "middle_acct_C"},
            {"id": "middle_acct_D"},
            {"id": "destination_acct_E"}
        ],
        "edges": [
            {"source": "source_acct_A", "target": "middle_acct_B", "amount": 1500000},
            {"source": "middle_acct_B", "target": "middle_acct_C", "amount": 1450000},
            {"source": "middle_acct_C", "target": "middle_acct_D", "amount": 1400000},
            {"source": "middle_acct_D", "target": "destination_acct_E", "amount": 1350000}
        ]
    }
}

MOCK_EXPLANATIONS = {
    "middle_acct_C": {
        "summary": "This account is flagged as a high-risk node within a layering chain.",
        "feature_contributions": [
            {"feature": "'Balanced State' Behavior (money in ≈ money out)", "impact": 0.45},
            {"feature": "Connection to other high-risk accounts", "impact": 0.30},
            {"feature": "High single-day transaction velocity", "impact": 0.20}
        ]
    }
}

# --- API ENDPOINTS ---

@app.get("/", tags=["Status"])
def read_root():
    """Root endpoint to check if the API is running."""
    return {"status": "API is operational"}

@app.get("/suspicious-networks", tags=["Networks"])
def get_suspicious_networks() -> List[Dict[str, Any]]:
    """Returns a list of the top flagged suspicious networks for the dashboard."""
    return MOCK_SUSPICIOUS_NETWORKS

@app.get("/network/{network_id}", tags=["Networks"])
def get_network_details(network_id: str) -> Dict[str, Any]:
    """Returns the nodes and edges for a specific network for graph visualization."""
    if network_id not in MOCK_GRAPH_DATA:
        raise HTTPException(status_code=404, detail="Network not found")
    return {"network_id": network_id, "graph": MOCK_GRAPH_DATA[network_id]}

@app.get("/account/{account_id}/explanation", tags=["XAI"])
def get_account_explanation(account_id: str) -> Dict[str, Any]:
    """Returns the XAI-generated reason for why an account is flagged."""
    if account_id not in MOCK_EXPLANATIONS:
        raise HTTPException(status_code=404, detail="Explanation for this account not found")
    return {"account_id": account_id, "explanation": MOCK_EXPLANATIONS[account_id]}