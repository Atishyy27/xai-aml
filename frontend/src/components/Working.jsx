import React, { useState } from "react";
import { Card } from "./ui/Primitives";
import { formatCompactCurrency, formatCount, formatPercent, patternMeta } from "../lib/format";

/* Show the working.
 *
 * A SHAP bar says "Pass-Through Ratio contributed +2.1". That is a number about a
 * number. It does not tell the reader where 0.98 came from, and an explanation
 * they cannot check is not an explanation -- it is just a second thing to trust.
 *
 * So every derived feature is rendered as its actual formula with this account's
 * real values substituted in. The arithmetic is reproducible by hand from the
 * ledger printed directly above it. These formulas are transcribed from
 * models/graph_features.py and must be changed with it -- a derivation that has
 * quietly drifted from the code is worse than none at all, because it is a lie
 * that looks like a proof.
 */

const inr = (v) => formatCompactCurrency(v);
const num = (v) => (Number.isInteger(v) ? formatCount(v) : v.toFixed(2));

const DERIVATIONS = [
  {
    feature: "throughput",
    formula: "in_total + out_total",
    substitute: (l) => `${inr(l.in_total)} + ${inr(l.out_total)}`,
    result: (l) => inr(l.throughput),
    why: "Total value moved. The model's single strongest lever — laundering is defined by moving money.",
  },
  {
    feature: "passthrough_ratio",
    formula: "min(in_total, out_total) / max(in_total, out_total)",
    substitute: (l) =>
      `${inr(Math.min(l.in_total, l.out_total))} / ${inr(Math.max(l.in_total, l.out_total))}`,
    result: (l) => l.passthrough_ratio.toFixed(3),
    why: "How much of what arrives is forwarded on. Approaches 1.0 for an account that exists to relay value rather than hold it.",
  },
  {
    feature: "out_peer_ratio",
    formula: "out_peers / out_count",
    substitute: (l) => `${num(l.out_peers)} / ${num(l.out_count)}`,
    result: (l) => (l.out_count ? (l.out_peers / l.out_count).toFixed(3) : "0"),
    why: "Distinct recipients per payment sent. Near 1.0 means every payment went somewhere new — money fanned out, not a repeat bill.",
  },
  {
    feature: "txns_per_day",
    formula: "(in_count + out_count) / active_days",
    substitute: (l) => `(${num(l.in_count)} + ${num(l.out_count)}) / ${num(l.active_days)}`,
    result: (l) =>
      l.active_days ? ((l.in_count + l.out_count) / l.active_days).toFixed(2) : "0",
    why: "Transaction rate over the window it was active. Activity compressed into a burst is a laundering tell.",
  },
];

export default function Working({ top }) {
  const [selected, setSelected] = useState(0);
  if (!top?.length) return null;

  const acc = top[selected];
  const l = acc.ledger;
  const predicted = patternMeta(acc.predicted);
  const actual = patternMeta(acc.actual);

  return (
    <Card
      className="working"
      title="Show the working"
      subtitle="Every number the model read for this account, and the arithmetic that produced it"
    >
      <div className="working__picker" role="tablist" aria-label="Top scored accounts">
        {top.slice(0, 8).map((a, i) => (
          <button
            key={a.account_id}
            type="button"
            role="tab"
            aria-selected={i === selected}
            className={`chip ${i === selected ? "is-on" : ""} ${a.correct ? "" : "chip--wrong"}`}
            onClick={() => setSelected(i)}
            title={a.correct ? "Model called this one right" : `Model said ${a.predicted}, truth was ${a.actual}`}
          >
            {a.account_id}
            {!a.correct && <span aria-hidden="true"> ✗</span>}
          </button>
        ))}
      </div>

      {/* The verdict, against a truth the reader generated. A wrong call is
          rendered as loudly as a right one. */}
      <div className={`verdict ${acc.correct ? "verdict--ok" : "verdict--bad"}`}>
        {acc.correct ? (
          <>
            Model scored <b>{formatPercent(acc.risk_score, 0)}</b> and called this{" "}
            <b>{predicted.label}</b>. Ground truth: <b>{actual.label}</b>. Correct.
          </>
        ) : (
          <>
            Model scored <b>{formatPercent(acc.risk_score, 0)}</b> and called this{" "}
            <b>{predicted.label}</b> — but the ground truth is <b>{actual.label}</b>.{" "}
            <b>It got this one wrong.</b>
          </>
        )}
      </div>

      <h4 className="working__head">1 · The ledger</h4>
      <p className="working__lede">
        What this account actually did. Everything below is derived from these numbers and nothing
        else — no label, no lookup.
      </p>
      <dl className="ledger">
        <div>
          <dt>Received</dt>
          <dd>{inr(l.in_total)}</dd>
        </div>
        <div>
          <dt>Sent</dt>
          <dd>{inr(l.out_total)}</dd>
        </div>
        <div>
          <dt>Payments in</dt>
          <dd>{num(l.in_count)}</dd>
        </div>
        <div>
          <dt>Payments out</dt>
          <dd>{num(l.out_count)}</dd>
        </div>
        <div>
          <dt>Distinct recipients</dt>
          <dd>{num(l.out_peers)}</dd>
        </div>
        <div>
          <dt>Days active</dt>
          <dd>{num(l.active_days)}</dd>
        </div>
      </dl>

      <h4 className="working__head">2 · The features, derived</h4>
      <p className="working__lede">
        The formulas from <code>models/graph_features.py</code>, with this account's values
        substituted. Check the arithmetic against the ledger above.
      </p>
      <ul className="derive">
        {DERIVATIONS.map((d) => (
          <li className="derive__row" key={d.feature}>
            <code className="derive__formula">{d.formula}</code>
            <span className="derive__sub">
              = {d.substitute(l)} <b>= {d.result(l)}</b>
            </span>
            <span className="derive__why">{d.why}</span>
          </li>
        ))}
      </ul>

      <h4 className="working__head">3 · What the model did with them</h4>
      <p className="working__lede">
        SHAP attribution, in classifier margin units, against the score above. Warm pushes the
        account toward risk; cool pulls it back.
      </p>
      <ul className="contrib">
        {acc.contributions.map((c) => {
          const max = Math.max(...acc.contributions.map((x) => Math.abs(x.impact)));
          const pct = (Math.abs(c.impact) / max) * 50;
          const up = c.impact > 0;
          return (
            <li className="contrib__row" key={c.feature} title={c.definition}>
              <span className="contrib__label">{c.label}</span>
              <span className="contrib__axis">
                <span
                  className="contrib__bar"
                  style={{
                    // Diverging around a fixed midpoint: the bar grows right for
                    // "raises risk" and left for "lowers", so the sign is legible
                    // from the geometry, not only the hue.
                    left: up ? "50%" : `${50 - pct}%`,
                    width: `${pct}%`,
                    background: up ? "var(--div-pos)" : "var(--div-neg)",
                  }}
                />
              </span>
              <span className="contrib__value num">
                {c.impact > 0 ? "+" : ""}
                {c.impact.toFixed(2)}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
