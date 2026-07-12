# models/simulator.py
"""Generate a fresh crime book at request time, then score it with the model
that was trained on a *different* book.

Why this exists
---------------
A dashboard over a fixed dataset cannot be argued with. The model's numbers look
good, and the reader has no way to find out whether that is because it learned
what laundering looks like or because it memorised 10,000 rows. SHAP over a
frozen book explains a result nobody can challenge.

So: let the reader invent the book. They choose the size, the crime mix, and the
seed; we generate it, score it with the already-trained classifier, and grade the
predictions against the ground truth we just wrote. The classifier has never seen
any of it. Precision and recall come out live -- and can come out badly, which is
the point. It is the difference between a demo and a claim.

What is generated
-----------------
Only the columns the model actually reads: who paid whom, when, how much, over
which channel, plus the account's KYC rating. Names, PANs, IPs, remarks and
cities exist in SynthDataGen's CSVs but no feature touches them, so generating
them would cost time and memory to produce data nothing consumes. This is also
why the simulator needs no Faker -- and therefore adds nothing to the runtime
requirements, which is what keeps the 512MB instance viable.

The three typologies mirror SynthDataGen/generate_data.py exactly -- fan-in
smurfing, multi-hop layering chains, and cash-out mules that terminate at
merchants. If they drifted from it, the model would be scored against a crime it
was never trained to recognise, and a poor result would say nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .dataset import Dataset, _build_features, _build_graph

# The instance has 512MB and no swap, and a request that OOMs takes the whole
# process down -- not just that request. These ceilings are what one book plus
# its feature matrix fits in alongside the resident model. The base book (10k
# accounts / 51k transactions) sits above them by design: the sandbox is meant to
# be cheap enough to re-run on a slider drag.
MAX_ACCOUNTS = 6_000
MAX_TRANSACTIONS = 30_000

# The generator draws states from the real book's vocabulary rather than
# inventing them, so the map in the UI keeps working on a simulated book.
STATES = [
    "Maharashtra", "Uttar Pradesh", "Karnataka", "Tamil Nadu", "Gujarat", "Rajasthan",
    "West Bengal", "Kerala", "Telangana", "Bihar", "Madhya Pradesh", "Punjab", "Haryana",
    "Odisha", "Assam", "Jharkhand", "Chhattisgarh", "Uttarakhand", "Himachal Pradesh",
    "Goa", "Tripura", "Manipur", "Meghalaya", "Nagaland", "Sikkim", "Arunachal Pradesh",
]

# The window the base book covers. Kept identical because two features read it:
# active_days and txns_per_day are rates over the observed span, and a book
# compressed into a different window would shift them for reasons that have
# nothing to do with crime.
START = pd.Timestamp("2025-08-18")
DAYS = 22


@dataclass(frozen=True)
class SimConfig:
    accounts: int = 3_000
    transactions: int = 15_000
    smurfing_ops: int = 8
    layering_chains: int = 12
    mule_ops: int = 12
    seed: int = 7

    def clamp(self) -> "SimConfig":
        """Clamp rather than reject.

        A slider that errors at its own maximum is a bug report waiting to happen,
        and the caller gets the applied config echoed back in the response, so a
        clamp is visible rather than silent.
        """
        return SimConfig(
            accounts=int(np.clip(self.accounts, 200, MAX_ACCOUNTS)),
            transactions=int(np.clip(self.transactions, 500, MAX_TRANSACTIONS)),
            smurfing_ops=int(np.clip(self.smurfing_ops, 0, 40)),
            layering_chains=int(np.clip(self.layering_chains, 0, 60)),
            mule_ops=int(np.clip(self.mule_ops, 0, 60)),
            seed=int(self.seed) % (2**31),
        )


def _accounts_frame(cfg: SimConfig, rng: np.random.Generator) -> pd.DataFrame:
    ids = [f"SIM{1001 + i}" for i in range(cfg.accounts)]
    return pd.DataFrame(
        {
            # 'External' is reserved for merchants, which are counterparties rather
            # than account-holders and must never enter the investigable population.
            "account_type": rng.choice(["Savings", "Current"], size=cfg.accounts),
            "initial_risk_rating": rng.integers(1, 6, size=cfg.accounts),
            "state": rng.choice(STATES, size=cfg.accounts),
            "city": "Unknown",
        },
        index=pd.Index(ids, name="account_id"),
    )


def _normal_transactions(cfg: SimConfig, ids: np.ndarray, rng: np.random.Generator) -> pd.DataFrame:
    """The licit baseline. Vectorised -- a Python loop over 30k rows is the
    difference between a slider that responds and one that times out."""
    n = cfg.transactions

    src = rng.integers(0, len(ids), size=n)
    dst = rng.integers(0, len(ids), size=n)
    # A self-payment is not a transaction. Rotating the collisions is cheaper than
    # rejection-sampling and unbiased enough for a baseline.
    dst = np.where(src == dst, (dst + 1) % len(ids), dst)

    # 70% inside business hours, matching the base generator. This is what makes
    # the small-hours concentration of crime a *finding* rather than an artefact:
    # the licit baseline has a daytime shape, so illicit traffic stands out
    # against it. Flatten this and the /statistics/clock lift collapses.
    business = rng.random(n) < 0.7
    hour = np.where(business, rng.integers(9, 18, n), rng.choice([*range(0, 9), *range(18, 24)], n))

    ts = (
        START
        + pd.to_timedelta(rng.integers(0, DAYS, n), unit="D")
        + pd.to_timedelta(hour, unit="h")
        + pd.to_timedelta(rng.integers(0, 60, n), unit="m")
    )

    # Lognormal(4.5, 1.8), as in the base book -- retail spend is heavy-tailed, and
    # a normal distribution here would make every large transfer look criminal.
    amount = np.round(rng.lognormal(4.5, 1.8, n), 2) + 1.0

    return pd.DataFrame(
        {
            "source_account": ids[src],
            "target_account": ids[dst],
            "timestamp": ts,
            "amount_inr": amount,
            "transaction_type": rng.choice(["TRANSFER", "PURCHASE"], size=n),
            "is_illicit": 0,
            "illicit_pattern_type": "NONE",
        }
    )


def _smurfing(cfg: SimConfig, ids: np.ndarray, rng: np.random.Generator) -> list[dict]:
    """Fan-in: many small deposits converge on one collector, inside a short window."""
    rows = []
    for _ in range(cfg.smurfing_ops):
        collector = ids[rng.integers(len(ids))]
        smurfs = rng.choice(ids[ids != collector], size=min(20, len(ids) - 1), replace=False)
        t0 = START + pd.Timedelta(days=int(rng.integers(0, max(1, DAYS - 3))))

        for _ in range(int(rng.integers(20, 51))):
            rows.append(
                {
                    "source_account": rng.choice(smurfs),
                    "target_account": collector,
                    "timestamp": t0 + pd.Timedelta(hours=int(rng.integers(0, 72)), minutes=int(rng.integers(0, 60))),
                    "amount_inr": round(float(rng.uniform(5_000, 49_000)), 2),
                    "transaction_type": "TRANSFER",
                    "is_illicit": 1,
                    "illicit_pattern_type": "SMURFING",
                }
            )
    return rows


def _layering(cfg: SimConfig, ids: np.ndarray, rng: np.random.Generator) -> list[dict]:
    """A chain: value hops account to account, shedding 1-2% a hop, to put
    distance between the money and its origin."""
    rows = []
    for _ in range(cfg.layering_chains):
        length = int(rng.integers(4, 9))
        if length > len(ids):
            continue
        chain = rng.choice(ids, size=length, replace=False)
        amount = float(rng.uniform(200_000, 1_000_000))
        t0 = START + pd.Timedelta(days=int(rng.integers(0, max(1, DAYS - 2))))

        for i in range(length - 1):
            amount = round(amount * float(rng.uniform(0.98, 0.99)), 2)
            rows.append(
                {
                    "source_account": chain[i],
                    "target_account": chain[i + 1],
                    "timestamp": t0 + pd.Timedelta(hours=i * 2),
                    "amount_inr": amount,
                    "transaction_type": "TRANSFER",
                    "is_illicit": 1,
                    "illicit_pattern_type": "LAYERING",
                }
            )
    return rows


def _mules(cfg: SimConfig, ids: np.ndarray, rng: np.random.Generator) -> list[dict]:
    """One large deposit in, then drained to cash via ATM and card spend.

    The cash-out legs terminate at MERCHANT accounts, which are admitted to the
    graph as External. That is not cosmetic: crediting the merchant with the MULE
    label is the exact bug that once taught the model 'receives card spend' means
    'launderer' and flagged 363 shopkeepers.
    """
    rows = []
    for _ in range(cfg.mule_ops):
        mule = ids[rng.integers(len(ids))]
        payer = ids[rng.integers(len(ids))]
        if payer == mule:
            continue
        t0 = START + pd.Timedelta(days=int(rng.integers(0, max(1, DAYS - 1))))
        incoming = round(float(rng.uniform(100_000, 500_000)), 2)

        rows.append(
            {
                "source_account": payer,
                "target_account": mule,
                "timestamp": t0,
                "amount_inr": incoming,
                "transaction_type": "TRANSFER",
                "is_illicit": 1,
                "illicit_pattern_type": "MULE",
            }
        )

        cashed = 0.0
        for _ in range(int(rng.integers(20, 51))):
            if cashed >= incoming * 0.95:
                break
            amount = round(float(rng.uniform(500, 10_000)), 2)
            rows.append(
                {
                    "source_account": mule,
                    "target_account": f"MERCHANT{int(rng.integers(1, 501))}",
                    "timestamp": t0 + pd.Timedelta(minutes=int(rng.integers(5, 241))),
                    "amount_inr": amount,
                    "transaction_type": str(rng.choice(["ATM_WITHDRAWAL", "PURCHASE"])),
                    "is_illicit": 1,
                    "illicit_pattern_type": "MULE",
                }
            )
            cashed += amount
    return rows


def generate(cfg: SimConfig) -> tuple[Dataset, SimConfig]:
    """Build a complete, self-consistent book. Deterministic in cfg.seed, so a
    result the reader finds surprising can be handed to someone else and
    reproduced exactly."""
    cfg = cfg.clamp()
    rng = np.random.default_rng(cfg.seed)

    accounts = _accounts_frame(cfg, rng)
    ids = accounts.index.to_numpy()

    tx = pd.concat(
        [
            _normal_transactions(cfg, ids, rng),
            pd.DataFrame(_smurfing(cfg, ids, rng) + _layering(cfg, ids, rng) + _mules(cfg, ids, rng)),
        ],
        ignore_index=True,
    )
    tx["transaction_id"] = [f"SIMTXN{i}" for i in range(len(tx))]

    # Merchants are referenced by the cash-out legs but were never issued an
    # account row. dataset.load() admits such counterparties as External; the
    # simulator must do the same, or graph_features would reindex them away and
    # every mule would lose its cash-out.
    missing = pd.Index(tx["target_account"].unique()).difference(accounts.index)
    if len(missing):
        accounts = pd.concat(
            [
                accounts,
                pd.DataFrame(
                    {
                        "account_type": "External",
                        "initial_risk_rating": 3,
                        "state": "Unknown",
                        "city": "Unknown",
                    },
                    index=pd.Index(missing, name="account_id"),
                ),
            ]
        )

    ds = Dataset(
        accounts=accounts,
        transactions=tx,
        features=_build_features(accounts, tx),
        graph=_build_graph(accounts, tx),
    )
    return ds, cfg
