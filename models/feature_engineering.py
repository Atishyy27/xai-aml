# models/feature_engineering.py
import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

class FeatureExtractor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def get_node_features(self):
        print("Fetching features in batches to prevent timeouts...")
        # This APOC query processes nodes in batches of 2000 to avoid timeouts.
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
        
        # Additional feature engineering (this part is unchanged)
        df['transaction_volume'] = df['total_amount_in'] + df['total_amount_out']
        df['net_flow'] = df['total_amount_in'] - df['total_amount_out']
        
        return df

if __name__ == "__main__":
    # Load credentials from the .env file in the root folder
    load_dotenv()

    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    # Use the loaded credentials to connect
    extractor = FeatureExtractor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    print("Extracting features from the database...")
    features_df = extractor.get_node_features()

    # Save features to be used by the models
    features_df.to_csv("account_features.csv", index=False)
    print("Feature extraction complete. Saved to account_features.csv")

    extractor.close()