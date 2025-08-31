# models/predictor.py
import dgl
import torch
import torch.nn.functional as F
import shap
import pandas as pd
import numpy as np
import joblib

from train_autoencoder import Autoencoder
from train_gcn import GCN, build_graph_from_neo4j

print("Loading AI Core...")

# --- Load feature data (raw) ---
features_df_raw = pd.read_csv("account_features.csv").set_index("account_id")
features_np_raw = features_df_raw.values  # raw features (used by GCN & RF surrogate)

# --- Load scaler for Autoencoder (scaled features) ---
scaler = joblib.load("scaler.pkl")  # created by train_autoencoder.py

# --- Load Autoencoder (expects scaled features) ---
ae_model = Autoencoder(input_dim=features_np_raw.shape[1])
ae_model.load_state_dict(torch.load("autoencoder.pth"))
ae_model.eval()

# --- Load GCN ---
# Build DGL graph from Neo4j (ensure Neo4j is running and credentials correct)
graph, node_map = build_graph_from_neo4j("bolt://localhost:7687", "neo4j", "password123")
graph = dgl.add_self_loop(graph)

# Align features with graph node order (for GCN inference)
# create a copy so we still have raw features_df_raw untouched
features_df = features_df_raw.loc[list(node_map.keys())]
features_for_gcn = torch.FloatTensor(features_df.values)  # raw features for GCN

# Load GCN model
gcn_model = GCN(in_feats=features_for_gcn.shape[1], h_feats=16, num_classes=2)
gcn_model.load_state_dict(torch.load("gcn.pth"))
gcn_model.eval()

# --- SHAP Surrogate Model (trained on raw features -> gcn preds) ---
from sklearn.ensemble import RandomForestClassifier

with torch.no_grad():
    gcn_logits = gcn_model(graph, features_for_gcn)
    gcn_preds = torch.argmax(F.softmax(gcn_logits, dim=1), dim=1).numpy()

# Train surrogate RF on RAW features (features_np_raw) aligned to node_map order
# We must ensure the RF training features align with gcn_preds
# features_np_raw is in CSV order; features_df (above) is in graph order.
# Build raw_features_in_graph_order for RF training:
raw_features_in_graph_order = features_df.values  # shape matched to gcn_preds
rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
rf_model.fit(raw_features_in_graph_order, gcn_preds)

explainer = shap.TreeExplainer(rf_model)

print("AI Core loaded.")


def get_prediction_and_explanation(account_id: str):
    """
    Unified prediction function:
      - Autoencoder (node-level anomaly) uses SCALED features
      - GCN (network-level risk) uses RAW features (same as used in training)
      - SHAP surrogate explains the GCN output using RAW features
    """
    if account_id not in features_df.index:
        return {"error": "Account not found"}

    # RAW features for this account (for GCN & SHAP)
    account_raw = features_df.loc[[account_id]].values  # shape (1, n_features)

    # SCALED features for this account (for Autoencoder)
    account_scaled = scaler.transform(account_raw)

    # --- 1. Node-Level Anomaly Score (Autoencoder) ---
    with torch.no_grad():
        reconstructed = ae_model(torch.FloatTensor(account_scaled))
        mse_loss = torch.mean((torch.FloatTensor(account_scaled) - reconstructed) ** 2, dim=1).item()

    anomaly_score = float(mse_loss)  # raw MSE (small now because scaling)
    # optionally scale for readability (not necessary). Example:
    anomaly_score_readable = anomaly_score * 1.0

    is_anomalous_node = anomaly_score_readable > 0.05  # tune threshold after inspection

    # --- 2. Graph-Level Prediction (GCN) ---
    node_idx = node_map[account_id]
    with torch.no_grad():
        gcn_output = gcn_model(graph, features_for_gcn)  # logits for all nodes
        probs = F.softmax(gcn_output[node_idx], dim=0).numpy()
        network_risk_score = float(probs[1])  # probability of illicit class

    # --- 3. XAI Explanation (SHAP surrogate on RAW features) ---
    # Explainer expects the same raw feature representation used for training RF.
    # shap_values may be list (multiclass) or 2D array (binary).
    shap_values = explainer.shap_values(account_raw)

    # Normalize how we pick the class contributions:
    if isinstance(shap_values, list) and len(shap_values) > 1:
        # choose class-1 contributions (illicit)
        values = shap_values[1][0]
    else:
        # shap_values is a 2D array shaped (1, n_features)
        if isinstance(shap_values, list):
            values = shap_values[0][0]
        else:
            # some versions return array directly
            values = shap_values[0] if shap_values.ndim == 3 else shap_values[0]

    # Pick top 2 features (most absolute contribution)
    top_features_idx = np.argsort(-np.abs(values))[:2]
    top_features_idx = np.array(top_features_idx).flatten()
    top_features = features_df.columns[top_features_idx].tolist()

    # Map feature names to human-friendly text (tweak as needed)
    def pretty_name(f):
        return f.replace("_", " ")

    explanation = (
        f"Network risk {network_risk_score:.2f}. Top contributors: "
        f"{pretty_name(top_features[0])} and {pretty_name(top_features[1])}. "
        f"Node anomaly score (MSE): {anomaly_score_readable:.6f}."
    )

    return {
        "account_id": account_id,
        "is_anomalous_node": bool(is_anomalous_node),
        "anomaly_score": anomaly_score_readable,
        "network_risk_score": network_risk_score,
        "explanation": explanation,
    }


if __name__ == "__main__":
    # Example usage (pick a valid account from the graph-aligned features)
    idx_example = 0 if len(list(features_df.index)) == 0 else 100
    test_account_id = list(features_df.index)[idx_example]
    result = get_prediction_and_explanation(test_account_id)
    print(result)
