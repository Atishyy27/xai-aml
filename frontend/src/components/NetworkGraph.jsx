import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { riskTier } from "../lib/format";

/* The old component declared `nodeCanvasObject` as a named function, never
 * passed it, and then inlined a second near-identical copy in JSX -- so edits to
 * the first silently did nothing. There is one renderer here.
 *
 * Node colour encodes RISK (sequential, one hue) rather than edge direction;
 * direction is already carried by the arrowheads. The focus node gets a ring,
 * not a different hue, so hue stays free for magnitude.
 */

const readVar = (name, fallback) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;

// Node radii are already scale-invariant, so a high fit-zoom is safe; this only
// stops a 2-node graph from filling the canvas with two dots and a hairline.
const MAX_ZOOM = 6;

const TIER_STEP = {
  critical: "--seq-700",
  serious: "--seq-600",
  warning: "--seq-500",
  good: "--seq-300",
};

export default function NetworkGraph({ graph, focusId, onSelect, highlight }) {
  const fgRef = useRef();
  const boxRef = useRef();
  const [dims, setDims] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const measure = () => {
      if (boxRef.current) {
        const { offsetWidth: width, offsetHeight: height } = boxRef.current;
        setDims({ width, height });
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (boxRef.current) ro.observe(boxRef.current);

    // The canvas reads its colours from CSS custom properties at draw time, and
    // the simulation stops repainting once it cools. Force one repaint when the
    // theme flips, or the graph keeps yesterday's palette.
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const repaint = () => fgRef.current?.refresh();
    mq.addEventListener("change", repaint);

    const themeObserver = new MutationObserver(repaint);
    themeObserver.observe(document.documentElement, { attributeFilter: ["data-theme"] });

    return () => {
      ro.disconnect();
      mq.removeEventListener("change", repaint);
      themeObserver.disconnect();
    };
  }, []);

  // ForceGraph mutates the objects it is handed (source/target become node refs),
  // so hand it a fresh copy whenever the payload changes.
  const data = useMemo(
    () => ({
      nodes: (graph?.nodes ?? []).map((n) => ({ ...n })),
      links: (graph?.edges ?? []).map((e) => ({ ...e })),
    }),
    [graph]
  );

  const zoomed = useRef(null);
  useEffect(() => {
    zoomed.current = null;
  }, [data]);

  const isHot = useCallback(
    (link) => {
      if (!highlight) return false;
      const s = typeof link.source === "object" ? link.source.id : link.source;
      const t = typeof link.target === "object" ? link.target.id : link.target;
      return s === highlight.from && t === highlight.to;
    },
    [highlight]
  );

  const drawNode = useCallback(
    (node, ctx, scale) => {
      const focus = node.id === focusId;
      // Radii are divided by the zoom scale so a node keeps a constant *screen*
      // size. Drawn in graph units instead, a 6-node ego graph -- which
      // zoomToFit blows up to ~10x -- renders nodes the size of dinner plates.
      const r = (focus ? 9 : 6) / scale;
      const tier = riskTier(node.risk_score ?? 0);
      const fill = readVar(TIER_STEP[tier.key], "#3987e5");

      const touched = highlight && (node.id === highlight.from || node.id === highlight.to);
      if (touched) {
        ctx.shadowBlur = 14;
        ctx.shadowColor = readVar("--series-3", "#c98500");
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.shadowBlur = 0;

      // A 2px surface ring separates overlapping marks -- never a dark border.
      ctx.lineWidth = 2 / scale;
      ctx.strokeStyle = readVar("--surface-1", "#1a1a19");
      ctx.stroke();

      if (focus) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 3.5 / scale, 0, 2 * Math.PI);
        ctx.strokeStyle = readVar("--text-primary", "#fff");
        ctx.lineWidth = 1.5 / scale;
        ctx.stroke();
      }

      // Label only the focus node and its risk-bearing peers; a label on every
      // node is unreadable past ~30 nodes.
      if (focus || scale > 1.6 || (node.risk_score ?? 0) >= 0.5) {
        const size = 11 / scale;
        ctx.font = `${focus ? 600 : 400} ${size}px system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = readVar("--text-secondary", "#c3c2b7");
        ctx.fillText(node.id, node.x, node.y + r + 2 / scale);
      }
    },
    [focusId, highlight]
  );

  return (
    <div ref={boxRef} className="graph">
      {dims.width > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={dims.width}
          height={dims.height}
          graphData={data}
          backgroundColor="transparent"
          nodeId="id"
          nodeRelSize={4}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            // Hit target larger than the mark.
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, 12, 0, 2 * Math.PI);
            ctx.fill();
          }}
          nodeLabel={(n) => `${n.id} — risk ${(n.risk_score * 100).toFixed(0)}% · ${n.state}`}
          onNodeClick={(n) => onSelect?.(n.id)}
          linkColor={(l) =>
            isHot(l)
              ? readVar("--series-3", "#c98500")
              : l.illicit
                ? readVar("--div-pos", "#e66767")
                : readVar("--gridline", "#2c2c2a")
          }
          linkWidth={(l) => (isHot(l) ? 3 : l.illicit ? 1.6 : 1)}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.18}
          linkLabel={(l) => `₹${Number(l.amount).toLocaleString("en-IN")} over ${l.count} txn(s)`}
          cooldownTicks={120}
          onEngineStop={() => {
            if (zoomed.current === data || !data.nodes.length) return;
            zoomed.current = data;
            const fg = fgRef.current;
            if (!fg) return;
            fg.zoomToFit(400, 80);
            // zoomToFit animates over 400ms, so the cap has to be applied after.
            setTimeout(() => {
              if (fg.zoom() > MAX_ZOOM) fg.zoom(MAX_ZOOM, 250);
            }, 450);
          }}
        />
      )}

      <div className="graph__legend">
        <span className="legend__item">
          <i className="legend__swatch legend__swatch--ring" aria-hidden="true" />
          Focus account
        </span>
        <span className="legend__item">
          <i className="legend__swatch" style={{ background: "var(--seq-700)" }} aria-hidden="true" />
          Higher risk
        </span>
        <span className="legend__item">
          <i className="legend__swatch" style={{ background: "var(--seq-300)" }} aria-hidden="true" />
          Lower risk
        </span>
        <span className="legend__item">
          <i className="legend__rule" style={{ background: "var(--div-pos)" }} aria-hidden="true" />
          Labelled illicit transfer
        </span>
      </div>
    </div>
  );
}
