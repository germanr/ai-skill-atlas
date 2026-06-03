import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import _ from "lodash";
import PAPERS_RAW from "./src/papers.json";
import ESTIMATES_RAW from "./src/estimates.json";
import CREATIVITY_DATA from "./src/creativity_papers.json";

// ─── Formatters ───
const fmt = (n) => (n == null ? "—" : n.toLocaleString());
const fmtSD = (n) => (n == null ? "—" : (n >= 0 ? "+" : "") + n.toFixed(2));
const fmtSE = (n) => (n == null ? "—" : n.toFixed(3));
const fmtCI = (lo, hi) => (lo == null || hi == null ? "—" : `[${lo >= 0 ? "+" : ""}${lo.toFixed(2)}, ${hi >= 0 ? "+" : ""}${hi.toFixed(2)}]`);

// ─── Palette (matches occ_exposure cream theme) ───
const C = {
  bg: "#F5F2ED",
  surface: "#FFFFFF",
  text: "#1A1A1A",
  textSec: "#6B6B6B",
  textTer: "#A0A0A0",
  accent: "#1A1A1A",
  accentLight: "#F0EEEA",
  border: "#E0DDD8",
  borderHover: "#C5C0B8",
  borderLight: "#EBE7E1",
};

// ─── Domain colors (matches paper Figure 5) ───
const DOMAIN = {
  "Math":              { color: "#7B1F1F", symbol: "circle"   },
  "Coding":            { color: "#D97706", symbol: "square"   },
  "Writing":           { color: "#1F5A2F", symbol: "triangle" },
  "Language":          { color: "#1E40AF", symbol: "cross"    },
  "Science":           { color: "#525252", symbol: "diamond"  },
  "General knowledge": { color: "#3A3A3A", symbol: "diamond"  },
  "Mixed":             { color: "#A0A0A0", symbol: "circle"   },
};

const DOMAIN_ORDER = ["Math", "Coding", "Writing", "Language", "Science", "General knowledge", "Mixed"];

const POPULATION_ORDER = [
  "Elementary",
  "Middle school",
  "High school",
  "Undergraduate",
  "Graduate",
  "Adults general",
  "Professional",
];

const F = {
  sans: "Inter, -apple-system, 'Segoe UI', sans-serif",
  mono: "'Share Tech Mono', 'JetBrains Mono', 'Consolas', monospace",
};

const GCSS = `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
* { box-sizing: border-box; margin: 0; }
body { background: ${C.bg}; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; font-family: ${F.sans}; color: ${C.text}; }
::selection { background: #1A1A1A; color: #FFF; }
@keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px; }
a { color: inherit; text-decoration: none; }
@media (max-width: 900px) {
  .grid-main { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)) !important; }
  .top-row { grid-template-columns: 1fr !important; }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; }
  .detail-layout { max-width: 100% !important; padding-left: 18px !important; padding-right: 18px !important; }
}
@media (max-width: 520px) {
  .grid-main { grid-template-columns: 1fr 1fr !important; gap: 8px !important; }
  .hero-title { font-size: 26px !important; line-height: 1.2 !important; }
  .filter-bar { flex-direction: column; align-items: stretch !important; gap: 8px !important; }
  .filter-group { width: 100%; }
}
`;

