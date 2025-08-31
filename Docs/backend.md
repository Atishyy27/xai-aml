# Backend API for Project SENTINEL

## 1.0 Objective

This document specifies the requirements for the backend service of Project SENTINEL. The objective is to build a high-performance, scalable, and robust API server that acts as the central nervous system of the application, connecting the Neo4j database, the AI Core, and the frontend user interface.

## 2.0 Justification: Why FastAPI and Neo4j?

The choice of technology is driven by the specific needs of a real-time, data-intensive intelligence platform.

- **Why a Decoupled API?** A service-oriented architecture is a modern best practice that separates concerns. A dedicated API allows the frontend and AI core to evolve independently and enables parallel development, which is critical for a hackathon.
- **Why FastAPI?** For a Python-based AI project, FastAPI is the optimal choice. Its asynchronous nature provides extremely high performance, and its automatic generation of OpenAPI (Swagger) documentation is an invaluable tool for ensuring the frontend and backend teams are perfectly aligned on the API contract.
- **Why Neo4j?** Money laundering is about relationships and flows between entities. A native graph database like Neo4j is purpose-built for storing and querying this type of connected data. Running complex graph queries (e.g., finding all accounts within a 2-hop radius of a suspect) is significantly more efficient and intuitive in Neo4j with Cypher than it would be with complex JOINs in a traditional SQL database.

## 3.0 Methodology & API Endpoints

### 3.1 Service Architecture

The backend is a Dockerized FastAPI application. It maintains a persistent connection pool to the Neo4j database container and dynamically loads the AI models from the `models` directory to perform inference. All communication with the frontend is handled via a RESTful JSON API.

### 3.2 API Endpoint Specifications

### `GET /suspicious-networks`

- **Description:** Returns a ranked list of the top 5 most suspicious networks/accounts detected by the AI Core. This is the primary endpoint for populating the IO's main dashboard.
- **Response Body:** `List[dict]` where each dict contains `network_id`, `risk_score`, `pattern_type`, `involved_accounts`, `total_amount_inr`.
- **Justification:** Provides a prioritized worklist for the IO, allowing them to focus on the highest-risk threats first.

### `GET /network/{account_id}`

- **Description:** Fetches the local subgraph for a given suspicious account ID to be rendered by the frontend visualization component. It returns the central node and all its neighbors within one hop.
- **Cypher Query:**Cypher
    
    `MATCH (target:Account {account_id: $acc_id})
    OPTIONAL MATCH path = (target)-[:TRANSFER]-(neighbor:Account)
    WITH nodes(path) as all_nodes, relationships(path) as all_rels
    UNWIND all_nodes as n
    UNWIND all_rels as r
    RETURN
        collect(DISTINCT {id: n.account_id}) AS nodes,
        collect(DISTINCT {source: startNode(r).account_id, target: endNode(r).account_id, amount: r.amount_inr}) AS edges`
    
- 
    
    **Justification:** Provides the necessary data for the interactive graph visualization, which is critical for an IO to understand the context and scope of a laundering network.
    

### `GET /account/{account_id}/explanation`

- **Description:** Returns the plain-English, evidence-based explanation for why an account or network was flagged.
- **Response Body:** `dict` containing `account_id` and a structured `explanation` object from the XAI engine.
- 
    
    **Justification:** Delivers the core "explainability" feature of the project, making the AI's output transparent and useful for building a legal case.
    

## 4.0 Technical Specifications

- **Framework:** FastAPI, Uvicorn
- **Language:** Python 3.10+
- **Libraries:** `neo4j`, `pydantic`
- **API Contract:** Defined in `openapi.json`.
- **Deployment:** Docker container orchestrated by `docker-compose.yml`.