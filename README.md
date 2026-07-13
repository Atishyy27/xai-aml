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

### What laundering actually looks like

Book-level intelligence, computed across all 51,144 transactions rather than scored per
account. It is the context an investigator reads a single case against.

| Panel | Finding |
|---|---|
| **When it happens** (`/statistics/clock`) | Illicit activity is **9.2× over-represented at midnight** and ~8× from 01:00–03:00. Reported as *lift over the licit baseline*, not raw volume — there are 45× more licit transactions, so their diurnal shape would otherwise swamp the signal. |
| **How it moves** (`/statistics/channels`) | Each typology has a clean channel fingerprint. Layering and smurfing are **100% transfer**; a mule is *defined* by the cash-out, so it inverts — **97%** of mule transactions leave as ATM cash or card spend. |
| **What the model weighs** (`/statistics/drivers`) | Global SHAP importance. **Money Throughput moves the score 4.2× more than any other feature** — the model's single strongest lever. |
| **How much it moves** (`/statistics/amounts`) | Median illicit transaction ₹8.3K against ₹91 for licit — a **91× gap**. Over half the retail book sits under ₹100, where laundering essentially never appears. |

Two candidate panels were **cut for failing the evidence bar**, which is the point of
listing them: *shared-IP collusion clusters* (no IP in the book is used by more than one
account, so there is nothing to cluster) and *laundering rings* (314 of the 379 flagged
accounts fall in a single connected component — an artefact of the generator, not a
finding). The amount panel likewise stops short of calling the pattern "structuring":
illicit amounts do cluster where retail traffic does not, but the generator encodes no
reporting threshold, so reading intent into it would be a story about the data rather
than a fact in it.

### The simulator — the part that can prove the model wrong

Every other screen reports on the book the classifier was fitted to, so a reader has no
way to tell a model that *learned* laundering from one that *memorised* 10,000 rows. SHAP
over a frozen dataset explains a result nobody can challenge.

So `/simulate` lets the reader write the book. They choose the size, the crime mix and the
seed; the server generates it, scores it with the **already-trained** classifier, and grades
the predictions against a ground truth that did not exist when the request arrived. Nothing
is retrained. It runs in ~600ms and holds ~300MB, inside the 512MB tier.

On a book it has never seen (3,000 accounts, 15,000 transactions, seed 7):

| | |
|---|---|
| **Caught** (recall) | 96% — 222 of 232 criminals |
| **Correct** (precision) | 91% — 23 false alarms |
| **ROC-AUC** | 0.997 |
| Mule / Layering / Smurfing recall | 100% / 100% / 93% |

The numbers are free to come out badly, and they do: **smurfing is the weak typology**, and
on a book with *zero* crime the model still flags ~0.7% of honest accounts. Both are
rendered as loudly as the wins — a scoreboard that can only go up is not evidence.

The generator mirrors `SynthDataGen/generate_data.py`'s three topologies exactly (fan-in
smurfing, multi-hop layering, cash-out mules terminating at merchants). If it drifted, the
model would be graded on a crime it was never trained to recognise and a poor score would
mean nothing. It generates only the columns the model reads — no names, PANs or IPs — which
is why it needs no Faker and adds nothing to the runtime requirements.

### Explanations

`shap.TreeExplainer` over the classifier — exact, not sampled, a few ms per account.

