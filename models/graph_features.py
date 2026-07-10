# models/graph_features.py
"""Per-account behavioural features for the pattern classifier.

Everything here is derived from transaction *behaviour* -- amounts, counts,
channel mix, timing, counterparty structure. Nothing reads `is_illicit` or
`illicit_pattern_type`. Those columns are labels; using them as inputs would
make the classifier a lookup table that scores 100% and generalises to nothing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .dataset import Dataset

CHANNELS = ["TRANSFER", "PURCHASE", "ATM_WITHDRAWAL"]


def _side_stats(tx: pd.DataFrame, key: str, ids: pd.Index, prefix: str) -> pd.DataFrame:
    g = tx.groupby(key)["amount_inr"]
    out = pd.DataFrame(index=ids)
    out[f"{prefix}_count"] = g.size().reindex(ids).fillna(0.0)
    out[f"{prefix}_total"] = g.sum().reindex(ids).fillna(0.0)
    out[f"{prefix}_mean"] = g.mean().reindex(ids).fillna(0.0)
    out[f"{prefix}_median"] = g.median().reindex(ids).fillna(0.0)
    out[f"{prefix}_max"] = g.max().reindex(ids).fillna(0.0)
    out[f"{prefix}_std"] = g.std().reindex(ids).fillna(0.0)
    return out


def build(ds: Dataset) -> pd.DataFrame:
    tx, ids = ds.transactions, ds.accounts.index

    f = pd.concat(
        [
            _side_stats(tx, "source_account", ids, "out"),
            _side_stats(tx, "target_account", ids, "in"),
        ],
        axis=1,
    )

    f["kyc_risk"] = ds.accounts["initial_risk_rating"].astype(float)
    f["throughput"] = f["in_total"] + f["out_total"]
    f["net_flow"] = f["in_total"] - f["out_total"]

    # Pass-through: a mule or layering hop receives and forwards nearly the same
    # value, so min/max of the two sides approaches 1. A normal account does not.
    hi = np.maximum(f["in_total"], f["out_total"])
    f["passthrough_ratio"] = np.where(hi > 0, np.minimum(f["in_total"], f["out_total"]) / hi, 0.0)

    # Channel mix on the outbound side. Cash-out via ATM is the mule signature.
    out_ch = (
        tx.groupby(["source_account", "transaction_type"]).size().unstack(fill_value=0).reindex(ids).fillna(0.0)
    )
    for c in CHANNELS:
        if c not in out_ch:
            out_ch[c] = 0.0
    out_n = out_ch[CHANNELS].sum(axis=1).replace(0, np.nan)
    for c in CHANNELS:
        f[f"out_frac_{c.lower()}"] = (out_ch[c] / out_n).fillna(0.0)

    # Distinct counterparties vs raw transaction count. Structuring fans money
    # across many distinct peers; a repeat-payment account reuses the same few.
    f["out_peers"] = tx.groupby("source_account")["target_account"].nunique().reindex(ids).fillna(0.0)
    f["in_peers"] = tx.groupby("target_account")["source_account"].nunique().reindex(ids).fillna(0.0)
    f["out_peer_ratio"] = (f["out_peers"] / f["out_count"].replace(0, np.nan)).fillna(0.0)
    f["in_peer_ratio"] = (f["in_peers"] / f["in_count"].replace(0, np.nan)).fillna(0.0)

    # Burstiness: activity compressed into a short window is a laundering tell.
    ts = pd.concat(
        [
            tx[["source_account", "timestamp"]].rename(columns={"source_account": "acc"}),
            tx[["target_account", "timestamp"]].rename(columns={"target_account": "acc"}),
        ]
    )
    agg = ts.groupby("acc")["timestamp"].agg(["min", "max", "size"])
    span = ((agg["max"] - agg["min"]).dt.total_seconds() / 86400.0).reindex(ids).fillna(0.0)
    f["active_days"] = span
    f["txns_per_day"] = (agg["size"].reindex(ids).fillna(0.0) / span.replace(0, np.nan)).fillna(0.0)

    # Reciprocity: layering chains loop value back around. Computed by joining the
    # edge list against its own reverse, which beats a per-node successor scan.
    edges = tx[["source_account", "target_account"]].drop_duplicates()
    rev = set(zip(edges["target_account"], edges["source_account"]))
    recip = edges[[(s, t) in rev for s, t in zip(edges["source_account"], edges["target_account"])]]
    f["reciprocal_edges"] = recip.groupby("source_account").size().reindex(ids).fillna(0.0)

    return f.replace([np.inf, -np.inf], 0.0).fillna(0.0).astype(float)


# A mule's cash-out leg terminates at a merchant or an ATM. The merchant is the
# venue, not a participant -- crediting it with the label would teach the model
# that "receives card spend" means "launderer", and every merchant on the book
# would be flagged.
CASHOUT_TYPES = {"ATM_WITHDRAWAL", "PURCHASE"}


def labels(ds: Dataset) -> pd.Series:
    """Account-level pattern label from the transaction ground truth.

    Used only for training and evaluation, never as a model input.

    Attribution is per-leg, not per-endpoint:
      * cash-out legs (ATM withdrawal, card purchase) credit the SOURCE only --
        all 656 of them terminate at a MERCHANT account.
      * transfer legs credit both ends, since both are moving the value on.

    Only 2 of ~697 flagged accounts touch more than one typology; they take
    whichever accounts for most of their illicit legs.
    """
    ill = ds.transactions[ds.transactions["is_illicit"] == 1]
    cashout = ill["transaction_type"].isin(CASHOUT_TYPES)

    sources = ill[["source_account", "illicit_pattern_type"]].rename(columns={"source_account": "acc"})
    targets = ill.loc[~cashout, ["target_account", "illicit_pattern_type"]].rename(
        columns={"target_account": "acc"}
    )

    both = pd.concat([sources, targets])
    winner = both.groupby("acc")["illicit_pattern_type"].agg(lambda s: s.value_counts().idxmax())
    return winner.reindex(ds.accounts.index).fillna("NONE")
