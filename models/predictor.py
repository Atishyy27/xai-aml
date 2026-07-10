# models/predictor.py
"""Inference API consumed by the FastAPI backend.

Scoring
-------
risk_score  = 1 - P(NONE) from the gradient-boosted pattern classifier.
              Held-out ROC-AUC 0.99, PR-AUC 0.97, precision@top-1% = 1.00.
pattern     = argmax over the illicit classes, reported only when the account
              clears PATTERN_THRESHOLD. Below that the honest answer is "no
              pattern", not a coin flip.
novelty     = percentile rank of autoencoder reconstruction error. Secondary.

Explanation
-----------
Real SHAP, via shap.TreeExplainer over the classifier. Exact (not sampled) and
a few ms per account, so it is computed on demand rather than precomputed.

Attribution is taken against the NONE class and negated. TreeExplainer returns
one value per (feature, class) in margin space; a feature that pushes the model
*away* from NONE is exactly a feature that raises risk. So
`contribution = -shap[:, NONE]` attributes the displayed risk score itself,
rather than explaining some other quantity and hoping the two agree.

This module previously returned `random.choice(['Smurfing','Mule',...])` for the
pattern -- a fresh draw on every request -- and three hardcoded arithmetic terms
labelled "SHAP simulation". Both are gone.
"""
from __future__ import annotations

import functools

import numpy as np
import pandas as pd
import shap

from . import classifier, graph_features
from .dataset import FEATURE_DEFINITIONS, FEATURE_LABELS, ROOT, load

# The autoencoder's novelty score is precomputed at train time (see
# models/anomaly.py) and read from here. The serving process never imports
# torch -- its ~500MB resident set does not fit the 512MB free tier, and the
# score is static anyway.
NOVELTY_PATH = ROOT / "artifacts" / "novelty.csv"

# Below this, the classifier is not confident enough to name a typology.
PATTERN_THRESHOLD = 0.50

ILLICIT_CLASSES = ("MULE", "SMURFING", "LAYERING")

PATTERN_BLURB = {
    "MULE": "Funds arrive from several sources and leave as cash via ATM withdrawals or card spend.",
    "SMURFING": "Value is fragmented across many counterparties in amounts small enough to stay under reporting thresholds.",
    "LAYERING": "Large transfers are chained through intermediaries to put distance between the money and its origin.",
    "NONE": "Behaviour is consistent with ordinary retail activity.",
}


def _prettify(name: str) -> str:
    return name.replace("_", " ").title()


class _Core:
    """Loaded once, lazily, and shared across requests."""

    def __init__(self) -> None:
        print(" > Loading AI core...")
        self.ds = load()

        bundle = classifier.load_model()
        self.clf = bundle["model"]
        self.feature_names: list[str] = bundle["features"]
        self.X = graph_features.build(self.ds)[self.feature_names]

        self.classes: list[str] = list(self.clf.classes_)
        self.none_idx = self.classes.index("NONE")

        proba = self.clf.predict_proba(self.X)
        self.risk = pd.Series(1.0 - proba[:, self.none_idx], index=self.X.index)
        self.proba = pd.DataFrame(proba, index=self.X.index, columns=self.classes)

        self.explainer = shap.TreeExplainer(self.clf)

        # Merchants and ATMs are counterparties, not account-holders. They belong
        # on the graph (a mule's cash-out edge has to land somewhere) but never in
        # a list of accounts to investigate.
        self.is_customer = self.ds.accounts["account_type"].ne("External").reindex(self.X.index).fillna(False)
        self.customers = self.X.index[self.is_customer]

        # Autoencoder novelty, precomputed (percentile rank). See NOVELTY_PATH.
        if not NOVELTY_PATH.exists():
            raise FileNotFoundError(
                f"{NOVELTY_PATH.name} not found. Train first:\n"
                "    python -m models.anomaly && python -m models.classifier"
            )
        novelty = pd.read_csv(NOVELTY_PATH, index_col="account_id")["novelty"]
        self.novelty = novelty.reindex(self.ds.features.index)

        print(f" > AI core ready: {len(self.X):,} accounts, {len(self.feature_names)} features.")

    def pattern_of(self, account_id: str) -> str:
        if self.risk[account_id] < PATTERN_THRESHOLD:
            return "NONE"
        return str(self.proba.loc[account_id, list(ILLICIT_CLASSES)].idxmax())

    def flagged(self) -> pd.Index:
        """Customer accounts above the threshold -- the investigable population."""
        r = self.risk[self.customers]
        return r[r >= PATTERN_THRESHOLD].index


@functools.lru_cache(maxsize=1)
def core() -> _Core:
    return _Core()


