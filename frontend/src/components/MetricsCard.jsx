import React from "react";
import { formatMetric } from "../lib/format";

/* The backend sends `{ value, unit, benchmark }` as raw numbers; formatting is
 * applied here so every rupee figure on screen uses the same en-IN grouping.
 *
 * The old version received pre-formatted strings from Python (`f"Rs{x:,.0f}"`)
 * and ran `toLocaleString` on anything that still looked numeric -- which is how
 * "Rs755,771" ended up beside "Rs7.4Cr" on the same page.
 */
export default function MetricsCard({ title, value, unit, benchmark, definition }) {
  return (
    <div className="metric">
      <div className="metric__head">
        <h5 className="metric__title">{title}</h5>
        {definition && (
          <span className="tooltip" tabIndex={0} role="note" aria-label={definition}>
            <span aria-hidden="true">ⓘ</span>
            <span className="tooltip__body">{definition}</span>
          </span>
        )}
      </div>
      <p className="metric__value">{formatMetric(value, unit)}</p>
      {benchmark != null && <p className="metric__benchmark">Typical: {formatMetric(benchmark, unit)}</p>}
    </div>
  );
}
