# models/train_gcn.py
import dgl
import torch
import torch.nn as nn
import torch.nn.functional as F
from dgl.nn.pytorch import GraphConv
from neo4j import GraphDatabase
import pandas as pd
import joblib
import os
from dotenv import load_dotenv
load_dotenv()

# --- 1. Define the GCN Architecture ---
class GCN(nn.Module):
    def __init__(self, in_feats, h_feats, num_classes):
        super(GCN, self).__init__()
        self.conv1 = GraphConv(in_feats, h_feats)
        self.conv2 = GraphConv(h_feats, num_classes)

    def forward(self, g, in_feat):
        h = self.conv1(g, in_feat)
        h = F.relu(h)
        h = self.conv2(g, h)
        return h

# --- 2. Function to fetch graph data from Neo4j ---
def build_graph_from_neo4j(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Get nodes
        print(" > Step 2a: Fetching all account nodes from Neo4j...")
        node_query = "MATCH (a:Account) RETURN a.account_id AS id"
        nodes_df = pd.DataFrame([r.data() for r in session.run(node_query)])
        node_map = {node_id: i for i, node_id in enumerate(nodes_df['id'])}
        print(f"   - Found {len(node_map)} nodes.")

        # Get edges
        print(" > Step 2b: Fetching all transaction relationships from Neo4j...")
        edge_query = "MATCH (a:Account)-[r:TRANSFER]->(b:Account) RETURN a.account_id AS src, b.account_id AS dst"
        edges_df = pd.DataFrame([r.data() for r in session.run(edge_query)])
        print(f"   - Found {len(edges_df)} relationships.")
        
        src_nodes = [node_map[sid] for sid in edges_df['src']]
        dst_nodes = [node_map[rid] for rid in edges_df['dst']]

    return dgl.graph((src_nodes, dst_nodes)), node_map

# --- 3. Training Script ---
if __name__ == "__main__":
    print("--- Step 1: Loading DataFrames ---")
    features_df = pd.read_csv("account_features.csv")
    labels_df = pd.read_csv('SynthDataGen/transactions.csv')
    print(" > DataFrames loaded successfully.")

    print("\n--- Step 2: Creating Ground-Truth Labels ---")
    illicit_accounts = set(labels_df[labels_df['is_illicit'] == 1]['source_account']).union(
                         set(labels_df[labels_df['is_illicit'] == 1]['target_account']))
    features_df['label'] = features_df['account_id'].apply(lambda x: 1 if x in illicit_accounts else 0)
    print(f" > Labeled {features_df['label'].sum()} accounts as illicit.")

    print("\n--- Step 3: Building Graph from Neo4j Database ---")
    graph, node_map = build_graph_from_neo4j(
        os.getenv("NEO4J_URI"),
        os.getenv("NEO4J_USER"),
        os.getenv("NEO4J_PASSWORD")
    )
    graph = dgl.add_self_loop(graph)
    print(" > Graph built successfully.")
    
    print("\n--- Step 4: Normalizing Features and Aligning Data ---")
    # Align features with graph node order FIRST
    features_df = features_df.set_index('account_id').loc[list(node_map.keys())]
    
    # Load the scaler saved by the autoencoder script
    scaler = joblib.load("scaler.pkl")
    
    # Separate features and labels
    features_to_scale = features_df.drop('label', axis=1).values
    labels_final = torch.LongTensor(features_df['label'].values)

    # Apply the scaler to normalize the features
    scaled_features = scaler.transform(features_to_scale)
    features_final = torch.FloatTensor(scaled_features)
    print(" > Features normalized and aligned.")
    
    # models/train_gcn.py

    print("\n--- Step 5: Training the GCN Model ---")

    # --- START CORRECTED CODE ---
    # Calculate class weights to handle the highly imbalanced data
    num_positives = labels_final.sum().item()
    num_negatives = len(labels_final) - num_positives

    # This new weight tells the model that misclassifying an illicit account
    # is much more "costly" than misclassifying a benign one.
    weight_for_illicit = num_negatives / num_positives
    weights = torch.tensor([1.0, weight_for_illicit]) 

    print(f" > Using class weights to handle imbalance: [Benign: 1.0, Illicit: {weight_for_illicit:.2f}]")
    # --- END CORRECTED CODE ---

    model = GCN(features_final.shape[1], 16, 2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    num_epochs = 100
    for epoch in range(num_epochs):
        logits = model(graph, features_final)

        # Apply the corrected weights to the loss function
        loss = F.cross_entropy(logits, labels_final, weight=weights)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch + 1}/{num_epochs}], Loss: {loss.item():.4f}')

    print(" > Training complete.")

    print("\n--- Step 6: Saving Model ---")
    torch.save(model.state_dict(), "gcn.pth")
    print(" > GCN model trained and saved to gcn.pth")