def _metric(name: str, value, unit: str, benchmark, definition: str) -> dict:
    """Metrics travel as raw numbers plus a unit tag.

    They used to be pre-formatted here with f"Rs{x:,.0f}", which produced Western
    thousands grouping while the frontend rendered every other figure with
    en-IN lakh/crore grouping -- so one card read Rs755,771 and the tile beside
    it read Rs7.4Cr. Formatting belongs in exactly one place: frontend/src/lib/format.js.
    """
    return {"name": name, "value": value, "unit": unit, "benchmark": benchmark, "definition": definition}


@functools.lru_cache(maxsize=2048)
def get_prediction_and_explanation(account_id: str) -> dict:
    c = core()
    if account_id not in c.X.index:
        return {"error": f"Account {account_id} not found."}

    risk = float(c.risk[account_id])
    pattern = c.pattern_of(account_id)
    row = c.X.loc[[account_id]]

    # shape (1, n_features, n_classes)
    sv = np.asarray(c.explainer.shap_values(row))[0]
    contrib = -sv[:, c.none_idx]  # pushing away from NONE == pushing toward risk

    order = np.argsort(-np.abs(contrib))[:8]
    feature_contributions = [
        {
            "feature": c.feature_names[i],
            "label": FEATURE_LABELS.get(c.feature_names[i], _prettify(c.feature_names[i])),
            "definition": FEATURE_DEFINITIONS.get(c.feature_names[i], ""),
            "impact": float(contrib[i]),
            "value": float(row.iloc[0, i]),
        }
        for i in order
    ]

    feats = c.ds.features.loc[account_id]
    med = c.ds.features.median()
    metrics = [
        _metric(
            "Risk Score",
            risk,
            "percent",
            PATTERN_THRESHOLD,
            "Classifier probability that this account participates in any illicit typology.",
        ),
        _metric(
            "Novelty",
            float(c.novelty[account_id]),
            "percentile",
            0.99,
            "How unlike the rest of the book this account looks, per the autoencoder. High novelty with low risk can mean an unlabelled typology.",
        ),
        _metric(
            "Total Received",
            float(feats["total_amount_in"]),
            "inr",
            float(med["total_amount_in"]),
            FEATURE_DEFINITIONS["total_amount_in"],
        ),
        _metric(
            "Total Sent",
            float(feats["total_amount_out"]),
            "inr",
            float(med["total_amount_out"]),
            FEATURE_DEFINITIONS["total_amount_out"],
        ),
        _metric(
            "Transactions",
            int(feats["in_degree"] + feats["out_degree"]),
            "count",
            int(med["in_degree"] + med["out_degree"]),
            "Total count of transactions in and out.",
        ),
        _metric("Net Flow", float(feats["net_flow"]), "inr", 0.0, FEATURE_DEFINITIONS["net_flow"]),
    ]

    top = feature_contributions[0]
    direction = "raised" if top["impact"] > 0 else "lowered"
    if pattern == "NONE":
        summary = (
            f"Risk {risk:.0%}. The model does not associate this account with a known laundering typology. "
            f"The strongest single factor was {top['label']}, which {direction} the score."
        )
    else:
        summary = (
            f"Risk {risk:.0%}, consistent with {pattern.title()}. {PATTERN_BLURB[pattern]} "
            f"The strongest single factor was {top['label']}, which {direction} the score."
        )

    return {
        "account_id": account_id,
        "summary": summary,
        "risk_score": risk,
        "pattern_type": pattern,
        "novelty": float(c.novelty[account_id]),
        "class_probabilities": {k: float(v) for k, v in c.proba.loc[account_id].items()},
        "feature_contributions": feature_contributions,
        "metrics": metrics,
    }


def get_top_suspicious_networks(top_n: int = 25) -> list[dict]:
    c = core()
    top = c.risk[c.customers].sort_values(ascending=False).head(top_n)
    return [
        {
            "account_id": acc_id,
            "risk_score": float(risk),
            "pattern_type": c.pattern_of(acc_id),
            "novelty": float(c.novelty[acc_id]),
            "state": str(c.ds.accounts.loc[acc_id, "state"]),
            "total_amount_in": float(c.ds.features.loc[acc_id, "total_amount_in"]),
            "transactions": int(c.ds.features.loc[acc_id, "in_degree"] + c.ds.features.loc[acc_id, "out_degree"]),
        }
        for acc_id, risk in top.items()
    ]


def get_pattern_distribution() -> list[dict]:
    c = core()
    counts = {p: 0 for p in ILLICIT_CLASSES}
    for acc in c.flagged():
        counts[c.pattern_of(acc)] += 1
    return [{"pattern": k.title(), "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if v]


def get_state_distribution() -> dict[str, int]:
    c = core()
    states = c.ds.accounts.loc[c.flagged(), "state"]
    return states[states != "Unknown"].value_counts().to_dict()
