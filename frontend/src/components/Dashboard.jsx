import React, { useMemo, useState } from "react";
import {
  API_BASE,
  getAmountProfile,
  getChannelMix,
  getHeatmapData,
  getPatternStatistics,
  getRiskClock,
  getRiskDrivers,
  getSuspiciousNetworks,
  getSummary,
} from "../api";
import { useFetch } from "../lib/useFetch";
import { Card, ErrorNote, Spinner, StatTile } from "./ui/Primitives";
import AccountsTable from "./AccountsTable";
import PatternShare from "./charts/PatternShare";
import GeoRisk from "./charts/GeoRisk";
import RiskClock from "./charts/RiskClock";
import ChannelMix from "./charts/ChannelMix";
import RiskDrivers from "./charts/RiskDrivers";
import AmountProfile from "./charts/AmountProfile";
import { formatCompactCurrency, formatCount, formatPercent, PATTERN_SLOT } from "../lib/format";

const TYPOLOGIES = ["ALL", "MULE", "SMURFING", "LAYERING"];

export default function Dashboard() {
  const [query, setQuery] = useState("");
  const [typology, setTypology] = useState("ALL");

  const summary = useFetch(() => getSummary(), []);
  const networks = useFetch(() => getSuspiciousNetworks(100), []);
  const patterns = useFetch(() => getPatternStatistics(), []);
  const geo = useFetch(() => getHeatmapData(), []);

  // Book-level intelligence. Static over the dataset, so these are fetched once
  // and never refetched by the filter row above -- the filters scope the flagged
  // account list, not the behaviour of the whole book.
  const clock = useFetch(() => getRiskClock(), []);
  const channels = useFetch(() => getChannelMix(), []);
  const drivers = useFetch(() => getRiskDrivers(8), []);
  const amounts = useFetch(() => getAmountProfile(), []);

  // One filter row scopes everything below it; charts do not carry their own.
  const filtered = useMemo(() => {
    const rows = networks.data ?? [];
    const q = query.trim().toUpperCase();
    return rows.filter(
      (r) =>
        (typology === "ALL" || r.pattern_type === typology) &&
        (!q || r.account_id.toUpperCase().includes(q) || r.state.toUpperCase().includes(q))
    );
  }, [networks.data, query, typology]);

  if (networks.error) {
    return (
      <ErrorNote onRetry={networks.refetch}>
        Could not reach the API at <code>{API_BASE}</code>.
        {import.meta.env.DEV && (
          <>
            {" "}
            Start it with <code>uvicorn backend.main:app --reload</code>.
          </>
        )}
      </ErrorNote>
    );
  }

  const s = summary.data;
  // The free instance sleeps; the first request of the day pays the wake.
  const waking = summary.slow || networks.slow;

  return (
    <div className="page">
      {waking && (
        <p className="wake-note" role="status">
          Waking the analysis server — it sleeps when idle on the free tier. This
          first load can take up to a minute; everything after it is instant.
        </p>
      )}
      <div className="kpi-row">
        <StatTile
          hero
          label="Accounts flagged"
          value={s ? formatCount(s.accounts_flagged) : "—"}
          hint={s ? `${formatPercent(s.flagged_rate, 2)} of ${formatCount(s.accounts_monitored)} monitored` : ""}
        />
        <StatTile
          label="Value at risk"
          value={s ? formatCompactCurrency(s.value_at_risk) : "—"}
          hint="Inbound value across flagged accounts"
        />
        <StatTile
          label="Transactions analysed"
          value={s ? formatCount(s.transactions_analysed) : "—"}
          hint="Full book"
        />
        <StatTile
          label="High novelty"
          value={s ? formatCount(s.high_novelty) : "—"}
          hint="99th percentile — unlike anything on the book"
        />
      </div>

      <div className="filters" role="search">
        <input
          type="search"
          className="input"
          placeholder="Filter by account ID or state…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter accounts"
        />
        <div className="segmented" role="group" aria-label="Filter by typology">
          {TYPOLOGIES.map((t) => (
            <button
              key={t}
              type="button"
              className={`segmented__btn ${typology === t ? "is-active" : ""}`}
              aria-pressed={typology === t}
              onClick={() => setTypology(t)}
            >
              {t !== "ALL" && (
                <i className="badge__dot" style={{ background: PATTERN_SLOT[t].var }} aria-hidden="true" />
              )}
              {t === "ALL" ? "All" : PATTERN_SLOT[t].label}
            </button>
          ))}
        </div>
        <span className="filters__count">{formatCount(filtered.length)} shown</span>
      </div>

      <div className="grid">
        <Card
          className="grid__main"
          title="Flagged accounts"
          subtitle="Ranked by classifier risk. Select a row to open its network."
        >
          {networks.loading && !networks.data ? (
            <Spinner label="Scoring accounts" />
          ) : (
            <div className={networks.stale ? "is-stale" : undefined}>
              <AccountsTable rows={filtered} filter={query} />
            </div>
          )}
        </Card>

        <div className="grid__side">
          <Card title="Typology mix" subtitle="Share of flagged accounts">
            {patterns.loading && !patterns.data ? <Spinner /> : <PatternShare data={patterns.data} />}
          </Card>

          <Card title="Geographic distribution" subtitle="Flagged accounts by state">
            {geo.loading && !geo.data ? <Spinner /> : <GeoRisk data={geo.data} />}
          </Card>
        </div>
      </div>

      {/* Book-level intelligence. Everything above scores accounts; this describes
          the behaviour those scores are drawn from -- the context an investigator
          reads a single case against. Deliberately below the fold: it is the
          second question, not the first. */}
      <section className="section">
        <h2 className="section__title">How laundering behaves</h2>
        <p className="section__lede">
          Across all {s ? formatCount(s.transactions_analysed) : "—"} transactions in the book, not
          just the flagged accounts.
        </p>

        <div className="grid grid--halves">
          <Card
            title="When it happens"
            subtitle="Illicit lift by hour of day"
          >
            {clock.loading && !clock.data ? <Spinner /> : <RiskClock data={clock.data} />}
          </Card>

          <Card title="How it moves" subtitle="Channel fingerprint by typology">
            {channels.loading && !channels.data ? <Spinner /> : <ChannelMix data={channels.data} />}
          </Card>

          <Card title="What the model weighs" subtitle="Global SHAP importance, all 10,000 accounts">
            {drivers.loading && !drivers.data ? <Spinner /> : <RiskDrivers data={drivers.data} />}
          </Card>

          <Card title="How much it moves" subtitle="Transaction size, illicit vs licit">
            {amounts.loading && !amounts.data ? <Spinner /> : <AmountProfile data={amounts.data} />}
          </Card>
        </div>
      </section>
    </div>
  );
}
