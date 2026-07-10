import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";
import { formatCount, formatPercent, patternMeta } from "../../lib/format";

/* Part-to-whole across 3 named categories -> horizontal stacked bar.
 *
 * This was a pie. A pie is only defensible for at-a-glance part-to-whole with
 * few segments and clearly separated values, and it makes comparing adjacent
 * slices hard. The stacked bar reads as a share, direct-labels every segment,
 * and leaves room for long typology names.
 *
 * Segments are separated by a 2px surface gap rather than a stroke.
 */

const H = 30;
const GAP = 2;

export default function PatternShare({ data }) {
  const [asTable, setAsTable] = useState(false);
  if (!data?.length) return <Empty>No accounts currently clear the flagging threshold.</Empty>;

  const rows = data.map((d) => ({ ...d, meta: patternMeta(d.pattern) }));
  const total = rows.reduce((s, d) => s + d.count, 0);

  let offset = 0;
  const segments = rows.map((d) => {
    const width = (d.count / total) * 100;
    const seg = { ...d, width, offset };
    offset += width;
    return seg;
  });

  return (
    <div className="chart">
      <div className="chart__head">
        <div className="legend" role="list">
          {rows.map((d) => (
            <span className="legend__item" role="listitem" key={d.pattern}>
              <i className="legend__swatch" style={{ background: d.meta.var }} aria-hidden="true" />
              {d.meta.label}
            </span>
          ))}
        </div>
        <TableViewToggle on={asTable} onToggle={() => setAsTable((v) => !v)} />
      </div>

      {asTable ? (
        <table className="table table--compact">
          <thead>
            <tr>
              <th scope="col">Typology</th>
              <th scope="col" className="num">
                Accounts
              </th>
              <th scope="col" className="num">
                Share
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.pattern}>
                <th scope="row">{d.meta.label}</th>
                <td className="num">{formatCount(d.count)}</td>
                <td className="num">{formatPercent(d.count / total, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <>
          <div className="stack" style={{ height: H }}>
            {segments.map((d) => (
              <div
                key={d.pattern}
                className="stack__seg"
                style={{
                  left: `${d.offset}%`,
                  width: `calc(${d.width}% - ${GAP}px)`,
                  background: d.meta.var,
                }}
                title={`${d.meta.label}: ${formatCount(d.count)} accounts (${formatPercent(d.count / total, 0)})`}
              />
            ))}
          </div>

          {/* Direct labels below the bar -- required relief for the sub-3:1
              contrast of slots 2 and 3 on the light surface. */}
          <ul className="stack__labels">
            {rows.map((d) => (
              <li key={d.pattern}>
                <span className="stack__label-name">{d.meta.label}</span>
                <span className="stack__label-value">
                  {formatCount(d.count)}
                  <span className="stack__label-share"> · {formatPercent(d.count / total, 0)}</span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="chart__foot">{formatCount(total)} accounts above the 50% flagging threshold.</p>
    </div>
  );
}
