import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";
import { formatCompactCurrency, formatPercent } from "../../lib/format";

/* Two distributions over ordered bands -> grouped bars.
 *
 * Shares within each population, not counts: there are 45x more licit
 * transactions, so a count chart would render the illicit series as a flat line
 * on the axis. As shares, the two distributions barely overlap -- which is the
 * finding.
 *
 * Bands arrive as raw numeric edges and are labelled here. The backend sends
 * {from, to}; currency rendering lives in lib/format.js and nowhere else.
 *
 * Note what this chart deliberately does NOT say. Illicit amounts cluster in
 * bands the retail book hardly touches, but the data encodes no reporting
 * threshold, so calling that "structuring" would be a story about the data
 * rather than a fact in it. It says the true, duller thing: laundering moves
 * money in far bigger units than shopping does.
 */

const bandLabel = ({ from, to }) => {
  if (to == null) return `> ${formatCompactCurrency(from)}`;
  if (from === 0) return `< ${formatCompactCurrency(to)}`;
  return `${formatCompactCurrency(from)}–${formatCompactCurrency(to)}`;
};

const SERIES = [
  { key: "illicit", label: "Illicit", color: "var(--div-pos)" },
  { key: "licit", label: "Licit", color: "var(--div-neg)" },
];

export default function AmountProfile({ data }) {
  const [asTable, setAsTable] = useState(false);
  if (!data?.bands?.length) return <Empty>No transactions to profile.</Empty>;

  const { bands, illicit, licit } = data;
  const max = Math.max(...bands.flatMap((b) => [b.illicit, b.licit]));

  return (
    <div className="chart">
      <div className="chart__head">
        <div className="legend" role="list">
          {SERIES.map((s) => (
            <span className="legend__item" role="listitem" key={s.key}>
              <i className="legend__swatch" style={{ background: s.color }} aria-hidden="true" />
              {s.label}
            </span>
          ))}
        </div>
        <TableViewToggle on={asTable} onToggle={() => setAsTable((v) => !v)} />
      </div>

      {asTable ? (
        <div className="table-scroll">
          <table className="table table--compact">
            <thead>
              <tr>
                <th scope="col">Amount</th>
                <th scope="col" className="num">Illicit</th>
                <th scope="col" className="num">Licit</th>
              </tr>
            </thead>
            <tbody>
              {bands.map((b) => (
                <tr key={b.from}>
                  <th scope="row">{bandLabel(b)}</th>
                  <td className="num">{formatPercent(b.illicit, 1)}</td>
                  <td className="num">{formatPercent(b.licit, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grouped">
          {bands.map((b) => (
            <div className="grouped__group" key={b.from}>
              <div className="grouped__bars">
                {SERIES.map((s) => (
                  <div
                    className="grouped__bar"
                    key={s.key}
                    // See ChannelMix: a zero must draw nothing. No illicit
                    // transaction in the book is under 100 rupees, and that empty
                    // slot is the point of the chart.
                    data-nonzero={b[s.key] > 0}
                    style={{ height: `${(b[s.key] / max) * 100}%`, background: s.color }}
                    title={`${s.label}: ${formatPercent(b[s.key], 1)} of ${s.label.toLowerCase()} transactions fall in ${bandLabel(b)}`}
                  />
                ))}
              </div>
              <span className="grouped__label">{bandLabel(b)}</span>
            </div>
          ))}
        </div>
      )}

      <p className="chart__foot">
        Median illicit transaction is <b>{formatCompactCurrency(illicit.median)}</b> against{" "}
        <b>{formatCompactCurrency(licit.median)}</b> for licit traffic — a{" "}
        <b>{Math.round(illicit.median / licit.median)}×</b> gap. Over half the retail book sits under
        ₹100, where laundering essentially never appears.
      </p>
    </div>
  );
}
