import React, { useEffect, useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import { Empty, Spinner, TableViewToggle } from "../ui/Primitives";
import { formatCount } from "../../lib/format";

const TOPO_URL = "/india-states.json";
const W = 460;
const H = 500;

/* Continuous magnitude -> sequential, ONE hue, light->dark. Never a rainbow.
 *
 * Three problems with the original, all fixed here:
 *
 *   1. It read `geo.properties.ST_NM`. The bundled topojson is district-level
 *      and spells the state key `st_nm` (lowercase), so the lookup was always
 *      undefined and every district rendered as count 0. The map never once
 *      displayed real data.
 *
 *   2. It built `rgba(5,150,255, intensity)` -- a continuous alpha ramp with no
 *      legend, so a shade could not be decoded back into a count.
 *
 *   3. It used react-simple-maps@3, whose React peer range stops at 18. On this
 *      project's React 19 `npm install` fails outright with ERESOLVE, which is
 *      why the frontend had no node_modules. Projecting with d3-geo directly
 *      removes the conflicting dependency instead of forcing it.
 *
 * Districts inherit their state's count, because the data is state-level.
 */

const STEPS = ["--seq-100", "--seq-200", "--seq-300", "--seq-400", "--seq-500", "--seq-600", "--seq-700"];

// Quantile bins keep the ramp readable when a few states dominate the counts.
function makeBins(values, n = 5) {
  const sorted = values.filter((v) => v > 0).sort((a, b) => a - b);
  if (!sorted.length) return [];
  const cuts = sorted.length
    ? Array.from({ length: n }, (_, i) => sorted[Math.max(0, Math.ceil(((i + 1) / n) * sorted.length) - 1)])
    : [];
  return [...new Set(cuts)];
}

export default function GeoRisk({ data }) {
  const [asTable, setAsTable] = useState(false);
  const [topo, setTopo] = useState(null);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(TOPO_URL)
      .then((r) => r.json())
      .then((t) => !cancelled && setTopo(t))
      .catch(() => !cancelled && setTopo(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const entries = useMemo(() => Object.entries(data ?? {}).sort((a, b) => b[1] - a[1]), [data]);
  const bins = useMemo(() => makeBins(Object.values(data ?? {})), [data]);

  const paths = useMemo(() => {
    if (!topo) return null;
    const fc = feature(topo, topo.objects.districts);
    const projection = geoMercator().fitSize([W, H], fc);
    const path = geoPath(projection);
    return fc.features.map((f, i) => ({ d: path(f), state: f.properties.st_nm, key: `${f.properties.dt_code}-${i}` }));
  }, [topo]);

  if (!entries.length) return <Empty>No flagged accounts have a resolved location.</Empty>;

  const stepFor = (count) => {
    if (!count) return "var(--surface-2)";
    const i = bins.findIndex((b) => count <= b);
    const idx = i === -1 ? bins.length - 1 : i;
    return `var(${STEPS[Math.min(STEPS.length - 1, idx + 2)]})`;
  };

  return (
    <div className="chart">
      <div className="chart__head">
        {/* A sequential encoding needs a scale legend, or a shade cannot be read. */}
        <div className="scale">
          <span className="scale__cap">Fewer</span>
          {bins.map((b, i) => (
            <i
              key={b}
              className="scale__swatch"
              style={{ background: `var(${STEPS[Math.min(6, i + 2)]})` }}
              title={`up to ${b}`}
            />
          ))}
          <span className="scale__cap">More</span>
        </div>
        <TableViewToggle on={asTable} onToggle={() => setAsTable((v) => !v)} />
      </div>

      {asTable ? (
        <div className="scroll-y">
          <table className="table table--compact">
            <thead>
              <tr>
                <th scope="col">State</th>
                <th scope="col" className="num">
                  Flagged accounts
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([state, count]) => (
                <tr key={state}>
                  <th scope="row">{state}</th>
                  <td className="num">{formatCount(count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : topo === false ? (
        <Empty>Could not load the map geometry.</Empty>
      ) : !paths ? (
        <Spinner label="Loading map" />
      ) : (
        <div className="map">
          <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Flagged accounts by Indian state">
            {paths.map((p) => {
              const count = data[p.state] ?? 0;
              const active = hover === p.state;
              return (
                <path
                  key={p.key}
                  d={p.d}
                  fill={active ? "var(--series-3)" : stepFor(count)}
                  stroke="var(--surface-1)"
                  strokeWidth={0.3}
                  onMouseEnter={() => setHover(p.state)}
                  onMouseLeave={() => setHover(null)}
                  style={{ cursor: "pointer" }}
                />
              );
            })}
          </svg>
          <p className="map__readout" aria-live="polite">
            {hover ? (
              <>
                <strong>{hover}</strong> · {formatCount(data[hover] ?? 0)} flagged
              </>
            ) : (
              <span className="muted">Hover a district to read its state</span>
            )}
          </p>
        </div>
      )}
      <p className="chart__foot">
        Flagged accounts by state of registration. District borders shown; shading is state-level.
      </p>
    </div>
  );
}
