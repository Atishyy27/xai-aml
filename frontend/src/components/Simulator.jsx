import React, { useCallback, useEffect, useRef, useState } from "react";
import { runSimulation } from "../api";
import { Card, ErrorNote, Empty } from "./ui/Primitives";
import { formatCount, formatPercent, patternMeta } from "../lib/format";
import Working from "./Working";

/* The adversarial page.
 *
 * Every other screen reports on the book the model was fitted to, which means the
 * reader has no way to tell a model that learned laundering from one that memorised
 * 10,000 rows. Here they write the book: size, crime mix, seed. We generate it,
 * score it with the already-trained classifier, and grade the predictions against a
 * ground truth that did not exist when the page loaded.
 *
 * Nothing is retrained. The numbers can come out badly, and if they do, that is
 * what gets rendered -- a scoreboard that can only go up is not evidence.
 */

const DEFAULTS = {
  accounts: 3000,
  transactions: 15000,
  smurfing_ops: 8,
  layering_chains: 12,
  mule_ops: 12,
  seed: 7,
};

const CONTROLS = [
  { key: "accounts", label: "Accounts", min: 200, max: 6000, step: 100, hint: "Size of the book" },
  { key: "transactions", label: "Legitimate transactions", min: 500, max: 30000, step: 500, hint: "The honest baseline the crime hides in" },
  { key: "smurfing_ops", label: "Smurfing operations", min: 0, max: 40, step: 1, hint: "Many small deposits fanning into one collector" },
  { key: "layering_chains", label: "Layering chains", min: 0, max: 60, step: 1, hint: "Value hopped through intermediaries" },
  { key: "mule_ops", label: "Cash-out mules", min: 0, max: 60, step: 1, hint: "Money in, then drained to ATM cash and card spend" },
  { key: "seed", label: "Random seed", min: 0, max: 999999, step: 1, hint: "Same seed, same book — so a surprising result can be handed to someone else" },
];

/* Precision and recall are not interchangeable and the difference is the whole
 * job, so they are spelled out rather than left as jargon on a tile. */
const GRADE = [
  { key: "recall", label: "Caught", gloss: "of the criminals in the book, how many the model flagged" },
  { key: "precision", label: "Correct", gloss: "of the accounts it flagged, how many were actually criminal" },
  { key: "f1", label: "F1", gloss: "the balance of the two" },
];

