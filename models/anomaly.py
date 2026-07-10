# models/anomaly.py
"""Unsupervised novelty scoring via an autoencoder.

This is a SECONDARY signal. The primary risk score comes from classifier.py,
which reaches 0.99 held-out ROC-AUC. Do not confuse the two.

The architecture is the one from train_autoencoder.py (9 -> 6 -> 3 -> 6 -> 9).
What changed:

  * It is trained on features that match the current dataset. The shipped
    autoencoder.pth and scaler.pkl were fit on a 50k-account feature matrix that
    does not correspond to any file still in the repo -- recomputing the features
    for the 10k real accounts reproduced the CSV's amount columns 0% of the time.

  * Amounts are log-compressed before scaling. net_flow spans [-1.3e6, 1.3e6];
    with a plain StandardScaler the reconstruction error is dominated by a
    handful of whales and every other account scores identically zero.

Training is unsupervised: every account goes in, labels are never consulted.

A caution worth writing down, because it is counter-intuitive and it bit this
model during development: reconstruction error is a WEAK global ranker here.
Trained to convergence the AE reconstructs the frauds about as well as everyone
else, and ROC-AUC sits near 0.5. An earlier under-trained checkpoint scored
0.65, which looks better but is only an artefact of stopping early -- picking
that checkpoint would be tuning on the evaluation metric.

What the AE is genuinely good for is its extreme tail: the top 1% of
reconstruction error is ~10x enriched for known-illicit accounts. So it is
surfaced as a "novelty" flag -- an account whose behaviour resembles nothing
else on the book, which is how a typology nobody has labelled yet would first
appear. It is not, and is not presented as, the detector.

Run `python -m models.anomaly` to train and evaluate.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from .dataset import FEATURE_COLUMNS, ROOT, load

ARTIFACT_DIR = ROOT / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "autoencoder.pth"
SCALER_PATH = ARTIFACT_DIR / "scaler.pkl"
METRICS_PATH = ARTIFACT_DIR / "anomaly_metrics.json"

# Novelty is a percentile over a static dataset, so it never changes at serving
# time. We compute it here, once, and the API reads this file -- which lets the
# running process avoid importing torch at all (torch's ~500MB resident set does
# not fit the 512MB free tier). See models/predictor.py.
NOVELTY_PATH = ARTIFACT_DIR / "novelty.csv"

SEED = 42

# Heavy-tailed money columns. initial_risk (1-10) and the degrees are already
# on a sane scale and are left alone.
LOG_COLUMNS = [
    "total_amount_out",
    "total_amount_in",
    "avg_amount_out",
    "avg_amount_in",
    "transaction_volume",
]
SIGNED_LOG_COLUMNS = ["net_flow"]  # can be negative


class Autoencoder(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 6), nn.ReLU(), nn.Linear(6, 3))
        self.decoder = nn.Sequential(nn.Linear(3, 6), nn.ReLU(), nn.Linear(6, input_dim))

    def forward(self, x):
        return self.decoder(self.encoder(x))


def compress(df: pd.DataFrame) -> np.ndarray:
    """log-compress heavy tails; returns a plain float array in FEATURE_COLUMNS order."""
    out = df[FEATURE_COLUMNS].copy()
    for c in LOG_COLUMNS:
        out[c] = np.log1p(out[c].clip(lower=0))
    for c in SIGNED_LOG_COLUMNS:
        out[c] = np.sign(out[c]) * np.log1p(out[c].abs())
    return out.to_numpy(dtype=np.float64)


def reconstruction_error(model: Autoencoder, X: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        rec = model(torch.FloatTensor(X)).numpy()
    return ((rec - X) ** 2).mean(axis=1)


def train(epochs: int = 120, batch_size: int = 512, lr: float = 3e-3, save: bool = True) -> dict:
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    ds = load()
    raw = compress(ds.features)
    scaler = StandardScaler().fit(raw)
    X = scaler.transform(raw).astype(np.float32)

    model = Autoencoder(X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    crit = nn.MSELoss()
    Xt = torch.from_numpy(X)
    n = len(X)

    model.train()
    for epoch in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, batch_size):
            xb = Xt[perm[i : i + batch_size]]
            loss = crit(model(xb), xb)
            opt.zero_grad()
            loss.backward()
            opt.step()
        if (epoch + 1) % 40 == 0:
            print(f"epoch {epoch + 1:4d}/{epochs}  loss={loss.item():.4f}")
    model.eval()

    err = reconstruction_error(model, X)

    # Honest evaluation: never used during training.
    ill = ds.transactions[ds.transactions["is_illicit"] == 1]
    flagged = set(ill["source_account"]) | set(ill["target_account"])
    y = ds.features.index.isin(flagged).astype(int)
    auc = float(roc_auc_score(y, err))

    top1pct = err >= np.percentile(err, 99)
    precision_at_1pct = float(y[top1pct].mean())
    base_rate = float(y.mean())

    print(f"\nROC-AUC (novelty vs is_illicit) : {auc:.3f}   <- expected to be weak; see module docstring")
    print(f"precision @ top 1% of novelty   : {precision_at_1pct:.3f}  (base rate {base_rate:.3f})")
    print(f"lift in the tail                : {precision_at_1pct / base_rate:.1f}x   <- this is what it is for")

    metrics = {
        "roc_auc": auc,
        "precision_at_1pct": precision_at_1pct,
        "base_rate": base_rate,
        "lift": precision_at_1pct / base_rate,
        "n_accounts": int(len(y)),
        "n_flagged": int(y.sum()),
        "final_loss": float(loss.item()),
    }

    # The percentile rank the API serves. Computed over every account, in the
    # dataset's own index, so predictor.py can just reindex it.
    novelty = pd.Series(err, index=ds.features.index).rank(pct=True)

    if save:
        ARTIFACT_DIR.mkdir(exist_ok=True)
        torch.save(model.state_dict(), MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2))
        novelty.rename("novelty").to_csv(NOVELTY_PATH, index_label="account_id")
        print(f"\nsaved -> {MODEL_PATH.name}, {SCALER_PATH.name}, {METRICS_PATH.name}, {NOVELTY_PATH.name}")

    return metrics


if __name__ == "__main__":
    train()
