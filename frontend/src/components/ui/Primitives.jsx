import React from "react";
import { riskTier } from "../../lib/format";

/* ------------------------------------------------------------------ Card */
export const Card = ({ title, subtitle, actions, children, className = "", ...rest }) => (
  <section className={`card ${className}`} {...rest}>
    {(title || actions) && (
      <header className="card__head">
        <div>
          {title && <h3 className="card__title">{title}</h3>}
          {subtitle && <p className="card__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="card__actions">{actions}</div>}
      </header>
    )}
    <div className="card__body">{children}</div>
  </section>
);

/* ------------------------------------------------------- Stat tile / hero */
export const StatTile = ({ label, value, hint, hero = false }) => (
  <div className={`stat ${hero ? "stat--hero" : ""}`}>
    <span className="stat__label">{label}</span>
    {/* Proportional figures, not tabular -- these are standalone numbers. */}
    <span className="stat__value">{value}</span>
    {hint && <span className="stat__hint">{hint}</span>}
  </div>
);

/* ----------------------------------------------------------------- Badges */
export const PatternBadge = ({ pattern }) => {
  const { label, var: color, slot } = pattern;
  return (
    <span className="badge">
      {slot > 0 && <i className="badge__dot" style={{ background: color }} aria-hidden="true" />}
      {label}
    </span>
  );
};

/* Status colour is always paired with its label, never carrying meaning alone. */
export const RiskBadge = ({ score }) => {
  const tier = riskTier(score);
  return (
    <span className={`badge badge--${tier.key}`}>
      <i className="badge__dot" aria-hidden="true" />
      {tier.label}
    </span>
  );
};

/* ------------------------------------------------------------- Risk meter */
/* A single ratio against a limit -> meter on a same-hue track. Sequential, so
 * the fill darkens with magnitude; the track is the surface, not a second hue. */
export const RiskMeter = ({ score }) => {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const step = score >= 0.85 ? "var(--seq-600)" : score >= 0.6 ? "var(--seq-500)" : "var(--seq-400)";
  return (
    <div
      className="meter"
      role="meter"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Risk score"
    >
      <div className="meter__fill" style={{ width: `${pct}%`, background: step }} />
    </div>
  );
};

/* -------------------------------------------------------------- Utilities */
export const Spinner = ({ label = "Loading" }) => (
  <div className="spinner" role="status">
    <span className="spinner__ring" aria-hidden="true" />
    <span className="spinner__label">{label}…</span>
  </div>
);

export const ErrorNote = ({ children, onRetry }) => (
  <div className="error-note" role="alert">
    <p>{children}</p>
    {onRetry && (
      <button type="button" className="btn" onClick={onRetry}>
        Retry
      </button>
    )}
  </div>
);

export const Empty = ({ children }) => <p className="empty">{children}</p>;

/* Every chart ships a table-view twin so no value is reachable only by colour. */
export const TableViewToggle = ({ on, onToggle }) => (
  <button type="button" className="btn btn--ghost" aria-pressed={on} onClick={onToggle}>
    {on ? "Chart" : "Table"}
  </button>
);
