# backend/main.py
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from typing import List, Dict, Any
import sys
from collections import Counter
import logging
from dotenv import load_dotenv
load_dotenv()

# Ensures the backend can find the 'models' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.predictor import get_prediction_and_explanation, get_top_suspicious_networks

app = FastAPI(
    title="XAI-AML Detection API",
    description="Live API for detecting and explaining money laundering networks.",
    version="1.0.0"
)

# --- CORS Middleware ---
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Neo4j Driver (Global & Robust) ---
# Create a single driver instance to be shared by the application.
# The driver manages a pool of connections, which is thread-safe.
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
driver = GraphDatabase.driver(URI, auth=AUTH)

@app.on_event("startup")
async def startup_event():
    # Verify connection on startup
    driver.verify_connectivity()
    print("FastAPI app starting up, Neo4j driver is ready.")

@app.on_event("shutdown")
def shutdown_event():
    # Close the driver connection pool on shutdown
    driver.close()
    print("FastAPI app shutting down, Neo4j driver closed.")


# --- LIVE API ENDPOINTS ---
@app.get("/", tags=["Status"])
def read_root():
    return {"status": "API is operational"}

# CORRECTED ENDPOINT FOR THE DASHBOARD
@app.get("/suspicious-networks", tags=["Networks"])
def get_suspicious_networks_list() -> List[Dict[str, Any]]:
    """
    Returns a list of the top flagged networks for the main dashboard.
    """
    try:
        live_networks = get_top_suspicious_networks()
        return live_networks
    except Exception as e:
        print(f"Error in AI Core: {e}")
        raise HTTPException(status_code=500, detail="Error processing data in the AI core.")

@app.get("/network/{account_id}", tags=["Networks"])
# CHANGE THIS FUNCTION SIGNATURE
def get_live_network_details(account_id: str, hops: int = Query(1, ge=1, le=2)) -> Dict[str, Any]:
    # This query now dynamically uses the 'hops' variable.
    # The f-string is safe here because 'hops' is validated by FastAPI to be an integer (1 or 2).
    query = f"""
    MATCH (target:Account {{account_id: $acc_id}})
    OPTIONAL MATCH path = (target)-[:TRANSFER*1..{hops}]-(neighbor:Account)
    WITH collect(path) as paths
    UNWIND paths as p
    WITH nodes(p) as all_nodes, relationships(p) as all_rels
    UNWIND all_nodes as n
    UNWIND all_rels as r
    RETURN
        collect(DISTINCT {{id: n.account_id}}) AS nodes,
        collect(DISTINCT {{source: startNode(r).account_id, target: endNode(r).account_id, amount: r.amount_inr}}) AS edges
    """
    try:
        with driver.session() as session:
            result = session.run(query, acc_id=account_id).single()
            if not result or not result["nodes"]:
                # If no neighbors, at least return the target node itself
                return {
                    "network_id": account_id,
                    "graph": {
                        "nodes": [{"id": account_id}],
                        "edges": []
                    }
                }
            
            graph_data = {"nodes": result["nodes"], "edges": result["edges"]}
            
            return {"network_id": account_id, "graph": graph_data}
    except Exception as e:
        print(f"Database query error for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Error querying the graph database.")

