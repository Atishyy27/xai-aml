# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from typing import List, Dict, Any
import sys
import os
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
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Neo4j Database Connection ---
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

class Neo4jApp:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

db = Neo4jApp(URI, AUTH)

@app.on_event("startup")
async def startup_event():
    print("FastAPI app starting up, Neo4j driver is ready.")

@app.on_event("shutdown")
def shutdown_event():
    db.close()
    print("FastAPI app shutting down, Neo4j driver closed.")

# --- LIVE API ENDPOINTS ---
@app.get("/", tags=["Status"])
def read_root():
    return {"status": "API is operational"}

@app.get("/suspicious-networks", tags=["Networks"])
def get_live_suspicious_networks() -> List[Dict[str, Any]]:
    try:
        live_networks = get_top_suspicious_networks()
        return live_networks
    except Exception as e:
        print(f"Error in AI Core: {e}")
        raise HTTPException(status_code=500, detail="Error processing data in the AI core.")

@app.get("/network/{account_id}", tags=["Networks"])
def get_live_network_details(account_id: str) -> Dict[str, Any]:
    query = """
    MATCH (target:Account {account_id: $acc_id})
    OPTIONAL MATCH path = (target)-[:TRANSFER*1..1]-(neighbor:Account)
    WITH collect(path) as paths
    UNWIND paths as p
    WITH nodes(p) as all_nodes, relationships(p) as all_rels
    UNWIND all_nodes as n
    UNWIND all_rels as r
    RETURN
        collect(DISTINCT {id: n.account_id}) AS nodes,
        collect(DISTINCT {source: startNode(r).account_id, target: endNode(r).account_id, amount: r.amount_inr}) AS edges
    """
    try:
        with db.driver.session() as session:
            result = session.run(query, acc_id=account_id).single()
            if not result or not result["nodes"]:
                raise HTTPException(status_code=404, detail="Account or network not found in graph.")
            
            graph_data = {"nodes": result["nodes"], "edges": result["edges"]}
            
            if not graph_data["nodes"]:
                graph_data["nodes"] = [{"id": account_id}]

            return {"network_id": account_id, "graph": graph_data}
    except Exception as e:
        print(f"Database query error for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Error querying the graph database.")

@app.get("/account/{account_id}/explanation", tags=["XAI"])
def get_live_account_explanation(account_id: str) -> Dict[str, Any]:
    try:
        result = get_prediction_and_explanation(account_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        print(f"XAI explanation error for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Error generating AI explanation.")