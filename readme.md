# Project SENTINEL 🛡️
### An Explainable AI Framework for Detecting and Dismantling Financial Laundering Networks

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![DGL](https://img.shields.io/badge/DGL-1.1+-F47A22?logo=dgl&logoColor=white)](https://www.dgl.ai/)

Project SENTINEL is a full-stack application designed to combat financial crime. It leverages a hybrid, two-stage AI pipeline to first identify anomalous accounts and then detect entire criminal networks within vast transaction graphs. Crucially, it provides human-readable explanations for its findings, bridging the gap between complex AI and actionable intelligence for investigators.

---
## Table of Contents
* [About The Project](#about-the-project)
* [Key Features](#key-features)
* [Detailed Documentation](#detailed-documentation)
* [Getting Started: A Step-by-Step Guide](#getting-started-a-step-by-step-guide)
* [Project Structure](#project-structure)

---
## About The Project

This project addresses a critical challenge in law enforcement: the lack of transparency in AI-driven security tools. An alert from a "black box" model is not enough to build a case. SENTINEL is built on the philosophy of **"Intelligence, not just Data,"** providing investigators with not only *what* is suspicious, but *why*.

### System Architecture
```mermaid
graph TD
    subgraph "A: Data Generation Pipeline"
        A1[SynthDataGen Scripts] --> A2{Accounts & Transactions CSVs};
    end
    subgraph "B: Local Setup & Training"
        A2 --> B1[Neo4j DB Loader];
        B1 --> B2[(Local Neo4j Database)];
        B2 --> B3[Feature Engineering];
        B3 --> B4[Model Training];
        B4 --> B5{AI Model Artifacts};
    end
    subgraph "C: Live Application"
        C1[Frontend UI <br>(React)] <--> C2[Backend API <br>(FastAPI)];
        C2 <--> B2;
        B5 --> C2;
    end
```


## Key Features
**Hybrid Two-Stage AI Core:** Combines an unsupervised Autoencoder for individual anomaly detection with a supervised Graph Neural Network (GCN) for high-accuracy network classification.

**Graph-Based Detection:** Utilizes a Neo4j graph database to natively model and analyze the complex relationships and money flows that define modern laundering schemes.

**Explainable AI (XAI) Engine:** Integrates the SHAP library to provide clear, feature-based explanations for every prediction, making the AI's decisions transparent and trustworthy for investigators.

**Realistic Synthetic Data:** Features a sophisticated data generation pipeline that simulates a financial ecosystem by injecting research-backed laundering typologies (Smurfing, Layering, and Mule Activity).

**Interactive Investigator UI:** A React-based frontend with interactive graph visualizations that allow investigators to intuitively explore and understand suspicious financial networks.

---

## Detailed Documentation

For a deeper dive into the technical design, methodology, and research basis for each component of the project, please refer to the documents below:

- [**Synthetic Dataset Generation](https://www.google.com/search?q=./Docs/Dataset_Generation.md):** The methodology for creating our high-fidelity, graph-structured financial dataset.
- [**AI Core Design](https://www.google.com/search?q=./Docs/AI_Core.md):** A detailed specification of our two-stage, hybrid, and explainable AI pipeline.
- [**Backend API Design](https://www.google.com/search?q=./Docs/backend.md):** The API contract and architecture for our FastAPI-based service.
- [**Frontend UI Design](https://www.google.com/search?q=./Docs/Frontend.md):** The component breakdown and UX philosophy for the investigator's dashboard.

---

## Getting Started: A Step-by-Step Guide

Follow these steps to set up and run the entire application on your local machine.

### 📋 Prerequisites

- [Git](https://git-scm.com/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js v18+](https://nodejs.org/)
- [Neo4j Desktop](https://neo4j.com/download/)

### ⚙️ Installation & Setup

**1. Clone the Repository & Setup Python Environment**

```bash

git clone https://github.com/Atishyy27/xai-aml.git
cd xai-aml

# Create and activate a Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

# Install all required Python packages
pip install -r requirements.txt`
```

**2. Setup Frontend Environment**

```bash
# Navigate to the frontend directory
cd frontend
# Install Node.js dependencies
npm install
# Return to the root directory
cd ..
```

**3. Setup Database & Environment File**

- Launch **Neo4j Desktop**, create a new local database, set a password, and **start the database**.
- In the project's root folder, create a `.env` file by copying the `.env.example` template.
- Fill in your `.env` file with your local Neo4j database credentials (URI, user, and password).

**4. Generate Data & Train Models**

- This crucial step runs all the necessary Python scripts in order. Make sure your `venv` is active and your Neo4j database is running.
```bash
# 1. Generate synthetic accounts.csv and transactions.csv
python SynthDataGen/generate_data.py

# 2. Load the CSVs into your Neo4j database
python SynthDataGen/load_to_neo4j.py

# 3. Create the feature set from the graph data
python models/feature_engineering.py

# 4. Train the AI models and create .pkl and .pth files
python models/train_autoencoder.py
python models/train_gcn.py
````

**5. Run the Application**

- You will need **two separate terminals** for this step.
- **In Terminal 1 (Backend):**
    - Make sure you are in the project root and your `venv` is active.
    - Start the FastAPI server:Bash
        
        `uvicorn backend.main:app --reload`
        
- **In Terminal 2 (Frontend):**
    - Navigate to the frontend directory: `cd frontend`
    - Start the React development server:Bash
        
        `npm run dev`
        

**6. Access the Application**

- Once both servers are running, open your browser and navigate to **`http://localhost:5173`**.

---

## Project Structure

```
.├── backend/            # FastAPI backend source code
├── Docs/               # Detailed design documents
├── frontend/           # React frontend source code
├── models/             # AI model training and inference scripts
├── SynthDataGen/       # Synthetic data generation scripts
├── .env.example        # Environment variable template
├── .gitignore          # Files and folders to ignore
├── requirements.txt    # Python dependencies
└── README.md           # You are here*
```
