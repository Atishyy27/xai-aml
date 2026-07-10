// Single source of truth for how a number, a risk score, or a typology is
// rendered. Previously each component re-implemented these inline, which is why
// the same amount could appear as "₹1,20,000", "120000" and "1.2L" on one screen.

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const inrCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});

export const formatCurrency = (n) => (Number.isFinite(n) ? inr.format(n) : "—");
export const formatCompactCurrency = (n) => (Number.isFinite(n) ? inrCompact.format(n) : "—");
export const formatCount = (n) => (Number.isFinite(n) ? n.toLocaleString("en-IN") : "—");
export const formatPercent = (n, digits = 1) => (Number.isFinite(n) ? `${(n * 100).toFixed(digits)}%` : "—");

export const formatDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};

/* Risk tiers map onto the reserved status palette. They always ship with a text
 * label -- colour never carries the meaning on its own. */
export const RISK_TIERS = [
  { min: 0.85, key: "critical", label: "Critical" },
  { min: 0.6, key: "serious", label: "High" },
  { min: 0.5, key: "warning", label: "Elevated" },
  { min: 0.0, key: "good", label: "Low" },
];

export const riskTier = (score) => RISK_TIERS.find((t) => score >= t.min) ?? RISK_TIERS.at(-1);

/* Typologies own a fixed categorical slot. The colour follows the entity, so
 * filtering the table never repaints the survivors. */
export const PATTERN_SLOT = {
  MULE: { slot: 1, label: "Mule", var: "var(--series-1)" },
  SMURFING: { slot: 2, label: "Smurfing", var: "var(--series-2)" },
  LAYERING: { slot: 3, label: "Layering", var: "var(--series-3)" },
  NONE: { slot: 0, label: "No pattern", var: "var(--text-muted)" },
};

export const patternMeta = (p) => PATTERN_SLOT[String(p).toUpperCase()] ?? PATTERN_SLOT.NONE;

/* The backend tags each metric with a unit rather than pre-formatting it, so
 * currency grouping is decided here and only here. */
const UNIT_FORMATTERS = {
  inr: formatCurrency,
  count: formatCount,
  percent: (v) => formatPercent(v, 1),
  percentile: (v) => `${Math.round(v * 100)}th pct`,
};

export const formatMetric = (value, unit) => {
  const fn = UNIT_FORMATTERS[unit];
  return fn && Number.isFinite(value) ? fn(value) : "—";
};

/* Feature values in the SHAP panel are money for some features and counts for
 * others; the backend does not tag them, so infer from the feature name. */
export const formatFeatureValue = (name, value) => {
  if (/total|mean|median|max|std|amount|flow|throughput/.test(name)) return formatCompactCurrency(value);
  if (/ratio|frac/.test(name)) return value.toFixed(2);
  if (/per_day|days/.test(name)) return value.toFixed(1);
  return formatCount(Math.round(value));
};
