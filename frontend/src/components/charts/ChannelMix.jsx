import React, { useState } from "react";
import { Empty, TableViewToggle } from "../ui/Primitives";
import { formatCount, formatPercent, patternMeta } from "../../lib/format";

/* Each typology's channel fingerprint -> grouped bars, x = channel, colour = typology.
 *
 * The obvious build is the transpose: one stacked bar per typology, coloured by
 * channel. It is wrong here. Colour follows the *entity*, and in this dashboard
 * the entity that owns a colour is the typology -- Mule is --series-1 in the
 * table, in the pattern chart, and on the graph. Colouring TRANSFER with that
 * same blue would make one hue mean "Mule" in one panel and "Transfer" in the
 * next, which is precisely the collision the palette exists to prevent.
 *
 * So typology keeps its slot and channel becomes the axis. Each typology's bars
 * still sum to 100% across the channels -- it is the same composition, read
 * along the other dimension, and it makes the fingerprints directly comparable:
 * the Mule bar towers over ATM_WITHDRAWAL, where no other typology appears at all.
 */

const CHANNEL_LABEL = {
  TRANSFER: "Transfer",
  PURCHASE: "Card purchase",
  ATM_WITHDRAWAL: "ATM withdrawal",
};

export default function ChannelMix({ data }) {
  const [asTable, setAsTable] = useState(false);
  if (!data?.length) return <Empty>No transactions to profile.</Empty>;

  const channels = Object.keys(data[0].channels);
  const rows = data.map((d) => ({ ...d, meta: patternMeta(d.typology.toUpperCase().replace("NO PATTERN", "NONE")) }));

  return (
    <div className="chart">
      <div className="chart__head">
        <div className="legend" role="list">
          {rows.map((d) => (
            <span className="legend__item" role="listitem" key={d.typology}>
              <i className="legend__swatch" style={{ background: d.meta.var }} aria-hidden="true" />
              {d.meta.label}
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
                <th scope="col">Typology</th>
                {channels.map((ch) => (
                  <th scope="col" className="num" key={ch}>
                    {CHANNEL_LABEL[ch] ?? ch}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.typology}>
                  <th scope="row">{d.meta.label}</th>
                  {channels.map((ch) => (
                    <td className="num" key={ch}>
                      {formatPercent(d.channels[ch], 0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grouped">
          {channels.map((ch) => (
            <div className="grouped__group" key={ch}>
              <div className="grouped__bars">
                {rows.map((d) => {
                  const v = d.channels[ch] ?? 0;
                  return (
                    <div
                      className="grouped__bar"
                      key={d.typology}
                      // A zero draws nothing at all. "Never" is the finding here --
                      // no layering transaction has ever touched an ATM -- and a
                      // 2px floor would render that as "rare but present".
                      data-nonzero={v > 0}
                      style={{ height: `${v * 100}%`, background: d.meta.var }}
                      title={`${d.meta.label}: ${formatPercent(v, 0)} of its ${formatCount(
                        d.transactions
                      )} transactions go through ${CHANNEL_LABEL[ch] ?? ch}`}
                    />
                  );
                })}
              </div>
              <span className="grouped__label">{CHANNEL_LABEL[ch] ?? ch}</span>
            </div>
          ))}
        </div>
      )}

      <p className="chart__foot">
        Share of each typology's own transactions, by channel. Layering and smurfing are{" "}
        <b>pure transfer</b>; a mule is defined by the cash-out, so it inverts — <b>97%</b> of mule
        transactions leave as ATM cash or card spend.
      </p>
    </div>
  );
}
