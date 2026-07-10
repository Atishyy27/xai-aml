import React from "react";
import { Empty } from "./ui/Primitives";
import { formatCurrency, formatDate } from "../lib/format";

export default function TransactionList({ transactions, onHover }) {
  if (!transactions?.length) return <Empty>No transactions match the current filter.</Empty>;

  return (
    <ul className="tx-list">
      {transactions.map((tx) => (
        <li
          key={tx.id}
          className="tx"
          onMouseEnter={() => onHover?.({ from: tx.from, to: tx.to })}
          onMouseLeave={() => onHover?.(null)}
        >
          <div className="tx__main">
            <div className="tx__route">
              <span className="mono">{tx.from}</span>
              <span className="tx__arrow" aria-label="to">
                →
              </span>
              <span className="mono">{tx.to}</span>
            </div>
            <div className="tx__meta">
              {formatDate(tx.date)} · {tx.type.replace("_", " ").toLowerCase()}
              {/* Status colour never travels alone -- the word "Illicit" carries it. */}
              {tx.illicit && (
                <span className="badge badge--critical">
                  <i className="badge__dot" aria-hidden="true" />
                  Illicit
                </span>
              )}
            </div>
          </div>
          <div className={`tx__amount tx__amount--${tx.direction}`}>
            {tx.direction === "in" ? "+" : "−"}
            {formatCurrency(tx.amount)}
          </div>
        </li>
      ))}
    </ul>
  );
}
