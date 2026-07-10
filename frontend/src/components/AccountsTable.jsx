import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PatternBadge, RiskBadge, RiskMeter, Empty } from "./ui/Primitives";
import { formatCompactCurrency, formatCount, formatPercent, patternMeta } from "../lib/format";

const COLUMNS = [
  { key: "account_id", label: "Account", sortable: true, align: "left" },
  { key: "risk_score", label: "Risk", sortable: true, align: "left" },
  { key: "pattern_type", label: "Typology", sortable: true, align: "left" },
  { key: "total_amount_in", label: "Received", sortable: true, align: "right" },
  { key: "transactions", label: "Txns", sortable: true, align: "right" },
  { key: "state", label: "State", sortable: true, align: "left" },
];

export default function AccountsTable({ rows, filter }) {
  const navigate = useNavigate();
  const [sort, setSort] = useState({ key: "risk_score", dir: "desc" });

  const sorted = useMemo(() => {
    const out = [...(rows ?? [])];
    const { key, dir } = sort;
    out.sort((a, b) => {
      const [x, y] = [a[key], b[key]];
      const cmp = typeof x === "number" ? x - y : String(x).localeCompare(String(y));
      return dir === "asc" ? cmp : -cmp;
    });
    return out;
  }, [rows, sort]);

  const toggleSort = (key) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "desc" ? "asc" : "desc" }));

  if (!rows?.length) return <Empty>No accounts match “{filter}”.</Empty>;

  return (
    <div className="scroll-y scroll-y--tall">
      <table className="table table--interactive">
        <thead>
          <tr>
            {COLUMNS.map((c) => {
              const active = sort.key === c.key;
              return (
                <th
                  key={c.key}
                  scope="col"
                  className={c.align === "right" ? "num" : undefined}
                  aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button type="button" className="th-sort" onClick={() => toggleSort(c.key)}>
                    {c.label}
                    <span className={`th-sort__caret ${active ? "is-active" : ""}`} aria-hidden="true">
                      {active && sort.dir === "asc" ? "▲" : "▼"}
                    </span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.account_id}
              tabIndex={0}
              role="link"
              onClick={() => navigate(`/network/${r.account_id}`)}
              onKeyDown={(e) => e.key === "Enter" && navigate(`/network/${r.account_id}`)}
            >
              <th scope="row" className="mono">
                {r.account_id}
              </th>
              <td>
                <div className="risk-cell">
                  <RiskMeter score={r.risk_score} />
                  <span className="risk-cell__value">{formatPercent(r.risk_score, 1)}</span>
                  <RiskBadge score={r.risk_score} />
                </div>
              </td>
              <td>
                <PatternBadge pattern={patternMeta(r.pattern_type)} />
              </td>
              <td className="num">{formatCompactCurrency(r.total_amount_in)}</td>
              <td className="num">{formatCount(r.transactions)}</td>
              <td className="muted">{r.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
