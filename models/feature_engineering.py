# models/feature_engineering.py
import pandas as pd
from neo4j import GraphDatabase

class FeatureExtractor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def get_node_features(self):
        # This Cypher query calculates key features for each account
        # in-degree, out-degree, amounts, etc.
        query = """
        MATCH (a:Account)
        OPTIONAL MATCH (a)-[r_out:TRANSFER]->()
        OPTIONAL MATCH (a)<-[r_in:TRANSFER]-()
        RETURN
            a.account_id AS account_id,
            a.initial_risk_rating as initial_risk,
            COUNT(DISTINCT r_out) AS out_degree,
            COUNT(DISTINCT r_in) AS in_degree,
            COALESCE(SUM(r_out.amount_inr), 0) AS total_amount_out,
            COALESCE(SUM(r_in.amount_inr), 0) AS total_amount_in,
            COALESCE(AVG(r_out.amount_inr), 0) AS avg_amount_out,
            COALESCE(AVG(r_in.amount_inr), 0) AS avg_amount_in
        """
        with self.driver.session() as session:
            results = session.run(query)
            df = pd.DataFrame([record.data() for record in results])
        
        # Additional feature engineering
        df['transaction_volume'] = df['total_amount_in'] + df['total_amount_out']
        df['net_flow'] = df['total_amount_in'] - df['total_amount_out']
        
        return df

if __name__ == "__main__":
    extractor = FeatureExtractor("bolt://localhost:7687", "neo4j", "password123")
    features_df = extractor.get_node_features()
    
    # Save features to be used by the models
    features_df.to_csv("account_features.csv", index=False)
    print("Feature extraction complete. Saved to account_features.csv")
    
    extractor.close()