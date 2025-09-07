# models/train_gcn.py
import dgl
import torch
import torch.nn as nn
import torch.nn.functional as F
from dgl.nn.pytorch import GraphConv
from neo4j import GraphDatabase
import pandas as pd
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
        # Get nodes and create a mapping from account_id to an integer index
        node_query = "MATCH (a:Account) RETURN a.account_id AS id"
        nodes_df = pd.DataFrame([r.data() for r in session.run(node_query)])
        node_map = {node_id: i for i, node_id in enumerate(nodes_df['id'])}
        
        # Get edges
        edge_query = "MATCH (a:Account)-[r:TRANSFER]->(b:Account) RETURN a.account_id AS src, b.account_id AS dst"
        edges_df = pd.DataFrame([r.data() for r in session.run(edge_query)])
        
        src_nodes = [node_map[sid] for sid in edges_df['src']]
        dst_nodes = [node_map[rid] for rid in edges_df['dst']]

    return dgl.graph((src_nodes, dst_nodes)), node_map

# --- 3. Training Script ---
if __name__ == "__main__":
    features_df = pd.read_csv("account_features.csv")
    
    labels_df = pd.read_csv('../SynthDataGen/transactions.csv')
    illicit_accounts = set(labels_df[labels_df['is_illicit'] == 1]['source_account'])
    features_df['label'] = features_df['account_id'].apply(lambda x: 1 if x in illicit_accounts else 0)

    # Build DGL graph
    graph, node_map = build_graph_from_neo4j(
        os.getenv("NEO4J_URI"),
        os.getenv("NEO4J_USER"),
        os.getenv("NEO4J_PASSWORD")
    )

    # Add self-loops to the graph to handle 0-in-degree nodes
    graph = dgl.add_self_loop(graph)
    
    # Align features with graph node order
    features_df = features_df.set_index('account_id').loc[list(node_map.keys())]

    features = torch.FloatTensor(features_df.drop('label', axis=1).values)
    labels = torch.LongTensor(features_df['label'].values)
    
    # Model Initialization
    model = GCN(features.shape[1], 16, 2) # 2 classes: benign (0), illicit (1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    # Training Loop
    print("Training GCN...")
    for epoch in range(100):
        logits = model(graph, features)
        loss = F.cross_entropy(logits, labels)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/100], Loss: {loss.item():.4f}')
            
    torch.save(model.state_dict(), "gcn.pth")
    print("GCN model trained and saved to gcn.pth")