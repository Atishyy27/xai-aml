# models/predictor.py
import dgl
import torch
import torch.nn.functional as F
import shap
import pandas as pd
import numpy as np
import joblib

# --- Import local modules ---
from .train_autoencoder import Autoencoder
from .train_gcn import GCN, build_graph_from_neo4j

print("Loading AI Core...")

# --- Load all data and models on startup ---
try:
    # Load feature data, scaler, and pre-trained models
    features_df_raw = pd.read_csv("account_features.csv").set_index("account_id")
    scaler = joblib.load("scaler.pkl")
    
    ae_model = Autoencoder(input_dim=features_df_raw.shape[1])
    ae_model.load_state_dict(torch.load("autoencoder.pth"))
    ae_model.eval()

    # Build the graph from Neo4j
    graph, node_map = build_graph_from_neo4j("bolt://localhost:7687", "neo4j", "password123")
    graph = dgl.add_self_loop(graph)

    # Align features with the graph's node order
    features_df = features_df_raw.loc[list(node_map.keys())]
    features_for_gcn = torch.FloatTensor(features_df.values)

    gcn_model = GCN(in_feats=features_for_gcn.shape[1], h_feats=16, num_classes=2)
    gcn_model.load_state_dict(torch.load("gcn.pth"))
    gcn_model.eval()

    # Create the SHAP explainer using a surrogate model
    from sklearn.ensemble import RandomForestClassifier
    with torch.no_grad():
        gcn_logits = gcn_model(graph, features_for_gcn)
        gcn_preds = torch.argmax(F.softmax(gcn_logits, dim=1), dim=1).numpy()

    rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
    rf_model.fit(features_df.values, gcn_preds)
    explainer = shap.TreeExplainer(rf_model)
    
    print("AI Core loaded successfully.")

except FileNotFoundError as e:
    print(f"FATAL ERROR: A required model or data file is missing: {e}")
    print("Please ensure 'account_features.csv', 'scaler.pkl', 'autoencoder.pth', and 'gcn.pth' are in the root folder.")
    # Exit gracefully if files are missing
    exit()

# --- FUNCTION 1: Get Top Suspicious Networks ---
def get_top_suspicious_networks(top_n=15):
    """
    Uses the trained GCN model to predict risk scores for all nodes,
    finds the most common illicit pattern for the top accounts, and returns the results.
    """
    print("Identifying top suspicious networks and their patterns...")
    
    with torch.no_grad():
        gcn_output = gcn_model(graph, features_for_gcn)
        probabilities = F.softmax(gcn_output, dim=1)
        risk_scores = probabilities[:, 1].numpy()

    results_df = pd.DataFrame({
        'account_id': features_df.index,
        'risk_score': risk_scores
    })
    top_networks_df = results_df.sort_values(by='risk_score', ascending=False).head(top_n)

    try:
        transactions_df = pd.read_csv("SynthDataGen/transactions.csv")
        illicit_txns = transactions_df[transactions_df['is_illicit'] == 1].copy()
        
        source_patterns = illicit_txns.groupby('source_account')['illicit_pattern_type'].agg(lambda x: x.value_counts().idxmax())
        target_patterns = illicit_txns.groupby('target_account')['illicit_pattern_type'].agg(lambda x: x.value_counts().idxmax())
        
        pattern_map = source_patterns.combine_first(target_patterns).to_dict()
        top_networks_df['pattern_type'] = top_networks_df['account_id'].map(pattern_map).fillna('Complex')
    
    except FileNotFoundError:
        print("Warning: transactions.csv not found. Assigning default pattern type.")
        top_networks_df['pattern_type'] = 'Unknown'

    return top_networks_df.to_dict('records')




# models/predictor.py

def get_prediction_and_explanation(account_id: str):
    """
    Generates a full, structured XAI report for a single account.
    This version uses the robust shap.Explanation object to prevent indexing errors.
    """
    if account_id not in node_map:
        return {"error": "Account not found"}

    node_idx = node_map[account_id]
    
    # --- 1. Get Data & AI Scores ---
    account_raw = features_df.loc[[account_id]] # Keep as DataFrame
    account_raw_np = account_raw.values # NumPy version for models
    
    account_scaled = scaler.transform(account_raw_np)
    account_tensor = torch.FloatTensor(account_scaled)
    
    with torch.no_grad():
        reconstruction = ae_model(account_tensor)
        anomaly_score = F.mse_loss(reconstruction, account_tensor).item()
        
        gcn_output = gcn_model(graph, features_for_gcn)
        probs = F.softmax(gcn_output[node_idx], dim=0).numpy()
        network_risk_score = float(probs[1])

    # --- 2. Generate SHAP Explanation (The Robust Way) ---
    shap_values = explainer(account_raw) # Pass DataFrame to explainer
    
    # We want the explanation for the "illicit" class (class 1)
    shap_values_for_illicit = shap_values[:, :, 1]
    
    # --- 3. Process the SHAP Explanation Object ---
    feature_contributions = []
    # Iterate through features and their corresponding SHAP values
    for feature_name, shap_value in zip(shap_values_for_illicit.feature_names, shap_values_for_illicit.values[0]):
        # We only care about features that INCREASE risk
        if shap_value > 0:
            feature_contributions.append({
                "feature": feature_name.replace('_', ' ').title(),
                "impact": float(shap_value)
            })

    # Sort contributions to find the most impactful ones
    feature_contributions.sort(key=lambda x: x['impact'], reverse=True)
    top_contributions = feature_contributions[:3]

    # --- 4. Create Dynamic Summary ---
    if top_contributions:
        summary = (
            f"Account flagged with a {network_risk_score:.0%} network risk score. "
            f"The AI's decision was primarily driven by its abnormal '{top_contributions[0]['feature']}'. "
            f"Its individual transaction behavior also shows a notable anomaly score of {anomaly_score:.4f}."
        )
    else:
        summary = (
            f"This account has a network risk of {network_risk_score:.0%}. Its risk is primarily "
            f"due to its connections to other high-risk accounts, rather than its own specific transaction features."
        )

    # --- 5. Assemble Final Report ---
    final_explanation_object = {
        "summary": summary,
        "feature_contributions": top_contributions
    }

    return {
        "account_id": account_id,
        "anomaly_score": anomaly_score,
        "network_risk_score": network_risk_score,
        "explanation": final_explanation_object
    }