**Show the working.** A SHAP bar saying "Pass-Through Ratio contributed +2.1" is a number
about a number. So the simulator renders each derived feature as its actual formula from
`models/graph_features.py` with the account's real values substituted — `min(₹9.1L, ₹9.2L) /
max(₹9.1L, ₹9.2L) = 0.996` — above the raw ledger it was computed from. The arithmetic is
checkable by hand. An explanation you cannot check is just a second thing to trust.

Attribution is taken against the `NONE` class and negated: a feature that pushes the
model *away* from `NONE` is exactly a feature that raises risk. So the chart explains the
number on screen rather than some correlated proxy. Values are in classifier margin
(log-odds) units and are **signed** — factors that *lower* risk render on the cool pole
of a diverging axis.

---

## Deployment

The API and the UI deploy separately.

```
Vercel  ──────────────►  Render (or any host)
React UI    CORS         FastAPI + committed models
```

**Why the models are committed.** The runtime artifacts — `pattern_classifier.joblib`,
`novelty.csv`, and the two metrics files — live in `artifacts/` and are checked in.
So the deploy needs no training step, and, crucially, **the serving process never
imports torch**: novelty is a percentile over a static dataset, precomputed at train
time. That drops the resident set from ~600MB to ~265MB, which is what lets it run on
a 512MB free instance. Regenerate the artifacts with the training deps:

```bash
pip install -r requirements-train.txt
python -m models.anomaly && python -m models.classifier
```

**API — Render (native Python).** `render.yaml` pins the config:

| Setting | Value |
|---|---|
| Build | `pip install -r requirements.txt` (torch-free, fast) |
| Start | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Env var `ALLOWED_ORIGINS` | your UI origin, e.g. `https://xai-aml.vercel.app` |

A manually-created service does **not** auto-adopt `render.yaml`; set the two commands
under **Settings** or re-create it via **New → Blueprint**. CORS reads `ALLOWED_ORIGINS`
and allows any `*.vercel.app` by regex; local dev origins are always allowed. The free
instance sleeps after ~15 minutes idle; waking it costs ~50s of container boot, which is
why the axios timeout is 180s (see *Cold starts* below).

A `Dockerfile` is also provided (for HF Spaces or Render-as-Docker): same idea, it
installs the runtime requirements and copies the committed artifacts — no torch, no
training. `.github/workflows/deploy-hf-space.yml` mirrors `main` to a HF Space if you
set `HF_TOKEN` (secret) and `HF_SPACE` (variable); it no-ops until then.

**Keeping it warm — and what actually works.** `.github/workflows/keep-warm.yml` asks
for a `/health` ping every 10 minutes. **GitHub does not honour that**, and it is worth
being precise about how badly: over one 15-hour window the schedule should have fired 89
times and fired **8**, with gaps up to 3.5 hours. GitHub deprioritises high-frequency
cron on shared runners, and no interval you write fixes it — asking for `*/5` gets you
throttled harder, not less. Against a 15-minute sleep threshold, a job that lands every
~2 hours keeps nothing warm. The workflow was measured, not trusted, and it does not do
the job it was written to do.

What does work:

- **`workflow_dispatch`.** A hand-triggered run is *not* throttled — it fires in seconds
  and the instance is warm ~75s later. Kick it before a demo, or just open the link
  yourself two minutes early. This is the reliable path and it is the one to use.
- **An external uptime pinger** (cron-job.org, UptimeRobot, Better Stack — all free, all
  honour 1–5 minute intervals). Point one at `/health` and the instance genuinely never
  sleeps. This is the only *hands-off* fix; it lives outside this repo because it needs
  an account, not a commit.

The scheduled cron is left enabled because a ping that lands is still a ping, and
`workflow_dispatch` shares the file. It is a bonus, not the mechanism. The mechanism for
a cold visitor is the next paragraph: the UI is built to survive the wait.

**UI — Vercel.** Set the project root to `frontend/`. No environment variable is
required: a production build defaults to the deployed API above. Point it elsewhere
by setting `VITE_API_URL` (Vite inlines it at build time), which takes precedence.

The default matters. Previously a production build with no `VITE_API_URL` fell back
to `127.0.0.1:8000` — aiming every visitor's browser at *their own machine* — and the
only symptom was all six panels erroring at once. The deployed bundle shipped that
way. Production now falls back to the real API instead.

Cold starts are visible, not hidden: the free instance sleeps, and the first request
pays ~50s of container wake plus ~25s of model warmup (graph build + SHAP explainer).
The axios timeout is 180s — a 60s timeout aborted the first load of the day before the
API could answer — and the dashboard shows a "waking the server" note after 6s rather
than a spinner that reads as a hang.

`vercel.json` rewrites all paths to `index.html`; without it a refresh on
`/network/ACC1234` 404s, because the router is a `BrowserRouter`.

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