@app.get("/account/{account_id}/explanation", tags=["XAI"])
def get_live_account_explanation(account_id: str) -> Dict[str, Any]:
    try:
        # This function still gets the core AI prediction
        result = get_prediction_and_explanation(account_id)
        print("--- AI MODEL OUTPUT ---", result)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # --- NEW LOGIC TO BUILD THE DETAILED RESPONSE ---
        
        # This is placeholder logic. Replace with your actual feature values.
        feature_values = result.get('feature_values', {})
        total_amount_in = feature_values.get('total_amount_in', 0)
        transaction_volume = feature_values.get('transaction_volume', 0)
        risk_score = result.get('risk_score', 0)

        metrics_data = [
            {
                "name": "Total Amount In (30d)",
                "value": total_amount_in,
                "benchmark": 500000,
                "definition": "Total monetary value of all incoming transactions in the last 30 days."
            },
            {
                "name": "Transaction Volume (30d)",
                "value": transaction_volume,
                "benchmark": 50,
                "definition": "Total number of transactions (in/out) in the last 30 days."
            },
            {
                "name": "Risk Score",
                "value": f"{(risk_score * 100):.1f}%",
                "benchmark": "25%",
                "definition": "The model's confidence that this account is involved in illicit activities."
            }
        ]
        
        # ✅ THE FIX IS HERE: Ensure we always have contributors to show
        feature_contributions = result.get("feature_contributions", [])
        
        # If the model found no significant contributors, build a default list
        # of the top features, even if their impact is 0.
        if not feature_contributions:
            all_features = result.get("all_shap_values", []) # Assume your model can provide this
            # Sort by absolute impact and take the top 3
            sorted_features = sorted(all_features, key=lambda x: abs(x.get('impact', 0)), reverse=True)
            feature_contributions = sorted_features[:3]

            # If there's still nothing, create a dummy message
            if not feature_contributions:
                 feature_contributions = [{"feature": "No significant factors", "impact": 0}]


        # Combine everything into the final, expected structure
        detailed_explanation = {
            "summary": result.get("summary", "No summary available."),
            "feature_contributions": feature_contributions,
            "metrics": metrics_data
        }

        return {"explanation": detailed_explanation}

    except Exception as e:
        print(f"XAI explanation error for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Error generating AI explanation.")

# ... (rest of your main.py file) ...

@app.get("/statistics/patterns", tags=["Statistics"])
def get_pattern_distribution() -> List[Dict[str, Any]]:
    """
    Returns the count of each illicit pattern type among high-risk accounts.
    """
    try:
        live_networks = get_top_suspicious_networks(top_n=1000)
        if not live_networks:
            return []

        pattern_counts = Counter(
            network['pattern_type'] 
            for network in live_networks 
            if 'pattern_type' in network and network['pattern_type'] != 'Complex'
        )

        formatted_data = [{"pattern": pattern, "count": count} for pattern, count in pattern_counts.items()]
        formatted_data.sort(key=lambda x: x['count'], reverse=True)

        return formatted_data
    except Exception as e:
        print(f"Error fetching pattern statistics: {e}")
        raise HTTPException(status_code=500, detail="Error processing pattern statistics.")
    
    
@app.get("/statistics/heatmap", tags=["Statistics"], response_model=Dict[str, int])
def get_heatmap_data() -> Dict[str, int]:
    """
    Aggregates high-risk accounts by state for the geographic heatmap.
    """
    try:
        # 1. Get a large sample of high-risk accounts from the AI core
        live_networks = get_top_suspicious_networks(top_n=1000)
        if not live_networks:
            return {}

        account_ids = [network["account_id"] for network in live_networks]

        # 2. Query Neo4j to count states directly
        query = """
        UNWIND $account_ids AS acc_id
        MATCH (a:Account {account_id: acc_id})
        WHERE a.state IS NOT NULL
        RETURN a.state AS state, COUNT(*) AS count
        """

        with driver.session() as session:
            results = session.run(query, account_ids=account_ids)
            state_counts = {record["state"]: record["count"] for record in results}

        return state_counts

    except Exception as e:
        logging.exception("Error fetching heatmap data")
        raise HTTPException(status_code=500, detail="Error processing heatmap data.")
    
# backend/main.py

@app.get("/network/{account_id}/illicit-transactions", tags=["Networks"])
def get_account_transactions(account_id: str):
    """
    Retrieves incoming and outgoing transactions for a specific account.
    """
    query = """
    MATCH (a:Account {account_id: $acc_id})
    // Find transactions where this account is either the source or target
    MATCH (source:Account)-[r:TRANSFER]->(target:Account)
    WHERE source = a OR target = a
    RETURN 
        source.account_id AS from_account, 
        target.account_id AS to_account, 
        r.amount_inr AS amount,
        // You can add more properties like transaction id, timestamp, etc.
        r.timestamp AS date
    ORDER BY r.timestamp DESC
    LIMIT 25
    """
    try:
        with driver.session() as session:
            result = session.run(query, acc_id=account_id)
            transactions = [
                {
                    "from": record["from_account"],
                    "to": record["to_account"],
                    "amount": record["amount"],
                    "date": record["date"]
                } for record in result
            ]
            return {"transactions": transactions}
    except Exception as e:
        print(f"Error fetching transactions for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Error querying transactions.")