// ────────────────────────────────────────────────────────────────────────────
// DerSimonian-Laird random-effects meta-analysis
// (same formula as 4-figures.do lines 295-320)
// ────────────────────────────────────────────────────────────────────────────
function randomEffectsMean(estimates) {
  const valid = estimates.filter(e => e.effect_size_sd != null && e.se != null && e.se > 0);
  if (valid.length === 0) return null;

  const w = valid.map(e => 1 / (e.se ** 2));
  const sumW = w.reduce((a, b) => a + b, 0);
  const muFE = valid.reduce((acc, e, i) => acc + w[i] * e.effect_size_sd, 0) / sumW;
  const Q = valid.reduce((acc, e, i) => acc + w[i] * (e.effect_size_sd - muFE) ** 2, 0);
  const k = valid.length;
  const sumW2 = w.reduce((a, b) => a + b * b, 0);
  const tau2 = Math.max(0, (Q - (k - 1)) / (sumW - sumW2 / sumW));

  const wRE = valid.map(e => 1 / (e.se ** 2 + tau2));
  const sumWRE = wRE.reduce((a, b) => a + b, 0);
  const grandMean = valid.reduce((acc, e, i) => acc + wRE[i] * e.effect_size_sd, 0) / sumWRE;
  const grandSE = 1 / Math.sqrt(sumWRE);

  return {
    mean: grandMean,
    se: grandSE,
    lo: grandMean - 1.96 * grandSE,
    hi: grandMean + 1.96 * grandSE,
    k,
    tau2,
    Q,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Image: lazy-load + domain-themed gradient fallback
// ────────────────────────────────────────────────────────────────────────────
const DOMAIN_GRADIENTS = {
  "Math":              "linear-gradient(135deg, #7B1F1F, #B73B3B)",
  "Coding":            "linear-gradient(135deg, #B45309, #F59E0B)",
  "Writing":           "linear-gradient(135deg, #1F5A2F, #3F8049)",
  "Language":          "linear-gradient(135deg, #1E3A8A, #3B65C7)",
  "Science":           "linear-gradient(135deg, #374151, #6B7280)",
  "General knowledge": "linear-gradient(135deg, #1F2937, #4B5563)",
  "Mixed":             "linear-gradient(135deg, #57534E, #A8A29E)",
};

function PaperImage({ paper, height = 120 }) {
  const [failed, setFailed] = useState(false);
  const domain = paper.learning_domain_primary || "Mixed";
  const gradient = DOMAIN_GRADIENTS[domain] || DOMAIN_GRADIENTS.Mixed;
  const url = `${import.meta.env.BASE_URL}images/${paper.image_filename || ("paper-" + paper.paper_key + ".jpg")}`;

  if (failed) {
    return (
      <div style={{
        height, background: gradient, borderRadius: "6px 6px 0 0",
        display: "flex", alignItems: "flex-end", padding: "12px 16px",
        position: "relative",
      }}>
        <span style={{ fontSize: 10, fontFamily: F.mono, color: "rgba(255,255,255,0.85)", letterSpacing: "0.5px", textTransform: "uppercase" }}>
          {domain}
        </span>
      </div>
    );
  }

  return (
    <div style={{ height, position: "relative", overflow: "hidden", borderRadius: "6px 6px 0 0" }}>
      <img
        src={url}
        alt={paper.title || domain}
        onError={() => setFailed(true)}
        loading="lazy"
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", filter: "brightness(0.78) saturate(1.05)" }}
      />
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "26px 14px 9px",
        background: "linear-gradient(transparent, rgba(0,0,0,0.55))",
      }}>
        <span style={{ fontSize: 10, fontFamily: F.mono, color: "rgba(255,255,255,0.92)", letterSpacing: "0.7px", textTransform: "uppercase" }}>
          {domain} · {paper.year || ""}
        </span>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Paper Tile (clickable card)
// ────────────────────────────────────────────────────────────────────────────
function Tile({ paper, onClick, idx, highlighted }) {
  const [h, setH] = useState(false);
  const isHl = highlighted === paper.paper_key;
  const eff = paper.avg_effect;
  const domain = paper.learning_domain_primary || "Mixed";
  const domainColor = (DOMAIN[domain] || DOMAIN.Mixed).color;

  return (
    <div
      onClick={() => onClick(paper)}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{
        background: isHl ? C.accentLight : C.surface,
        border: `1px solid ${h || isHl ? C.borderHover : C.border}`,
        borderRadius: 6,
        cursor: "pointer",
        transition: "all 0.15s ease",
        transform: h ? "translateY(-2px)" : "none",
        boxShadow: h ? "0 6px 18px rgba(0,0,0,0.08)" : "none",
        animation: `fadeUp 0.35s cubic-bezier(.22,1,.36,1) ${Math.min(idx * 0.02, 0.4)}s both`,
        overflow: "hidden",
        display: "flex", flexDirection: "column",
      }}
    >
      <PaperImage paper={paper} height={120} />
      <div style={{ padding: "12px 14px 14px", flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{ fontSize: 10, color: C.textTer, fontFamily: F.mono, letterSpacing: "0.5px", marginBottom: 4 }}>
          {(paper.country_emoji || "")} {paper.country?.toUpperCase()} · {paper.population_category?.toUpperCase() || ""}
        </div>
        <div style={{
          fontSize: 13.5, fontWeight: 600, fontFamily: F.sans, lineHeight: 1.32, color: C.text, marginBottom: 6,
          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
          minHeight: 36,
        }}>
          {paper.title}
        </div>
        <div style={{ fontSize: 11.5, color: C.textSec, fontFamily: F.sans, marginBottom: 8 }}>
          {paper.authors_short} ({paper.year}) · n = {fmt(paper.n_total)}
        </div>
        <div style={{ marginTop: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 3 }}>
            <span style={{ fontSize: 10, fontFamily: F.mono, color: C.textTer, letterSpacing: "0.5px" }}>AVG EFFECT</span>
            <span style={{ fontSize: 12, fontFamily: F.mono, fontWeight: 600, color: eff == null ? C.textTer : (eff >= 0 ? "#1F5A2F" : "#A02020") }}>
              {fmtSD(eff)} SD
            </span>
          </div>
          <EffectBar value={eff} color={domainColor} />
        </div>
      </div>
    </div>
  );
}

function EffectBar({ value, color }) {
  if (value == null) return <div style={{ height: 3, background: C.borderLight, borderRadius: 2 }} />;
  // map effect from [-1, 1] to [0, 100]
  const center = 50;
  const pct = Math.min(Math.abs(value) * 50, 50);
  const left = value >= 0 ? center : center - pct;
  return (
    <div style={{ position: "relative", height: 4, background: C.borderLight, borderRadius: 2, overflow: "visible" }}>
      <div style={{ position: "absolute", left: `${center}%`, top: -2, width: 1, height: 8, background: C.textTer }} />
      <div style={{
        position: "absolute", top: 0, left: `${left}%`, height: 4,
        width: `${pct}%`, background: color, borderRadius: 2,
        transition: "width 0.3s, left 0.3s",
      }} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Filter Chip
// ────────────────────────────────────────────────────────────────────────────
function Chip({ label, active, onClick, color }) {
  const [h, setH] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{
        padding: "5px 11px",
        fontSize: 12,
        fontFamily: F.sans,
        fontWeight: active ? 600 : 400,
        background: active ? (color || C.accent) : (h ? C.accentLight : "transparent"),
        color: active ? "#FFF" : (h ? C.text : C.textSec),
        border: `1px solid ${active ? (color || C.accent) : C.border}`,
        borderRadius: 999,
        cursor: "pointer",
        transition: "all 0.15s",
        letterSpacing: "0.2px",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Marker shapes (SVG)
// ────────────────────────────────────────────────────────────────────────────
function Marker({ shape, color, size = 7, cx, cy, hollow = false, onMouseEnter, onMouseLeave, onClick, opacity = 1 }) {
  const fill = hollow ? "#FFFFFF" : color;
  const stroke = color;
  const strokeWidth = hollow ? 1.6 : 1.2;
  const handlers = { onMouseEnter, onMouseLeave, onClick, style: { cursor: onClick ? "pointer" : "default" } };
  const baseProps = { fill, stroke, strokeWidth, opacity };

  switch (shape) {
    case "circle":
      return <circle cx={cx} cy={cy} r={size} {...baseProps} {...handlers} />;
    case "square":
      return <rect x={cx - size} y={cy - size} width={size * 2} height={size * 2} {...baseProps} {...handlers} />;
    case "triangle":
      return <polygon points={`${cx},${cy - size} ${cx - size},${cy + size * 0.75} ${cx + size},${cy + size * 0.75}`} {...baseProps} {...handlers} />;
    case "diamond":
      return <polygon points={`${cx},${cy - size} ${cx + size},${cy} ${cx},${cy + size} ${cx - size},${cy}`} {...baseProps} {...handlers} />;
    case "cross":
      return (
        <g {...handlers}>
          <line x1={cx - size} y1={cy - size} x2={cx + size} y2={cy + size} stroke={color} strokeWidth={1.8} opacity={opacity} />
          <line x1={cx - size} y1={cy + size} x2={cx + size} y2={cy - size} stroke={color} strokeWidth={1.8} opacity={opacity} />
        </g>
      );
    default:
      return <circle cx={cx} cy={cy} r={size} {...baseProps} {...handlers} />;
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Forest Plot (centerpiece — interactive replica of paper Figure 5)
// ────────────────────────────────────────────────────────────────────────────
function ForestPlot({ estimates, papers, onSelectPaper, width = 900 }) {
  const [hovered, setHovered] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Filter to plotable estimates (effect_size_sd + se required)
  const plotable = estimates
    .filter(e => e.effect_size_sd != null && e.se != null && e.se > 0)
    .map(e => ({
      ...e,
      ci_lo: e.ci_lower != null ? e.ci_lower : e.effect_size_sd - 1.96 * e.se,
      ci_hi: e.ci_upper != null ? e.ci_upper : e.effect_size_sd + 1.96 * e.se,
    }));

  // Sort all estimates by effect size descending (own paper treated like any other)
  const sorted = [...plotable].sort((a, b) => b.effect_size_sd - a.effect_size_sd);

  // Grand-mean band
  const re = randomEffectsMean(plotable);

  // Precision-weighted marker scaling (used in dashboard variant)
  // Layout
  const labelWidth = 280;
  const padLeft = 12;
  const padRight = 24;
  const padTop = 36;
  const padBottom = 56;
  const rowHeight = 24;
  const plotHeight = sorted.length * rowHeight;
  const totalHeight = padTop + plotHeight + padBottom;
  const xMin = -1.0;
  const xMax = 1.0;
  const xRange = xMax - xMin;
  const plotWidth = width - labelWidth - padLeft - padRight;

  const xScale = (x) => labelWidth + padLeft + ((x - xMin) / xRange) * plotWidth;
  const yScale = (i) => padTop + (i + 0.5) * rowHeight;

  // Show legend for present domains
  const presentDomains = Array.from(new Set(plotable.map(e => e.learning_domain).filter(Boolean)));

  // Tick marks
  const xTicks = [-1.0, -0.5, 0, 0.5, 1.0];

  if (plotable.length === 0) {
    return (
      <div style={{
        padding: "60px 20px", textAlign: "center", color: C.textSec,
        background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
      }}>
        No estimates match the current filters.
      </div>
    );
  }

  // Style tokens (refined editorial)
  const bandColor = "#1E40AF";
  const bandOpacity = 0.08;
  const ciOpacity = 0.45;
  const ciStrokeWidth = 1.4;
  const labelFontSize = 10.5;

  return (
    <div style={{
      position: "relative",
      background: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 8,
      padding: "8px 0 0",
      overflow: "visible",
    }}>
      <svg width={width} height={totalHeight} style={{ display: "block", maxWidth: "100%" }} viewBox={`0 0 ${width} ${totalHeight}`}>
        {/* Zebra striping: alternating row backgrounds */}
        {sorted.map((_, i) => i % 2 === 1 && (
          <rect
            key={`zebra-${i}`}
            x={padLeft}
            y={padTop + i * rowHeight}
            width={width - padLeft - padRight}
            height={rowHeight}
            fill="#FAFAFA"
          />
        ))}

        {/* Grand-mean shaded band */}
        {re && (
          <>
            <rect
              x={xScale(re.lo)}
              y={padTop}
              width={Math.max(0, xScale(re.hi) - xScale(re.lo))}
              height={plotHeight}
              fill={bandColor}
              opacity={bandOpacity}
            />
            <line
              x1={xScale(re.mean)}
              y1={padTop}
              x2={xScale(re.mean)}
              y2={padTop + plotHeight}
              stroke={bandColor}
              strokeWidth={1.2}
              opacity={0.45}
            />
          </>
        )}

        {/* X = 0 dashed line */}
        <line
          x1={xScale(0)}
          y1={padTop}
          x2={xScale(0)}
          y2={padTop + plotHeight}
          stroke={C.textTer}
          strokeDasharray="3 3"
          strokeWidth={1}
        />

        {/* X-axis grid lines */}
        {xTicks.filter(t => t !== 0).map(t => (
          <line
            key={`grid-${t}`}
            x1={xScale(t)}
            y1={padTop}
            x2={xScale(t)}
            y2={padTop + plotHeight}
            stroke={C.borderLight}
            strokeWidth={0.6}
          />
        ))}

        {/* Estimates */}
        {sorted.map((e, i) => {
          const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
          const cx = xScale(Math.max(xMin, Math.min(xMax, e.effect_size_sd)));
          const cy = yScale(i);
          const ciLoX = xScale(Math.max(xMin, e.ci_lo));
          const ciHiX = xScale(Math.min(xMax, e.ci_hi));
          const isHl = hovered === e.estimate_id;

          // Build label: prefer study_label, else paper authors + outcome
          let label = e.study_label || `${e.paper_key}`;
          if (label.length > 44) label = label.slice(0, 42) + "…";

          return (
            <g key={e.estimate_id}
               onMouseEnter={(ev) => {
                 setHovered(e.estimate_id);
                 const svgEl = ev.currentTarget.ownerSVGElement;
                 const rect = svgEl.getBoundingClientRect();
                 setTooltipPos({ x: cx, y: cy });
               }}
               onMouseLeave={() => setHovered(null)}
               onClick={() => {
                 const p = papers.find(p => p.paper_key === e.paper_key);
                 if (p) onSelectPaper(p);
               }}
               style={{ cursor: "pointer" }}
            >
              {/* hover hit area (full row) */}
              <rect
                x={padLeft}
                y={cy - rowHeight / 2}
                width={width - padLeft - padRight}
                height={rowHeight}
                fill={isHl ? C.accentLight : "transparent"}
                opacity={0.6}
              />

              {/* Study label */}
              <text
                x={labelWidth + padLeft - 8}
                y={cy + 3}
                fontSize={labelFontSize}
                fontFamily={F.sans}
                fill={C.textSec}
                fontWeight={400}
                textAnchor="end"
              >
                {label}
              </text>

              {/* CI line + caps in domain color */}
              <line x1={ciLoX} y1={cy} x2={ciHiX} y2={cy} stroke={dom.color} strokeWidth={ciStrokeWidth} opacity={ciOpacity} />
              <line x1={ciLoX} y1={cy - 3} x2={ciLoX} y2={cy + 3} stroke={dom.color} strokeWidth={ciStrokeWidth} opacity={ciOpacity} />
              <line x1={ciHiX} y1={cy - 3} x2={ciHiX} y2={cy + 3} stroke={dom.color} strokeWidth={ciStrokeWidth} opacity={ciOpacity} />

              {/* Marker */}
              <Marker
                shape={dom.symbol}
                color={dom.color}
                size={isHl ? 8 : 6.5}
                cx={cx}
                cy={cy}
                hollow={dom.symbol === "cross"}
                opacity={1}
              />
            </g>
          );
        })}

        {/* X-axis */}
        <line
          x1={labelWidth + padLeft}
          y1={padTop + plotHeight + 6}
          x2={labelWidth + padLeft + plotWidth}
          y2={padTop + plotHeight + 6}
          stroke={C.text}
          strokeWidth={0.8}
        />
        {xTicks.map(t => (
          <g key={`tick-${t}`}>
            <line
              x1={xScale(t)}
              y1={padTop + plotHeight + 6}
              x2={xScale(t)}
              y2={padTop + plotHeight + 10}
              stroke={C.text}
              strokeWidth={0.8}
            />
            <text
              x={xScale(t)}
              y={padTop + plotHeight + 22}
              fontSize={11}
              fontFamily={F.mono}
              fill={C.textSec}
              textAnchor="middle"
            >
              {t >= 0 ? "+" : ""}{t.toFixed(1)}
            </text>
          </g>
        ))}
        <text
          x={labelWidth + padLeft + plotWidth / 2}
          y={padTop + plotHeight + 44}
          fontSize={12.5}
          fontFamily={F.sans}
          fill={C.text}
          textAnchor="middle"
          fontWeight={500}
        >
          Effect size (Standard Deviations)
        </text>

        {/* Grand-mean label */}
        {re && (
          <g>
            <text
              x={xScale(re.mean) + 8}
              y={padTop - 6}
              fontSize={11}
              fontFamily={F.sans}
              fill={bandColor}
              fontWeight={600}
            >
              Grand mean = {fmtSD(re.mean)} (k={re.k})
            </text>
            <line
              x1={xScale(re.mean)}
              y1={padTop - 14}
              x2={xScale(re.mean)}
              y2={padTop - 2}
              stroke={bandColor}
              strokeWidth={1.2}
              opacity={0.7}
            />
          </g>
        )}
      </svg>

      {/* Legend (11 o'clock: top-left inside plot area, just to the right of the label column) */}
      <div style={{
        position: "absolute", top: 40, left: 296,
        background: "rgba(255,255,255,0.92)", border: `1px solid ${C.borderLight}`, borderRadius: 6,
        padding: "8px 12px", display: "flex", flexDirection: "column", gap: 4,
        fontSize: 11, fontFamily: F.sans,
      }}>
        {presentDomains.sort((a, b) => DOMAIN_ORDER.indexOf(a) - DOMAIN_ORDER.indexOf(b)).map(d => {
          const dom = DOMAIN[d] || DOMAIN.Mixed;
          return (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <svg width={14} height={14} style={{ flexShrink: 0 }}>
                <Marker shape={dom.symbol} color={dom.color} size={5.5} cx={7} cy={7} hollow={dom.symbol === "cross"} />
              </svg>
              <span style={{ color: C.textSec }}>{d}</span>
            </div>
          );
        })}
      </div>

      {/* Tooltip (OWID-style white card) */}
      {hovered && (() => {
        const e = plotable.find(x => x.estimate_id === hovered);
        if (!e) return null;
        const p = papers.find(p => p.paper_key === e.paper_key);
        const effColor = e.effect_size_sd >= 0 ? "#1F5A2F" : "#A02020";
        const rowLabel = {
          fontSize: 11.5, color: C.textSec, fontFamily: F.sans,
          marginBottom: 2, lineHeight: 1.3,
        };
        const rowValue = {
          fontSize: 16, fontWeight: 700, color: C.text,
          fontFamily: F.sans, lineHeight: 1.2,
        };
        const rowWrap = {
          padding: "10px 14px",
          borderTop: `1px solid ${C.borderLight}`,
        };
        // Flip the tooltip above the marker when there's not enough room below
        const tooltipH = 250;
        const wouldOverflow = tooltipPos.y - 30 + tooltipH > totalHeight - 8;
        const topPx = wouldOverflow
          ? Math.max(8, tooltipPos.y - tooltipH + 14)
          : Math.max(8, tooltipPos.y - 30);
        return (
          <div style={{
            position: "absolute",
            left: Math.min(tooltipPos.x + 14, width - 270),
            top: topPx,
            background: "#FFFFFF",
            color: C.text,
            border: `1px solid ${C.borderHover}`,
            borderRadius: 4,
            fontFamily: F.sans,
            pointerEvents: "none",
            width: 260,
            zIndex: 50,
            boxShadow: "0 4px 14px rgba(0,0,0,0.10)",
          }}>
            {/* Header strip */}
            <div style={{
              padding: "10px 14px",
              background: "#F3F1EC",
            }}>
              <div style={{ fontSize: 13.5, fontWeight: 700, color: C.text, lineHeight: 1.25 }}>
                {p?.authors_short} ({p?.year})
              </div>
              <div style={{ fontSize: 11.5, color: C.textSec, marginTop: 2, lineHeight: 1.3 }}>
                {e.study_label && e.study_label !== `${p?.authors_short} (${p?.year})`
                  ? e.study_label.replace(`${p?.authors_short}, `, "").replace(`${p?.authors_short} (${p?.year}), `, "")
                  : (p?.country_emoji + " " + (p?.country || ""))}
              </div>
            </div>
            {/* Effect size row */}
            <div style={rowWrap}>
              <div style={rowLabel}>Effect size <span style={{ color: C.textTer }}>(SD)</span></div>
              <div style={{ ...rowValue, color: effColor }}>{fmtSD(e.effect_size_sd)}</div>
            </div>
            {/* 95% CI row */}
            <div style={rowWrap}>
              <div style={rowLabel}>95% confidence interval</div>
              <div style={{ ...rowValue, fontSize: 13.5, fontFamily: F.mono, fontWeight: 500 }}>
                {fmtCI(e.ci_lo, e.ci_hi)}
              </div>
            </div>
            {/* Sample size row */}
            <div style={rowWrap}>
              <div style={rowLabel}>Sample size <span style={{ color: C.textTer }}>(participants)</span></div>
              <div style={rowValue}>{fmt(e.n_total)}</div>
            </div>
            {/* Estimand + method row */}
            {(e.estimand || e.estimation_method) && (
              <div style={rowWrap}>
                <div style={rowLabel}>Estimand <span style={{ color: C.textTer }}>(method)</span></div>
                <div style={{ ...rowValue, fontSize: 12, fontFamily: F.mono }}>
                  {e.estimand || "—"}
                  {e.estimation_method && (
                    <span style={{ color: C.textTer, fontWeight: 400 }}> · {e.estimation_method}</span>
                  )}
                </div>
              </div>
            )}
            {/* Domain + timing footer */}
            <div style={{
              ...rowWrap,
              fontSize: 11, color: C.textTer, fontFamily: F.sans,
            }}>
              <span style={{
                display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                background: (DOMAIN[e.learning_domain] || DOMAIN.Mixed).color,
                marginRight: 6, verticalAlign: "middle",
              }} />
              {e.learning_domain} · {e.outcome_timing}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Inclusion Criteria + Submission boxes
// ────────────────────────────────────────────────────────────────────────────
function InclusionBox() {
  return (
    <div style={{
      background: C.accentLight,
      border: `1px solid ${C.border}`,
      borderRadius: 8,
      padding: "16px 18px",
      fontSize: 13,
      fontFamily: F.sans,
      lineHeight: 1.55,
      color: C.text,
    }}>
      <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px", marginBottom: 7 }}>
        INCLUSION CRITERIA
      </div>
      Studies are included if they (1) <strong>randomly assign</strong> access to AI vs. a no-AI control (or use a clean quasi-experimental design with an unassisted assessment), and (2) report at least <strong>50 total participants</strong>. Effect sizes are standardized in SD units of the control group where possible.
    </div>
  );
}

function SubmissionBox() {
  return (
    <div style={{
      background: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 8,
      padding: "16px 18px",
      fontSize: 13,
      fontFamily: F.sans,
      lineHeight: 1.55,
      color: C.text,
    }}>
      <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px", marginBottom: 7 }}>
        SUGGEST A PAPER
      </div>
      Know of a study we missed? Send the citation, effect size, SE, and sample size to{" "}
      <a
        href="mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20paper%20suggestion&body=Citation%3A%20%0APaper%20PDF%2Flink%3A%20%0AEffect%20size%20(SD)%3A%20%0AStandard%20error%3A%20%0ASample%20size%3A%20%0ANotes%3A%20"
        style={{ color: C.text, fontWeight: 600, borderBottom: `1.5px solid ${C.text}` }}
      >
        learning_study@middlebury.edu
      </a>{" "}
      and I'll add it.
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Report Card (detail view)
// ────────────────────────────────────────────────────────────────────────────
// ── Per-dimension icon map (used by all prototypes) ──
const DIM_ICON = {
  title:        "📄",
  authors:      "👥",
  year:         "📅",
  venue:        "🏛",
  country:      "🌍",
  population:   "🧑‍🎓",
  setting:      "🏫",
  lab_vs_field: "🔬",
  study_design: "🎲",
  ai_tool:      "🤖",
  ai_design:    "🛠",
  n_total:      "🔢",
  incentives:   "💰",
  domain:       "🧠",
  comparison:   "📊",
  outcome:      "🎯",
  summary:      "📝",
};

const COMPARISON_LABEL = {
  ai_vs_bau:    "AI vs business-as-usual control",
  ai_vs_active: "AI vs active control",
  ai_design:    "Off-the-shelf vs scaffolded AI",
};

function ReportCard({ paper, estimates, onBack }) {
  const myEstsAll = estimates.filter(e => e.paper_key === paper.paper_key);
  const myEsts = myEstsAll.filter(e => e.is_subgroup !== true);
  const mySubgroups = myEstsAll.filter(e => e.is_subgroup === true);
  // Group subgroups by their `subgroup` label (fallback: "Other")
  const subgroupsByCategory = mySubgroups.reduce((acc, e) => {
    const k = e.subgroup || "Other";
    (acc[k] = acc[k] || []).push(e);
    return acc;
  }, {});

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [paper.paper_key]);

  const pdfHref = paper.pdf_filename
    ? `${import.meta.env.BASE_URL}pdfs/${encodeURI(paper.pdf_filename)}`
    : paper.pdf_url || null;

  const bibtex = `@article{${paper.paper_key},
  title   = {${paper.title}},
  author  = {${paper.authors_full || paper.authors_short}},
  year    = {${paper.year || ""}},
  journal = {${paper.venue || "Working paper"}}
}`;

  const copyBib = () => {
    navigator.clipboard.writeText(bibtex).then(() => {
      // visual hint via state
    });
  };

  const dom = DOMAIN[paper.learning_domain_primary] || DOMAIN.Mixed;

  return (
    <div style={{ background: C.bg, minHeight: "100vh", animation: "fadeIn 0.25s" }}>
      {/* Hero */}
      <div style={{ position: "relative", height: 280, overflow: "hidden", background: DOMAIN_GRADIENTS[paper.learning_domain_primary] || DOMAIN_GRADIENTS.Mixed }}>
        <PaperImageHero paper={paper} />
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.6) 100%)",
        }} />
        <div style={{
          position: "absolute", left: 0, right: 0, bottom: 0,
          padding: "22px 28px 24px",
          maxWidth: 900,
          margin: "0 auto",
        }} className="detail-layout">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <button
              onClick={onBack}
              style={{
                background: "rgba(255,255,255,0.18)", color: "#FFF",
                border: "1px solid rgba(255,255,255,0.35)", borderRadius: 4,
                padding: "5px 12px", fontSize: 12, fontFamily: F.sans, cursor: "pointer",
                backdropFilter: "blur(8px)",
              }}>← Back</button>
            <span style={{ fontSize: 10.5, fontFamily: F.mono, color: "rgba(255,255,255,0.85)", letterSpacing: "0.7px" }}>
              {paper.learning_domain_primary?.toUpperCase()} · {paper.population_category?.toUpperCase()} · {paper.country_emoji} {paper.country?.toUpperCase()}
            </span>
          </div>
          <h1 style={{
            fontSize: 30, fontWeight: 700, color: "#FFF", fontFamily: F.sans,
            lineHeight: 1.18, marginBottom: 10, textShadow: "0 2px 12px rgba(0,0,0,0.3)",
          }}>{paper.title}</h1>
          <div style={{ fontSize: 14, color: "rgba(255,255,255,0.92)", fontFamily: F.sans }}>
            {paper.authors_full || paper.authors_short} · <span style={{ fontFamily: F.mono }}>{paper.venue}</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "28px 28px 80px" }} className="detail-layout">
        {/* Action bar */}
        <div style={{ display: "flex", gap: 10, marginBottom: 22, flexWrap: "wrap" }}>
          {pdfHref && (
            <a
              href={pdfHref}
              target="_blank"
              rel="noreferrer"
              style={{
                background: C.text, color: "#FFF",
                padding: "9px 16px", fontSize: 12.5, borderRadius: 5,
                fontFamily: F.sans, fontWeight: 500,
                display: "inline-flex", alignItems: "center", gap: 6,
              }}>📄 Download PDF</a>
          )}
          <button
            onClick={copyBib}
            style={{
              background: C.surface, color: C.text, border: `1px solid ${C.border}`,
              padding: "9px 16px", fontSize: 12.5, borderRadius: 5,
              fontFamily: F.sans, fontWeight: 500, cursor: "pointer",
              display: "inline-flex", alignItems: "center", gap: 6,
            }}>📋 Copy BibTeX</button>
          <a
            href={`mailto:learning_study@middlebury.edu?subject=${encodeURIComponent("The AI and Human Skill Atlas — correction for " + paper.authors_short + " (" + paper.year + ")")}`}
            style={{
              background: C.surface, color: C.textSec, border: `1px solid ${C.border}`,
              padding: "9px 16px", fontSize: 12.5, borderRadius: 5,
              fontFamily: F.sans, fontWeight: 500,
              display: "inline-flex", alignItems: "center", gap: 6,
            }}>✏ Suggest correction</a>
        </div>

        <PrototypeA paper={paper} />

        {/* Effect sizes */}
        <Section title={`Effect sizes (${myEsts.length})`}>
          <div style={{
            background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, overflow: "hidden",
          }}>
            {myEsts.map((e, idx) => (
              <EstimateRow key={e.estimate_id} est={e} domain={dom} idx={idx} last={idx === myEsts.length - 1} />
            ))}
          </div>
        </Section>

        {/* Treatments and controls */}
        <Section title="Treatments & controls">
          <div style={{
            background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
            padding: "14px 18px", fontSize: 13.5, lineHeight: 1.6,
          }}>
            {myEsts.length > 0 && myEsts[0] && (
              <>
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textTer, letterSpacing: "1px", marginBottom: 4 }}>TREATMENT</div>
                  <div style={{ color: C.text }}>{myEsts[0].treatment}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textTer, letterSpacing: "1px", marginBottom: 4 }}>CONTROL</div>
                  <div style={{ color: C.text }}>{myEsts[0].control}</div>
                </div>
              </>
            )}
          </div>
        </Section>

        {/* Subgroup / heterogeneity estimates (always visible on the report card) */}
        {mySubgroups.length > 0 && (
          <Section title={`Subgroup & heterogeneity estimates (${mySubgroups.length})`}>
            <div style={{
              background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, overflow: "hidden",
            }}>
              {Object.entries(subgroupsByCategory).map(([category, rows], gIdx) => (
                <div key={category} style={{
                  borderBottom: gIdx === Object.keys(subgroupsByCategory).length - 1 ? "none" : `1px solid ${C.borderLight}`,
                }}>
                  <div style={{
                    padding: "10px 18px 6px",
                    background: C.accentLight,
                    fontSize: 11, fontFamily: F.mono, color: C.textSec,
                    letterSpacing: "1px", textTransform: "uppercase",
                  }}>
                    {category}
                  </div>
                  {rows.map((e, idx) => (
                    <EstimateRow key={e.estimate_id} est={e} domain={dom} idx={idx} last={idx === rows.length - 1} />
                  ))}
                </div>
              ))}
            </div>
            <div style={{
              fontSize: 11.5, color: C.textTer, marginTop: 8, fontStyle: "italic",
              fontFamily: F.sans,
            }}>
              Subgroup / heterogeneity rows are excluded from the main forest plot by default. Use the "Subgroups" filter on the browse page to include them.
            </div>
          </Section>
        )}

        {/* Citation */}
        <Section title="How to cite">
          <pre style={{
            background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
            padding: "12px 16px", fontSize: 12, fontFamily: F.mono, color: C.text,
            overflowX: "auto", whiteSpace: "pre-wrap", lineHeight: 1.5,
          }}>{bibtex}</pre>
        </Section>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Prototype A — Each dimension is a row with an emoji icon
// ────────────────────────────────────────────────────────────────────────────
function PrototypeA({ paper }) {
  const rows = [
    { icon: DIM_ICON.title,        label: "Title",         value: paper.title },
    { icon: DIM_ICON.authors,      label: "Authors",       value: paper.authors_full || paper.authors_short },
    { icon: DIM_ICON.year,         label: "Year",          value: paper.year },
    { icon: DIM_ICON.venue,        label: "Venue",         value: paper.venue },
    { icon: DIM_ICON.country,      label: "Country",       value: (paper.country_emoji || "") + " " + (paper.country || "") },
    { icon: DIM_ICON.population,   label: "Population",    value: paper.population_category },
    { icon: DIM_ICON.lab_vs_field, label: "Setting",       value: paper.lab_vs_field },
    { icon: DIM_ICON.study_design, label: "Study design",  value: paper.study_design },
    { icon: DIM_ICON.n_total,      label: "Sample size",   value: fmt(paper.n_total) },
    { icon: DIM_ICON.incentives,   label: "Performance incentive", value: paper.incentives },
    { icon: DIM_ICON.ai_tool,      label: "AI tool",       value: paper.ai_tool },
    { icon: DIM_ICON.ai_design,    label: "AI design",     value: paper.ai_design },
    { icon: DIM_ICON.domain,       label: "Learning domain", value: paper.learning_domain_primary },
  ];
  const hasStructured = paper.summary_setup || paper.summary_strategy || paper.summary_results;
  return (
    <>
      {hasStructured ? (
        <div style={{
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
          marginBottom: 20, overflow: "hidden",
        }}>
          {[
            { icon: "🧪", label: "Setup",              text: paper.summary_setup },
            { icon: "🧮", label: "Empirical strategy", text: paper.summary_strategy },
            { icon: "🏁", label: "Key results",        text: paper.summary_results },
          ].filter(b => b.text).map((b, i, arr) => (
            <div key={b.label} style={{
              padding: "14px 20px",
              borderBottom: i === arr.length - 1 ? "none" : `1px solid ${C.borderLight}`,
              fontSize: 14, lineHeight: 1.6,
            }}>
              <div style={{
                fontSize: 10.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px",
                marginBottom: 6,
              }}>{b.icon} {b.label.toUpperCase()}</div>
              <div style={{ color: C.text }}>{b.text}</div>
            </div>
          ))}
        </div>
      ) : paper.summary && (
        <div style={{
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
          padding: "16px 20px", marginBottom: 20, fontSize: 14.5, lineHeight: 1.65,
          color: C.text,
        }}>
          {paper.summary}
        </div>
      )}
      <div style={{
        background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
        marginBottom: 26, overflow: "hidden",
      }}>
        {rows.map((r, i) => (
          <div key={r.label} style={{
            display: "grid", gridTemplateColumns: "44px 160px 1fr",
            alignItems: "baseline", gap: 4,
            padding: "11px 18px",
            background: i % 2 === 1 ? "#FAFAFA" : "transparent",
            borderBottom: i === rows.length - 1 ? "none" : `1px solid ${C.borderLight}`,
            fontSize: 14,
          }}>
            <span style={{ fontSize: 18, lineHeight: 1 }}>{r.icon}</span>
            <span style={{ fontSize: 11, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px", textTransform: "uppercase" }}>{r.label}</span>
            <span style={{ color: C.text, lineHeight: 1.45 }}>{r.value || "—"}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function PaperImageHero({ paper }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  const url = `${import.meta.env.BASE_URL}images/${paper.image_filename || ("paper-" + paper.paper_key + ".jpg")}`;
  return (
    <img
      src={url}
      alt={paper.title}
      onError={() => setFailed(true)}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.78) saturate(1.05)" }}
    />
  );
}

function Stat({ label, value, small, badge, color }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontFamily: F.mono, color: C.textTer, letterSpacing: "1px", marginBottom: 5, textTransform: "uppercase" }}>{label}</div>
      <div style={{
        fontSize: small ? 14 : (badge ? 13 : 19),
        fontWeight: badge ? 600 : (small ? 500 : 600),
        color: color || C.text,
        fontFamily: badge ? F.mono : F.sans,
        lineHeight: 1.25,
      }}>
        {value || "—"}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <h3 style={{
        fontSize: 11.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1.2px",
        textTransform: "uppercase", marginBottom: 10, fontWeight: 500,
      }}>{title}</h3>
      {children}
    </div>
  );
}

function EstimateRow({ est, domain, last, idx = 0 }) {
  // Mini number line: -1 to +1 with marker
  const range = 2.0; // [-1, +1]
  const pct = ((Math.max(-1, Math.min(1, est.effect_size_sd)) + 1) / range) * 100;
  return (
    <div style={{
      padding: "14px 18px",
      background: idx % 2 === 1 ? "#FAFAFA" : "transparent",
      borderBottom: last ? "none" : `1px solid ${C.borderLight}`,
      fontSize: 13,
    }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 110px", gap: 16, alignItems: "center", marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 3 }}>{est.outcome}</div>
          <div style={{ fontSize: 11.5, color: C.textSec, fontFamily: F.sans }}>
            {est.outcome_timing} · n = {fmt(est.n_total)} · {est.learning_domain}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{
            fontSize: 16, fontWeight: 600, fontFamily: F.mono,
            color: est.effect_size_sd >= 0 ? "#1F5A2F" : "#A02020",
          }}>{fmtSD(est.effect_size_sd)}</div>
          <div style={{ fontSize: 10.5, color: C.textTer, fontFamily: F.mono }}>SD</div>
        </div>
      </div>
      {/* Number line */}
      <div style={{ position: "relative", height: 20, marginBottom: 4 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 9, height: 2, background: C.borderLight, borderRadius: 1 }} />
        <div style={{ position: "absolute", left: "50%", top: 4, width: 1, height: 12, background: C.textTer }} />
        {est.ci_lower != null && est.ci_upper != null && (
          <div style={{
            position: "absolute",
            left: `${Math.max(0, ((Math.max(-1, est.ci_lower) + 1) / range) * 100)}%`,
            width: `${Math.min(100, ((Math.min(1, est.ci_upper) - Math.max(-1, est.ci_lower)) / range) * 100)}%`,
            top: 8, height: 4, background: domain.color, opacity: 0.4, borderRadius: 2,
          }} />
        )}
        <div style={{
          position: "absolute", left: `${pct}%`, top: 4, width: 12, height: 12,
          background: domain.color, borderRadius: domain.symbol === "square" ? 0 : "50%",
          transform: "translateX(-50%)",
          border: `1.5px solid ${domain.color}`,
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontFamily: F.mono, color: C.textTer }}>
        <span>−1.0</span><span>0</span><span>+1.0</span>
      </div>
      {est.ci_lower != null && (
        <div style={{ fontSize: 11.5, color: C.textSec, marginTop: 6, fontFamily: F.mono }}>
          95% CI {fmtCI(est.ci_lower, est.ci_upper)} · SE {fmtSE(est.se)}
        </div>
      )}
      {est.treatment && (
        <div style={{ fontSize: 12, color: C.textSec, marginTop: 8, lineHeight: 1.5 }}>
          <span style={{ fontWeight: 500, color: C.text }}>{est.treatment}</span>{" "}vs{" "}
          <span style={{ color: C.textSec }}>{est.control}</span>
        </div>
      )}
      {(est.estimand || est.estimation_method) && (
        <div style={{ display: "flex", gap: 8, marginTop: 9, flexWrap: "wrap", alignItems: "center" }}>
          {est.estimand && (
            <span style={{
              fontSize: 10, fontFamily: F.mono, fontWeight: 600, letterSpacing: "0.5px",
              color: "#FFF", background: C.text, padding: "2px 7px", borderRadius: 3,
              textTransform: "uppercase",
            }} title="Estimand (parameter identified)">{est.estimand}</span>
          )}
          {est.estimation_method && (
            <span style={{
              fontSize: 11, fontFamily: F.mono, color: C.textSec,
            }} title="Estimation method">{est.estimation_method}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// About Page
// ────────────────────────────────────────────────────────────────────────────
function AboutPage({ onBack, nPapers, nEstimates, papers, onSelectPaper }) {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  // Sort papers chronologically (newest first) for the data-sources list
  const sortedPapers = [...papers].sort((a, b) => (b.year || 0) - (a.year || 0));

  const sectionLabel = {
    fontSize: 11, fontWeight: 500, color: C.textTer,
    marginBottom: 12, letterSpacing: "0.5px",
    fontFamily: F.mono, textTransform: "uppercase",
  };

  return (
    <div style={{ background: C.bg, minHeight: "100vh", animation: "fadeIn 0.25s" }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${C.border}`,
        background: `${C.bg}EE`,
        backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
            <h1 className="hero-title" style={{
              fontSize: 22, fontWeight: 700, fontFamily: F.sans, color: C.text,
              lineHeight: 1.2, margin: 0,
            }}>
              The AI and Human Skill Atlas
            </h1>
            <button
              onClick={onBack}
              style={{
                background: "none", border: "none", cursor: "pointer",
                fontSize: 14, fontFamily: F.sans, color: C.text,
                borderBottom: `1.5px solid ${C.text}`, padding: "3px 0",
                letterSpacing: "0.3px",
              }}>← Back to browse</button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 28px 100px" }} className="detail-layout">
        {/* The single white card, occ_exposure-style */}
        <div style={{
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
          padding: "28px",
          animation: "fadeUp 0.3s cubic-bezier(.22,1,.36,1) both",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, fontFamily: F.sans, margin: 0, color: C.text }}>About this resource</h2>
            <button onClick={onBack} title="Close"
              style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer", color: C.textTer, padding: "0 4px", lineHeight: 1 }}>×</button>
          </div>

          <p style={{ fontSize: 14, lineHeight: 1.7, color: C.textSec, margin: "0 0 24px", maxWidth: 720 }}>
            This site curates experimental evidence on the learning impact of generative AI. It currently covers <strong style={{ color: C.text }}>{nPapers} papers</strong> and <strong style={{ color: C.text }}>{nEstimates} effect sizes</strong> from randomized studies (and a handful of well-identified quasi-experiments) conducted worldwide. Effect sizes are standardized in SD units of the control group where possible. The forest-plot grand mean uses a random-effects model (DerSimonian–Laird).
          </p>

          {/* Inclusion criteria */}
          <div style={sectionLabel}>Inclusion criteria</div>
          <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
            <div style={{
              padding: "14px 16px", background: C.bg, borderRadius: 6, border: `1px solid ${C.borderLight}`,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 4 }}>1. Source of variation</div>
              <div style={{ color: C.textSec, lineHeight: 1.55, fontSize: 12.5 }}>The study randomly assigns access to AI vs. a no-AI control, or uses a clean quasi-experimental design with an unassisted assessment.</div>
            </div>
            <div style={{
              padding: "14px 16px", background: C.bg, borderRadius: 6, border: `1px solid ${C.borderLight}`,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 4 }}>2. Sample size</div>
              <div style={{ color: C.textSec, lineHeight: 1.55, fontSize: 12.5 }}>The study has at least 50 total participants.</div>
            </div>
          </div>

          {/* Data sources — one cream card per paper, clickable to open report */}
          <div style={sectionLabel}>Data sources · {sortedPapers.length} papers</div>
          <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
            {sortedPapers.map(p => {
              const pdfHref = p.pdf_filename
                ? `${import.meta.env.BASE_URL}pdfs/${encodeURI(p.pdf_filename)}`
                : null;
              return (
                <div key={p.paper_key}
                  onClick={() => onSelectPaper(p)}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = C.borderHover}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = C.borderLight}
                  style={{
                    padding: "14px 16px", background: C.bg, borderRadius: 6,
                    border: `1px solid ${C.borderLight}`,
                    cursor: "pointer", transition: "border-color 0.15s",
                  }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 4 }}>
                    {p.authors_short} ({p.year}) — "{p.title}"
                    {p.venue && <span style={{ fontWeight: 400, color: C.textTer, fontSize: 11, marginLeft: 8 }}>{p.venue}</span>}
                  </div>
                  <div style={{ color: C.textSec, lineHeight: 1.55, fontSize: 12.5 }}>
                    {p.country_emoji} {p.country} · {p.population_category} · {p.lab_vs_field} · {p.study_design} · n = {fmt(p.n_total)}
                    {pdfHref && (
                      <>
                        {" · "}
                        <a href={pdfHref} target="_blank" rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          style={{ color: C.textSec, borderBottom: `1px dotted ${C.borderHover}` }}>PDF</a>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Methodology notes */}
          <div style={sectionLabel}>Methodology notes</div>
          <ul style={{ fontSize: 13, lineHeight: 1.7, color: C.textSec, margin: "0 0 28px", paddingLeft: 20 }}>
            <li>Effect sizes are standardized in SD units of the control group. Some papers reported raw effects; SEs were back-calculated using sample sizes or recomputed using control-group SDs.</li>
            <li>Forest-plot grand mean uses the random-effects (DerSimonian–Laird) estimator. The 95% confidence band reflects between-study heterogeneity.</li>
            <li>The default view excludes outcomes measured <em>with</em> AI access (e.g., Bastani assisted-practice scores), since those reflect AI-augmented performance rather than learning. Toggle "Include AI-assisted performance" in the OUTCOME filter to add them back.</li>
            <li>Comparison types are mutually exclusive in the forest plot. "AI vs business-as-usual" is the default; "AI vs active control" and "Off-the-shelf vs scaffolded AI" can be viewed separately.</li>
            <li>Subgroup estimates (e.g., by gender, prior ability, topic) are hidden by default to keep the plot readable. Use the SUBGROUPS chips to overlay specific dimensions.</li>
          </ul>

          {/* Suggest a paper */}
          <div style={sectionLabel}>Suggest a paper</div>
          <p style={{ fontSize: 13.5, lineHeight: 1.7, color: C.textSec, margin: "0 0 28px" }}>
            Know of a study we missed? Send the citation, effect size, SE, and sample size to{" "}
            <a href="mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20paper%20suggestion&body=Citation%3A%20%0APaper%20PDF%2Flink%3A%20%0AEffect%20size%20(SD)%3A%20%0AStandard%20error%3A%20%0ASample%20size%3A%20%0ANotes%3A%20"
              style={{ color: C.text, fontWeight: 600, borderBottom: `1px solid ${C.text}` }}>
              learning_study@middlebury.edu
            </a>{" "}
            and I'll add it.
          </p>

          {/* How to cite */}
          <div style={sectionLabel}>How to cite this resource</div>
          <pre style={{
            fontFamily: F.mono, fontSize: 12, color: C.text,
            background: C.bg, border: `1px solid ${C.borderLight}`, borderRadius: 5,
            padding: "12px 14px", whiteSpace: "pre-wrap", overflow: "auto", margin: "0 0 24px",
          }}>{`@misc{reyes_atlas_ai_human_skill,
  title  = {The AI and Human Skill Atlas},
  author = {Reyes, Germán},
  year   = {2026},
  url    = {https://germanr.github.io/ai-skill-atlas/}
}`}</pre>

          {/* Built by */}
          <div style={{ fontSize: 11, color: C.textTer, margin: 0, fontFamily: F.mono }}>
            Built by <a href="https://www.germanr.com" target="_blank" rel="noreferrer" style={{ color: C.text, fontWeight: 600 }}>Germán Reyes</a>, Middlebury College.
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Estimates Table (OWID-style Table tab)
// ────────────────────────────────────────────────────────────────────────────
function EstimatesTable({ estimates, papers, onSelectPaper }) {
  const paperByKey = useMemo(() => {
    const m = {};
    papers.forEach(p => { m[p.paper_key] = p; });
    return m;
  }, [papers]);

  const sorted = [...estimates].sort((a, b) => (b.effect_size_sd ?? -999) - (a.effect_size_sd ?? -999));

  if (sorted.length === 0) {
    return (
      <div style={{
        padding: "60px 20px", textAlign: "center", color: C.textSec,
        background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
      }}>
        No estimates match the current filters.
      </div>
    );
  }

  const th = {
    fontSize: 10.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px",
    textTransform: "uppercase", textAlign: "left", padding: "10px 12px",
    background: C.accentLight, borderBottom: `1px solid ${C.border}`, position: "sticky", top: 0,
  };
  const td = {
    fontSize: 12.5, padding: "10px 12px", borderBottom: `1px solid ${C.borderLight}`,
    fontFamily: F.sans, color: C.text, verticalAlign: "top",
  };

  return (
    <div style={{
      background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
      overflow: "auto", maxHeight: 720,
    }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>
            <th style={th}>Study</th>
            <th style={{ ...th, textAlign: "right" }}>Effect (SD)</th>
            <th style={{ ...th, textAlign: "right" }}>SE</th>
            <th style={{ ...th, textAlign: "right" }}>95% CI</th>
            <th style={{ ...th, textAlign: "right" }}>n</th>
            <th style={th}>Domain</th>
            <th style={th}>Outcome</th>
            <th style={th}>Timing</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e, i) => {
            const p = paperByKey[e.paper_key];
            const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
            const lo = e.ci_lower != null ? e.ci_lower : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd - 1.96 * e.se : null);
            const hi = e.ci_upper != null ? e.ci_upper : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd + 1.96 * e.se : null);
            return (
              <tr key={e.estimate_id}
                onClick={() => p && onSelectPaper(p)}
                style={{ background: i % 2 === 1 ? "#FAFAFA" : "transparent", cursor: p ? "pointer" : "default" }}
                onMouseEnter={(ev) => ev.currentTarget.style.background = C.accentLight}
                onMouseLeave={(ev) => ev.currentTarget.style.background = i % 2 === 1 ? "#FAFAFA" : "transparent"}
              >
                <td style={td}>
                  <div style={{ fontWeight: 500 }}>{e.study_label}</div>
                  {e.is_subgroup && e.subgroup && (
                    <div style={{ fontSize: 11, color: C.textTer, fontStyle: "italic", marginTop: 2 }}>subgroup · {e.subgroup}</div>
                  )}
                </td>
                <td style={{ ...td, fontFamily: F.mono, textAlign: "right", fontWeight: 600, color: e.effect_size_sd >= 0 ? "#1F5A2F" : "#A02020" }}>
                  {fmtSD(e.effect_size_sd)}
                </td>
                <td style={{ ...td, fontFamily: F.mono, textAlign: "right", color: C.textSec }}>{fmtSE(e.se)}</td>
                <td style={{ ...td, fontFamily: F.mono, textAlign: "right", color: C.textSec }}>{fmtCI(lo, hi)}</td>
                <td style={{ ...td, fontFamily: F.mono, textAlign: "right", color: C.textSec }}>{fmt(e.n_total)}</td>
                <td style={td}>
                  <span style={{
                    display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                    background: dom.color, marginRight: 6, verticalAlign: "middle",
                  }} /> {e.learning_domain}
                </td>
                <td style={{ ...td, color: C.textSec, maxWidth: 280 }}>{e.outcome}</td>
                <td style={{ ...td, color: C.textSec }}>{e.outcome_timing}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// CSV download helper
// ────────────────────────────────────────────────────────────────────────────
function downloadCSV(estimates, papers) {
  const paperByKey = Object.fromEntries(papers.map(p => [p.paper_key, p]));
  const cols = [
    "paper_key", "authors", "year", "study_label", "effect_size_sd", "se",
    "ci_lower", "ci_upper", "n_total", "learning_domain", "outcome",
    "outcome_timing", "treatment", "control", "comparison_type",
    "estimand", "estimation_method",
    "outcome_with_ai", "is_subgroup", "subgroup",
    "country", "population_category", "lab_vs_field", "study_design",
    "ai_tool", "ai_design", "incentives", "venue",
  ];
  const escape = (v) => {
    if (v == null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const rows = estimates.map(e => {
    const p = paperByKey[e.paper_key] || {};
    return cols.map(c => {
      if (c === "authors") return escape(p.authors_full || p.authors_short || "");
      if (c === "year") return escape(p.year);
      if (["country", "population_category", "lab_vs_field", "study_design",
           "ai_tool", "ai_design", "incentives", "venue"].includes(c)) return escape(p[c]);
      const lo = e.ci_lower != null ? e.ci_lower : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd - 1.96 * e.se : null);
      const hi = e.ci_upper != null ? e.ci_upper : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd + 1.96 * e.se : null);
      if (c === "ci_lower") return escape(lo);
      if (c === "ci_upper") return escape(hi);
      return escape(e[c]);
    }).join(",");
  });
  const csv = cols.join(",") + "\n" + rows.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ai-skill-atlas-estimates-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ────────────────────────────────────────────────────────────────────────────
// SectionTabs — Learning / Creativity switcher used in both section headers
// ────────────────────────────────────────────────────────────────────────────
function SectionTabs({ section, onChange }) {
  const tab = (key, label, badge) => {
    const active = section === key;
    return (
      <button
        key={key}
        onClick={() => onChange(key)}
        style={{
          background: active ? C.text : "transparent",
          color: active ? "#FFF" : C.text,
          border: `1px solid ${active ? C.text : C.border}`,
          padding: "6px 14px",
          borderRadius: 999,
          fontSize: 13,
          fontFamily: F.sans,
          fontWeight: 500,
          cursor: "pointer",
          letterSpacing: "0.2px",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        {label}
        {badge && (
          <span style={{
            fontFamily: F.mono,
            fontSize: 10,
            opacity: active ? 0.7 : 0.55,
            letterSpacing: "0.4px",
          }}>{badge}</span>
        )}
      </button>
    );
  };
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      {tab("learning", "Learning")}
      {tab("creativity", "Creativity", "BETA")}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// CreativityTile — visual card for a creativity paper
// ────────────────────────────────────────────────────────────────────────────
function CreativityTile({ paper, idx }) {
  const [h, setH] = useState(false);
  const [failed, setFailed] = useState(false);
  const url = `${import.meta.env.BASE_URL}images/paper-${paper.paper_key}.jpg`;
  const n = paper.n_outcomes_extracted || 0;
  return (
    <a
      href={paper.doi_or_url}
      target="_blank"
      rel="noopener noreferrer"
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{
        background: "#FFF",
        border: `1px solid ${h ? "#222" : "#E5E2D9"}`,
        borderRadius: 6,
        textDecoration: "none",
        color: "inherit",
        transition: "all 0.15s ease",
        transform: h ? "translateY(-2px)" : "none",
        boxShadow: h ? "0 6px 18px rgba(0,0,0,0.08)" : "none",
        animation: `fadeUp 0.35s cubic-bezier(.22,1,.36,1) ${Math.min(idx * 0.02, 0.4)}s both`,
        overflow: "hidden",
        display: "flex", flexDirection: "column",
      }}
    >
      <div style={{ height: 120, position: "relative", overflow: "hidden", borderRadius: "6px 6px 0 0", background: "#EFEBE0" }}>
        {!failed && (
          <img
            src={url}
            alt={paper.title}
            onError={() => setFailed(true)}
            loading="lazy"
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", filter: "brightness(0.78) saturate(1.05)" }}
          />
        )}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          padding: "26px 14px 9px",
          background: "linear-gradient(transparent, rgba(0,0,0,0.55))",
        }}>
          <span style={{ fontSize: 10, fontFamily: F.mono, color: "rgba(255,255,255,0.92)", letterSpacing: "0.7px", textTransform: "uppercase" }}>
            {paper.theme.replace("Anchor — ", "").replace(" / ", " · ")} · {paper.year}
          </span>
        </div>
        {paper.included_in_curated_subset && (
          <span style={{
            position: "absolute", top: 8, right: 8,
            background: "rgba(255,255,255,0.92)", color: "#222",
            fontSize: 9, fontFamily: F.mono, fontWeight: 600, letterSpacing: "0.5px",
            padding: "2px 6px", borderRadius: 3,
          }}>CURATED</span>
        )}
      </div>
      <div style={{ padding: "12px 14px 14px", flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{ fontSize: 10, color: C.muted, fontFamily: F.mono, letterSpacing: "0.5px", marginBottom: 4 }}>
          {paper.design_class.toUpperCase()} · {paper.venue}
        </div>
        <div style={{
          fontSize: 13.5, fontWeight: 600, fontFamily: F.sans, lineHeight: 1.32, color: C.text, marginBottom: 6,
          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
          minHeight: 36,
        }}>
          {paper.title}
        </div>
        <div style={{ fontSize: 11.5, color: C.muted, fontFamily: F.sans, marginBottom: 8 }}>
          {paper.authors_short} ({paper.year}){paper.n_total != null ? ` · n = ${paper.n_total.toLocaleString()}` : ""}
        </div>
        <div style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontSize: 10, fontFamily: F.mono, color: C.muted, letterSpacing: "0.5px" }}>
            {n > 0 ? `${n} ESTIMATES` : paper.stub ? "STUB" : "—"}
          </span>
          <span style={{ fontSize: 10, fontFamily: F.mono, color: C.muted, letterSpacing: "0.5px" }}>
            {paper.outcome_focus}
          </span>
        </div>
      </div>
    </a>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// CreativityPage — collected creativity papers, theme-grouped card grid
// ────────────────────────────────────────────────────────────────────────────
function CreativityPage({ section, onChangeSection, onShowAbout }) {
  const { theme_order = [], papers = [] } = CREATIVITY_DATA || {};
  const [curatedOnly, setCuratedOnly] = useState(false);

  const visiblePapers = useMemo(
    () => curatedOnly ? papers.filter(p => p.included_in_curated_subset) : papers,
    [papers, curatedOnly]
  );

  const byTheme = useMemo(() => {
    const m = new Map();
    visiblePapers.forEach(p => {
      if (!m.has(p.theme)) m.set(p.theme, []);
      m.get(p.theme).push(p);
    });
    return m;
  }, [visiblePapers]);

  const nEstimates = visiblePapers.reduce((s, p) => s + (p.n_outcomes_extracted || 0), 0);
  const nPapersWithEstimates = visiblePapers.filter(p => (p.n_outcomes_extracted || 0) > 0).length;
  const nCurated = papers.filter(p => p.included_in_curated_subset).length;

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${C.border}`,
        background: `${C.bg}EE`,
        backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
            <h1 className="hero-title" style={{
              fontSize: 22, fontWeight: 700, fontFamily: F.sans, color: C.text,
              lineHeight: 1.2, margin: 0,
            }}>
              The AI and Human Skill Atlas
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <SectionTabs section={section} onChange={onChangeSection} />
              <button
                onClick={onShowAbout}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontSize: 16, fontFamily: F.sans, color: C.text, fontWeight: 500,
                  borderBottom: `2px solid ${C.text}`, padding: "3px 0",
                  letterSpacing: "0.3px",
                }}>About</button>
            </div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "44px 28px 80px" }}>
        {/* Hero */}
        <div style={{ marginBottom: 36 }}>
          <div style={{
            fontFamily: F.mono, fontSize: 11, letterSpacing: "1.4px",
            color: C.muted, textTransform: "uppercase", marginBottom: 10,
          }}>
            CREATIVITY · IN DEVELOPMENT
          </div>
          <h2 style={{
            fontSize: 32, fontWeight: 700, lineHeight: 1.2,
            fontFamily: F.sans, marginBottom: 14, letterSpacing: "-0.5px",
          }}>
            Does generative AI make us more creative, or more alike?
          </h2>
          <p style={{
            fontSize: 16, lineHeight: 1.6, color: C.text, maxWidth: 720,
          }}>
            A growing body of experiments asks whether AI lifts individual creativity, whether
            it narrows the diversity of what we collectively produce, and whether the
            homogenization persists after the tool is taken away. This section catalogs that
            literature; effect-size extraction and the forest plot are in progress.
          </p>
        </div>

        {/* Stats strip */}
        <div className="stats-row" style={{
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0,
          border: `1px solid ${C.border}`, borderRadius: 6,
          marginBottom: 36, overflow: "hidden", background: "#FFF",
        }}>
          {[
            { label: "Papers", value: visiblePapers.length },
            { label: "RCT / Hybrid", value: visiblePapers.filter(p => p.design_class === "RCT" || p.design_class === "Hybrid").length },
            { label: "Effect-size estimates", value: nEstimates },
            { label: "Papers with estimates", value: nPapersWithEstimates },
          ].map((s, i) => (
            <div key={s.label} style={{
              padding: "18px 20px",
              borderRight: i < 3 ? `1px solid ${C.border}` : "none",
            }}>
              <div style={{
                fontSize: 26, fontWeight: 700, fontFamily: F.sans,
                lineHeight: 1, marginBottom: 6,
              }}>{s.value}</div>
              <div style={{
                fontFamily: F.mono, fontSize: 10, letterSpacing: "1.0px",
                color: C.muted, textTransform: "uppercase",
              }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Curated-subset filter (matches the learning section's inclusion criteria) */}
        <div style={{
          display: "flex", alignItems: "center", gap: 12,
          marginBottom: 24, paddingBottom: 18, borderBottom: `1px solid ${C.border}`,
          flexWrap: "wrap",
        }}>
          <div style={{
            fontFamily: F.mono, fontSize: 11, letterSpacing: "1.4px",
            color: C.muted, textTransform: "uppercase",
          }}>
            INCLUSION CRITERIA
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              onClick={() => setCuratedOnly(false)}
              style={{
                background: !curatedOnly ? C.text : "transparent",
                color: !curatedOnly ? "#FFF" : C.text,
                border: `1px solid ${!curatedOnly ? C.text : C.border}`,
                padding: "5px 12px", borderRadius: 999,
                fontSize: 12, fontFamily: F.sans, fontWeight: !curatedOnly ? 600 : 400,
                cursor: "pointer", letterSpacing: "0.2px",
              }}>All papers ({papers.length})</button>
            <button
              onClick={() => setCuratedOnly(true)}
              style={{
                background: curatedOnly ? C.text : "transparent",
                color: curatedOnly ? "#FFF" : C.text,
                border: `1px solid ${curatedOnly ? C.text : C.border}`,
                padding: "5px 12px", borderRadius: 999,
                fontSize: 12, fontFamily: F.sans, fontWeight: curatedOnly ? 600 : 400,
                cursor: "pointer", letterSpacing: "0.2px",
              }}>RCT · N ≥ 50 ({nCurated})</button>
          </div>
          <div style={{ fontSize: 11, color: C.muted, fontFamily: F.sans, flex: 1, minWidth: 200 }}>
            Same criteria as the learning section: randomized design with AI as treatment, and ≥ 50 participants.
          </div>
        </div>

        {/* Papers grouped by theme — card grid */}
        {theme_order.map(theme => {
          const list = byTheme.get(theme) || [];
          if (!list.length) return null;
          return (
            <div key={theme} style={{ marginBottom: 36 }}>
              <h3 style={{
                fontSize: 14, fontWeight: 600, fontFamily: F.sans,
                marginBottom: 14, color: C.text,
                paddingBottom: 8, borderBottom: `1px solid ${C.border}`,
              }}>
                {theme}
                <span style={{
                  fontFamily: F.mono, fontSize: 11, color: C.muted,
                  marginLeft: 10, fontWeight: 400, letterSpacing: "0.5px",
                }}>{list.length}</span>
              </h3>
              <div className="grid-main" style={{
                display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16,
              }}>
                {list.map((p, idx) => (
                  <CreativityTile key={p.paper_key} paper={p} idx={idx} />
                ))}
              </div>
            </div>
          );
        })}

        {/* What's next */}
        <div style={{
          marginTop: 48, padding: "24px 26px",
          background: "#F8F6F0", border: `1px solid ${C.border}`, borderRadius: 6,
        }}>
          <div style={{
            fontFamily: F.mono, fontSize: 11, letterSpacing: "1.4px",
            color: C.muted, textTransform: "uppercase", marginBottom: 10,
          }}>
            WHAT'S COMING
          </div>
          <ul style={{ paddingLeft: 18, lineHeight: 1.7, fontSize: 14 }}>
            <li><b>Done:</b> effect-size extraction from {nPapersWithEstimates} papers ({nEstimates} outcomes total — Cohen's d, raw means, cosine similarities, Likert-rating betas)</li>
            <li>Forest plot of individual-creativity effects (Cohen's d only — comparable across papers)</li>
            <li>Companion forest plot of homogenization effects (mixed metric units; needs harmonization)</li>
            <li>Filter by outcome type (individual creativity / homogenization / diversity / idea quantity)</li>
            <li>Re-extraction of the 2 remaining stubs (Hintze, Liu-Wang-Yang) once PDFs are available</li>
          </ul>
          <div style={{ marginTop: 16, fontSize: 13, color: C.muted }}>
            Have a paper to add?{" "}
            <a
              href="mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20creativity%20paper%20suggestion"
              style={{ color: C.text, borderBottom: `1px solid ${C.text}` }}
            >Email it in.</a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Main App
// ────────────────────────────────────────────────────────────────────────────
export default function App() {
  const [section, setSection] = useState("learning"); // "learning" | "creativity"
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [showAbout, setShowAbout] = useState(false);
  const [search, setSearch] = useState("");
  const [activeDomains, setActiveDomains] = useState(new Set());
  const [activePopulations, setActivePopulations] = useState(new Set());
  const [activeSettings, setActiveSettings] = useState(new Set());
  const [comparisonType, setComparisonType] = useState("ai_vs_bau"); // "ai_vs_bau" | "ai_vs_active" | "ai_design"
  const [outcomeMode, setOutcomeMode] = useState("without_ai");      // "without_ai" | "all"
  const [activeSubgroupValues, setActiveSubgroupValues] = useState(new Set()); // specific subgroup values (e.g. "Prior achievement: Below median") to overlay
  const [sortBy, setSortBy] = useState("effect");
  const [view, setView] = useState("chart"); // "chart" | "table"

  // Inject global CSS once
  useEffect(() => {
    const styleEl = document.createElement("style");
    styleEl.innerHTML = GCSS;
    document.head.appendChild(styleEl);
    return () => { document.head.removeChild(styleEl); };
  }, []);

  const papers = PAPERS_RAW;
  const estimates = ESTIMATES_RAW;

  const allDomains = useMemo(() => {
    const s = new Set();
    papers.forEach(p => p.learning_domain_primary && s.add(p.learning_domain_primary));
    return DOMAIN_ORDER.filter(d => s.has(d));
  }, [papers]);

  const allPopulations = useMemo(() => {
    const s = new Set();
    papers.forEach(p => p.population_category && s.add(p.population_category));
    return POPULATION_ORDER.filter(x => s.has(x)).concat(
      Array.from(s).filter(x => !POPULATION_ORDER.includes(x))
    );
  }, [papers]);

  const allSettings = useMemo(() => ["Lab", "Field", "Online", "Hybrid"].filter(x =>
    papers.some(p => p.lab_vs_field === x)
  ), [papers]);

  // Apply filters
  const filteredPapers = useMemo(() => {
    return papers.filter(p => {
      if (search) {
        const q = search.toLowerCase();
        if (!(p.title?.toLowerCase().includes(q) ||
              p.authors_full?.toLowerCase().includes(q) ||
              p.authors_short?.toLowerCase().includes(q) ||
              p.country?.toLowerCase().includes(q) ||
              p.summary?.toLowerCase().includes(q))) return false;
      }
      if (activeDomains.size > 0 && !activeDomains.has(p.learning_domain_primary)) return false;
      if (activePopulations.size > 0 && !activePopulations.has(p.population_category)) return false;
      if (activeSettings.size > 0 && !activeSettings.has(p.lab_vs_field)) return false;
      return true;
    });
  }, [papers, search, activeDomains, activePopulations, activeSettings]);

  const filteredEstimates = useMemo(() => {
    const paperKeys = new Set(filteredPapers.map(p => p.paper_key));
    return estimates.filter(e => {
      if (!paperKeys.has(e.paper_key)) return false;
      // Comparison-type filter (radio; exactly one always selected)
      if ((e.comparison_type || "ai_vs_bau") !== comparisonType) return false;
      // Outcome filter: exclude AI-assisted outcomes by default
      if (outcomeMode === "without_ai" && e.outcome_with_ai === true) return false;
      // Subgroup filter: only include subgroup rows whose specific value is active
      if (e.is_subgroup === true) {
        if (!activeSubgroupValues.has(e.subgroup)) return false;
      }
      return true;
    });
  }, [filteredPapers, estimates, comparisonType, outcomeMode, activeSubgroupValues]);

  // Specific subgroup values that appear in ≥2 distinct papers (passes the chip filter)
  const availableSubgroupValues = useMemo(() => {
    const papersByValue = new Map();
    estimates.forEach(e => {
      if (e.is_subgroup === true && e.subgroup) {
        if (!papersByValue.has(e.subgroup)) papersByValue.set(e.subgroup, new Set());
        papersByValue.get(e.subgroup).add(e.paper_key);
      }
    });
    return Array.from(papersByValue.entries())
      .filter(([, paperSet]) => paperSet.size >= 2)
      .sort((a, b) => b[1].size - a[1].size || a[0].localeCompare(b[0]))
      .map(([value]) => value);
  }, [estimates]);

  // Papers that contribute at least one estimate to the current comparison-type view
  const papersWithEstimates = useMemo(() => {
    const keysInView = new Set(filteredEstimates.map(e => e.paper_key));
    return filteredPapers.filter(p => keysInView.has(p.paper_key));
  }, [filteredPapers, filteredEstimates]);

  const sortedPapers = useMemo(() => {
    const arr = [...papersWithEstimates];
    arr.sort((a, b) => {
      if (sortBy === "effect") {
        return (b.avg_effect ?? -999) - (a.avg_effect ?? -999);
      }
      if (sortBy === "year") return (b.year || 0) - (a.year || 0);
      if (sortBy === "n") return (b.n_total || 0) - (a.n_total || 0);
      return a.authors_short?.localeCompare(b.authors_short);
    });
    return arr;
  }, [papersWithEstimates, sortBy]);

  const toggleSet = (set, val, setter) => {
    const next = new Set(set);
    if (next.has(val)) next.delete(val); else next.add(val);
    setter(next);
  };

  if (section === "creativity") {
    return <CreativityPage
      section={section}
      onChangeSection={setSection}
      onShowAbout={() => setShowAbout(true)}
    />;
  }

  if (selectedPaper) {
    return <ReportCard paper={selectedPaper} estimates={estimates} onBack={() => setSelectedPaper(null)} />;
  }

  if (showAbout) {
    return <AboutPage
      onBack={() => setShowAbout(false)}
      nPapers={papers.length}
      nEstimates={estimates.length}
      papers={papers}
      onSelectPaper={(p) => { setShowAbout(false); setSelectedPaper(p); }}
    />;
  }

  // ── Grid view ─────────────────────────────────────────────────────────────
  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${C.border}`,
        background: `${C.bg}EE`,
        backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
            <h1 className="hero-title" style={{
              fontSize: 22, fontWeight: 700, fontFamily: F.sans, color: C.text,
              lineHeight: 1.2, margin: 0,
            }}>
              The AI and Human Skill Atlas
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <SectionTabs section={section} onChange={setSection} />
              <button
                onClick={() => setShowAbout(true)}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontSize: 16, fontFamily: F.sans, color: C.text, fontWeight: 500,
                  borderBottom: `2px solid ${C.text}`, padding: "3px 0",
                  letterSpacing: "0.3px",
                }}>About</button>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 28px 80px" }}>
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <FilterRow
            label="Domain"
            options={allDomains}
            active={activeDomains}
            onToggle={(v) => toggleSet(activeDomains, v, setActiveDomains)}
            colorMap={Object.fromEntries(Object.entries(DOMAIN).map(([k, v]) => [k, v.color]))}
          />
          <FilterRow
            label="Population"
            options={allPopulations}
            active={activePopulations}
            onToggle={(v) => toggleSet(activePopulations, v, setActivePopulations)}
          />
          <FilterRow
            label="Setting"
            options={allSettings}
            active={activeSettings}
            onToggle={(v) => toggleSet(activeSettings, v, setActiveSettings)}
          />
          <FilterRow
            label="Comparison"
            options={[
              { value: "ai_vs_bau",     label: "AI vs business-as-usual control" },
              { value: "ai_vs_active",  label: "AI vs active control" },
              { value: "ai_design",     label: "Off-the-shelf vs scaffolded AI" },
            ]}
            active={new Set([comparisonType])}
            onToggle={(v) => setComparisonType(v)}
            isRadio
          />
          <FilterRow
            label="Outcome"
            options={[
              { value: "without_ai", label: "Measured without AI (learning)" },
              { value: "all",        label: "Include AI-assisted performance" },
            ]}
            active={new Set([outcomeMode])}
            onToggle={(v) => setOutcomeMode(v)}
            isRadio
          />
          {availableSubgroupValues.length > 0 && (
            <FilterRow
              label="Subgroups"
              options={availableSubgroupValues}
              active={activeSubgroupValues}
              onToggle={(v) => toggleSet(activeSubgroupValues, v, setActiveSubgroupValues)}
            />
          )}
        </div>

        {/* View tabs (Chart / Table) + estimate count + Download CSV */}
        <div style={{ marginBottom: 32 }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 10, gap: 10, flexWrap: "wrap",
          }}>
            <div style={{ display: "flex", gap: 6 }}>
              {[
                { key: "chart", label: "Chart" },
                { key: "table", label: "Table" },
              ].map(opt => (
                <button
                  key={opt.key}
                  onClick={() => setView(opt.key)}
                  style={{
                    padding: "6px 14px", fontSize: 13, fontFamily: F.sans,
                    background: view === opt.key ? C.text : "transparent",
                    color: view === opt.key ? "#FFF" : C.text,
                    border: `1px solid ${view === opt.key ? C.text : C.border}`,
                    borderRadius: 4, cursor: "pointer",
                    fontWeight: view === opt.key ? 600 : 400,
                    letterSpacing: "0.2px",
                  }}>{opt.label}</button>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
              <div style={{ fontSize: 11, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px" }}>
                {filteredEstimates.length} ESTIMATES · {papersWithEstimates.length} PAPERS
              </div>
              <button
                onClick={() => downloadCSV(filteredEstimates, papers)}
                style={{
                  padding: "5px 12px", fontSize: 12, fontFamily: F.sans,
                  background: C.surface, color: C.text,
                  border: `1px solid ${C.border}`, borderRadius: 4,
                  cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6,
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = C.borderHover}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = C.border}
              >
                ↓ Download CSV
              </button>
            </div>
          </div>
          {view === "chart" ? (
            <>
              <div style={{ fontSize: 11, fontFamily: F.sans, color: C.textTer, fontStyle: "italic", marginBottom: 6 }}>
                hover for details · click to open report
              </div>
              <ForestPlot estimates={filteredEstimates} papers={papers} onSelectPaper={setSelectedPaper} width={1144} />
            </>
          ) : (
            <EstimatesTable estimates={filteredEstimates} papers={papers} onSelectPaper={setSelectedPaper} />
          )}
        </div>

        {/* Tiles header */}
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 14, flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 11, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px" }}>
            {papersWithEstimates.length} PAPERS
          </div>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <input
              type="text"
              placeholder="Search title, author, country…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                background: C.surface, border: `1px solid ${C.border}`,
                padding: "5px 11px", fontSize: 12, borderRadius: 4,
                width: 220, fontFamily: F.sans, color: C.text,
                outline: "none",
              }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ fontSize: 11, fontFamily: F.mono, color: C.textTer, letterSpacing: "0.5px", alignSelf: "center" }}>SORT:</span>
              {["effect", "year", "n", "author"].map(opt => (
                <button
                  key={opt}
                  onClick={() => setSortBy(opt)}
                  style={{
                    padding: "3px 0", border: "none", background: "none", cursor: "pointer",
                    fontSize: 11.5, fontFamily: F.sans,
                    fontWeight: sortBy === opt ? 600 : 400,
                    color: sortBy === opt ? C.text : C.textTer,
                    borderBottom: sortBy === opt ? `1.5px solid ${C.text}` : "1.5px solid transparent",
                    letterSpacing: "0.3px",
                  }}>{opt}</button>
              ))}
            </div>
          </div>
        </div>

        {/* Tile grid */}
        {sortedPapers.length === 0 ? (
          <div style={{
            padding: "60px 20px", textAlign: "center", color: C.textSec,
            background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8,
          }}>
            No papers match the current filters. Try clearing some filters.
          </div>
        ) : (
          <div className="grid-main" style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16,
          }}>
            {sortedPapers.map((p, idx) => (
              <Tile key={p.paper_key} paper={p} onClick={setSelectedPaper} idx={idx} />
            ))}
          </div>
        )}

        {/* Footer */}
        <div style={{
          marginTop: 60, paddingTop: 24, borderTop: `1px solid ${C.border}`,
          fontSize: 12, color: C.textSec, lineHeight: 1.6, fontFamily: F.sans,
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }} className="footer-grid">
            <div>
              <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textTer, letterSpacing: "1px", marginBottom: 6 }}>HOW TO CITE THIS RESOURCE</div>
              <pre style={{
                fontFamily: F.mono, fontSize: 11.5, color: C.text,
                background: C.surface, border: `1px solid ${C.border}`, borderRadius: 5,
                padding: "10px 12px", whiteSpace: "pre-wrap", overflow: "auto",
              }}>{`@misc{reyes_atlas_ai_human_skill,
  title  = {The AI and Human Skill Atlas},
  author = {Reyes, Germán},
  year   = {2026},
  url    = {https://germanr.github.io/ai-skill-atlas/}
}`}</pre>
            </div>
            <div>
              <div style={{ fontSize: 10.5, fontFamily: F.mono, color: C.textTer, letterSpacing: "1px", marginBottom: 6 }}>BUILT BY</div>
              <p>
                <a href="https://www.germanr.com" target="_blank" rel="noreferrer" style={{ color: C.text, borderBottom: `1px solid ${C.text}` }}>Germán Reyes</a>, Middlebury College.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Filter row (label + chips)
// ────────────────────────────────────────────────────────────────────────────
function FilterRow({ label, options, active, onToggle, colorMap, isRadio }) {
  if (!options || options.length === 0) return null;
  return (
    <div className="filter-bar" style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
      <div className="filter-group" style={{
        fontSize: 10.5, fontFamily: F.mono, color: C.textSec, letterSpacing: "1px",
        minWidth: 90,
      }}>{label.toUpperCase()}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", flex: 1 }}>
        {options.map((opt) => {
          const value = typeof opt === "string" ? opt : opt.value;
          const optLabel = typeof opt === "string" ? opt : opt.label;
          const color = colorMap ? colorMap[value] : null;
          return (
            <Chip
              key={value}
              label={optLabel}
              active={active.has(value)}
              onClick={() => onToggle(value)}
              color={color}
            />
          );
        })}
        {!isRadio && active.size > 0 && (
          <button
            onClick={() => options.forEach(o => active.has(typeof o === "string" ? o : o.value) && onToggle(typeof o === "string" ? o : o.value))}
            style={{
              background: "none", border: "none", color: C.textTer, fontSize: 11,
              cursor: "pointer", fontFamily: F.sans, textDecoration: "underline",
              padding: "4px 6px",
            }}>clear</button>
        )}
      </div>
    </div>
  );
}
