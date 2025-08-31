# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add the models directory to the Python path to allow direct imports
# This is a common pattern for structuring larger applications.
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models'))

# Now you can import the predictor function
from predictor import get_prediction_and_explanation

app = FastAPI(
    title="Project SENTINEL API",
    description="API for detecting and explaining money laundering networks."
)

# --- CORS Middleware ---
# This allows your frontend (running on a different port) to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Project SENTINEL AI Service is running."}

@app.get("/suspicious-networks")
def get_suspicious_networks():
    """
    Returns a list of the top flagged networks.
    NOTE: In a real system, this would query the AI core for the highest-risk networks.
    For the hackathon, we can return a pre-selected list of known illicit accounts from our dataset.
    """
    # This is a placeholder for the hackathon to ensure the UI has something to show.
    known_illicit_accounts = [
        {"account_id": "account_id_from_your_data_1", "risk_score": 0.98},
        {"account_id": "account_id_from_your_data_2", "risk_score": 0.95},
        {"account_id": "account_id_from_your_data_3", "risk_score": 0.92},
        {"account_id": "account_id_from_your_data_4", "risk_score": 0.89},
        {"account_id": "account_id_from_your_data_5", "risk_score": 0.85},
    ]
    return {"networks": known_illicit_accounts}

@app.get("/account/{account_id}/explanation")
def get_account_explanation(account_id: str):
    """
    Takes an account ID and returns the AI-driven prediction and explanation.
    This is the core endpoint that connects to your AI model.
    """
    try:
        # This is the live call to your AI core.
        result = get_prediction_and_explanation(account_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        # General exception handler for any issues within the AI module
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@app.get("/network/{network_id}")
def get_network_graph(network_id: str):
    """
    Returns the nodes and edges for a specific network for visualization.
    NOTE: This logic needs to be implemented. It would query Neo4j to get the
    local neighborhood of the given account ID (network_id).
    """
    # Placeholder for the graph data needed by D3.js
    # You would implement a Cypher query here to get, for example,
    # all accounts within 2 hops of the central 'network_id' account.
    mock_graph_data = {
        "nodes": [
            {"id": network_id, "group": "center"},
            {"id": "neighbor_1", "group": "source"},
            {"id": "neighbor_2", "group": "source"},
            {"id": "neighbor_3", "group": "destination"}
        ],
        "links": [
            {"source": "neighbor_1", "target": network_id, "value": 1000},
            {"source": "neighbor_2", "target": network_id, "value": 2500},
            {"source": network_id, "target": "neighbor_3", "value": 3500}
        ]
    }
    return mock_graph_data