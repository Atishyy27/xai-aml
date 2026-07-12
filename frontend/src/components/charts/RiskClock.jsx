import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";
import { formatCount } from "../../lib/format";

/* Magnitude across an ordered (cyclical) dimension -> vertical bars, 24 of them.
 *
 * The measure is *lift*, not raw illicit volume. Plotting raw volume would mostly
 * re-plot when anyone transacts at all -- there are 45x more licit transactions,
 * so their diurnal shape swamps everything. Lift asks the sharper question: given
 * a transaction at this hour, how much likelier is it to be illicit than the
 * book's base rate? 1.0 is that baseline, and it gets an explicit rule.
 *
 * Magnitude -> one sequential hue, light to dark. Not the categorical slots:
 * those are bound to typologies (Mule/Smurfing/Layering) everywhere else in the
 * dashboard, and an hour of the day is not a typology.
 */

const BASELINE = 1;

// The scale is anchored above the spike so the ceiling does not move when the
// data does; the four small-hours bars are the story and they must not clip.
const ceiling = (rows) => Math.max(10, Math.ceil(Math.max(...rows.map((r) => r.lift ?? 0))));

// Sequential ramp, snapped by magnitude. Steps 100-700 are the project's single
// blue hue, already validated against both surfaces.
const fill = (lift, max) => {
  const t = lift / max;
  if (t >= 0.8) return "var(--seq-700)";
  if (t >= 0.6) return "var(--seq-600)";
  if (t >= 0.4) return "var(--seq-500)";
  if (t >= 0.25) return "var(--seq-400)";
  if (t >= 0.12) return "var(--seq-300)";
  if (t >= 0.06) return "var(--seq-200)";
  return "var(--seq-100)";
};

const hh = (h) => `${String(h).padStart(2, "0")}:00`;

export default function RiskClock({ data }) {
  const [asTable, setAsTable] = useState(false);
  if (!data?.length) return <Empty>No transactions to profile.</Empty>;

  const max = ceiling(data);
  const peak = data.reduce((a, b) => ((b.lift ?? 0) > (a.lift ?? 0) ? b : a));

  return (
    <div className="chart">
      <div className="chart__head">
        <p className="chart__note">
          Lift over the licit baseline. <b>1.0×</b> means an hour is no more criminal than any other.
        </p>
        <TableViewToggle on={asTable} onToggle={() => setAsTable((v) => !v)} />
      </div>

      {asTable ? (
        <div className="table-scroll">
          <table className="table table--compact">
            <thead>
              <tr>
                <th scope="col">Hour</th>
                <th scope="col" className="num">Lift</th>
                <th scope="col" className="num">Illicit</th>
                <th scope="col" className="num">Licit</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.hour}>
                  <th scope="row">{hh(d.hour)}</th>
                  <td className="num">{d.lift == null ? "—" : `${d.lift.toFixed(1)}×`}</td>
                  <td className="num">{formatCount(d.illicit)}</td>
                  <td className="num">{formatCount(d.licit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          <div className="clock" style={{ "--baseline": `${(BASELINE / max) * 100}%` }}>
            {data.map((d) => {
              const lift = d.lift ?? 0;
              return (
                <div className="clock__col" key={d.hour}>
                  <div
                    className="clock__bar"
                    data-nonzero={lift > 0}
                    style={{ height: `${(lift / max) * 100}%`, background: fill(lift, max) }}
                    title={`${hh(d.hour)} — ${lift.toFixed(1)}× lift (${formatCount(d.illicit)} illicit of ${formatCount(
                      d.illicit + d.licit
                    )})`}
                  />
                </div>
              );
            })}
          </div>

          {/* Only every 6th hour is ticked. Labelling all 24 at this width
              collides; the peak is direct-labelled instead. */}
          <div className="clock__axis" aria-hidden="true">
            {[0, 6, 12, 18].map((h) => (
              <span key={h}>{hh(h)}</span>
            ))}
            <span>23:00</span>
          </div>
        </>
      )}

      <p className="chart__foot">
        Laundering peaks at <b>{hh(peak.hour)}</b> — <b>{peak.lift?.toFixed(1)}× </b>
        the licit baseline. The small hours (00:00–03:00) carry the heaviest concentration in the book.
      </p>
    </div>
  );
}