export default function Simulator() {
  const [cfg, setCfg] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  // The live config is read from a ref, not closed over, so `run` stays stable and
  // the mount effect below cannot re-fire on every slider drag. (A setCfg updater
  // would be the obvious trick here and it is wrong: React does not promise to
  // invoke the updater synchronously, so it would sometimes post a stale body.)
  const cfgRef = useRef(cfg);
  cfgRef.current = cfg;

  const run = useCallback(async (override) => {
    setBusy(true);
    setError(null);
    try {
      setResult(await runSimulation(override ?? cfgRef.current));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, []);

  // Run the default book once on arrival. A page that opens on "press the button
  // to see anything" wastes the one moment the reader is actually curious -- and
  // the whole claim here is that a run is cheap (~600ms).
  useEffect(() => {
    run(DEFAULTS);
  }, [run]);

  const set = (k) => (e) => setCfg((c) => ({ ...c, [k]: Number(e.target.value) }));
  const crimeFree = cfg.smurfing_ops + cfg.layering_chains + cfg.mule_ops === 0;

  return (
    <div className="page">
      <section className="section" style={{ marginTop: 0 }}>
        <h2 className="section__title">Write your own crime book</h2>
        <p className="section__lede">
          The classifier was fitted to one fixed dataset. Build a different one — any size, any
          crime mix — and it will be scored by that same model, which has never seen a row of it.
          Nothing is retrained. The result is graded against ground truth generated on the spot,
          so it is free to come out badly.
        </p>

        <div className="grid grid--sim">
          <Card title="The book" subtitle="Every knob changes what the model is asked to find">
            <div className="controls">
              {CONTROLS.map((c) => (
                <label className="control" key={c.key}>
                  <span className="control__head">
                    <span className="control__label">{c.label}</span>
                    <output className="control__value">{formatCount(cfg[c.key])}</output>
                  </span>
                  <input
                    type="range"
                    min={c.min}
                    max={c.max}
                    step={c.step}
                    value={cfg[c.key]}
                    onChange={set(c.key)}
                    disabled={busy}
                  />
                  <span className="control__hint">{c.hint}</span>
                </label>
              ))}
            </div>

            <div className="controls__actions">
              <button type="button" className="btn btn--primary" onClick={() => run()} disabled={busy}>
                {busy ? "Generating and scoring…" : "Generate & detect"}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setCfg(DEFAULTS)}
                disabled={busy}
              >
                Reset
              </button>
            </div>

            {crimeFree && (
              <p className="control__warn">
                No crime in this book. Worth running: a detector that flags nobody on a clean book
                is behaving correctly, and one that flags somebody is crying wolf.
              </p>
            )}
          </Card>

          <div className="grid__report">
            {error && (
              <ErrorNote onRetry={() => run()}>
                The simulation failed: {error.message}. Very large books can exceed the free
                instance's memory — try fewer accounts.
              </ErrorNote>
            )}

            {!result && !error && (
              <Card title="No book yet">
                <Empty>
                  Set the sliders and press <b>Generate &amp; detect</b>. A run takes about a second.
                </Empty>
              </Card>
            )}

            {result && <Scorecard result={result} />}
          </div>
        </div>

        {result && <Working top={result.top} />}
      </section>
    </div>
  );
}

function Scorecard({ result }) {
  const { detection: d, book, by_pattern, config, elapsed_ms } = result;
  const clean = book.criminal_accounts === 0;

  return (
    <>
      <Card
        title="How the model did on a book it has never seen"
        subtitle={`${formatCount(book.accounts)} accounts · ${formatCount(
          book.transactions
        )} transactions · ${formatCount(book.criminal_accounts)} criminal · generated and scored in ${elapsed_ms}ms`}
      >
        {clean ? (
          <p className="verdict">
            {d.false_alarms === 0 ? (
              <>
                A clean book, and the model flagged <b>nobody</b>. No false alarms out of{" "}
                {formatCount(book.accounts)} honest accounts — it is not just calling everything
                suspicious.
              </>
            ) : (
              <>
                A clean book, but the model flagged <b>{formatCount(d.false_alarms)}</b> honest
                accounts. Those are false positives with no crime to find.
              </>
            )}
          </p>
        ) : (
          <>
            <div className="grade">
              {GRADE.map((g) => (
                <div className="grade__cell" key={g.key}>
                  <span className="grade__value">{formatPercent(d[g.key], 0)}</span>
                  <span className="grade__label">{g.label}</span>
                  <span className="grade__gloss">{g.gloss}</span>
                </div>
              ))}
              <div className="grade__cell">
                <span className="grade__value">{d.roc_auc == null ? "—" : d.roc_auc.toFixed(3)}</span>
                <span className="grade__label">ROC-AUC</span>
                <span className="grade__gloss">how well it ranks criminals above honest accounts</span>
              </div>
            </div>

            {/* The counts behind the percentages. A recall of 96% means nothing until
                you know it is 222 of 232. */}
            <ul className="tally">
              <li>
                <b>{formatCount(d.caught)}</b> caught
              </li>
              <li>
                <b>{formatCount(d.missed)}</b> missed
                <span className="tally__note"> — criminals it let through</span>
              </li>
              <li>
                <b>{formatCount(d.false_alarms)}</b> false alarms
                <span className="tally__note"> — honest accounts it flagged</span>
              </li>
              <li>
                <b>{formatCount(d.clean_and_cleared)}</b> correctly cleared
              </li>
            </ul>
          </>
        )}
        <p className="chart__foot">
          Seed <b>{config.seed}</b> — the same seed rebuilds this exact book, so any result here can
          be handed to someone else and reproduced.
        </p>
      </Card>

      {by_pattern.length > 0 && (
        <Card title="Which crimes it catches" subtitle="Recall per typology, on this book">
          <ul className="recall">
            {by_pattern.map((p) => {
              const meta = patternMeta(p.pattern.toUpperCase());
              return (
                <li className="recall__row" key={p.pattern}>
                  <span className="recall__label">
                    <i className="legend__swatch" style={{ background: meta.var }} aria-hidden="true" />
                    {meta.label}
                  </span>
                  <span className="recall__track">
                    <span
                      className="recall__bar"
                      style={{ width: `${p.recall * 100}%`, background: meta.var }}
                    />
                  </span>
                  <span className="recall__value num">
                    {p.caught}/{p.actual}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="chart__foot">
            An aggregate score can hide that the model catches every mule and misses every smurf —
            and those are different failures. Broken out so it cannot.
          </p>
        </Card>
      )}
    </>
  );
}
