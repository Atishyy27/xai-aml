# PRD: Synthetic Transaction Graph Dataset

## 1.0 Objective
This document outlines the requirements, methodology, and technical specifications for the synthetic dataset used in Project SENTINEL. The primary objective is to create a high-fidelity, graph-structured financial dataset that is realistic, challenging, and directly relevant for training and validating advanced Anti-Money Laundering (AML) AI models.

## 2.0 Justification: Why Synthetic Data?
The development of effective AML models is critically hindered by the lack of public, large-scale, and accurately labeled real-world financial data. [cite_start]As noted in the research, privacy regulations and data confidentiality make it nearly impossible for developers to access production data[cite: 48, 458]. [cite_start]Therefore, a sophisticated synthetic data generator is a core requirement for building a robust and evaluable prototype[cite: 106, 368]. Our approach is to simulate a realistic financial ecosystem and inject it with known, research-backed laundering typologies.

## 3.0 Methodology & Research Basis
The generation process is divided into two phases: creating a realistic baseline of normal activity (the "haystack") and then injecting specific, traceable illicit patterns (the "needles").

### 3.1 Baseline Generation (The "Haystack")
To effectively detect anomalies, we must first accurately model normalcy.

* **Network Structure**: We generate a "small-world" graph to simulate natural financial communities (e.g., employees of a company, social circles). [cite_start]This ensures that the baseline graph structure is non-random and reflects real-world clustering[cite: 84, 346].
* **Transaction Amounts**: Transaction values follow a **Log-Normal Distribution**. [cite_start]This is based on academic findings which observed that real transaction distributions are heavily skewed and well-modeled by this distribution[cite: 218, 482].
* **Temporal Patterns**: Transaction timestamps simulate realistic daily and weekly cycles, with higher activity during business hours and lower activity on nights and weekends. [cite_start]This is critical for training models to recognize time-based anomalies[cite: 93, 355].

### 3.2 Illicit Pattern Injection (The "Needles")
We embed specific laundering topologies into the baseline data. Each pattern is directly inspired by typologies described in the provided research.

* **Pattern 1: Structuring / Smurfing (Fan-in Topology)**
    * [cite_start]**Description**: A central "collector" account receives many small deposits from a large set of disparate "smurf" accounts over a short period to avoid reporting thresholds[cite: 6, 268].
    * **Research Basis**: This classic pattern is a primary target for AML systems. [cite_start]The "fan-in" network structure is a key indicator analyzed in streaming detection algorithms like **MONLAD**[cite: 37, 88, 300, 349].

* **Pattern 2: Layering (Multi-hop Chains)**
    * [cite_start]**Description**: Funds are moved through a complex chain of accounts (e.g., A→B→C→D), often splitting and merging, to obscure the original source from the final destination[cite: 7, 269, 485].
    * [cite_start]**Research Basis**: The detection of these multi-step flows is the central focus of graph-based AML systems like **FlowScope**, which justifies its inclusion as a core illicit pattern for our GNN to detect[cite: 36, 87, 299, 348].

* **Pattern 3: Mule Activity (Rapid Movement / "Balanced State")**
    * [cite_start]**Description**: A mule account receives a significant sum of illicit funds and then almost immediately disperses it via multiple smaller transactions, leaving a near-zero balance[cite: 149, 222, 411].
    * **Research Basis**: This "pass-through" behavior is characteristic of money mules. [cite_start]The methodology of tracking accounts that rapidly "reach a balanced state" (money in ≈ money out) is the foundational concept of the **MONLAD** framework[cite: 88, 300, 349].

## 4.0 Technical Specifications

### 4.1 Data Schema
#### `accounts.csv`
| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `account_id` | String | Unique identifier for the account (Primary Key). |
| `initial_risk_rating` | Integer | A baseline risk score (1-5). |
| `created_at` | Timestamp | Date and time of account creation. |

#### `transactions.csv`
| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `transaction_id` | String | Unique identifier for the transaction. |
| `source_account` | String | The `account_id` of the sender. |
| `target_account` | String | The `account_id` of the receiver. |
| `timestamp` | Datetime | Precise date and time of the transaction. |
| `amount` | Float | Transaction value. |
| `is_illicit` | Integer | Ground Truth Label (0 for Normal, 1 for Illicit). |
| `illicit_pattern_type`| String | 'NONE', 'SMURFING', 'LAYERING', 'MULE'. |

### 4.2 Minimum Viable Configuration (for Hackathon)
* **Total Accounts**: 50,000
* **Total Transactions**: 500,000
* **Illicit Transaction Ratio**: 1% (5,000 transactions). [cite_start]This is crucial for simulating the extreme class imbalance challenge cited in nearly all reviewed papers[cite: 50, 312, 370].
* [cite_start]**Illicit Network Structure**: The 5,000 illicit transactions are organized into ~50 distinct laundering networks to test the model's ability to detect coordinated conspiracies, not just individual fraudulent events[cite: 34, 84, 296, 346].