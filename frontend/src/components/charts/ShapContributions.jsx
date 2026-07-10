import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";
import { formatFeatureValue } from "../../lib/format";

/* Signed SHAP attribution -> the data's job is POLARITY, so this is a diverging
 * bar centred on a neutral zero rule: warm pole = raises risk, cool pole =
 * lowers it. The old component drew every impact as a positive red bar labelled
 * "+X% risk", which made a factor that *exonerated* the account look like a
 * factor that condemned it.
 *
 * Units are the classifier's margin (log-odds), not percent. Labelling margins
 * as "% risk" was one of the fabrications; they are not the same quantity.
 */

const ROW_H = 34;
const BAR_H = 14;
const END_R = 4; // rounded data-ends
const LABEL_W = 150;
const VALUE_W = 74;

export default function ShapContributions({ features }) {
  const [asTable, setAsTable] = useState(false);
  if (!features?.length) return <Empty>The model reported no contributing factors for this account.</Empty>;

  const max = Math.max(...features.map((f) => Math.abs(f.impact))) || 1;
  const plotW = 260;
  const mid = LABEL_W + plotW / 2;
  const height = features.length * ROW_H + 26;

  const scale = (v) => (v / max) * (plotW / 2 - 6);

  return (
    <div className="chart">
      <div className="chart__head">
        <div className="legend" role="list">
          <span className="legend__item" role="listitem">
            <i className="legend__swatch" style={{ background: "var(--div-pos)" }} aria-hidden="true" />
            Raises risk
          </span>
          <span className="legend__item" role="listitem">
            <i className="legend__swatch" style={{ background: "var(--div-neg)" }} aria-hidden="true" />
            Lowers risk
          </span>
        </div>
        <TableViewToggle on={asTable} onToggle={() => setAsTable((v) => !v)} />
      </div>

      {asTable ? (
        <table className="table table--compact">
          <thead>
            <tr>
              <th scope="col">Factor</th>
              <th scope="col" className="num">
                Value
              </th>
              <th scope="col" className="num">
                Impact
              </th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => (
              <tr key={f.feature}>
                <th scope="row">{f.label}</th>
                <td className="num">{formatFeatureValue(f.feature, f.value)}</td>
                <td className="num">
                  {f.impact >= 0 ? "+" : "−"}
                  {Math.abs(f.impact).toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <svg width="100%" viewBox={`0 0 ${LABEL_W + plotW + VALUE_W} ${height}`} role="img" className="shap">
          <title>Feature contributions to the risk score, in classifier margin units</title>

          {/* neutral zero rule -- a hairline, solid, one shade off the surface */}
          <line x1={mid} y1={16} x2={mid} y2={height - 10} stroke="var(--axis)" strokeWidth="1" />

          {features.map((f, i) => {
            const y = 22 + i * ROW_H;
            const w = Math.abs(scale(f.impact));
            const pos = f.impact >= 0;
            const x = pos ? mid + 1 : mid - 1 - w;
            return (
              <g key={f.feature} className="shap__row">
                <title>
                  {f.label}: {formatFeatureValue(f.feature, f.value)} — {pos ? "raises" : "lowers"} risk by{" "}
                  {Math.abs(f.impact).toFixed(3)}
                  {f.definition ? `. ${f.definition}` : ""}
                </title>

                {/* generous hit target, independent of the thin mark */}
                <rect x={0} y={y - 6} width={LABEL_W + plotW + VALUE_W} height={ROW_H - 2} fill="transparent" />

                <text x={LABEL_W - 10} y={y + BAR_H / 2} className="shap__label" textAnchor="end">
                  {f.label}
                </text>

                <rect
                  x={x}
                  y={y}
                  width={Math.max(w, 1)}
                  height={BAR_H}
                  rx={END_R}
                  fill={pos ? "var(--div-pos)" : "var(--div-neg)"}
                />

                <text x={LABEL_W + plotW + 8} y={y + BAR_H / 2} className="shap__value">
                  {pos ? "+" : "−"}
                  {Math.abs(f.impact).toFixed(2)}
                </text>
              </g>
            );
          })}
        </svg>
      )}
      <p className="chart__foot">
        Exact SHAP values over the gradient-boosted classifier, in margin (log-odds) units. Bars left of the
        rule pushed the model toward “not suspicious”.
      </p>
    </div>
  );
}
