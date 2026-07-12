import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";

/* Global SHAP importance -> horizontal bars, length = magnitude, hue = polarity.
 *
 * The per-account chart (ExplanationPanel) answers "why did THIS account score?"
 * This answers the question a reviewer asks first: "what did the model learn at
 * all?" Same attribution, same units (classifier margin / log-odds), averaged
 * over every account -- so the two charts are read on the same terms.
 *
 * Length is mean |contribution|: how much the feature moves the score. Hue is the
 * average direction, on the same diverging pair the per-account chart uses (warm
 * = raises risk, cool = lowers it). The two are independent: a feature can be a
 * top driver and still be risk-lowering on balance, which is exactly what net_flow
 * does -- and a length-only chart would hide that.
 */

export default function RiskDrivers({ data }) {
  const [asTable, setAsTable] = useState(false);
  if (!data?.length) return <Empty>Model drivers unavailable.</Empty>;

  const max = Math.max(...data.map((d) => d.importance));
  const hue = (d) => (d.direction === "raises" ? "var(--div-pos)" : "var(--div-neg)");

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
        <div className="table-scroll">
          <table className="table table--compact">
            <thead>
              <tr>
                <th scope="col">Feature</th>
                <th scope="col">On average</th>
                <th scope="col" className="num">Impact</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.feature}>
                  <th scope="row">{d.label}</th>
                  <td>{d.direction === "raises" ? "Raises risk" : "Lowers risk"}</td>
                  <td className="num">{d.importance.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ul className="drivers">
          {data.map((d) => (
            <li className="drivers__row" key={d.feature} title={d.definition}>
              <span className="drivers__label">{d.label}</span>
              <span className="drivers__track">
                <span
                  className="drivers__bar"
                  style={{ width: `${(d.importance / max) * 100}%`, background: hue(d) }}
                />
              </span>
              {/* Value in text ink, never in the series colour. */}
              <span className="drivers__value num">{d.importance.toFixed(3)}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="chart__foot">
        Mean |SHAP| across all 10,000 accounts, in classifier margin units. <b>{data[0].label}</b> moves
        the score {(data[0].importance / data[1].importance).toFixed(1)}× more than anything else — the
        model's single strongest lever.
      </p>
    </div>
  );
}
