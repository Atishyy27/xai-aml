import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# --- Config ---
NUM_CUSTOMERS = 5000
NUM_ACCOUNTS = 10000
NUM_TRANSACTIONS_NORMAL = 50000
START_DATE = datetime(2025, 8, 18)
END_DATE = datetime(2025, 9, 9)

# Illicit Config
NUM_SMURFING_OPS = 10
NUM_LAYERING_CHAINS = 20
NUM_CASH_OUT_MULES = 20

fake = Faker('en_IN')

def generate_pan():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5)) + \
           ''.join(random.choices('0123456789', k=4)) + \
           random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

# --- 1. Generate Accounts ---
print("Step 1: Generating accounts with upgraded schema...")
accounts_data = []
for i in range(NUM_ACCOUNTS):
    accounts_data.append({
        'account_id': f'ACC{1001 + i}',
        'customer_id': f'CUST{1001 + random.randint(0, NUM_CUSTOMERS - 1)}',
        'pan_card': generate_pan(),
        'account_type': random.choice(['Savings', 'Current']),
        'created_at': fake.date_time_between(start_date=START_DATE - timedelta(days=730), end_date=START_DATE).isoformat(),
        'city': fake.city_name(),
        'state': fake.state(),
        'branch_ifsc': f"BANK{random.randint(1000,9999)}",
        'initial_risk_rating': random.randint(1, 5)
    })
accounts_df = pd.DataFrame(accounts_data)

# --- 2. Generate Normal Transactions ---
print("Step 2: Generating normal transaction baseline with temporal patterns...")
transactions_data = []
account_ids = accounts_df['account_id'].tolist()
days_in_period = (END_DATE - START_DATE).days

for i in range(NUM_TRANSACTIONS_NORMAL):
    source, target = random.sample(account_ids, 2)
    
    # Logic we implement: 70% of transactions happen during business hours (9 AM - 6 PM)
    if random.random() < 0.7:
        hour = random.randint(9, 17)
    else:
        hour = random.choice([*range(0, 9), *range(18, 24)])
        
    transaction_date = START_DATE + timedelta(days=random.randint(0, days_in_period), hours=hour, minutes=random.randint(0, 59))
    amount_inr = round(np.random.lognormal(mean=4.5, sigma=1.8), 2) + 1.00 # Based on Dumitrescu et al.

    transactions_data.append({
        'transaction_id': f'TXN{100001 + i}',
        'source_account': source,
        'target_account': target,
        'timestamp': transaction_date.isoformat(),
        'amount_inr': amount_inr,
        'transaction_type': random.choice(['TRANSFER', 'PURCHASE']), # NEW FIELD
        'remarks': fake.sentence(nb_words=3),
        'source_ip': fake.ipv4(),
        'is_illicit': 0,
        'illicit_pattern_type': 'NONE'
    })

transactions_df = pd.DataFrame(transactions_data)
current_txn_id = 100001 + NUM_TRANSACTIONS_NORMAL

# --- 3. Inject Illicit Patterns (with `illicit_pattern_type` label) ---

def inject_smurfing(df, accounts, num_ops, start_txn_id):
    print("Injecting smurfing patterns (Fan-in Topology)...")
    new_txns = []
    # This logic is inspired by the "fan-in" patterns described in papers like MONLAD.
    for _ in range(num_ops):
        target_account = random.choice(accounts)
        smurf_accounts = random.sample([acc for acc in accounts if acc != target_account], 20)
        op_start_date = START_DATE + timedelta(days=random.randint(0, days_in_period - 3))
        
        for i in range(random.randint(20, 50)):
            source = random.choice(smurf_accounts)
            amount_inr = round(random.uniform(5000, 49000), 2)
            txn_date = op_start_date + timedelta(hours=random.randint(0, 72), minutes=random.randint(0, 59))
            
            new_txns.append({
                'transaction_id': f'TXN{start_txn_id}', 'source_account': source, 'target_account': target_account,
                'timestamp': txn_date.isoformat(), 'amount_inr': amount_inr, 'transaction_type': 'TRANSFER',
                'remarks': 'payment', 'source_ip': fake.ipv4(), 'is_illicit': 1,
                'illicit_pattern_type': 'SMURFING'
            })
            start_txn_id += 1
    return pd.concat([df, pd.DataFrame(new_txns)], ignore_index=True), start_txn_id

