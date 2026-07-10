# models/dataset.py
"""Loads the SynthDataGen CSVs and derives the account feature matrix.

This replaces the Neo4j-backed feature_engineering.FeatureExtractor. The graph
is small enough (10k accounts / 51k transactions) to hold in memory, which
removes the Aura dependency entirely.

transactions.csv references ~363 accounts that accounts.csv does not contain.
Dropping them would discard 57% of the illicit transactions, because the mule
and layering chains deliberately route through them. They are instead admitted
as EXTERNAL accounts with unknown geography, which is also what they represent:
counterparties outside the institution's book.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "SynthDataGen"

FEATURE_COLUMNS = [
    "initial_risk",
    "out_degree",
    "in_degree",
    "total_amount_out",
    "total_amount_in",
    "avg_amount_out",
    "avg_amount_in",
    "transaction_volume",
    "net_flow",
]

# Human-readable copy for each feature, surfaced in the XAI panel so an
# investigator can read the SHAP chart without reading the source.
FEATURE_LABELS = {
    "initial_risk": "KYC Risk Rating",
    "out_degree": "Outgoing Transfers",
    "in_degree": "Incoming Transfers",
    "total_amount_out": "Total Sent",
    "total_amount_in": "Total Received",
    "avg_amount_out": "Avg. Sent",
    "avg_amount_in": "Avg. Received",
    "transaction_volume": "Total Throughput",
    "net_flow": "Net Flow",
}

FEATURE_DEFINITIONS = {
    "initial_risk": "Risk rating (1-10) assigned at onboarding by the KYC process.",
    "out_degree": "Number of transactions sent by this account.",
    "in_degree": "Number of transactions received by this account.",
    "total_amount_out": "Sum of all outgoing transaction amounts.",
    "total_amount_in": "Sum of all incoming transaction amounts.",
    "avg_amount_out": "Mean value of an outgoing transaction.",
    "avg_amount_in": "Mean value of an incoming transaction.",
    "transaction_volume": "Total money moved through the account (in + out).",
    "net_flow": "Received minus sent. Near zero on a high throughput implies pass-through behaviour.",
}


@dataclass(frozen=True)
class Dataset:
    accounts: pd.DataFrame  # indexed by account_id
    transactions: pd.DataFrame
    features: pd.DataFrame  # indexed by account_id, columns == FEATURE_COLUMNS
    graph: nx.DiGraph

    @property
    def account_ids(self) -> list[str]:
        return list(self.features.index)


def _build_features(accounts: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    ids = accounts.index

    out = tx.groupby("source_account")["amount_inr"].agg(["count", "sum", "mean"])
    inn = tx.groupby("target_account")["amount_inr"].agg(["count", "sum", "mean"])

    f = pd.DataFrame(index=ids)
    f["initial_risk"] = accounts["initial_risk_rating"].astype(float)
    f["out_degree"] = out["count"].reindex(ids).fillna(0.0)
    f["in_degree"] = inn["count"].reindex(ids).fillna(0.0)
    f["total_amount_out"] = out["sum"].reindex(ids).fillna(0.0)
    f["total_amount_in"] = inn["sum"].reindex(ids).fillna(0.0)
    f["avg_amount_out"] = out["mean"].reindex(ids).fillna(0.0)
    f["avg_amount_in"] = inn["mean"].reindex(ids).fillna(0.0)
    f["transaction_volume"] = f["total_amount_in"] + f["total_amount_out"]
    f["net_flow"] = f["total_amount_in"] - f["total_amount_out"]

    return f[FEATURE_COLUMNS].astype(float)


def _build_graph(accounts: pd.DataFrame, tx: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(
        (acc_id, {"state": state, "city": city, "account_type": atype})
        for acc_id, state, city, atype in zip(
            accounts.index, accounts["state"], accounts["city"], accounts["account_type"]
        )
    )

    # Parallel edges are collapsed: we keep the aggregate value and count, plus
    # whether *any* leg of the edge was labelled illicit.
    grouped = (
        tx.groupby(["source_account", "target_account"])
        .agg(amount=("amount_inr", "sum"), count=("amount_inr", "size"), illicit=("is_illicit", "max"))
        .reset_index()
    )
    g.add_edges_from(
        (src, dst, {"amount": float(amt), "count": int(cnt), "illicit": bool(ill)})
        for src, dst, amt, cnt, ill in zip(
            grouped["source_account"],
            grouped["target_account"],
            grouped["amount"],
            grouped["count"],
            grouped["illicit"],
        )
    )
    return g


def _admit_external_accounts(accounts: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    """Add placeholder rows for counterparties absent from the account master."""
    seen = set(tx["source_account"]) | set(tx["target_account"])
    missing = sorted(seen - set(accounts.index))
    if not missing:
        return accounts

    external = pd.DataFrame(
        {
            "customer_id": None,
            "pan_card": None,
            "account_type": "External",
            "created_at": None,
            "city": "Unknown",
            "state": "Unknown",
            "branch_ifsc": None,
            # No KYC was ever run on these, so we cannot claim a low rating.
            # Use the population median rather than inventing a clean record.
            "initial_risk_rating": float(accounts["initial_risk_rating"].median()),
        },
        index=pd.Index(missing, name="account_id"),
    )
    return pd.concat([accounts, external])


@functools.lru_cache(maxsize=1)
def load() -> Dataset:
    accounts = pd.read_csv(DATA_DIR / "accounts.csv").set_index("account_id")
    tx = pd.read_csv(DATA_DIR / "transactions.csv")
    # read_csv's parse_dates silently leaves these as object dtype; convert explicitly.
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], format="ISO8601")

    accounts = _admit_external_accounts(accounts, tx)
    features = _build_features(accounts, tx)
    graph = _build_graph(accounts, tx)
    return Dataset(accounts=accounts, transactions=tx, features=features, graph=graph)


if __name__ == "__main__":
    ds = load()
    print(f"accounts     : {len(ds.accounts):,}")
    print(f"transactions : {len(ds.transactions):,}")
    print(f"illicit      : {int(ds.transactions['is_illicit'].sum()):,}")
    print(f"graph        : {ds.graph.number_of_nodes():,} nodes / {ds.graph.number_of_edges():,} edges")
    print()
    print(ds.features.describe().T[["mean", "50%", "max"]])
