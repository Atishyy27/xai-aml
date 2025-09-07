import pandas as pd
from neo4j import GraphDatabase
import time
import os
from dotenv import load_dotenv

# --- Config ---
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
ACCOUNTS_CSV_PATH = "SynthDataGen/accounts.csv"
TRANSACTIONS_CSV_PATH = "SynthDataGen/transactions.csv"

# --- Main Loading Script ---
class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return result

    def create_constraints(self):
        print("Creating constraints for faster import...")
        self.run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE")
        
    def load_accounts(self, accounts_df):
        print(f"Loading {len(accounts_df)} accounts into Neo4j...")
        query = """
        UNWIND $rows AS row
        MERGE (a:Account {account_id: row.account_id})
        SET a.customer_id = row.customer_id,
            a.pan_card = row.pan_card,
            a.account_type = row.account_type,
            a.created_at = datetime(row.created_at),
            a.city = row.city,
            a.state = row.state,
            a.branch_ifsc = row.branch_ifsc,
            a.initial_risk_rating = toInteger(row.initial_risk_rating) // # UPDATED to include new risk rating field
        """
        rows = accounts_df.to_dict('records')
        self.run_query(query, parameters={'rows': rows})
        print("Accounts loaded successfully.")

    def load_transactions(self, transactions_df):
        print(f"Loading {len(transactions_df)} transactions into Neo4j...")
        query = """
        UNWIND $rows AS row
        MATCH (source:Account {account_id: row.source_account})
        MATCH (target:Account {account_id: row.target_account})
        MERGE (source)-[t:TRANSFER {transaction_id: row.transaction_id}]->(target)
        SET t.amount_inr = toFloat(row.amount_inr),
            t.timestamp = datetime(row.timestamp),
            t.transaction_type = row.transaction_type,
            t.remarks = row.remarks,
            t.source_ip = row.source_ip,
            t.is_illicit = toInteger(row.is_illicit),
            t.illicit_pattern_type = row.illicit_pattern_type   // # UPDATED to include new pattern type field
        """
        rows = transactions_df.to_dict('records')
        
        batch_size = 5000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            self.run_query(query, parameters={'rows': batch})
            print(f"  Loaded batch {i // batch_size + 1}...")

        print("Transactions loaded successfully.")

if __name__ == "__main__":
    start_time = time.time()
     
    print("Reading CSV files...")
    accounts = pd.read_csv(ACCOUNTS_CSV_PATH)
    transactions = pd.read_csv(TRANSACTIONS_CSV_PATH)

    loader = Neo4jLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    loader.create_constraints()
    loader.load_accounts(accounts)
    loader.load_transactions(transactions)
    
    loader.close()
    
    end_time = time.time()
    print(f"\nData loading complete. Total time: {end_time - start_time:.2f} seconds.")