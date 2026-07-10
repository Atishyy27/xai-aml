import React, { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getAccountExplanation, getNetworkGraph, getTransactions } from "../api";
import { useFetch } from "../lib/useFetch";
import { Card, ErrorNote, PatternBadge, RiskBadge, Spinner } from "./ui/Primitives";
import NetworkGraph from "./NetworkGraph";
import ShapContributions from "./charts/ShapContributions";
import MetricsCard from "./MetricsCard";
import TransactionList from "./TransactionList";
import { formatPercent, patternMeta } from "../lib/format";

export default function NetworkView() {
  const { networkId } = useParams();
  const navigate = useNavigate();

  const [hops, setHops] = useState(1);
  const [illicitOnly, setIllicitOnly] = useState(false);
  const [highlight, setHighlight] = useState(null);

  const graph = useFetch(() => getNetworkGraph(networkId, hops), [networkId, hops]);
  const explain = useFetch(() => getAccountExplanation(networkId), [networkId]);
  const txns = useFetch(() => getTransactions(networkId, { illicitOnly, limit: 60 }), [networkId, illicitOnly]);

  const onSelect = useCallback((id) => navigate(`/network/${id}`), [navigate]);

  if (explain.error) {
    return (
      <ErrorNote onRetry={explain.refetch}>
        Could not load the report for <code>{networkId}</code>.
      </ErrorNote>
    );
  }

  const report = explain.data?.explanation;

  return (
    <div className="page">
      <nav className="crumbs">
        <Link to="/" className="link">
          ← All flagged accounts
        </Link>
      </nav>

      <header className="acct-head">
        <div>
          <h2 className="acct-head__id mono">{networkId}</h2>
          {report && (
            <div className="acct-head__badges">
              <RiskBadge score={report.risk_score} />
              <PatternBadge pattern={patternMeta(report.pattern_type)} />
              <span className="muted">
                Risk {formatPercent(report.risk_score, 1)} · novelty {formatPercent(report.novelty, 0)} percentile
              </span>
            </div>
          )}
        </div>

        <div className="segmented" role="group" aria-label="Analysis depth">
          {[1, 2].map((h) => (
            <button
              key={h}
              type="button"
              className={`segmented__btn ${hops === h ? "is-active" : ""}`}
              aria-pressed={hops === h}
              disabled={graph.loading}
              onClick={() => setHops(h)}
            >
              {h}-hop
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid--investigate">
        <Card className="grid__graph" title="Transaction network" subtitle={`${hops}-hop neighbourhood`}>
          {graph.loading && !graph.data ? (
            <Spinner label="Building neighbourhood" />
          ) : (
            <div className={graph.stale ? "is-stale" : undefined}>
              <NetworkGraph graph={graph.data?.graph} focusId={networkId} onSelect={onSelect} highlight={highlight} />
            </div>
          )}
        </Card>

        <div className="grid__report">
          <Card title="Why this account was flagged">
            {explain.loading && !report ? (
              <Spinner label="Explaining" />
            ) : (
              <>
                <p className="summary">{report.summary}</p>
                <div className="metric-grid">
                  {report.metrics.map((m) => (
                    <MetricsCard
                      key={m.name}
                      title={m.name}
                      value={m.value}
                      unit={m.unit}
                      benchmark={m.benchmark}
                      definition={m.definition}
                    />
                  ))}
                </div>
              </>
            )}
          </Card>

          <Card title="Contributing factors">
            {explain.loading && !report ? (
              <Spinner />
            ) : (
              <ShapContributions features={report.feature_contributions} />
            )}
          </Card>

          <Card
            title="Transactions"
            subtitle="Hover a row to trace it on the graph"
            actions={
              <label className="check">
                <input type="checkbox" checked={illicitOnly} onChange={(e) => setIllicitOnly(e.target.checked)} />
                Labelled illicit only
              </label>
            }
          >
            {txns.loading && !txns.data ? (
              <Spinner />
            ) : (
              <div className={txns.stale ? "is-stale" : undefined}>
                <TransactionList transactions={txns.data?.transactions} onHover={setHighlight} />
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
