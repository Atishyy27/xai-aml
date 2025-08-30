# /backend/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Project SENTINEL Backend - To be implemented."}


@app.get("/suspicious-networks")
def get_suspicious_networks_mock():
    """
    This is a MOCK endpoint. It returns fake data for frontend development.
    """
    mock_data = [
        {"network_id": "net_001", "risk_score": 95, "reason": "Suspected Smurfing"},
        {"network_id": "net_002", "risk_score": 92, "reason": "Complex Layering Chain"},
    ]
    return mock_data