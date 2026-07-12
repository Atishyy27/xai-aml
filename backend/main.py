# backend/main.py
"""SENTINEL API.

Serves entirely from the in-memory graph built in models/dataset.py. The Neo4j
dependency is gone: the Aura instance in .env no longer resolves, and the graph
(10k nodes / 51k edges) fits comfortably in process. Cypher queries have been
replaced by networkx traversals.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parent.parent))

from models import predictor
from models.dataset import ROOT, load

ARTIFACTS = ROOT / "artifacts"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the models before the first request rather than paying ~20s on it.
    predictor.core()
    yield


app = FastAPI(
    title="SENTINEL API",
    description="Explainable detection of money-laundering networks.",
    version="2.0.0",
    lifespan=lifespan,
)

# 5173 is Vite's default, but Windows reserves 5076-5175 (see
# `netsh interface ipv4 show excludedportrange`), so 5200 is the fallback the
# dev script uses on this machine.
_DEV_PORTS = (5173, 5200, 3000)
_DEV_ORIGINS = [f"http://{h}:{p}" for h in ("localhost", "127.0.0.1") for p in _DEV_PORTS]

# The UI is deployed separately (Vercel), so production origins cannot be known
# at build time. Set ALLOWED_ORIGINS as a comma-separated list in the Space's
# settings; dev origins stay allowed either way so a local UI can hit the
# deployed API while debugging.
_extra = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEV_ORIGINS + _extra,
    # Vercel preview deployments get a fresh subdomain per commit; pinning each
    # one is not workable.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Status"])
def health() -> dict[str, str]:
    """Liveness probe. Deliberately does not touch the models -- it answers
    'is the process up', which is what the container healthcheck asks."""
    return {"status": "ok"}


@app.get("/", tags=["Status"])
def read_root() -> dict[str, Any]:
    ds = load()
    return {
        "status": "operational",
        "accounts": len(ds.accounts),
        "transactions": len(ds.transactions),
    }


@app.get("/model-card", tags=["Status"])
def model_card() -> dict[str, Any]:
    """Held-out metrics for both models. Surfaced in the UI so the numbers on
    screen can be traced to an evaluation rather than taken on trust."""
    def _read(name: str) -> dict:
        p = ARTIFACTS / name
        return json.loads(p.read_text()) if p.exists() else {}

    return {
        "classifier": _read("pattern_metrics.json"),
        "novelty": _read("anomaly_metrics.json"),
        "pattern_threshold": predictor.PATTERN_THRESHOLD,
    }


@app.get("/suspicious-networks", tags=["Networks"])
def suspicious_networks(limit: int = Query(25, ge=1, le=200)) -> list[dict[str, Any]]:
    return predictor.get_top_suspicious_networks(top_n=limit)


@app.get("/network/{account_id}", tags=["Networks"])
def network(account_id: str, hops: int = Query(1, ge=1, le=2)) -> dict[str, Any]:
    ds = load()
    g = ds.graph
    if account_id not in g:
        raise HTTPException(404, f"Account {account_id} not found.")

    # Undirected ego graph: money laundering neighbourhoods matter in both
    # directions, and the old Cypher used an undirected -[:TRANSFER*1..n]- match.
    import networkx as nx

    ego = nx.ego_graph(g.to_undirected(as_view=True), account_id, radius=hops)
    nodes = list(ego.nodes())

    c = predictor.core()
    node_payload = [
        {
            "id": n,
            "risk_score": float(c.risk[n]) if n in c.risk.index else 0.0,
            "pattern_type": c.pattern_of(n) if n in c.risk.index else "NONE",
            "state": str(ds.accounts.loc[n, "state"]) if n in ds.accounts.index else "Unknown",
            "is_focus": n == account_id,
        }
        for n in nodes
    ]

    seen = set(nodes)
    edge_payload = [
        {
            "source": u,
            "target": v,
            "amount": float(d["amount"]),
            "count": int(d["count"]),
            "illicit": bool(d["illicit"]),
        }
        # Read directed edges off the original graph, restricted to the ego set.
        for u, v, d in g.edges(nbunch=nodes, data=True)
        if u in seen and v in seen
    ]

    return {"network_id": account_id, "graph": {"nodes": node_payload, "edges": edge_payload}}


@app.get("/account/{account_id}/explanation", tags=["XAI"])
def explanation(account_id: str) -> dict[str, Any]:
    result = predictor.get_prediction_and_explanation(account_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return {"explanation": result}


@app.get("/network/{account_id}/transactions", tags=["Networks"])
def transactions(
    account_id: str,
    illicit_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    ds = load()
    if account_id not in ds.accounts.index:
        raise HTTPException(404, f"Account {account_id} not found.")

    tx = ds.transactions
    mine = tx[(tx["source_account"] == account_id) | (tx["target_account"] == account_id)]
    if illicit_only:
        # The old endpoint was named "illicit-transactions" but never filtered.
        mine = mine[mine["is_illicit"] == 1]
    mine = mine.sort_values("timestamp", ascending=False).head(limit)

    return {
        "transactions": [
            {
                "id": r.transaction_id,
                "from": r.source_account,
                "to": r.target_account,
                "amount": float(r.amount_inr),
                "date": r.timestamp.isoformat(),
                "type": r.transaction_type,
                "illicit": bool(r.is_illicit),
                "direction": "in" if r.target_account == account_id else "out",
            }
            for r in mine.itertuples()
        ]
    }


@app.get("/statistics/patterns", tags=["Statistics"])
def pattern_statistics() -> list[dict[str, Any]]:
    return predictor.get_pattern_distribution()


@app.get("/statistics/heatmap", tags=["Statistics"])
def heatmap() -> dict[str, int]:
    return predictor.get_state_distribution()


@app.get("/statistics/summary", tags=["Statistics"])
def summary() -> dict[str, Any]:
    c = predictor.core()
    ds = load()
    flagged = c.flagged()
    monitored = int(c.is_customer.sum())
    return {
        "accounts_monitored": monitored,
        "accounts_flagged": int(len(flagged)),
        "flagged_rate": float(len(flagged) / monitored),
        "transactions_analysed": int(len(ds.transactions)),
        "value_at_risk": float(ds.features.loc[flagged, "total_amount_in"].sum()),
        "high_novelty": int((c.novelty[c.customers] >= 0.99).sum()),
    }


@app.get("/statistics/clock", tags=["Statistics"])
def clock() -> list[dict[str, Any]]:
    """Illicit activity by hour of day, as a lift over the licit baseline.
    Laundering concentrates in the small hours: ~8-9x lift between 00:00 and 03:00."""
    return predictor.get_hourly_profile()


@app.get("/statistics/channels", tags=["Statistics"])
def channels() -> list[dict[str, Any]]:
    """Each typology's channel fingerprint. Layering and smurfing are pure
    transfer; a mule is defined by its cash-out, so it inverts (ATM + card)."""
    return predictor.get_channel_mix()


@app.get("/statistics/amounts", tags=["Statistics"])
def amounts() -> dict[str, Any]:
    """Transaction size, illicit vs licit, in log-spaced bands."""
    return predictor.get_amount_profile()


@app.get("/statistics/drivers", tags=["XAI"])
def drivers(limit: int = Query(8, ge=3, le=26)) -> list[dict[str, Any]]:
    """Global SHAP importance -- what the model weighs across the whole book, as
    opposed to /account/{id}/explanation, which says why one account scored."""
    return predictor.get_risk_drivers(top_n=limit)


class SimulationRequest(BaseModel):
    """Bounds are enforced here AND clamped in the simulator. Belt and braces on
    purpose: these numbers decide how much memory a request allocates, and the
    instance has 512MB with no swap -- an OOM does not fail the request, it kills
    the process for everyone."""

    accounts: int = Field(3000, ge=200, le=6000)
    transactions: int = Field(15000, ge=500, le=30000)
    smurfing_ops: int = Field(8, ge=0, le=40)
    layering_chains: int = Field(12, ge=0, le=60)
    mule_ops: int = Field(12, ge=0, le=60)
    seed: int = Field(7, ge=0, le=999_999)


# One simulation at a time. Each holds a whole book plus its feature matrix in
# memory; two concurrent runs on the free instance is how you OOM the process.
# Queue rather than reject -- the run takes ~2s, so waiting is cheaper than a
# 503 the user has to understand.
_sim_lock = asyncio.Lock()


@app.post("/simulate", tags=["Simulator"])
async def simulate(req: SimulationRequest) -> dict[str, Any]:
    """Generate a book the model has never seen, score it, and grade the result
    against the ground truth we just wrote.

    Nothing is retrained. The classifier fitted to SynthDataGen's book is asked to
    find crime in a book that did not exist when the request arrived, and the
    precision/recall that come back are real -- including when they are bad.
    """
    from models.simulator import SimConfig

    cfg = SimConfig(**req.model_dump())

    async with _sim_lock:
        # Generation + feature engineering + SHAP is CPU-bound and blocking. Run it
        # off the event loop, or a 2s simulation freezes /health and Render's
        # health check starts failing mid-demo.
        started = time.perf_counter()
        result = await asyncio.to_thread(predictor.simulate, cfg)
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)

    return result


@app.get("/accounts/search", tags=["Networks"])
def search(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    c = predictor.core()
    q_up = q.upper()
    hits = [a for a in c.customers if q_up in a.upper()][:limit]
    return [{"account_id": a, "risk_score": float(c.risk[a]), "pattern_type": c.pattern_of(a)} for a in hits]
