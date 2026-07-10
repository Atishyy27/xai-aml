---
title: SENTINEL AML API
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

<!-- The YAML block above configures the Hugging Face Space (Docker SDK, port
     7860). It is required by HF and harmless on GitHub. -->

# Project SENTINEL 🛡️
### An Explainable AI Framework for Detecting and Dismantling Financial Laundering Networks

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.8-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![SHAP](https://img.shields.io/badge/SHAP-0.48-8A2BE2)](https://shap.readthedocs.io/)

SENTINEL flags accounts involved in money laundering, names the typology, and shows an
investigator *why* — with real SHAP attribution over the model that produced the score.

Everything runs offline from the CSVs in `SynthDataGen/`. No database to provision.

---

## Quick start

```bash
pip install -r requirements.txt

# Train both models (~1 min on CPU). Writes to artifacts/.
python -m models.anomaly
python -m models.classifier

# API on :8000  (first request warms the models, ~25s)
uvicorn backend.main:app --reload

# UI on :5200
cd frontend && npm install && npm run dev
```

> **Port note.** Vite's default 5173 falls inside a Windows reserved range on some
> machines (`netsh interface ipv4 show excludedportrange protocol=tcp`). The dev
> script uses 5200; the API allows both origins.

---

## How it works

```
SynthDataGen/*.csv
      │
      ├─ models/dataset.py          in-memory graph (10,363 nodes / 50,917 edges)
      │                              + the 9 aggregate account features
      │
      ├─ models/graph_features.py   26 behavioural features per account
      │                              (channel mix, pass-through ratio, burstiness,
      │                               counterparty spread, reciprocity)
      │
      ├─ models/classifier.py       ← risk score + typology       [PRIMARY]
      ├─ models/anomaly.py          ← novelty score               [SECONDARY]
      └─ models/predictor.py        ← inference + SHAP, consumed by backend/
```

### Risk score and typology — the primary signal

A gradient-boosted tree (`HistGradientBoostingClassifier`) over the 26 behavioural
features, predicting `NONE | MULE | SMURFING | LAYERING`. The displayed risk score is
`1 − P(NONE)`.

Held-out (25% stratified split, 2,591 accounts):

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| NONE | 1.00 | 1.00 | 1.00 | 2507 |
| MULE | 0.82 | 0.90 | 0.86 | 10 |
| SMURFING | 0.82 | 0.82 | 0.82 | 44 |
| LAYERING | 0.93 | 0.90 | 0.92 | 30 |

**Macro-F1 0.90**, accuracy 0.993. As a binary detector the risk score reaches
**ROC-AUC 0.99**, PR-AUC 0.97, precision@top-1% = 1.00.

MULE's support is only 10 accounts in the test split, so its per-class numbers are
noisy — read them with that in mind.

### Novelty — the secondary signal

The autoencoder (9→6→3→6→9) from the original design, retrained on features that match
the current data. It is **not** the detector, and the code says so.

Trained to convergence, reconstruction error is a weak global ranker: ROC-AUC **0.49**.
Autoencoders reconstruct anomalies about as well as everything else once they have the
capacity. What it *is* good for is the tail — the top 1% of reconstruction error is
**10.2× enriched** for known-illicit accounts, which is how an unlabelled typology would
first surface. It ships as a "novelty" column, not a risk score.

An earlier under-trained checkpoint scored 0.65 AUC. Shipping that checkpoint would have
been tuning on the evaluation metric, so it was not shipped.

### Explanations

`shap.TreeExplainer` over the classifier — exact, not sampled, a few ms per account.

Attribution is taken against the `NONE` class and negated: a feature that pushes the
model *away* from `NONE` is exactly a feature that raises risk. So the chart explains the
number on screen rather than some correlated proxy. Values are in classifier margin
(log-odds) units and are **signed** — factors that *lower* risk render on the cool pole
of a diverging axis.

---

## Deployment

The API and the UI deploy separately.

```
Vercel  ──────────────►  Hugging Face Space
React UI    CORS         FastAPI, port 7860
                         models baked in at build
```

**API — Hugging Face Spaces (Docker SDK).** `Dockerfile` trains both models during
the build, so the image is self-contained and its metrics are the ones above. Set
one variable in the Space settings:

| Variable | Value |
|---|---|
| `ALLOWED_ORIGINS` | `https://<your-app>.vercel.app` (comma-separated for several) |

Any `*.vercel.app` origin is allowed by regex so preview deployments work without
re-pinning each commit's subdomain. Local dev origins are always allowed.

**UI — Vercel.** Set the project root to `frontend/`. One required variable:

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://<user>-<space>.hf.space` |

Vite inlines this at build time. A production build without it falls back to
`127.0.0.1:8000` — pointing every visitor's browser at their own machine — so the
bundle logs a loud console error rather than failing as six simultaneous panel
errors. `vercel.json` rewrites all paths to `index.html`; without it a refresh on
`/network/ACC1234` 404s, because the router is a `BrowserRouter`.

**Pushing to the Space.** `.github/workflows/deploy-hf-space.yml` mirrors `main` to
the Space on every push, so a normal `git push origin main` redeploys. It needs two
one-time settings under **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `HF_TOKEN` | a write token from huggingface.co/settings/tokens |
| Variable | `HF_SPACE` | `owner/space`, e.g. `Atishyy27/xai-aml` |

Until both are set the workflow no-ops with a warning rather than failing. To push
by hand instead:

```bash
git remote add space https://<user>:<token>@huggingface.co/spaces/<user>/<space>
git push --force space main
```

Notes: the free tier sleeps, and a cold start pays container boot plus ~25s of
model warmup, which is why the axios timeout is 60s. `torch` installs from the CPU
wheel index — the default Linux wheel is a ~2.5GB CUDA build, to run one 9→6→3→6→9
MLP that is scored once at startup.

---

## Design notes

**Labels are per-leg, not per-endpoint.** A mule's cash-out leg terminates at a merchant.
Crediting both endpoints with the `MULE` label taught the model that "receives card spend"
means "launderer" — 363 of the 403 accounts it called mules were merchants, and three of
them ranked in the top 15 most-suspicious. Cash-out legs (ATM withdrawal, card purchase)
now credit the source only. Merchants stay on the graph as counterparties but never enter
the investigable population.

**Nothing in the feature set reads `is_illicit` or `illicit_pattern_type`.** Those are
labels. They are used for training, for evaluation, and to mark known-bad edges red in the
graph — never as model inputs.

**The frontend formats; the backend doesn't.** Metrics travel as `{value, unit}`. When the
API pre-formatted currency with Python's `f"{x:,.0f}"`, one card read `₹755,771` while the
tile beside it read `₹7.4Cr`.

**Charts follow the data's job.** Magnitude → sequential single hue. Polarity (SHAP) →
diverging, warm/cool poles, neutral midpoint. Identity (typology) → a fixed categorical
slot per typology, so filtering never repaints the survivors. Every chart has a table-view
twin, and the palette was validated for colour-vision deficiency rather than eyeballed.

---

## Project structure

```
backend/main.py            FastAPI app — serves from the in-memory graph
models/dataset.py          CSV → graph + features
models/graph_features.py   behavioural features + ground-truth labels
models/classifier.py       typology classifier (train + evaluate)
models/anomaly.py          autoencoder novelty (train + evaluate)
models/predictor.py        inference API + SHAP
frontend/src/lib/          formatting + data-fetching hook
frontend/src/components/   UI, charts under charts/, primitives under ui/
SynthDataGen/              generator + accounts.csv + transactions.csv
```

## Removed from the Neo4j-backed design

The following were deleted — none were on any runtime path:

- `models/feature_engineering.py`, `models/train_gcn.py` — imported `neo4j` / `dgl`
- `models/train_autoencoder.py` — superseded by `models/anomaly.py`
- `autoencoder.pth`, `gcn.pth`, `scaler.pkl`, `account_features.csv` at the repo root —
  fit on a 50,000-account matrix that matched no file in the repo. Recomputing those
  features for the 10,000 real accounts reproduced the CSV's amount columns **0%** of the
  time. The live artifacts are trained into `artifacts/` at build time.
- `frontend/public/geoBoundaries-IND-ADM3.topojson` (12.7 MB) — not referenced; the
  choropleth loads `india-states.json`.

The GCN was loaded on import and never called; `models/classifier.py` replaces it. The
Aura instance in `.env` no longer resolves, and `neo4j/` stays gitignored.
