# AI Core for Project SENTINEL

## 1.0 Objective

This document specifies the requirements for the AI Core of Project SENTINEL. The objective is to design and implement a hybrid, two-stage machine learning pipeline that:

1. Identifies individually anomalous accounts from a large transaction graph.
2. Detects entire networks of accounts involved in coordinated illicit activity.
3. Provides human-readable explanations for its findings to generate actionable intelligence.

## 2.0 Justification: Why a Hybrid, Two-Stage, Explainable Model?

A single model is insufficient to capture the complexity of money laundering. Our architecture is a direct synthesis of the most effective approaches identified in the literature.

- **Why Hybrid (Unsupervised + Supervised)?** The AML problem requires detecting both *known* and *unknown* threats. An unsupervised model excels at identifying novel anomalies, while a supervised model can be trained to recognize specific, known laundering typologies with high accuracy. The
    
    `Amaretto` framework demonstrates the power of combining these approaches to improve overall detection performance.
    
- **Why Two-Stage (Node + Graph)?** Money laundering manifests as both abnormal individual behavior and suspicious network structures. A two-stage model addresses both aspects.
    - **Stage 1 (Node-Level):** Acts as a high-performance filter to identify potentially risky accounts based on their own transaction patterns, reducing the search space for the more computationally intensive graph analysis.
    - **Stage 2 (Graph-Level):** Analyzes the connections *between* these risky nodes to uncover the conspiracy. This aligns with the findings of numerous papers that graph-based analysis is essential for detecting coordinated schemes like layering and mule activity.
- **Why Explainable?** For an AI tool to be useful in law enforcement, its decisions cannot be a "black box." An Investigating Officer needs evidence and justification to build a case. The critical review by Kute et al. (2021) highlights that the lack of interpretability is a primary barrier to AI adoption in AML and that XAI is the necessary solution.

## 3.0 Methodology & Research Basis

### 3.1 Feature Engineering

The model's performance relies on robust features extracted from the transaction graph.

- **Methodology:** A Python script will connect to the Neo4j database and run Cypher queries to compute a feature vector for each account.
- **Features:**
    - **Graph Topology Features:** `in_degree`, `out_degree`.
    - **Transactional Features:** `total_amount_in`, `total_amount_out`, `avg_amount_in`, `avg_amount_out`, `transaction_count`.
    - **Derived Features:** `net_flow` (in - out), `transaction_velocity`.
- 
    
    **Research Basis:** These features are consistently identified across the literature as fundamental indicators of financial activity and risk.
    

### 3.2 Stage 1: Unsupervised Anomaly Detection (Autoencoder)

- **Methodology:** A PyTorch-based Autoencoder neural network will be trained on the feature vectors of all accounts. The model will learn a compressed representation of "normal" account behavior.
- **Anomaly Scoring:** The Mean Squared Error (MSE) between an account's original feature vector and its reconstructed vector will serve as its anomaly score. A high score indicates the account's behavior is abnormal and difficult to model.
- 
    
    **Research Basis:** Autoencoders are a proven technique for unsupervised anomaly detection in financial contexts, as they can identify subtle deviations from normal patterns without needing labeled data.
    

### 3.3 Stage 2: Supervised Network Detection (GCN)

- **Methodology:** A Graph Convolutional Network (GCN) will be implemented using PyTorch and the Deep Graph Library (DGL). The GCN will be trained on the entire transaction graph, using the `is_illicit` flags from the synthetic data as ground-truth labels.
- **Function:** The GCN learns from both the features of an account and the features of its neighbors, allowing it to identify complex network topologies that are indicative of money laundering.
- **Research Basis:** GCNs are the state-of-the-art for machine learning on graph data. Their effectiveness in detecting illicit transactions in financial networks, particularly in the cryptocurrency space, is demonstrated in papers like Weber et al. (2019) and Alarab et al. (2020) .

### 3.4 Stage 3: XAI Engine (SHAP)

- **Methodology:** We will use the SHAP (SHapley Additive exPlanations) library to interpret the predictions of our models. For a given flagged network or account, SHAP calculates the contribution of each input feature to the final risk score.
- **Function:** This provides the crucial "why" behind an alert. The output will be a list of the top features (e.g., `"high 'net_flow' value"`, `"connection to known mule account"`) and their impact on the risk score.
- **Research Basis:** Kute et al. (2021) identify SHAP as a key model-agnostic XAI technique capable of explaining complex black-box models, making it the ideal choice for providing transparency to the IO.

## 4.0 Technical Specifications

- **Libraries:** PyTorch, DGL, Scikit-learn, SHAP, Pandas, NumPy, Neo4j Driver.
- **Input:** `account_features.csv` generated from the Neo4j database.
- **Output:** A Python module (`predictor.py`) containing two primary functions:
    1. `get_top_suspicious_networks()`: Returns a ranked list of the highest-risk networks.
    2. `get_prediction_and_explanation(account_id)`: Returns a JSON object with risk scores and a structured, plain-English explanation.
- **Artifacts:** Saved model files (`autoencoder.pth`, `gcn.pth`).