def inject_layering(df, accounts, num_chains, start_txn_id):
    print("Injecting layering chains (Multi-hop)...")
    new_txns = []
    # This logic simulates the multi-step flows that algorithms like FlowScope are designed to detect.
    for _ in range(num_chains):
        chain_length = random.randint(4, 8)
        chain_accounts = random.sample(accounts, chain_length)
        initial_amount = round(random.uniform(200000, 1000000), 2)
        op_start_date = START_DATE + timedelta(days=random.randint(0, days_in_period - 2))
        
        current_amount = initial_amount
        for i in range(chain_length - 1):
            source, target = chain_accounts[i], chain_accounts[i+1]
            amount_inr = round(current_amount * random.uniform(0.98, 0.99), 2)
            txn_date = op_start_date + timedelta(hours=i*2 + random.uniform(-1, 1))
            
            new_txns.append({
                'transaction_id': f'TXN{start_txn_id}', 'source_account': source, 'target_account': target,
                'timestamp': txn_date.isoformat(), 'amount_inr': amount_inr, 'transaction_type': 'TRANSFER',
                'remarks': 'fund transfer', 'source_ip': fake.ipv4(), 'is_illicit': 1,
                'illicit_pattern_type': 'LAYERING'
            })
            start_txn_id += 1
            current_amount = amount_inr
    return pd.concat([df, pd.DataFrame(new_txns)], ignore_index=True), start_txn_id

def inject_cash_out_mule(df, accounts, num_mules, start_txn_id):
    print("Injecting cash-out mule patterns (Balanced State Behavior)...")
    new_txns = []
    # This simulates the "balanced state" behavior identified as a key indicator in the MONLAD paper.
    for _ in range(num_mules):
        mule_account = random.choice(accounts)
        source_account = random.choice([acc for acc in accounts if acc != mule_account])
        op_start_date = START_DATE + timedelta(days=random.randint(0, days_in_period - 1))
        
        incoming_amount = round(random.uniform(100000, 500000), 2)
        new_txns.append({
            'transaction_id': f'TXN{start_txn_id}', 'source_account': source_account, 'target_account': mule_account,
            'timestamp': op_start_date.isoformat(), 'amount_inr': incoming_amount, 'transaction_type': 'TRANSFER',
            'remarks': 'transfer', 'source_ip': fake.ipv4(), 'is_illicit': 1,
            'illicit_pattern_type': 'MULE'
        })
        start_txn_id += 1
        
        total_cashed_out = 0
        for _ in range(random.randint(20, 50)):
            if total_cashed_out >= incoming_amount * 0.95: break
            
            mode = random.choice(['ATM_WITHDRAWAL', 'PURCHASE'])
            amount_inr = round(random.uniform(500, 10000), 2)
            txn_date = op_start_date + timedelta(minutes=random.randint(5, 240))
            
            new_txns.append({
                'transaction_id': f'TXN{start_txn_id}', 'source_account': mule_account, 'target_account': f"MERCHANT{random.randint(1,500)}",
                'timestamp': txn_date.isoformat(), 'amount_inr': amount_inr, 'transaction_type': mode,
                'remarks': 'purchase' if mode == 'PURCHASE' else 'cash withdrawal', 'source_ip': fake.ipv4(), 'is_illicit': 1,
                'illicit_pattern_type': 'MULE' # UPGRADED LABEL
            })
            start_txn_id += 1
            total_cashed_out += amount_inr
    return pd.concat([df, pd.DataFrame(new_txns)], ignore_index=True), start_txn_id

# --- Execute Injection and Finalize ---
transactions_df, current_txn_id = inject_smurfing(transactions_df, account_ids, NUM_SMURFING_OPS, current_txn_id)
transactions_df, current_txn_id = inject_layering(transactions_df, account_ids, NUM_LAYERING_CHAINS, current_txn_id)
transactions_df, current_txn_id = inject_cash_out_mule(transactions_df, account_ids, NUM_CASH_OUT_MULES, current_txn_id)

# --- 4. Finalize and Save ---
print("Step 4: Saving datasets to CSV...")
transactions_df = transactions_df.sample(frac=1).reset_index(drop=True)
accounts_df.to_csv('accounts.csv', index=False)
transactions_df.to_csv('transactions.csv', index=False)

print("\nUpgraded synthetic dataset generation complete!")
print(f"Generated {len(accounts_df)} accounts.")
print(f"Generated {len(transactions_df)} transactions.")
print(f"Number of illicit transactions: {transactions_df['is_illicit'].sum()}")