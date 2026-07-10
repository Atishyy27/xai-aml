# models/classifier.py
"""Supervised pattern classifier: MULE / SMURFING / LAYERING / NONE.

Replaces the GCN, which required DGL (uninstallable here) and was in any case
loaded-but-never-called by the old predictor. A gradient-boosted tree over the
behavioural features in graph_features.py does the same job on this dataset,
trains in seconds on CPU, and -- unlike the `random.choice` it also replaces --
returns the same answer every time you ask.

Run `python -m models.classifier` to train and print a held-out report.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from . import graph_features
from .dataset import ROOT, load

ARTIFACT = ROOT / "artifacts" / "pattern_classifier.joblib"
METRICS = ROOT / "artifacts" / "pattern_metrics.json"

CLASSES = ["NONE", "MULE", "SMURFING", "LAYERING"]
SEED = 42


def train(save: bool = True) -> dict:
    ds = load()
    X = graph_features.build(ds)
    y = graph_features.labels(ds)

    # Stratify: LAYERING is only ~119 of 10,363 accounts, so a random split can
    # otherwise leave the test set with almost none of it.
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=SEED, stratify=y)

    clf = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.1,
        max_depth=6,
        # The classes are wildly imbalanced (93% NONE). Without this the model
        # can hit 93% accuracy by predicting NONE forever.
        class_weight="balanced",
        random_state=SEED,
    )
    clf.fit(X_tr, y_tr)

    pred = clf.predict(X_te)
    report = classification_report(y_te, pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_te, pred, labels=CLASSES)

    print(classification_report(y_te, pred, zero_division=0))
    print("confusion matrix (rows=true, cols=pred), order:", CLASSES)
    print(cm)

    metrics = {
        "classes": CLASSES,
        "confusion_matrix": cm.tolist(),
        "macro_f1": report["macro avg"]["f1-score"],
        "accuracy": report["accuracy"],
        "per_class": {c: report[c] for c in CLASSES if c in report},
        "n_train": len(X_tr),
        "n_test": len(X_te),
        "features": list(X.columns),
    }

    if save:
        ARTIFACT.parent.mkdir(exist_ok=True)
        # Refit on everything now that the honest score is recorded.
        clf_full = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.1, max_depth=6, class_weight="balanced", random_state=SEED
        ).fit(X, y)
        joblib.dump({"model": clf_full, "features": list(X.columns)}, ARTIFACT)
        METRICS.write_text(json.dumps(metrics, indent=2))
        print(f"\nsaved -> {ARTIFACT.name}, {METRICS.name}")

    return metrics


def load_model():
    # This used to call train() when the artifact was missing. That hid a real
    # failure -- a container built without models would quietly spend ~40s
    # training inside the first request instead of failing at boot -- and it
    # meant the served model was never the one whose metrics we published.
    if not ARTIFACT.exists():
        raise FileNotFoundError(
            f"{ARTIFACT} not found. Train first:\n"
            "    python -m models.anomaly && python -m models.classifier"
        )
    return joblib.load(ARTIFACT)


if __name__ == "__main__":
    train()
