# 🚀 Project Setup Guide

Follow these steps to set up and run the entire application locally.

### Step 1: Prerequisites
- Git
- Python 3.10+
- Node.js 18+
- Neo4j Desktop

### Step 2: Initial Code & Environment Setup
1. Clone the repository: `git clone <your-repo-url>`
2. Navigate into the project folder: `cd CIIS`
3. Create and activate the Python virtual environment:
   - `python -m venv venv`
   - `.\venv\Scripts\activate`
4. Install all Python dependencies:
   - `pip install -r requirements.txt`

### Step 3: Data Generation & Loading
This step creates the CSVs and populates your local Neo4j database.
1. Start a local database in **Neo4j Desktop**. Get the URI, username, and password.
2. In the `SynthDataGen/load_to_neo4j.py` script, update the `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` variables with your local database credentials.
3. Run the data generation script:
   - `python SynthDataGen/generate_data.py`
4. Run the data loading script:
   - `python SynthDataGen/load_to_neo4j.py`

### Step 4: Feature Engineering & Model Training
This step uses the data in Neo4j to create features and train the AI models.
1. In `models/feature_engineering.py`, update the database credentials if needed.
2. Run the scripts in order:
   - `python models/feature_engineering.py`  (Creates `account_features.csv`)
   - `python models/train_autoencoder.py` (Creates `autoencoder.pth` and `scaler.pkl`)
   - `python models/train_gcn.py`         (Creates `gcn.pth`)

### Step 5: Run the Application
1. **Start the Backend:**
   - In your first terminal (with the `venv` active), run:
     - `uvicorn backend.main:app --reload`
   - The backend will be live at `http://127.0.0.1:8000`.

2. **Start the Frontend:**
   - Open a **new terminal**.
   - Navigate to the frontend folder: `cd frontend`
   - Install dependencies: `npm install`
   - Start the app: `npm run dev`
   - The frontend will be live at `http://localhost:5173`.