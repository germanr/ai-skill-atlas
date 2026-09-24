import React, { useState, useEffect, useMemo, useRef, useId } from "react";
import PAPERS_RAW from "./src/papers.json";
import ESTIMATES_RAW from "./src/estimates.json";
import CREATIVITY_DATA from "./src/creativity_papers.json";
import { randomEffectsMean, ciOf, bibtexAuthors, filterEstimates, isPlottableEstimate, isPoolableEstimate } from "./src/shared.mjs";
import RELEASE from "./src/release.json";
import RELEASE_INDEX from "./public/releases/index.json";
import EVIDENCE_METADATA from "./src/evidence_metadata.json";
import { resolveStudyMetadata, resolveEstimateMetadata, formatSample } from "./src/evidence-metadata.mjs";
import { parseViewState, serializeViewState } from "./src/view-state.mjs";
import { buildEstimatesCSV } from "./src/export.mjs";

// ─── Formatters ───
const fmt = (n) => (n == null ? "—" : n.toLocaleString());
const fmtSD = (n) => (n == null ? "—" : (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(2));
const fmtSE = (n) => (n == null ? "—" : n.toFixed(3));
const fmtCI = (lo, hi) => (lo == null || hi == null ? "—" : `[${fmtSD(lo)}, ${fmtSD(hi)}]`);
const studyMetadata = (paper) => resolveStudyMetadata(paper, EVIDENCE_METADATA);
const estimateMetadata = (estimate, paper) => resolveEstimateMetadata(estimate, paper, EVIDENCE_METADATA);
const studySample = (paper) => formatSample(studyMetadata(paper).sample);
const estimateSample = (estimate, paper) => formatSample(estimateMetadata(estimate, paper).sample);
const releaseDate = () => new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${RELEASE.date}T00:00:00Z`));
const releaseMonth = () => new Intl.DateTimeFormat("en", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${RELEASE.date}T00:00:00Z`));

// ─── Design tokens — "evidence journal": white, ink, hairline rules ───
const C = {
  paper: "#FFFFFF",        // page background
  paperHi: "#FFFFFF",      // raised surface (cards, plot)
  paperDeep: "#F5F4F1",    // recessed surface (hovers, table headers)
  ink: "#1B1A18",          // primary text
  ink2: "#5B5751",         // secondary text
  ink3: "#787269",         // tertiary text (AA contrast on white)
  rule: "#DDDAD3",         // hairline rules
  ruleSoft: "#ECEAE5",     // softer rules
  accent: "#1D4E89",       // scholarly blue — pooled estimate, links, active
  accentSoft: "rgba(29,78,137,0.08)",
  pos: "#1A5632",
  neg: "#8C1D18",
};

// ─── Domain palette (continuous with paper Figure 5) ───
const DOMAIN = {
  "Math":              { color: "#7B1F1F", symbol: "circle"   },
  "Coding":            { color: "#9A5410", symbol: "square"   },
  "Writing":           { color: "#1F5A2F", symbol: "triangle" },
  "Language":          { color: "#24509E", symbol: "cross"    },
  "Science":           { color: "#50555E", symbol: "diamond"  },
  "Engineering":       { color: "#155E75", symbol: "square"   },
  "Economics":         { color: "#5B2E83", symbol: "triangle" },
  "Medicine":          { color: "#0E7C5B", symbol: "circle"   },
  "General knowledge": { color: "#3D3A35", symbol: "diamond"  },
  "Mixed":             { color: "#6E6759", symbol: "circle"   },
};
const DOMAIN_ORDER = ["Math", "Coding", "Writing", "Language", "Economics", "Medicine", "Science", "Engineering", "General knowledge", "Mixed"];

const POPULATION_ORDER = [
  "Elementary", "Middle school", "High school",
  "Undergraduate", "Graduate", "University (mixed)",
  "Adults general", "Professional",
];

// Sample scope: the default view shows student samples (matching the paper's
// curated meta-analysis). Adult online-panel and professional samples sit
// behind the Sample filter. Any population category not listed here counts
// as a student sample.
const NON_STUDENT_POPULATIONS = new Set(["Adults general", "Professional"]);
const isStudentPaper = (p) => !NON_STUDENT_POPULATIONS.has(p.population_category);
const VIEW_OPTIONS = {
  domains: [...new Set(ESTIMATES_RAW.map(e => e.learning_domain).filter(Boolean))],
  populations: [...new Set(PAPERS_RAW.map(p => p.population_category).filter(Boolean))],
  paperKeys: PAPERS_RAW.map(p => p.paper_key),
};
const parseCurrentView = () => parseViewState(window.location.href, {
  ...VIEW_OPTIONS, defaultView: window.innerWidth < 640 ? "table" : "chart",
});

const F = {
  serif: "'Newsreader', Georgia, 'Times New Roman', serif",
  sans: "'IBM Plex Sans', 'Helvetica Neue', Helvetica, sans-serif",
  mono: "'IBM Plex Mono', Consolas, monospace",
};

// Creativity section: page stays reachable at ?section=creativity for previewing,
// but no links are shown until this is flipped to true.
const SHOW_CREATIVITY = false;

// Small-caps mono label — the house style for metadata
const SC = (extra = {}) => ({
  fontFamily: F.mono, fontSize: 10.5, letterSpacing: "0.14em",
  textTransform: "uppercase", color: C.ink2, fontWeight: 500, ...extra,
});

export const GCSS = `
* { box-sizing: border-box; margin: 0; }
html { scroll-behavior: smooth; }
body { background: ${C.paper}; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; font-family: ${F.sans}; color: ${C.ink}; }
::selection { background: ${C.ink}; color: ${C.paper}; }
a { color: inherit; text-decoration: none; }
button { font: inherit; }
:focus-visible { outline: 2px solid ${C.accent}; outline-offset: 2px; }
#evidence, #studies { scroll-margin-top: 120px; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: ${C.rule}; border-radius: 3px; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes drawIn { from { opacity: 0; transform: scaleX(0.96); } to { opacity: 1; transform: scaleX(1); } }
.hover-row:hover { background: ${C.paperDeep} !important; }
.plot-scroll { overflow-x: auto; }
@media (max-width: 1000px) {
  .hero-grid { grid-template-columns: 1fr !important; gap: 28px !important; }
  .hero-pooled { border-left: none !important; padding-left: 0 !important; border-top: 1px solid ${C.rule}; padding-top: 22px !important; }
  .stats-band { grid-template-columns: 1fr 1fr !important; }
  .stats-band > div { border-bottom: 1px solid ${C.ruleSoft}; }
  .grid-cards { grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)) !important; }
  .footer-grid { grid-template-columns: 1fr !important; gap: 28px !important; }
  .notes-band { grid-template-columns: 1fr !important; }
  .facts-grid { grid-template-columns: 1fr !important; }
}
@media (max-width: 620px) {
  .wrap { padding-left: 18px !important; padding-right: 18px !important; }
  .grid-cards { grid-template-columns: 1fr 1fr !important; gap: 10px !important; }
  .nav-links { gap: 12px !important; }
  .toolbar { flex-direction: column; align-items: stretch !important; }
}
@media (max-width: 460px) {
  .grid-cards { grid-template-columns: 1fr !important; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
`;

// DerSimonian–Laird pooling, shared CI, and BibTeX helpers live in
// src/shared.mjs so the smoke tests exercise the exact production logic.

// ────────────────────────────────────────────────────────────────────────────
// Atoms
// ────────────────────────────────────────────────────────────────────────────

// Wordmark glyph: a miniature forest plot
function Glyph({ size = 26, color = C.ink }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true" style={{ display: "block" }}>
      <line x1="3" y1="6" x2="17" y2="6" stroke={color} strokeWidth="1.6" />
      <rect x="8" y="3.9" width="4.2" height="4.2" fill={color} />
      <line x1="8" y1="13" x2="24" y2="13" stroke={color} strokeWidth="1.6" />
      <rect x="14.5" y="10.9" width="4.2" height="4.2" fill={color} />
      <polygon points="13,18.5 17.5,21.5 13,24.5 8.5,21.5" fill={C.accent} />
    </svg>
  );
}

function DoubleRule({ style = {} }) {
  return (
    <div style={style} aria-hidden="true">
      <div style={{ height: 2, background: C.ink }} />
      <div style={{ height: 3 }} />
      <div style={{ height: 1, background: C.ink }} />
    </div>
  );
}

function SectionHead({ index, title, sub, right }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span style={{ fontFamily: F.mono, fontSize: 12, color: C.accent, fontWeight: 600, letterSpacing: "0.1em" }}>{index}</span>
          <h2 style={{ fontFamily: F.serif, fontSize: 30, fontWeight: 600, letterSpacing: "-0.01em", color: C.ink, lineHeight: 1.15 }}>{title}</h2>
        </div>
        {right}
      </div>
      {sub && <p style={{ fontFamily: F.sans, fontSize: 14, color: C.ink2, lineHeight: 1.6, marginTop: 8, maxWidth: 640 }}>{sub}</p>}
      <div style={{ height: 1, background: C.rule, marginTop: 14 }} />
    </div>
  );
}

function GhostBtn({ children, onClick, href, download, title, small }) {
  const [h, setH] = useState(false);
  const style = {
    display: "inline-flex", alignItems: "center", gap: 7,
    padding: small ? "6px 12px" : "9px 16px",
    fontFamily: F.mono, fontSize: small ? 10.5 : 11.5, letterSpacing: "0.08em", textTransform: "uppercase",
    color: h ? C.paper : C.ink, background: h ? C.ink : "transparent",
    border: `1px solid ${C.ink}`, borderRadius: 2, cursor: "pointer",
    transition: "all 0.15s ease", whiteSpace: "nowrap",
  };
  const handlers = { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false), title };
  if (href) return <a href={href} download={download} target={download ? undefined : "_blank"} rel="noreferrer" style={style} {...handlers}>{children}</a>;
  return <button onClick={onClick} style={style} {...handlers}>{children}</button>;
}

function SolidBtn({ children, href, onClick }) {
  const [h, setH] = useState(false);
  const style = {
    display: "inline-flex", alignItems: "center", gap: 7,
    padding: "9px 16px",
    fontFamily: F.mono, fontSize: 11.5, letterSpacing: "0.08em", textTransform: "uppercase",
    color: C.paper, background: h ? C.accent : C.ink,
    border: `1px solid ${h ? C.accent : C.ink}`, borderRadius: 2, cursor: "pointer",
    transition: "all 0.15s ease", whiteSpace: "nowrap",
  };
  const handlers = { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) };
  if (href) return <a href={href} target="_blank" rel="noreferrer" style={style} {...handlers}>{children}</a>;
  return <button onClick={onClick} style={style} {...handlers}>{children}</button>;
}

// ────────────────────────────────────────────────────────────────────────────
// Site header — shared masthead
// active: "learning" | "creativity" | "about"
// onSection: optional in-app section switcher; falls back to hrefs
// ────────────────────────────────────────────────────────────────────────────
function SiteHeader({ active, onSection, onHome }) {
  const base = import.meta.env.BASE_URL;
  const NavItem = ({ id, label, badge, href }) => {
    const [h, setH] = useState(false);
    const isActive = active === id;
    const style = {
      fontFamily: F.mono, fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase",
      color: isActive ? C.ink : (h ? C.ink : C.ink2),
      background: "none", border: "none", cursor: "pointer", padding: "4px 0",
      borderBottom: isActive ? `2px solid ${C.ink}` : "2px solid transparent",
      transition: "color 0.15s", display: "inline-flex", alignItems: "baseline", gap: 5,
    };
    const inner = (
      <>
        {label}
        {badge && <span style={{ fontSize: 8.5, color: C.accent, letterSpacing: "0.1em", fontWeight: 600 }}>{badge}</span>}
      </>
    );
    const handlers = { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) };
    if (onSection && (id === "learning" || id === "creativity")) {
      return <button style={style} onClick={() => onSection(id)} {...handlers}>{inner}</button>;
    }
    return <a style={style} href={href} {...handlers}>{inner}</a>;
  };

  return (
    <header style={{ position: "sticky", top: 0, zIndex: 100, background: C.paper }}>
      <div className="wrap" style={{ maxWidth: 1140, margin: "0 auto", padding: "0 28px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, padding: "15px 0 13px", flexWrap: "wrap" }}>
          <a
            href={base}
            onClick={onHome ? (e) => { e.preventDefault(); onHome(); } : undefined}
            style={{ display: "flex", alignItems: "center", gap: 11, cursor: "pointer" }}
          >
            <Glyph size={25} />
            <div style={{ fontFamily: F.serif, fontSize: 19.5, fontWeight: 650, letterSpacing: "-0.012em", lineHeight: 1.05, color: C.ink }}>
              The AI <span style={{ fontStyle: "italic", fontWeight: 500 }}>&amp;</span> Human Skill Atlas
            </div>
          </a>
          <nav className="nav-links" style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <NavItem id="learning" label="Learning" href={base} />
            {SHOW_CREATIVITY && <NavItem id="creativity" label="Creativity" badge="β" href={`${base}?section=creativity`} />}
            <NavItem id="about" label="About" href={`${base}about/`} />
          </nav>
        </div>
        <DoubleRule />
      </div>
    </header>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Hero strip plot — every estimate as one dot on the effect-size axis
// ────────────────────────────────────────────────────────────────────────────
function StripPlot({ estimates, pooled, height = 92 }) {
  const ref = useRef(null);
  const [width, setWidth] = useState(1084);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const xMin = -1.0, xMax = 1.0;
  const axisY = height - 26;
  const xScale = (x) => ((Math.max(xMin, Math.min(xMax, x)) - xMin) / (xMax - xMin)) * width;
  const ticks = [-1, -0.5, 0, 0.5, 1];

  // Deterministic vertical jitter (golden-ratio sequence) so dots don't pile up
  const dots = estimates
    .filter(e => e.effect_size_sd != null)
    .map((e, i) => ({
      x: xScale(e.effect_size_sd),
      y: axisY - 14 - ((i * 0.618034) % 1) * (axisY - 34),
      color: (DOMAIN[e.learning_domain] || DOMAIN.Mixed).color,
      key: e.estimate_id,
    }));

  return (
    <div ref={ref} style={{ width: "100%" }}>
      <svg width={width} height={height} style={{ display: "block", overflow: "visible" }} aria-hidden="true">
        {/* zero line */}
        <line x1={xScale(0)} y1={6} x2={xScale(0)} y2={axisY} stroke={C.ink3} strokeWidth={1} strokeDasharray="2 3" />
        {/* dots */}
        {dots.map((d, i) => (
          <circle key={d.key} cx={d.x} cy={d.y} r={3.4} fill={d.color} opacity={0.82}
            style={{ animation: `fadeIn 0.5s ease ${Math.min(i * 0.012, 0.7)}s both` }} />
        ))}
        {/* pooled diamond marker on the axis */}
        {pooled && (
          <polygon
            points={`${xScale(pooled.mean)},${axisY - 7} ${xScale(pooled.hi)},${axisY} ${xScale(pooled.mean)},${axisY + 7} ${xScale(pooled.lo)},${axisY}`}
            fill={C.accent}
          />
        )}
        {/* axis */}
        <line x1={0} y1={axisY} x2={width} y2={axisY} stroke={C.ink} strokeWidth={1} />
        {ticks.map(t => (
          <g key={t}>
            <line x1={xScale(t)} y1={axisY} x2={xScale(t)} y2={axisY + 5} stroke={C.ink} strokeWidth={1} />
            <text x={xScale(t)} y={axisY + 18} textAnchor="middle" fontFamily={F.mono} fontSize={10} fill={C.ink2}>
              {t > 0 ? `+${t.toFixed(1)}` : t === 0 ? "0" : `−${Math.abs(t).toFixed(1)}`}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Hero
// ────────────────────────────────────────────────────────────────────────────
function Hero({ papers, estimates, defaultEstimates, pooled }) {
  const nCountries = new Set(papers.map(p => p.country).filter(Boolean)).size;
  const nStandardized = estimates.filter(e => Number.isFinite(e.effect_size_sd)).length;

  const stat = (label, value) => (
    <div key={label} data-stat={label} style={{ padding: "16px 22px 15px", borderRight: `1px solid ${C.ruleSoft}` }}>
      <div style={{ fontFamily: F.serif, fontSize: 31, fontWeight: 650, lineHeight: 1, color: C.ink, letterSpacing: "-0.01em" }}>{value}</div>
      <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginTop: 6 }}>{label}</div>
    </div>
  );

  return (
    <section style={{ paddingTop: 52, paddingBottom: 8 }}>
      <div style={{ animation: "fadeUp 0.5s cubic-bezier(.22,1,.36,1) both" }}>
        <div style={SC({ fontSize: 10.5, color: C.ink3 })}>
          Last updated · {releaseMonth()}
        </div>
      </div>

      <div className="hero-grid" style={{
        display: "grid", gridTemplateColumns: "1fr 320px", gap: 56,
        alignItems: "start", marginTop: 18,
      }}>
        {/* Left: headline */}
        <div>
          <h1 style={{
            fontFamily: F.serif, fontWeight: 650, color: C.ink,
            fontSize: "clamp(34px, 4.6vw, 52px)", lineHeight: 1.08, letterSpacing: "-0.02em",
            animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.05s both",
          }}>
            Does AI hurt or help learning?
          </h1>
          <p style={{
            fontFamily: F.sans, fontSize: 16, lineHeight: 1.62, color: C.ink2,
            maxWidth: 560, marginTop: 22,
            animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.12s both",
          }}>
            Explore evidence on how generative AI affects learning. The default pooled view
            covers randomized experiments with student samples. We report standardized effects
            when the source provides enough information. Other records remain available in
            study reports and downloads.
          </p>
        </div>

        {/* Right: pooled estimate panel */}
        <div className="hero-pooled" style={{
          borderLeft: `1px solid ${C.rule}`, paddingLeft: 32,
          animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.18s both",
        }}>
          <div style={SC({ fontSize: 10, color: C.ink3 })}>Pooled learning effect</div>
          {pooled ? (
            <>
              <div style={{
                fontFamily: F.serif, fontSize: 64, fontWeight: 650, lineHeight: 1,
                color: pooled.mean >= 0 ? C.pos : C.neg, marginTop: 10, letterSpacing: "-0.02em",
                fontVariantNumeric: "tabular-nums",
              }}>
                {fmtSD(pooled.mean)}
                <span style={{ fontSize: 19, color: C.ink3, fontWeight: 500, marginLeft: 8, letterSpacing: 0 }}>SD</span>
              </div>
              <div style={{ fontFamily: F.mono, fontSize: 12.5, color: C.ink2, marginTop: 10 }}>
                95% CI {fmtCI(pooled.lo, pooled.hi)}
              </div>
              <p style={{ fontFamily: F.sans, fontSize: 12, lineHeight: 1.6, color: C.ink3, marginTop: 12 }}>
                Random-effects pooled estimate across {pooled.k} primary estimates
                from student samples: AI vs. business-as-usual, learning measured
                without AI in hand. Adult and professional samples are behind the
                Sample filter below.
              </p>
            </>
          ) : (
            <div style={{ fontFamily: F.mono, fontSize: 13, color: C.ink3, marginTop: 12 }}>—</div>
          )}
        </div>
      </div>

      {/* Strip plot */}
      <div style={{ marginTop: 40, animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.24s both" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
          <span style={SC({ fontSize: 9.5, color: C.ink3 })}>Each dot is one estimate from a student sample · effect on learning, in standard deviations</span>
          <span style={{ display: "inline-flex", gap: 14, flexWrap: "wrap" }}>
            {DOMAIN_ORDER.filter(d => defaultEstimates.some(e => e.learning_domain === d)).map(d => (
              <span key={d} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontFamily: F.sans, fontSize: 11, color: C.ink2 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: DOMAIN[d].color, display: "inline-block" }} />
                {d}
              </span>
            ))}
          </span>
        </div>
        <StripPlot estimates={defaultEstimates} pooled={pooled} />
      </div>

      {/* Stats band */}
      <div className="stats-band" style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
        border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi,
        marginTop: 36, overflow: "hidden",
        animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.3s both",
      }}>
        {stat("Studies", fmt(papers.length))}
        {stat("Estimate records", fmt(estimates.length))}
        {stat("Standardized effects", fmt(nStandardized))}
        {stat("Country / setting labels", fmt(nCountries))}
      </div>
      <p style={{ fontSize: 11.5, color: C.ink3, lineHeight: 1.6, marginTop: 9 }}>
        Counts cover the full learning dataset, including secondary records. Only {fmt(nStandardized)} of {fmt(estimates.length)} records have a standardized effect; fewer have an uncertainty interval. Sample counts may refer to people, sessions, or other observations, so they are not added together.
      </p>
    </section>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Filter chips
// ────────────────────────────────────────────────────────────────────────────
function Chip({ label, active, onClick, color }) {
  const [h, setH] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      aria-pressed={active}
      style={{
        padding: "5px 11px",
        fontSize: 11, fontFamily: F.mono, letterSpacing: "0.04em",
        fontWeight: active ? 600 : 400,
        background: active ? (color || C.ink) : (h ? C.paperDeep : "transparent"),
        color: active ? C.paper : (h ? C.ink : C.ink2),
        border: `1px solid ${active ? (color || C.ink) : C.rule}`,
        borderRadius: 2, cursor: "pointer",
        transition: "all 0.13s", whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

function FilterRow({ label, options, active, onToggle, colorMap, isRadio, last }) {
  if (!options || options.length === 0) return null;
  return (
    <div role="group" aria-label={`${label} filter`} style={{
      display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap",
      padding: "11px 0", borderBottom: last ? "none" : `1px solid ${C.ruleSoft}`,
    }}>
      <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), minWidth: 96, paddingTop: 4 }}>{label}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", flex: 1, alignItems: "center" }}>
        {options.map((opt) => {
          const value = typeof opt === "string" ? opt : opt.value;
          const optLabel = typeof opt === "string" ? opt : opt.label;
          const color = colorMap ? colorMap[value] : null;
          return (
            <Chip key={value} label={optLabel} active={active.has(value)} onClick={() => onToggle(value)} color={color} />
          );
        })}
        {!isRadio && [...active].some(v => v !== "__all") && (
          <button
            onClick={() => onToggle("__all")}
            style={{
              background: "none", border: "none", color: C.ink3, fontSize: 10.5,
              cursor: "pointer", fontFamily: F.mono, textDecoration: "underline",
              letterSpacing: "0.06em", padding: "4px 6px", textTransform: "uppercase",
            }}>clear</button>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Marker shapes (SVG)
// ────────────────────────────────────────────────────────────────────────────
function Marker({ shape, color, size = 7, cx, cy, opacity = 1 }) {
  const baseProps = { fill: color, stroke: C.paperHi, strokeWidth: 1, opacity };
  switch (shape) {
    case "circle":
      return <circle cx={cx} cy={cy} r={size} {...baseProps} />;
    case "square":
      return <rect x={cx - size * 0.9} y={cy - size * 0.9} width={size * 1.8} height={size * 1.8} {...baseProps} />;
    case "triangle":
      return <polygon points={`${cx},${cy - size * 1.1} ${cx - size},${cy + size * 0.8} ${cx + size},${cy + size * 0.8}`} {...baseProps} />;
    case "diamond":
      return <polygon points={`${cx},${cy - size * 1.15} ${cx + size * 1.15},${cy} ${cx},${cy + size * 1.15} ${cx - size * 1.15},${cy}`} {...baseProps} />;
    case "cross":
      return (
        <g opacity={opacity}>
          <line x1={cx - size} y1={cy - size} x2={cx + size} y2={cy + size} stroke={color} strokeWidth={2.2} />
          <line x1={cx - size} y1={cy + size} x2={cx + size} y2={cy - size} stroke={color} strokeWidth={2.2} />
        </g>
      );
    default:
      return <circle cx={cx} cy={cy} r={size} {...baseProps} />;
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Forest plot — the centerpiece
// ────────────────────────────────────────────────────────────────────────────
function OverflowArrow({ x, y, direction, color, size = 6, opacity = 1, stroke }) {
  const baseX = x + (direction === "left" ? size : -size);
  return <polygon points={`${x},${y} ${baseX},${y - size * 0.65} ${baseX},${y + size * 0.65}`} fill={color} opacity={opacity} stroke={stroke} strokeWidth={stroke ? 1.5 : 0} />;
}

function ForestPlot({ estimates, papers, onSelectPaper, width = 1084, sortMode = "effect" }) {
  const [hovered, setHovered] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const clipId = `forest-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  // Rows need an effect plus either a usable SE (pooled, precision-sized) or
  // a stored CI (drawn at fixed size, excluded from pooling).
  const plotable = estimates
    .filter(isPlottableEstimate)
    .map(e => {
      const { lo, hi } = ciOf(e);
      return { ...e, ci_lo: lo, ci_hi: hi, hasSE: isPoolableEstimate(e) };
    });

  const yearOf = (e) => (papers.find(p => p.paper_key === e.paper_key)?.year) || 0;
  const sorted = [...plotable].sort((a, b) => {
    if (sortMode === "precision") return (a.se ?? Infinity) - (b.se ?? Infinity);
    if (sortMode === "year") return yearOf(b) - yearOf(a) || b.effect_size_sd - a.effect_size_sd;
    return b.effect_size_sd - a.effect_size_sd;
  });

  const re = randomEffectsMean(plotable);

  // Precision-weighted marker sizes (SE-less rows get a fixed neutral size)
  const sqrtW = plotable.filter(e => e.hasSE).map(e => Math.sqrt(1 / (e.se ** 2)));
  const wLo = Math.min(...sqrtW), wHi = Math.max(...sqrtW);
  const sizeOf = (e) => {
    if (!e.hasSE) return 4.2;
    if (wHi === wLo) return 5;
    return 3.4 + 3.6 * ((Math.sqrt(1 / (e.se ** 2)) - wLo) / (wHi - wLo));
  };

  // Layout
  const labelW = 282;
  const valueW = 70;
  const padL = 6, padR = 8;
  const padTop = 14;
  const rowH = 26;
  const plotH = sorted.length * rowH;
  const pooledH = re ? 52 : 0;
  const axisH = 52;
  const totalH = padTop + plotH + pooledH + axisH;
  const xMin = -1.0, xMax = 1.0;
  const plotW = width - labelW - valueW - padL - padR;
  const xScale = (x) => labelW + padL + ((x - xMin) / (xMax - xMin)) * plotW;
  // The pooled summary row sits at the TOP of the plot; study rows follow.
  const yScale = (i) => padTop + pooledH + (i + 0.5) * rowH;
  const xTicks = [-1.0, -0.5, 0, 0.5, 1.0];
  const axisTop = padTop + plotH + pooledH;

  if (plotable.length === 0) {
    return (
      <div style={{
        padding: "64px 20px", textAlign: "center", color: C.ink2, fontFamily: F.sans, fontSize: 14,
        background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
      }}>
        {estimates.length === 0
          ? "No estimates match the current filters."
          : "Matching records lack a standardized effect or uncertainty interval. Open Table to inspect them."}
      </div>
    );
  }

  return (
    <div style={{ position: "relative", background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
      <div className="plot-scroll">
        <div style={{ position: "relative", width, margin: "0 auto" }}>
          <svg width={width} height={totalH} style={{ display: "block" }} aria-label="Forest plot of learning effects">
            <defs>
              <clipPath id={clipId}>
                <rect x={xScale(xMin)} y={padTop} width={plotW} height={axisTop - padTop} />
              </clipPath>
            </defs>

            {/* Zebra striping across the full row (label, plot, value) */}
            {sorted.map((_e, i) => i % 2 === 1 && (
              <rect key={`zebra-${i}`} x={0} y={padTop + pooledH + i * rowH} width={width} height={rowH} fill="#F7F6F3" />
            ))}

            {/* Pooled-estimate band across study rows */}
            {re && (
              <rect
                x={xScale(re.lo)} y={padTop + pooledH}
                width={Math.max(0, xScale(re.hi) - xScale(re.lo))} height={plotH}
                fill={C.accent} opacity={0.07}
                clipPath={`url(#${clipId})`}
              />
            )}

            {/* Gridlines */}
            {xTicks.filter(t => t !== 0).map(t => (
              <line key={`g-${t}`} x1={xScale(t)} y1={padTop} x2={xScale(t)} y2={axisTop} stroke={C.ruleSoft} strokeWidth={1} />
            ))}
            {/* Zero line */}
            <line x1={xScale(0)} y1={padTop} x2={xScale(0)} y2={axisTop} stroke={C.ink3} strokeWidth={1} strokeDasharray="3 3" />
            {/* Pooled mean vertical */}
            {re && (
              <line x1={xScale(re.mean)} y1={padTop} x2={xScale(re.mean)} y2={axisTop} stroke={C.accent} strokeWidth={1} opacity={0.5} clipPath={`url(#${clipId})`} />
            )}

            {/* Rows */}
            {sorted.map((e, i) => {
              const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
              const cx = xScale(Math.max(xMin, Math.min(xMax, e.effect_size_sd)));
              const cy = yScale(i);
              const loClamped = e.ci_lo < xMin, hiClamped = e.ci_hi > xMax;
              const intervalVisible = e.ci_hi >= xMin && e.ci_lo <= xMax;
              const pointOutside = e.effect_size_sd < xMin || e.effect_size_sd > xMax;
              const ciLoX = xScale(Math.min(xMax, Math.max(xMin, e.ci_lo)));
              const ciHiX = xScale(Math.max(xMin, Math.min(xMax, e.ci_hi)));
              const isHl = hovered === e.estimate_id;
              let label = e.study_label || e.paper_key;
              if (label.length > 42) label = label.slice(0, 40) + "…";

              return (
                <g key={e.estimate_id}
                  onMouseEnter={() => { setHovered(e.estimate_id); setTooltipPos({ x: cx, y: cy }); }}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => { const p = papers.find(p => p.paper_key === e.paper_key); if (p) onSelectPaper(p); }}
                  onFocus={() => { setHovered(e.estimate_id); setTooltipPos({ x: cx, y: cy }); }}
                  onBlur={() => setHovered(null)}
                  onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); const p = papers.find(p => p.paper_key === e.paper_key); if (p) onSelectPaper(p); } }}
                  tabIndex={0} role="button"
                  aria-label={`${e.study_label}: ${fmtSD(e.effect_size_sd)} SD. Open study record.`}
                  data-estimate-id={e.estimate_id}
                  style={{ cursor: "pointer" }}
                >
                  <rect x={0} y={cy - rowH / 2} width={width} height={rowH} fill={isHl ? "#EDEBE6" : "transparent"} />
                  <text x={labelW - 6} y={cy + 3.5} fontSize={11} fontFamily={F.sans} fill={isHl ? C.ink : C.ink2} fontWeight={isHl ? 600 : 400} textAnchor="end">
                    {label}
                  </text>
                  <g clipPath={`url(#${clipId})`}>
                    {/* Intervals outside the axis have no visible endpoint cap. */}
                    {intervalVisible && <line x1={ciLoX} y1={cy} x2={ciHiX} y2={cy} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />}
                    {intervalVisible && !loClamped && <line x1={ciLoX} y1={cy - 3.5} x2={ciLoX} y2={cy + 3.5} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />}
                    {intervalVisible && !hiClamped && <line x1={ciHiX} y1={cy - 3.5} x2={ciHiX} y2={cy + 3.5} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />}
                    {loClamped && <OverflowArrow x={xScale(xMin)} y={cy} direction="left" color={dom.color} opacity={0.55} />}
                    {hiClamped && <OverflowArrow x={xScale(xMax)} y={cy} direction="right" color={dom.color} opacity={0.55} />}
                    {pointOutside
                      ? <OverflowArrow x={cx} y={cy} direction={e.effect_size_sd < xMin ? "left" : "right"} color={dom.color} size={isHl ? 10 : 8} />
                      : <Marker shape={dom.symbol} color={dom.color} size={isHl ? sizeOf(e) + 1.2 : sizeOf(e)} cx={cx} cy={cy} opacity={e.hasSE ? 1 : 0.65} />}
                  </g>
                  {/* Value column */}
                  <text x={width - padR} y={cy + 3.5} fontSize={11} fontFamily={F.mono}
                    fill={e.effect_size_sd >= 0 ? C.pos : C.neg} fontWeight={isHl ? 600 : 500} textAnchor="end">
                    {fmtSD(e.effect_size_sd)}
                  </text>
                </g>
              );
            })}

            {/* Pooled diamond row (top of the plot, above the study rows) */}
            {re && (() => {
              const cy = padTop + 24;
              return (
                <g aria-label={`Pooled estimate: ${fmtSD(re.mean)} SD, 95% CI ${fmtCI(re.lo, re.hi)}`}>
                  <title>{`Pooled estimate: ${fmtSD(re.mean)} SD, 95% CI ${fmtCI(re.lo, re.hi)}`}</title>
                  <text x={labelW - 6} y={cy + 3.5} fontSize={11.5} fontFamily={F.sans} fontWeight={600} fill={C.ink} textAnchor="end">
                    Pooled estimate (random effects)
                  </text>
                  <g clipPath={`url(#${clipId})`}>
                    <polygon
                      points={`${xScale(re.lo)},${cy} ${xScale(re.mean)},${cy - 9} ${xScale(re.hi)},${cy} ${xScale(re.mean)},${cy + 9}`}
                      fill={C.accent}
                    />
                    {re.lo < xMin && <OverflowArrow x={xScale(xMin)} y={cy} direction="left" color={C.accent} size={9} stroke={C.paper} />}
                    {re.hi > xMax && <OverflowArrow x={xScale(xMax)} y={cy} direction="right" color={C.accent} size={9} stroke={C.paper} />}
                  </g>
                  <text x={width - padR} y={cy + 3.5} fontSize={11.5} fontFamily={F.mono} fill={C.accent} fontWeight={600} textAnchor="end">
                    {fmtSD(re.mean)}
                  </text>
                  <line x1={0} y1={padTop + pooledH - 8} x2={width} y2={padTop + pooledH - 8} stroke={C.rule} strokeWidth={1} />
                </g>
              );
            })()}

            {/* X axis */}
            <line x1={labelW + padL} y1={axisTop + 8} x2={labelW + padL + plotW} y2={axisTop + 8} stroke={C.ink} strokeWidth={1} />
            {xTicks.map(t => (
              <g key={`t-${t}`}>
                <line x1={xScale(t)} y1={axisTop + 8} x2={xScale(t)} y2={axisTop + 13} stroke={C.ink} strokeWidth={1} />
                <text x={xScale(t)} y={axisTop + 26} fontSize={10.5} fontFamily={F.mono} fill={C.ink2} textAnchor="middle">
                  {t > 0 ? `+${t.toFixed(1)}` : t === 0 ? "0" : `−${Math.abs(t).toFixed(1)}`}
                </text>
              </g>
            ))}
            <text x={labelW + padL + plotW / 2} y={axisTop + 44} fontSize={11.5} fontFamily={F.sans} fill={C.ink2} textAnchor="middle">
              Effect on learning (standard deviations) — negative ← · → positive
            </text>
          </svg>

          {/* Tooltip */}
          {hovered && (() => {
            const e = plotable.find(x => x.estimate_id === hovered);
            if (!e) return null;
            const p = papers.find(p => p.paper_key === e.paper_key);
            const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
            const tooltipW = 264, tooltipH = 215;
            const left = Math.max(8, Math.min(tooltipPos.x + 16, width - tooltipW - 12));
            const top = tooltipPos.y + tooltipH + 24 > totalH
              ? Math.max(8, tooltipPos.y - tooltipH - 6)
              : tooltipPos.y + 14;
            const row = { display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "7px 14px", borderTop: `1px solid ${C.ruleSoft}` };
            const rl = { fontFamily: F.sans, fontSize: 11, color: C.ink3 };
            const rv = { fontFamily: F.mono, fontSize: 12, color: C.ink, fontWeight: 500 };
            return (
              <div style={{
                position: "absolute", left, top, width: tooltipW, zIndex: 50,
                background: C.paperHi, border: `1px solid ${C.ink}`, borderRadius: 2,
                boxShadow: "4px 4px 0 rgba(26,23,19,0.12)", pointerEvents: "none",
                animation: "fadeIn 0.12s ease both",
              }}>
                <div style={{ padding: "10px 14px 9px" }}>
                  <div style={{ fontFamily: F.serif, fontSize: 14.5, fontWeight: 650, color: C.ink, lineHeight: 1.2 }}>
                    {p?.authors_short} ({p?.year})
                  </div>
                  <div style={{ fontFamily: F.sans, fontSize: 11, color: C.ink2, marginTop: 3, lineHeight: 1.4 }}>
                    {e.outcome}
                  </div>
                </div>
                <div style={row}>
                  <span style={rl}>Effect size</span>
                  <span style={{ ...rv, color: e.effect_size_sd >= 0 ? C.pos : C.neg, fontWeight: 600 }}>{fmtSD(e.effect_size_sd)} SD</span>
                </div>
                <div style={row}>
                  <span style={rl}>95% CI</span>
                  <span style={rv}>{fmtCI(e.ci_lo, e.ci_hi)}</span>
                </div>
                <div style={row}>
                  <span style={rl}>Sample</span>
                  <span style={{ ...rv, fontSize: 11, textAlign: "right", maxWidth: "70%" }}>{estimateSample(e, p)}</span>
                </div>
                {(e.estimand || e.estimation_method) && (
                  <div style={row}>
                    <span style={rl}>Estimand</span>
                    <span style={{ ...rv, fontSize: 11 }}>{e.estimand || "—"}{e.estimation_method ? ` · ${e.estimation_method}` : ""}</span>
                  </div>
                )}
                <div style={{ ...row, borderTop: `1px solid ${C.ruleSoft}` }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, ...rl }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: dom.color, display: "inline-block" }} />
                    {e.learning_domain} · {e.outcome_timing}
                  </span>
                  <span style={{ ...rl, fontStyle: "italic" }}>click to open</span>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Estimates table
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
        padding: "64px 20px", textAlign: "center", color: C.ink2, fontFamily: F.sans, fontSize: 14,
        background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
      }}>
        No estimates match the current filters.
      </div>
    );
  }

  const th = {
    ...SC({ fontSize: 9.5, color: C.ink2 }),
    textAlign: "left", padding: "11px 12px",
    background: C.paperDeep, borderBottom: `1px solid ${C.rule}`,
    position: "sticky", top: 0, zIndex: 2, whiteSpace: "nowrap",
  };
  const td = {
    fontSize: 12.5, padding: "10px 12px", borderBottom: `1px solid ${C.ruleSoft}`,
    fontFamily: F.sans, color: C.ink, verticalAlign: "top",
  };
  const num = { fontFamily: F.mono, textAlign: "right", fontVariantNumeric: "tabular-nums" };

  return (
    <div role="region" aria-label="Estimates table; scroll horizontally for all columns" tabIndex={0} style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2, overflow: "auto", maxHeight: 720 }}>
      <table style={{ width: "100%", minWidth: 960, borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>
            <th style={th}>Study</th>
            <th style={{ ...th, textAlign: "right" }}>Effect (SD)</th>
            <th style={{ ...th, textAlign: "right" }}>SE</th>
            <th style={{ ...th, textAlign: "right" }}>95% CI</th>
            <th style={{ ...th, textAlign: "right" }}>Estimate sample</th>
            <th style={th}>Domain</th>
            <th style={th}>Outcome</th>
            <th style={th}>Timing</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => {
            const p = paperByKey[e.paper_key];
            const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
            const { lo, hi } = ciOf(e);
            return (
              <tr key={e.estimate_id} className="hover-row"
                data-estimate-id={e.estimate_id}
                onClick={() => p && onSelectPaper(p)}
                tabIndex={p ? 0 : -1}
                onKeyDown={(ev) => { if (p && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); onSelectPaper(p); } }}
                style={{ cursor: p ? "pointer" : "default", background: "transparent", transition: "background 0.1s" }}
              >
                <td style={{ ...td, minWidth: 200 }}>
                  <div style={{ fontWeight: 500 }}>{e.study_label}</div>
                  {e.is_subgroup && e.subgroup && (
                    <div style={{ fontSize: 10.5, color: C.ink3, fontFamily: F.mono, marginTop: 2 }}>subgroup · {e.subgroup}</div>
                  )}
                </td>
                <td style={{ ...td, ...num, fontWeight: 600, color: e.effect_size_sd >= 0 ? C.pos : C.neg }}>{fmtSD(e.effect_size_sd)}</td>
                <td style={{ ...td, ...num, color: C.ink2 }}>{fmtSE(e.se)}</td>
                <td style={{ ...td, ...num, color: C.ink2, whiteSpace: "nowrap" }}>{fmtCI(lo, hi)}</td>
                <td style={{ ...td, ...num, color: C.ink2, minWidth: 145, fontSize: 11 }}>{estimateSample(e, p)}</td>
                <td style={{ ...td, whiteSpace: "nowrap" }}>
                  <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: dom.color, marginRight: 7, verticalAlign: "middle" }} />
                  <span style={{ fontSize: 12 }}>{e.learning_domain}</span>
                </td>
                <td style={{ ...td, color: C.ink2, maxWidth: 300, fontSize: 12 }}>{e.outcome}</td>
                <td style={{ ...td, color: C.ink2, fontSize: 12, whiteSpace: "nowrap" }}>{e.outcome_timing}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Study card — typographic, no photography
// ────────────────────────────────────────────────────────────────────────────
function EffectBar({ value, color }) {
  if (value == null) return <div style={{ height: 3, background: C.ruleSoft, borderRadius: 1 }} />;
  const center = 50;
  const pct = Math.min(Math.abs(value) * 50, 50);
  const left = value >= 0 ? center : center - pct;
  return (
    <div style={{ position: "relative", height: 4, background: C.ruleSoft, borderRadius: 1, overflow: "visible" }}>
      <div style={{ position: "absolute", left: "50%", top: -2, width: 1, height: 8, background: C.ink3 }} />
      <div style={{ position: "absolute", top: 0, left: `${left}%`, height: 4, width: `${pct}%`, background: color, borderRadius: 1 }} />
    </div>
  );
}

function StudyCard({ paper, onClick, idx, viewEffect, viewDomains }) {
  const [h, setH] = useState(false);
  const eff = viewEffect !== undefined ? viewEffect : paper.avg_effect;
  const domain = viewDomains?.length ? viewDomains.join(" / ") : paper.learning_domain_primary || "Mixed";
  const dom = DOMAIN[domain] || DOMAIN.Mixed;

  return (
    <div
      data-paper-key={paper.paper_key}
      onClick={() => onClick(paper)}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(paper); } }}
      style={{
        background: C.paperHi,
        borderLeft: `1px solid ${h ? C.ink : C.rule}`,
        borderRight: `1px solid ${h ? C.ink : C.rule}`,
        borderBottom: `1px solid ${h ? C.ink : C.rule}`,
        borderTop: `3px solid ${dom.color}`,
        borderRadius: 2,
        cursor: "pointer",
        transition: "all 0.15s ease",
        transform: h ? "translateY(-3px)" : "none",
        boxShadow: h ? "5px 5px 0 rgba(26,23,19,0.1)" : "none",
        animation: `fadeUp 0.4s cubic-bezier(.22,1,.36,1) ${Math.min(idx * 0.025, 0.4)}s both`,
        display: "flex", flexDirection: "column",
        padding: "15px 16px 14px",
        minHeight: 188,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 9 }}>
        <span style={SC({ fontSize: 9, color: dom.color, fontWeight: 600 })}>{domain}</span>
        <span style={SC({ fontSize: 9, color: C.ink3 })}>{paper.country}</span>
      </div>
      <div style={{
        fontFamily: F.serif, fontSize: 16, fontWeight: 600, lineHeight: 1.28, color: C.ink,
        display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
        marginBottom: 8, letterSpacing: "-0.005em",
      }}>
        {paper.title}
      </div>
      <div style={{ fontFamily: F.sans, fontSize: 11.5, color: C.ink2, marginBottom: 12 }}>
        {paper.authors_short} ({paper.year})
      </div>
      <div style={{ marginTop: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
          <span style={SC({ fontSize: 8.5, color: C.ink3 })}>
            {paper.population_category} · {studySample(paper)}
          </span>
          <span style={{
            fontSize: 12.5, fontFamily: F.mono, fontWeight: 600,
            color: eff == null ? C.ink3 : (eff >= 0 ? C.pos : C.neg),
          }}>
            {fmtSD(eff)} <span style={{ fontSize: 9, color: C.ink3, fontWeight: 400 }}>SD</span>
          </span>
        </div>
        <EffectBar value={eff} color={dom.color} />
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Inclusion criteria + paper suggestion band
// ────────────────────────────────────────────────────────────────────────────
const SUGGEST_MAILTO = "mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20paper%20suggestion&body=Citation%20(or%20link%2FPDF)%3A%20%0ANotes%20(optional)%3A%20";

function NotesBand() {
  const cell = { padding: "20px 24px" };
  return (
    <div className="notes-band" style={{
      display: "grid", gridTemplateColumns: "1fr 1fr",
      border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi,
      marginTop: 28, overflow: "hidden",
    }}>
      <div style={{ ...cell, borderRight: `1px solid ${C.ruleSoft}` }}>
        <div style={{ ...SC({ fontSize: 9.5, color: C.accent }), marginBottom: 9 }}>Inclusion criteria</div>
        <p style={{ fontFamily: F.sans, fontSize: 13, lineHeight: 1.62, color: C.ink2 }}>
          Studies enter the atlas if they <strong style={{ color: C.ink }}>randomly assign</strong> access
          to AI against a no-AI control (or use a clean quasi-experimental design with an unassisted
          assessment) and report at least <strong style={{ color: C.ink }}>50 participants</strong>.
          Inclusion never depends on what a study found.
          {" "}<a href={`${import.meta.env.BASE_URL}about/`} style={{ color: C.accent, textDecoration: "underline" }}>Some existing records still need denominator or inclusion checks.</a>
        </p>
      </div>
      <div style={cell}>
        <div style={{ ...SC({ fontSize: 9.5, color: C.accent }), marginBottom: 9 }}>Suggest a paper</div>
        <p style={{ fontFamily: F.sans, fontSize: 13, lineHeight: 1.62, color: C.ink2 }}>
          Know of a study we missed? Send the paper or citation to{" "}
          <a href={SUGGEST_MAILTO} style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
            learning_study@middlebury.edu
          </a>{" "}and it will be reviewed against the criteria.
        </p>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Footer
// ────────────────────────────────────────────────────────────────────────────
const BIBTEX_SITE = `@misc{reyes_atlas_ai_human_skill,
  title  = {The AI and Human Skill Atlas},
  author = {Reyes, Germán},
  year   = {2026},
  url    = {https://aiskillatlas.org/},
  note   = {Data release ${RELEASE.id}, ${RELEASE.date}}
}`;

function Footer() {
  const base = import.meta.env.BASE_URL;
  return (
    <footer style={{ marginTop: 72 }}>
      <div className="wrap" style={{ maxWidth: 1140, margin: "0 auto", padding: "0 28px 56px" }}>
        <DoubleRule style={{ marginBottom: 28 }} />
        <div className="footer-grid" style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: 44 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 12 }}>
              <Glyph size={20} />
              <span style={{ fontFamily: F.serif, fontSize: 15.5, fontWeight: 650 }}>The AI <span style={{ fontStyle: "italic", fontWeight: 500 }}>&</span> Human Skill Atlas</span>
            </div>
            <p style={{ fontFamily: F.sans, fontSize: 12.5, lineHeight: 1.65, color: C.ink2, maxWidth: 330 }}>
              A living atlas of randomized experiments on how generative AI affects human
              skill formation. Built on the meta-analysis in Contractor &amp; Reyes (2026).
            </p>
            <p style={{ fontFamily: F.sans, fontSize: 12.5, lineHeight: 1.65, color: C.ink2, marginTop: 10 }}>
              Built by{" "}
              <a href="https://www.germanr.com" target="_blank" rel="noreferrer" style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
                Germán Reyes
              </a>, Middlebury College, with research assistance from Nam Nguyen and Wills Erda.
            </p>
          </div>
          <div>
            <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginBottom: 12 }}>Cite this resource</div>
            <pre style={{
              fontFamily: F.mono, fontSize: 10.5, color: C.ink2, lineHeight: 1.55,
              background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
              padding: "12px 14px", whiteSpace: "pre-wrap", overflow: "auto",
            }}>{BIBTEX_SITE}</pre>
          </div>
          <div>
            <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginBottom: 12 }}>Navigate</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["The evidence", `${base}#evidence`],
                ["The studies", `${base}#studies`],
                ...(SHOW_CREATIVITY ? [["Creativity (beta)", `${base}?section=creativity`]] : []),
                ["About & methodology", `${base}about/`],
                ["Data releases", `${base}about/#data-releases`],
                ["Suggest a paper", SUGGEST_MAILTO],
              ].map(([label, href]) => (
                <a key={label} href={href} style={{
                  fontFamily: F.sans, fontSize: 12.5, color: C.ink2,
                  borderBottom: "1px solid transparent", width: "fit-content",
                }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = C.ink; e.currentTarget.style.borderBottomColor = C.ink; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = C.ink2; e.currentTarget.style.borderBottomColor = "transparent"; }}
                >{label}</a>
              ))}
            </div>
          </div>
        </div>
        <div style={{
          marginTop: 36, paddingTop: 16, borderTop: `1px solid ${C.ruleSoft}`,
          display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 10,
        }}>
          <span style={{ ...SC({ fontSize: 9, color: C.ink3 }), overflowWrap: "anywhere" }}>Data release {RELEASE.id} · {releaseDate()}</span>
          <span style={SC({ fontSize: 9, color: C.ink3 })}>aiskillatlas.org</span>
        </div>
      </div>
    </footer>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Report card (study detail)
// ────────────────────────────────────────────────────────────────────────────
function EstimateRow({ est, paper, domain, last }) {
  const range = 2.0; // [-1, +1]
  const hasEffect = Number.isFinite(est.effect_size_sd);
  const pct = ((Math.max(-1, Math.min(1, est.effect_size_sd)) + 1) / range) * 100;
  const { lo: ciLo, hi: ciHi } = ciOf(est);
  const clamp = (x) => Math.max(-1, Math.min(1, x));
  return (
    <div data-estimate-id={est.estimate_id} data-has-standardized-effect={hasEffect} style={{ padding: "16px 22px", borderBottom: last ? "none" : `1px solid ${C.ruleSoft}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "baseline", marginBottom: 4 }}>
        <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 13.5, color: C.ink, lineHeight: 1.4 }}>{est.outcome}</div>
        <div style={{
          fontSize: 17, fontWeight: 600, fontFamily: F.mono, whiteSpace: "nowrap",
          color: !hasEffect ? C.ink3 : est.effect_size_sd >= 0 ? C.pos : C.neg,
        }}>
          {fmtSD(est.effect_size_sd)} {hasEffect && <span style={{ fontSize: 10, color: C.ink3, fontWeight: 400 }}>SD</span>}
        </div>
      </div>
      <div style={{ fontFamily: F.mono, fontSize: 10.5, color: C.ink3, marginBottom: 12 }}>
        {est.outcome_timing} · {estimateSample(est, paper)}
        {est.se != null && <span data-statistic="se"> · SE {fmtSE(est.se)}</span>}
        {ciLo != null && ciHi != null && <span data-statistic="ci"> · 95% CI {fmtCI(ciLo, ciHi)}</span>}
      </div>
      {!hasEffect && <p style={{ fontSize: 11.5, color: C.ink3, marginBottom: 10, lineHeight: 1.5 }}>Standardized effect unavailable. This does not mean the effect is zero.</p>}
      {hasEffect && (ciLo == null || ciHi == null) && <p style={{ fontSize: 11.5, color: C.ink3, marginBottom: 10, lineHeight: 1.5 }}>Uncertainty interval unavailable.</p>}
      {/* Number line (only when an SD-unit effect exists) */}
      {hasEffect && (
        <>
          <div style={{ position: "relative", height: 16 }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: 7, height: 1, background: C.rule }} />
            <div style={{ position: "absolute", left: "50%", top: 2, width: 1, height: 11, background: C.ink3 }} />
            {ciLo != null && ciHi != null && (
              <div style={{
                position: "absolute",
                left: `${((clamp(ciLo) + 1) / range) * 100}%`,
                width: `${Math.max(0, ((clamp(ciHi) - clamp(ciLo)) / range) * 100)}%`,
                top: 5.5, height: 4, background: domain.color, opacity: 0.3, borderRadius: 2,
              }} />
            )}
            <div style={{
              position: "absolute", left: `${pct}%`, top: 2.5, width: 10, height: 10,
              background: domain.color, borderRadius: domain.symbol === "square" ? 0 : "50%",
              transform: "translateX(-50%)", border: `1.5px solid ${C.paperHi}`,
              boxShadow: `0 0 0 1px ${domain.color}`,
            }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, fontFamily: F.mono, color: C.ink3, marginTop: 2 }}>
            <span>−1.0</span><span>0</span><span>+1.0</span>
          </div>
        </>
      )}
      {est.treatment && (
        <div style={{ fontSize: 12, color: C.ink2, marginTop: 10, lineHeight: 1.55, fontFamily: F.sans }}>
          <span style={{ fontWeight: 600, color: C.ink }}>{est.treatment}</span>
          <span style={{ color: C.ink3 }}> vs. </span>
          <span>{est.control}</span>
        </div>
      )}
      {est.notes && (
        <div style={{ fontSize: 11.5, color: C.ink3, marginTop: 8, lineHeight: 1.55, fontFamily: F.sans, fontStyle: "italic" }}>
          {est.notes}
        </div>
      )}
      {(est.estimand || est.estimation_method) && (
        <div style={{ display: "flex", gap: 8, marginTop: 9, flexWrap: "wrap", alignItems: "center" }}>
          {est.estimand && (
            <span style={{
              fontSize: 9, fontFamily: F.mono, fontWeight: 600, letterSpacing: "0.1em",
              color: C.ink, border: `1px solid ${C.ink}`, padding: "2px 7px", borderRadius: 2,
              textTransform: "uppercase",
            }} title="Estimand (parameter identified)">{est.estimand}</span>
          )}
          {est.estimation_method && (
            <span style={{ fontSize: 11, fontFamily: F.mono, color: C.ink2 }} title="Estimation method">{est.estimation_method}</span>
          )}
        </div>
      )}
      <SourceDetails metadata={estimateMetadata(est, paper)} />
    </div>
  );
}

function SourceDetails({ metadata }) {
  const { sample, provenance } = metadata;
  const sourceField = (key, fallback) => provenance[key] || provenance.missing_reasons?.[key] || fallback;
  const fields = [
    ["Source document", sourceField("source_document", "Not recorded")],
    ["Document version", sourceField("source_version", "Not verified")],
    ["Source location", sourceField("source_locator", "Not yet reviewed. See the existing coding notes.")],
    ["Extraction date", sourceField("extraction_date", "Not recorded")],
    ["Source review", provenance.review_status === "reviewed" ? `Reviewed (${provenance.review_basis})` : "Pending primary-source review"],
    ["Metadata check", provenance.review_date ? `${provenance.review_date}${provenance.review_basis === "local_coding" ? " (existing local coding only)" : ""}` : "Not recorded"],
    ["Sample definition", sample.review_status === "reviewed" ? (sample.review_basis === "local_coding" ? "Checked against existing local coding" : "Reviewed against the source") : "Unit and denominator not yet reviewed"],
    ["Treatment count", sample.treatment_n == null ? null : formatSample({ ...sample, n: sample.treatment_n })],
    ["Control count", sample.control_n == null ? null : formatSample({ ...sample, n: sample.control_n })],
    ["Sample notes", sample.notes],
    ["Derivation / coding notes", sourceField("derivation_notes", null)],
  ].filter(([, value]) => value);
  return (
    <details style={{ marginTop: 13, borderTop: `1px solid ${C.ruleSoft}`, paddingTop: 10, fontSize: 12, lineHeight: 1.6, color: C.ink2 }}>
      <summary style={{ cursor: "pointer", color: C.accent, fontFamily: F.sans }}>Source, sample, and version details</summary>
      <dl style={{ marginTop: 10, display: "grid", gap: 9 }}>
        {fields.map(([label, value]) => <div key={label}>
          <dt style={{ ...SC({ fontSize: 9 }), marginBottom: 2 }}>{label}</dt>
          <dd style={{ margin: 0, overflowWrap: "anywhere" }}>{value}</dd>
        </div>)}
      </dl>
      {provenance.source_url && <a href={provenance.source_url} target="_blank" rel="noreferrer" style={{ color: C.accent, textDecoration: "underline", display: "inline-block", marginTop: 9 }}>Source page ↗</a>}
      <p style={{ marginTop: 10, fontSize: 11 }}>Atlas release {RELEASE.id}. A release date is not the date of the source paper or its extraction.</p>
    </details>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 34 }}>
      <div style={{ ...SC({ fontSize: 10, color: C.ink2 }), marginBottom: 10, display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ whiteSpace: "nowrap" }}>{title}</span>
        <span style={{ flex: 1, height: 1, background: C.rule }} />
      </div>
      {children}
    </div>
  );
}

function ReportCard({ paper, estimates, onBack }) {
  const headingRef = useRef(null);
  const myEstsAll = estimates.filter(e => e.paper_key === paper.paper_key);
  const myEsts = myEstsAll.filter(e => e.is_subgroup !== true);
  const mySubgroups = myEstsAll.filter(e => e.is_subgroup === true);
  const subgroupsByCategory = mySubgroups.reduce((acc, e) => {
    const k = e.subgroup || "Other";
    (acc[k] = acc[k] || []).push(e);
    return acc;
  }, {});
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    window.scrollTo({ top: 0 });
    headingRef.current?.focus({ preventScroll: true });
  }, [paper.paper_key]);

  const pdfHref = paper.pdf_filename
    ? `${import.meta.env.BASE_URL}pdfs/${encodeURI(paper.pdf_filename)}`
    : paper.pdf_url || null;

  const bibtex = `@article{${paper.paper_key},
  title   = {${paper.title}},
  author  = {${bibtexAuthors(paper.authors_full || paper.authors_short)}},
  year    = {${paper.year || ""}},
  journal = {${paper.venue || "Working paper"}}
}`;

  const copyBib = () => {
    navigator.clipboard.writeText(bibtex).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  const dom = DOMAIN[paper.learning_domain_primary] || DOMAIN.Mixed;

  const facts = [
    ["Authors", paper.authors_full || paper.authors_short],
    ["Year", paper.year],
    ["Venue", paper.venue],
    ["Country", paper.country],
    ["Population", paper.population_category],
    ["Setting", [paper.lab_vs_field, paper.setting_detail].filter(Boolean).join(" — ")],
    ["Study design", paper.study_design],
    ["Study sample", studySample(paper)],
    ["Sample notes", studyMetadata(paper).sample.notes],
    ["Recruited participants", studyMetadata(paper).sample.recruited_n == null ? null : fmt(studyMetadata(paper).sample.recruited_n)],
    ["Randomized participants", studyMetadata(paper).sample.randomized_n == null ? null : fmt(studyMetadata(paper).sample.randomized_n)],
    ["Incentives", paper.incentives],
    ["AI tool", paper.ai_tool],
    ["AI design", paper.ai_design],
    ["Learning domain", paper.learning_domain_primary],
    ["Coding notes", paper.coding_notes || null],
  ].filter(([, v]) => v != null && v !== "");

  const summaryBlocks = [
    { label: "Setup", text: paper.summary_setup },
    { label: "Empirical strategy", text: paper.summary_strategy },
    { label: "Key results", text: paper.summary_results },
  ].filter(b => b.text);

  return (
    <div style={{ animation: "fadeIn 0.25s" }}>
      <div className="wrap" style={{ maxWidth: 880, margin: "0 auto", padding: "30px 28px 40px" }}>
        {/* Breadcrumb */}
        <button onClick={onBack} style={{
          ...SC({ fontSize: 10.5, color: C.ink2 }),
          background: "none", border: "none", cursor: "pointer", padding: 0,
          display: "inline-flex", alignItems: "center", gap: 7,
        }}
          onMouseEnter={(e) => e.currentTarget.style.color = C.ink}
          onMouseLeave={(e) => e.currentTarget.style.color = C.ink2}
        >
          <span aria-hidden="true">←</span> All studies
        </button>

        {/* Title block */}
        <div style={{ marginTop: 26, animation: "fadeUp 0.4s cubic-bezier(.22,1,.36,1) both" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={SC({ fontSize: 10, color: dom.color, fontWeight: 600 })}>
              {paper.learning_domain_primary}
            </span>
            <span style={{ width: 3, height: 3, borderRadius: "50%", background: C.ink3, display: "inline-block" }} />
            <span style={SC({ fontSize: 10 })}>{paper.population_category}</span>
            <span style={{ width: 3, height: 3, borderRadius: "50%", background: C.ink3, display: "inline-block" }} />
            <span style={SC({ fontSize: 10 })}>{paper.country}</span>
            <span style={{ width: 3, height: 3, borderRadius: "50%", background: C.ink3, display: "inline-block" }} />
            <span style={SC({ fontSize: 10 })}>{paper.study_design}</span>
          </div>
          <h1 ref={headingRef} tabIndex={-1} style={{
            fontFamily: F.serif, fontSize: "clamp(28px, 4vw, 42px)", fontWeight: 650,
            lineHeight: 1.12, letterSpacing: "-0.018em", color: C.ink, marginTop: 14,
          }}>
            {paper.title}
          </h1>
          <div style={{ fontFamily: F.sans, fontSize: 14.5, color: C.ink2, marginTop: 14 }}>
            {paper.authors_full || paper.authors_short}
            {paper.venue && <span style={{ color: C.ink3 }}> · <span style={{ fontStyle: "italic", fontFamily: F.serif, fontSize: 15 }}>{paper.venue}</span></span>}
            {paper.year && <span style={{ color: C.ink3 }}> · {paper.year}</span>}
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 10, marginTop: 22, flexWrap: "wrap", alignItems: "center" }}>
            {pdfHref && <SolidBtn href={pdfHref}>Download PDF</SolidBtn>}
            <GhostBtn onClick={copyBib}>{copied ? "Copied ✓" : "Copy BibTeX"}</GhostBtn>
            <a
              href={`mailto:learning_study@middlebury.edu?subject=${encodeURIComponent("The AI and Human Skill Atlas — correction for " + paper.authors_short + " (" + paper.year + ")")}`}
              style={{ fontFamily: F.mono, fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ink3, borderBottom: `1px solid ${C.rule}`, paddingBottom: 1 }}
              onMouseEnter={(e) => { e.currentTarget.style.color = C.ink; e.currentTarget.style.borderBottomColor = C.ink; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = C.ink3; e.currentTarget.style.borderBottomColor = C.rule; }}
            >Suggest a correction</a>
          </div>
        </div>

        <div style={{ height: 1, background: C.rule, margin: "30px 0 32px" }} />

        {/* Structured summary */}
        {summaryBlocks.length > 0 ? (
          <Section title="Study summary">
            <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
              {summaryBlocks.map((b, i) => (
                <div key={b.label} style={{
                  padding: "18px 22px",
                  borderBottom: i === summaryBlocks.length - 1 ? "none" : `1px solid ${C.ruleSoft}`,
                  display: "grid", gridTemplateColumns: "150px 1fr", gap: 18,
                }} className="facts-grid">
                  <div style={SC({ fontSize: 9.5, color: C.accent })}>{b.label}</div>
                  <div style={{ fontFamily: F.serif, fontSize: 15.5, lineHeight: 1.62, color: C.ink }}>{b.text}</div>
                </div>
              ))}
            </div>
          </Section>
        ) : paper.summary && (
          <Section title="Study summary">
            <p style={{
              fontFamily: F.serif, fontSize: 16.5, lineHeight: 1.65, color: C.ink,
              background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2, padding: "20px 24px",
            }}>{paper.summary}</p>
          </Section>
        )}

        {/* Study facts */}
        <Section title="Study record">
          <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
            {facts.map(([label, value], i) => (
              <div key={label} style={{
                display: "grid", gridTemplateColumns: "190px 1fr", gap: 18,
                padding: "11px 22px",
                borderBottom: i === facts.length - 1 ? "none" : `1px solid ${C.ruleSoft}`,
                fontSize: 13.5,
              }} className="facts-grid">
                <span style={SC({ fontSize: 9.5, color: C.ink3 })}>{label}</span>
                <span style={{ color: C.ink, lineHeight: 1.5, fontFamily: F.sans }}>{value}</span>
              </div>
            ))}
          </div>
          <SourceDetails metadata={studyMetadata(paper)} />
          <p style={{ fontSize: 11.5, color: C.ink3, marginTop: 10, lineHeight: 1.6 }}>
            Study participants and analyzed observations can differ. Each estimate below has its own sample count. Missing units are marked unreviewed rather than assumed to count people.
          </p>
        </Section>

        {/* Full-sample records may lack a standardized effect or interval. */}
        <Section title={`Estimate records (${myEsts.length})`}>
          <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
            {myEsts.map((e, idx) => (
              <EstimateRow key={e.estimate_id} est={e} paper={paper} domain={dom} last={idx === myEsts.length - 1} />
            ))}
          </div>
        </Section>

        {/* Subgroups */}
        {mySubgroups.length > 0 && (
          <Section title={`Subgroup & heterogeneity estimates (${mySubgroups.length})`}>
            <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
              {Object.entries(subgroupsByCategory).map(([category, rows], gIdx) => (
                <div key={category} style={{
                  borderBottom: gIdx === Object.keys(subgroupsByCategory).length - 1 ? "none" : `1px solid ${C.rule}`,
                }}>
                  <div style={{ ...SC({ fontSize: 9.5, color: C.ink2 }), padding: "10px 22px 8px", background: C.paperDeep }}>
                    {category}
                  </div>
                  {rows.map((e, idx) => (
                    <EstimateRow key={e.estimate_id} est={e} paper={paper} domain={dom} last={idx === rows.length - 1} />
                  ))}
                </div>
              ))}
            </div>
            <p style={{ fontSize: 11.5, color: C.ink3, marginTop: 9, fontStyle: "italic", fontFamily: F.sans, lineHeight: 1.5 }}>
              Subgroup rows are excluded from the main forest plot and the pooled estimates.
            </p>
          </Section>
        )}

        {/* Citation */}
        <Section title="How to cite">
          <pre style={{
            background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
            padding: "14px 18px", fontSize: 11.5, fontFamily: F.mono, color: C.ink,
            overflowX: "auto", whiteSpace: "pre-wrap", lineHeight: 1.6,
          }}>{bibtex}</pre>
        </Section>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// About page
// ────────────────────────────────────────────────────────────────────────────
export function AboutPage({ onBack, nPapers, nEstimates, papers, onSelectPaper, estimates = ESTIMATES_RAW }) {
  useEffect(() => {
    let cancelled = false;
    // Parent styles and web fonts can change the target's position after mount.
    // Measure only after those layout changes, including on direct anchor links.
    let frame = requestAnimationFrame(() => {
      document.fonts.ready.then(() => {
        if (cancelled) return;
        frame = requestAnimationFrame(() => {
          if (cancelled) return;
          const target = window.location.hash && document.getElementById(window.location.hash.slice(1));
          if (target) target.scrollIntoView({ block: "start", behavior: "instant" });
          else window.scrollTo({ top: 0, behavior: "instant" });
        });
      });
    });
    return () => { cancelled = true; cancelAnimationFrame(frame); };
  }, []);

  const sortedPapers = [...papers].sort((a, b) =>
    (b.year || 0) - (a.year || 0) || (a.authors_short || "").localeCompare(b.authors_short || "")
  );
  const nCountries = new Set(papers.map(p => p.country).filter(Boolean)).size;
  const nStandardized = estimates.filter(e => Number.isFinite(e.effect_size_sd)).length;

  const h2 = {
    fontFamily: F.serif, fontSize: 23, fontWeight: 650, color: C.ink,
    letterSpacing: "-0.01em", margin: "44px 0 6px",
  };
  const body = { fontFamily: F.sans, fontSize: 14, lineHeight: 1.72, color: C.ink2, margin: "12px 0 0" };
  const rule = <div style={{ height: 1, background: C.rule, marginTop: 10 }} />;

  return (
    <div style={{ background: C.paper, minHeight: "100vh", animation: "fadeIn 0.25s" }}>
      <SiteHeader active="about" />
      <div className="wrap" style={{ maxWidth: 780, margin: "0 auto", padding: "44px 28px 90px" }}>
        <div style={SC({ fontSize: 10.5, color: C.ink3 })}>About</div>
        <h1 style={{
          fontFamily: F.serif, fontSize: "clamp(30px, 4.4vw, 44px)", fontWeight: 650,
          lineHeight: 1.1, letterSpacing: "-0.02em", marginTop: 12,
        }}>
          About the Atlas
        </h1>
        <p style={{ fontFamily: F.serif, fontSize: 17.5, lineHeight: 1.6, color: C.ink2, marginTop: 18, fontStyle: "italic" }}>
          The Atlas collects studies on how generative AI affects human learning,
          standardizes results where the source permits, and documents each study. It is descriptive by design: the
          interpretation is left to the reader.
        </p>

        <p style={{ ...body, marginTop: 26 }}>
          Generative AI is entering classrooms and workplaces faster than evidence on its effects can
          accumulate. The studies that do exist are scattered across economics, education, computer
          science, and psychology, and each reports results in its own format. This site puts them in
          one place. It currently covers <strong style={{ color: C.ink }}>{nPapers} studies</strong> and{" "}
          <strong style={{ color: C.ink }}>{nEstimates} estimate records</strong>, including{" "}
          <strong style={{ color: C.ink }}>{nStandardized} standardized effects</strong>, from randomized and
          observational studies across {nCountries} country or multi-country setting labels, with
          participants ranging from elementary students to professionals.
        </p>
        <p style={body}>
          Effects use standard-deviation units where source statistics permit. The denominator follows
          the source or documented calculation, such as a control-group or pooled-arm standard deviation.
          Records without a standardized effect remain in the dataset. A missing value is not a zero.
          The default pooled view uses randomized student-sample estimates and the DerSimonian–Laird
          random-effects model. Every estimate links to a study record that
          documents the design, sample, incentives, and AI tool, and the full dataset can be downloaded
          as a CSV.
        </p>

        <h2 style={h2}>Inclusion criteria</h2>
        {rule}
        <p style={body}>
          A study enters the atlas if it satisfies two conditions. Both are checked before looking at
          the results, so inclusion never depends on what a study found.
        </p>
        <div style={{ marginTop: 16, border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi }}>
          {[
            ["1 · Source of variation", "The study randomly assigns access to generative AI against a no-AI comparison group, or exploits a credible quasi-experiment with an AI-free assessment."],
            ["2 · Sample size", "The study reports at least 50 participants in total."],
          ].map(([t, d], i, arr) => (
            <div key={t} style={{ padding: "15px 20px", borderBottom: i === arr.length - 1 ? "none" : `1px solid ${C.ruleSoft}` }}>
              <div style={{ ...SC({ fontSize: 10, color: C.accent }), marginBottom: 5 }}>{t}</div>
              <div style={{ fontFamily: F.sans, fontSize: 13.5, color: C.ink, lineHeight: 1.6 }}>{d}</div>
            </div>
          ))}
        </div>
        <p style={body}>
          These conditions exclude observational and adoption studies without random or quasi-random
          variation, studies that lack an AI-free (or alternative-AI) comparison, and studies below the
          size threshold.
        </p>
        <p style={body}>
          The stated threshold refers to study participants, not sessions or outcome observations.
          Kalam et al. (2025) is excluded from the current dataset because its 33 participants fall
          below the 50-participant threshold. Its records remain in the previous archived release.
          Other sample definitions remain marked unreviewed until checked against their sources.
        </p>

        <h2 style={h2}>What counts as learning</h2>
        {rule}
        <p style={body}>
          Studies measure learning in different ways, and the differences matter when comparing effect
          sizes. One organizing device is <strong style={{ color: C.ink }}>Bloom's taxonomy</strong>,
          which orders cognitive skills from lower to higher: remembering, understanding, applying,
          analyzing, evaluating, and creating.
        </p>
        <div style={{ marginTop: 16, border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi }}>
          {[
            ["Lower-order · remember, understand, apply", "Typically measured with test scores (multiple-choice or short-answer items). These are easy to standardize and grade, and they dominate the literature."],
            ["Higher-order · analyze, evaluate, create", "Measured with essays, open-ended problems, or transfer tasks. These are noisier and harder to grade, but closer to the skills education targets."],
          ].map(([t, d], i, arr) => (
            <div key={t} style={{ padding: "15px 20px", borderBottom: i === arr.length - 1 ? "none" : `1px solid ${C.ruleSoft}` }}>
              <div style={{ ...SC({ fontSize: 10, color: C.accent }), marginBottom: 5 }}>{t}</div>
              <div style={{ fontFamily: F.sans, fontSize: 13.5, color: C.ink, lineHeight: 1.6 }}>{d}</div>
            </div>
          ))}
        </div>
        <p style={body}>
          An effect on a multiple-choice quiz and an effect on essay quality are therefore different
          constructs, even when both are expressed in SD units. The outcome column in the data records
          what each study measured.
        </p>

        <h2 style={h2}>How to read the estimates</h2>
        {rule}
        <div style={{ marginTop: 4 }}>
          {[
            ["The pooled mean masks variation.", "Effects differ by subject, by population, and above all by whether the outcome was measured with or without AI in hand. Read the spread, not only the average."],
            ["Precision varies.", "Some estimates come from large pre-registered field experiments, others from small single-site studies over short horizons. The coding notes on each record state how derived quantities were computed and note design features relevant to interpretation."],
            ["Independence varies.", "Some studies were conducted by, or in collaboration with, the companies whose tools they evaluate. The study records note this where it applies."],
            ["Intervals overlap.", "Most pairs of studies cannot be reliably ranked. The forest plot describes a distribution, not a leaderboard."],
          ].map(([t, d]) => (
            <div key={t} style={{ display: "grid", gridTemplateColumns: "10px 1fr", gap: 14, padding: "13px 0", borderBottom: `1px solid ${C.ruleSoft}` }}>
              <span style={{ color: C.accent, fontFamily: F.mono, fontSize: 13, lineHeight: 1.5 }}>—</span>
              <p style={{ fontFamily: F.sans, fontSize: 13.5, lineHeight: 1.65, color: C.ink2, margin: 0 }}>
                <strong style={{ color: C.ink }}>{t}</strong> {d}
              </p>
            </div>
          ))}
        </div>

        <h2 style={h2}>Included studies · {sortedPapers.length}</h2>
        {rule}
        <div style={{ marginTop: 4 }}>
          {sortedPapers.map(p => {
            const pdfHref = p.pdf_filename ? `${import.meta.env.BASE_URL}pdfs/${encodeURI(p.pdf_filename)}` : null;
            return (
              <div key={p.paper_key}
                onClick={() => onSelectPaper(p)}
                className="hover-row"
                role="button" tabIndex={0}
                onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onSelectPaper(p); } }}
                style={{ padding: "13px 10px 13px 0", borderBottom: `1px solid ${C.ruleSoft}`, cursor: "pointer", transition: "background 0.1s" }}
              >
                <div style={{ fontFamily: F.sans, fontSize: 13.5, fontWeight: 600, color: C.ink, lineHeight: 1.45 }}>
                  {p.authors_short} ({p.year}) — "{p.title}"
                  {p.venue && <span style={{ fontWeight: 400, color: C.ink3, fontSize: 11.5, marginLeft: 8, fontStyle: "italic", fontFamily: F.serif }}>{p.venue}</span>}
                </div>
                <div style={{ fontFamily: F.mono, fontSize: 10.5, color: C.ink3, marginTop: 4, letterSpacing: "0.02em" }}>
                  {p.country} · {p.population_category} · {p.lab_vs_field} · {p.study_design} · {studySample(p)}
                  {pdfHref && (
                    <>
                      {" · "}
                      <a href={pdfHref} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
                        style={{ color: C.ink2, borderBottom: `1px dotted ${C.ink3}` }}>PDF</a>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <h2 style={h2}>Methods</h2>
        {rule}
        <div style={{ marginTop: 4 }}>
          {[
            ["Standardization.", "Effects are expressed in standard-deviation units where the source permits. Available derivation details appear in each estimate's coding and source notes. Missing source versions, locators, and derivations remain marked unreviewed."],
            ["Pooling.", "The pooled mean uses the DerSimonian–Laird random-effects estimator; the shaded band in the forest plot is its 95% confidence interval, which reflects between-study heterogeneity."],
            ["Design.", "Every estimate is classed as a lab, field, or online randomized experiment, or as observational (credible quasi-experimental variation without random assignment). The default view and the headline pooled estimate cover randomized experiments only; observational studies appear under the Design filter."],
            ["Samples.", "The default view shows student samples (elementary school through university). Studies of adult online-panel and professional samples are in the atlas but shown only when the Sample filter is set to Non-students or All samples."],
            ["Learning vs. assisted performance.", "The default view excludes outcomes measured with AI access (e.g., assisted-practice scores), which capture AI-augmented performance rather than learning. The Outcome filter adds them back."],
            ["Outcome timing.", "All timings is the default. Immediate and Delayed use the existing outcome codes, independently of AI availability during assessment. These are broad categories, not common follow-up intervals. Comparisons across filtered subsets do not identify learning decay because the studies can differ. Some classifications, including LearnLM next-topic assessments, still need source review."],
            ["Sample counts.", "Study sample counts and analyzed observations are separate. They may count people, sessions, or other units. Unreviewed units are labeled explicitly. Counts are not summed across outcomes or studies, since units and sample overlap can differ."],
            ["Comparisons.", "AI vs. business-as-usual is the default and never pooled with the others. AI vs. active control and off-the-shelf vs. scaffolded AI can each be viewed separately."],
            ["Subgroups.", "Heterogeneity estimates (by gender, prior achievement, topic) are excluded from the forest plot and the pooled estimates; they appear on each study's record."],
          ].map(([t, d]) => (
            <div key={t} style={{ display: "grid", gridTemplateColumns: "10px 1fr", gap: 14, padding: "12px 0", borderBottom: `1px solid ${C.ruleSoft}` }}>
              <span style={{ color: C.accent, fontFamily: F.mono, fontSize: 13, lineHeight: 1.5 }}>—</span>
              <p style={{ fontFamily: F.sans, fontSize: 13.5, lineHeight: 1.65, color: C.ink2, margin: 0 }}>
                <strong style={{ color: C.ink }}>{t}</strong> {d}
              </p>
            </div>
          ))}
        </div>

        <h2 style={h2}>Data</h2>
        {rule}
        <p style={body}>
          Two CSV exports are available from the browse page: the current filtered slice, and the
          complete dataset (every estimate, including subgroup rows, with every field). The main columns:
        </p>
        <div style={{ marginTop: 16, border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi, padding: "16px 20px" }}>
          <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginBottom: 12 }}>Data dictionary</div>
          <div style={{ display: "grid", gap: 9 }}>
            {[
              ["paper_key", "Short identifier for the study."],
              ["effect_size_sd", "Standardized effect where available. The source or calculation determines the SD denominator. Positive favors the treatment condition; the record documents any outcome-direction change."],
              ["se", "Standard error of the effect (SD units)."],
              ["ci_lower / ci_upper", "95% confidence limits for a standardized effect, where available. Source notes may describe raw-unit intervals or Bayesian credible intervals instead."],
              ["n_total", "Original reported count, retained unchanged. It need not count people. Use the sample-unit and review fields."],
              ["study_sample_n / unit", "Study-level sample count and its unit. Recruited and randomized counts are separate when known."],
              ["estimate_analyzed_n / unit", "Reviewed estimate-level sample count and unit. The analyzed count is blank when the sample definition is unreviewed or unavailable; the original count remains in n_total."],
              ["sample_review_status", "Whether the sample definition was checked. Review basis distinguishes local coding from primary-source review."],
              ["source_document / locator", "Source document and supporting page, table, or analysis output. Blank fields remain unreviewed."],
              ["source_version / review_date", "Document version and metadata-check date, separate from the Atlas release date."],
              ["release_id / selection", "Atlas data release and the filter choices used for an export. A full export identifies its full-dataset scope."],
              ["learning_domain", "Subject area (math, coding, writing, language, science…)."],
              ["outcome / outcome_timing", "What was measured, and whether immediate or delayed."],
              ["comparison_type", "AI vs. business-as-usual, AI vs. active control, or off-the-shelf vs. scaffolded AI."],
              ["estimand / estimation_method", "Parameter identified (ITT, LATE…) and how it was estimated."],
              ["outcome_with_ai", "Whether the outcome was measured with AI in hand."],
              ["is_subgroup / subgroup", "Whether the row is a heterogeneity estimate, and its label."],
              ["coding_notes", "How derived quantities were computed (e.g., back-calculated SEs) and design features relevant to interpretation."],
              ["design_class", "lab_rct, field_rct, or online_rct (randomized experiments by setting), or observational (no random assignment)."],
            ].map(([col, desc]) => (
              <div key={col} style={{ display: "grid", gridTemplateColumns: "190px 1fr", gap: 12, alignItems: "baseline" }} className="facts-grid">
                <code style={{ fontFamily: F.mono, fontSize: 11, color: C.ink, fontWeight: 500 }}>{col}</code>
                <span style={{ fontSize: 12.5, color: C.ink2, lineHeight: 1.55, fontFamily: F.sans }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>

        <h2 id="data-releases" style={{ ...h2, scrollMarginTop: 125 }}>Data releases</h2>
        {rule}
        <p style={body}>
          Current release: <strong>{RELEASE.id}</strong> ({releaseDate()}). Shared view links always use
          the current data. The archives below preserve released data and the corresponding calculation
          and interface code. Their manifests list file hashes. Historical interactive browsing is not available.
        </p>
        <p style={body}>
          Source-document versions, locators, and derivations are recorded separately from the release date.
          Missing source fields remain marked unreviewed. New or revised estimates must include reviewed
          source and sample metadata before a release can be created. Unchanged legacy estimates can retain
          their missing fields while the source audit continues.
        </p>
        <div style={{ marginTop: 15 }}>
          {RELEASE_INDEX.releases.map(release => {
            const asset = path => `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;
            return <div key={release.id} style={{ padding: "15px 0", borderBottom: `1px solid ${C.ruleSoft}` }}>
              <div style={{ fontSize: 13, fontWeight: 600, overflowWrap: "anywhere" }}>{release.id} · {release.date}</div>
              <p style={{ ...body, marginTop: 4, fontSize: 12 }}>{release.label}</p>
              {release.kind === "baseline" && <p style={{ fontSize: 12, color: C.ink3, marginTop: 4 }}>Snapshot taken before this implementation. Not a reconstructed July release.</p>}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 15, marginTop: 9, fontSize: 12, color: C.accent }}>
                <a href={asset(release.downloads.estimates.csv)} download>Learning estimates CSV ↓</a>
                <a href={asset(release.downloads.estimates.json)} download>Learning estimates JSON ↓</a>
                <a href={asset(release.downloads.papers.json)} download>Study records JSON ↓</a>
                <a href={asset(release.manifest_path)} target="_blank" rel="noreferrer">Manifest, code, and other files ↗</a>
              </div>
            </div>;
          })}
        </div>

        <h2 style={h2}>Updates</h2>
        {rule}
        <p style={body}>
          The atlas is a living resource: new papers, recoded estimates, and methodology changes are
          logged here as they happen.
        </p>
        <div style={{ marginTop: 12 }}>
          {[
            [RELEASE.date, RELEASE.label],
            ["July 2026", "Initial public version with an interactive forest plot, study records, CSV export, and methodology page. No verified snapshot of that release is available here."],
          ].map(([date, text]) => (
            <div key={date} style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: 14, padding: "10px 0", borderBottom: `1px solid ${C.ruleSoft}` }}>
              <span style={{ fontFamily: F.mono, fontSize: 10.5, color: C.ink3, letterSpacing: "0.04em", paddingTop: 2 }}>{date}</span>
              <span style={{ fontSize: 13, color: C.ink2, lineHeight: 1.6, fontFamily: F.sans }}>{text}</span>
            </div>
          ))}
        </div>

        <h2 style={h2}>Contributing</h2>
        {rule}
        <p style={body}>
          If a study is missing, or a number looks wrong, email{" "}
          <a href={SUGGEST_MAILTO} style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
            learning_study@middlebury.edu
          </a>{" "}with the paper or citation. Suggestions are evaluated against the inclusion
          criteria above and nothing else.
        </p>

        <h2 style={h2}>Authorship and independence</h2>
        {rule}
        <p style={body}>
          The atlas is maintained by{" "}
          <a href="https://www.germanr.com" target="_blank" rel="noreferrer" style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
            Germán Reyes
          </a>{" "}(Middlebury College), with research assistance from Nam Nguyen and Wills Erda. One included study,{" "}
          <a href="https://germanr.com/papers/cr_ai_learning.pdf" target="_blank" rel="noreferrer" style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
            Contractor and Reyes (2026)
          </a>, is by the maintainer.
        </p>

        <h2 style={h2}>How to cite this resource</h2>
        {rule}
        <pre style={{
          fontFamily: F.mono, fontSize: 11.5, color: C.ink, lineHeight: 1.6,
          background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
          padding: "14px 18px", whiteSpace: "pre-wrap", overflow: "auto", marginTop: 16,
        }}>{BIBTEX_SITE}</pre>
      </div>
      <Footer />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Creativity section (beta)
// ────────────────────────────────────────────────────────────────────────────
function CreativityCard({ paper, idx }) {
  const [h, setH] = useState(false);
  const n = paper.n_outcomes_extracted || 0;
  return (
    <a
      href={paper.doi_or_url}
      target="_blank"
      rel="noopener noreferrer"
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{
        background: C.paperHi,
        borderLeft: `1px solid ${h ? C.ink : C.rule}`,
        borderRight: `1px solid ${h ? C.ink : C.rule}`,
        borderBottom: `1px solid ${h ? C.ink : C.rule}`,
        borderTop: `3px solid ${C.accent}`,
        borderRadius: 2,
        transition: "all 0.15s ease",
        transform: h ? "translateY(-3px)" : "none",
        boxShadow: h ? "5px 5px 0 rgba(26,23,19,0.1)" : "none",
        animation: `fadeUp 0.4s cubic-bezier(.22,1,.36,1) ${Math.min(idx * 0.025, 0.4)}s both`,
        display: "flex", flexDirection: "column",
        padding: "15px 16px 14px", minHeight: 170,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 9 }}>
        <span style={SC({ fontSize: 9, color: C.accent, fontWeight: 600 })}>{paper.design_class}</span>
        {paper.included_in_curated_subset && (
          <span style={SC({ fontSize: 8.5, color: C.ink3 })}>curated</span>
        )}
      </div>
      <div style={{
        fontFamily: F.serif, fontSize: 15.5, fontWeight: 600, lineHeight: 1.28, color: C.ink,
        display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
        marginBottom: 8,
      }}>
        {paper.title}
      </div>
      <div style={{ fontFamily: F.sans, fontSize: 11.5, color: C.ink2, marginBottom: 12 }}>
        {paper.authors_short} ({paper.year}){paper.n_total != null ? ` · ${studySample(paper)}` : ""}
      </div>
      <div style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
        <span style={SC({ fontSize: 8.5, color: C.ink3 })}>
          {n > 0 ? `${n} estimates` : paper.stub ? "stub" : "—"}
        </span>
        <span style={SC({ fontSize: 8.5, color: C.ink3 })}>{paper.outcome_focus}</span>
      </div>
    </a>
  );
}

function CreativityPage({ onSection }) {
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

  const stat = (label, value) => (
    <div key={label} style={{ padding: "16px 22px 15px", borderRight: `1px solid ${C.ruleSoft}` }}>
      <div style={{ fontFamily: F.serif, fontSize: 31, fontWeight: 650, lineHeight: 1, color: C.ink }}>{value}</div>
      <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginTop: 6 }}>{label}</div>
    </div>
  );

  return (
    <div style={{ background: C.paper, minHeight: "100vh", color: C.ink }}>
      <SiteHeader active="creativity" onSection={onSection} />
      <div className="wrap" style={{ maxWidth: 1140, margin: "0 auto", padding: "48px 28px 80px" }}>
        {/* Hero */}
        <div style={SC({ fontSize: 10.5, color: C.ink3 })}>Creativity · Section in development</div>
        <h1 style={{
          fontFamily: F.serif, fontWeight: 650, color: C.ink,
          fontSize: "clamp(30px, 4.2vw, 46px)", lineHeight: 1.08, letterSpacing: "-0.02em",
          marginTop: 16, maxWidth: 760,
        }}>
          Generative AI and creativity
        </h1>
        <p style={{ fontFamily: F.sans, fontSize: 15.5, lineHeight: 1.62, color: C.ink2, maxWidth: 640, marginTop: 18 }}>
          A growing body of experiments asks whether AI lifts individual creativity, whether it narrows
          the diversity of what we collectively produce, and whether the homogenization persists after
          the tool is taken away. This section catalogs that literature; effect-size extraction and the
          forest plot are in progress.
        </p>

        {/* Stats band */}
        <div className="stats-band" style={{
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
          border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi,
          margin: "32px 0 36px", overflow: "hidden",
        }}>
          {stat("Papers", visiblePapers.length)}
          {stat("RCT / Hybrid", visiblePapers.filter(p => p.design_class === "RCT" || p.design_class === "Hybrid").length)}
          {stat("Effect-size estimates", nEstimates)}
          {stat("Papers with estimates", nPapersWithEstimates)}
        </div>

        {/* Curated toggle */}
        <div style={{
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
          padding: "12px 0", borderTop: `1px solid ${C.rule}`, borderBottom: `1px solid ${C.rule}`,
          marginBottom: 36,
        }}>
          <div style={SC({ fontSize: 9.5, color: C.ink3 })}>Inclusion</div>
          <Chip label={`All papers (${papers.length})`} active={!curatedOnly} onClick={() => setCuratedOnly(false)} />
          <Chip label={`RCT · n ≥ 50 (${nCurated})`} active={curatedOnly} onClick={() => setCuratedOnly(true)} />
          <span style={{ fontFamily: F.sans, fontSize: 11.5, color: C.ink3, flex: 1, minWidth: 200 }}>
            Same criteria as the learning section: randomized design with AI as treatment, ≥ 50 participants.
          </span>
        </div>

        {/* Themes */}
        {theme_order.map(theme => {
          const list = byTheme.get(theme) || [];
          if (!list.length) return null;
          return (
            <div key={theme} style={{ marginBottom: 40 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 14 }}>
                <h3 style={{ fontFamily: F.serif, fontSize: 19, fontWeight: 650, color: C.ink }}>{theme}</h3>
                <span style={{ fontFamily: F.mono, fontSize: 11, color: C.ink3 }}>{list.length}</span>
                <span style={{ flex: 1, height: 1, background: C.rule }} />
              </div>
              <div className="grid-cards" style={{
                display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(235px, 1fr))", gap: 14,
              }}>
                {list.map((p, idx) => (
                  <CreativityCard key={p.paper_key} paper={p} idx={idx} />
                ))}
              </div>
            </div>
          );
        })}

        {/* What's coming */}
        <div style={{
          marginTop: 52, border: `1px solid ${C.rule}`, borderRadius: 2,
          background: C.paperHi, padding: "22px 26px",
        }}>
          <div style={{ ...SC({ fontSize: 9.5, color: C.accent }), marginBottom: 12 }}>What's coming</div>
          {[
            `Done: effect-size extraction from ${nPapersWithEstimates} papers (${nEstimates} outcomes total — Cohen's d, raw means, cosine similarities, Likert-rating betas)`,
            "Forest plot of individual-creativity effects (Cohen's d only — comparable across papers)",
            "Companion forest plot of homogenization effects (mixed metric units; needs harmonization)",
            "Filter by outcome type (individual creativity / homogenization / diversity / idea quantity)",
            "Re-extraction of the 2 remaining stubs (Hintze, Liu-Wang-Yang) once PDFs are available",
          ].map((t, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "10px 1fr", gap: 14, padding: "8px 0" }}>
              <span style={{ color: C.accent, fontFamily: F.mono, fontSize: 13 }}>—</span>
              <p style={{ fontFamily: F.sans, fontSize: 13.5, lineHeight: 1.6, color: C.ink2, margin: 0 }}>{t}</p>
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 13, color: C.ink2, fontFamily: F.sans }}>
            Have a paper to add?{" "}
            <a href="mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20creativity%20paper%20suggestion"
              style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>Email it in.</a>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// CSV download helper
// ────────────────────────────────────────────────────────────────────────────
function downloadCSV(estimates, papers, { full = false, viewUrl = "", selection = {} } = {}) {
  const csv = buildEstimatesCSV(estimates, papers, {
    releaseId: RELEASE.id, releaseDate: RELEASE.date, metadata: EVIDENCE_METADATA,
    viewUrl: full ? "" : viewUrl,
    selection: full ? { scope: "full", dataset: "learning" } : { ...selection, scope: "filtered", dataset: "learning" },
  });
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ai-skill-atlas-estimates-${full ? "full" : "filtered"}-${RELEASE.id}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ────────────────────────────────────────────────────────────────────────────
// Main app
// ────────────────────────────────────────────────────────────────────────────
// Error boundary: a runtime failure should show a message, not a blank page.
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#FFFFFF", fontFamily: "Georgia, serif", color: "#1B1A18", padding: 24 }}>
          <div style={{ maxWidth: 480, textAlign: "center" }}>
            <div style={{ fontSize: 22, fontWeight: 650, marginBottom: 10 }}>Something went wrong.</div>
            <div style={{ fontSize: 14, lineHeight: 1.6, color: "#5B5751", marginBottom: 18 }}>
              The atlas hit an unexpected error while rendering. Reloading usually fixes it; if it persists, please email learning_study@middlebury.edu.
            </div>
            <button onClick={() => window.location.reload()} style={{ font: "inherit", fontSize: 13, padding: "8px 18px", cursor: "pointer", background: "#1B1A18", color: "#FFFFFF", border: "none", borderRadius: 2 }}>
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function AppInner() {
  const [initialView] = useState(parseCurrentView);
  const [section, setSection] = useState(initialView.state.section);
  const [selectedPaper, setSelectedPaper] = useState(() => PAPERS_RAW.find(p => p.paper_key === initialView.state.paperKey) || null);
  const [search, setSearch] = useState(initialView.state.search);
  const [designMode, setDesignMode] = useState(initialView.state.designMode);
  const [sampleMode, setSampleMode] = useState(initialView.state.sampleMode);
  const [activeDomains, setActiveDomains] = useState(() => new Set(initialView.state.activeDomains));
  const [activePopulations, setActivePopulations] = useState(() => new Set(initialView.state.activePopulations));
  const [comparisonType, setComparisonType] = useState(initialView.state.comparisonType);
  const [outcomeMode, setOutcomeMode] = useState(initialView.state.outcomeMode);
  const [timingMode, setTimingMode] = useState(initialView.state.timingMode);
  const [sortBy, setSortBy] = useState(initialView.state.sortBy);
  const [view, setView] = useState(initialView.state.view);
  const [plotSort, setPlotSort] = useState(initialView.state.plotSort);
  const [invalidParams, setInvalidParams] = useState(initialView.invalidParams);
  const [shareStatus, setShareStatus] = useState("");
  const [manualLink, setManualLink] = useState("");
  const viewState = useMemo(() => ({
    section, paperKey: selectedPaper?.paper_key || null, search, designMode, sampleMode,
    activeDomains, activePopulations, comparisonType, outcomeMode, timingMode, sortBy, view, plotSort,
  }), [section, selectedPaper, search, designMode, sampleMode, activeDomains, activePopulations, comparisonType, outcomeMode, timingMode, sortBy, view, plotSort]);

  // Replacing the current browse entry avoids one Back step per keystroke.
  // A study opens a separate history entry containing the same selection.
  useEffect(() => {
    const next = serializeViewState(viewState, window.location.href, VIEW_OPTIONS);
    if (next !== window.location.pathname + window.location.search + window.location.hash) {
      window.history.replaceState(window.history.state, "", next);
    }
    setShareStatus("");
    setManualLink("");
  }, [viewState]);

  // Inject global CSS once
  useEffect(() => {
    const styleEl = document.createElement("style");
    styleEl.innerHTML = GCSS;
    document.head.appendChild(styleEl);
    return () => { document.head.removeChild(styleEl); };
  }, []);

  // Browser Back and Forward restore the complete selection, not only a paper.
  useEffect(() => {
    const onPop = () => {
      const { state, invalidParams: invalid } = parseCurrentView();
      setSelectedPaper(PAPERS_RAW.find(p => p.paper_key === state.paperKey) || null);
      setSection(state.section);
      setSearch(state.search);
      setDesignMode(state.designMode);
      setSampleMode(state.sampleMode);
      setActiveDomains(new Set(state.activeDomains));
      setActivePopulations(new Set(state.activePopulations));
      setComparisonType(state.comparisonType);
      setOutcomeMode(state.outcomeMode);
      setTimingMode(state.timingMode);
      setSortBy(state.sortBy);
      setView(state.view);
      setPlotSort(state.plotSort);
      setInvalidParams(invalid);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // Scroll to #evidence / #studies anchors: the browser's native anchor pass
  // runs before React renders the sections, so handle it after mount.
  useEffect(() => {
    const scrollToHash = () => {
      if (lastFocusRef.current) return;
      const id = window.location.hash.slice(1);
      if (!id) return;
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: "smooth" });
    };
    const t = setTimeout(scrollToHash, 80);
    window.addEventListener("hashchange", scrollToHash);
    return () => { clearTimeout(t); window.removeEventListener("hashchange", scrollToHash); };
  }, []);

  const lastFocusRef = useRef(null);
  useEffect(() => {
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => { window.history.scrollRestoration = previous; };
  }, []);

  useEffect(() => {
    if (selectedPaper || !lastFocusRef.current) return;
    // Wait until history traversal finishes. Native fragment processing can
    // otherwise move focus back to the page after React restores the row.
    const timer = setTimeout(() => {
      const { attribute, value, left, top } = lastFocusRef.current;
      document.querySelector(`[${attribute}="${CSS.escape(value)}"]`)?.focus({ preventScroll: true });
      window.scrollTo({ left, top, behavior: "instant" });
      lastFocusRef.current = null;
    }, 0);
    return () => clearTimeout(timer);
  }, [selectedPaper]);

  const openPaper = (p) => {
    const source = document.activeElement?.closest("[data-estimate-id], [data-paper-key]");
    const attribute = source?.hasAttribute("data-estimate-id") ? "data-estimate-id" : "data-paper-key";
    lastFocusRef.current = {
      attribute, value: source?.getAttribute(attribute) || p.paper_key,
      left: window.scrollX, top: window.scrollY,
    };
    setSelectedPaper(p);
    // Preserve the browse fragment so Back does not trigger a second anchor
    // navigation that would override the restored focus and scroll position.
    window.history.pushState({ inApp: true }, "", serializeViewState({ ...viewState, paperKey: p.paper_key }, window.location.href, VIEW_OPTIONS));
  };
  const closePaper = () => {
    // If this record was opened in-app, closing = going back, so the Back
    // button afterwards does not reopen it. Deep links get a clean replace.
    if (selectedPaper && window.history.state?.inApp) {
      window.history.back();
    } else {
      setSelectedPaper(null);
      window.history.replaceState({}, "", serializeViewState({ ...viewState, paperKey: null }, window.location.href, VIEW_OPTIONS));
    }
  };
  const goSection = (s) => {
    setSection(s);
    setSelectedPaper(null);
    window.history.pushState({}, "", serializeViewState({ ...viewState, section: s, paperKey: null }, window.location.href, VIEW_OPTIONS));
  };

  const currentViewURL = () => {
    const url = new URL(serializeViewState({ ...viewState, paperKey: null }, window.location.href, VIEW_OPTIONS), window.location.origin);
    url.hash = "evidence";
    return url.href;
  };
  const copyViewLink = async () => {
    const url = currentViewURL();
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(url);
      setManualLink("");
      setShareStatus("View link copied. It opens this selection using the current data.");
    } catch {
      setManualLink(url);
      setShareStatus("Clipboard unavailable. Select and copy the view link below.");
    }
  };

  const papers = PAPERS_RAW;
  const estimates = ESTIMATES_RAW;

  // Papers in the current sample scope (Students by default)
  const sampledPapers = useMemo(() => papers.filter(p =>
    sampleMode === "all" ? true :
    sampleMode === "students" ? isStudentPaper(p) : !isStudentPaper(p)
  ), [papers, sampleMode]);

  // Default-view estimates (hero strip + pooled headline): student samples,
  // full-sample, no-AI outcomes, vs. BAU.
  const defaultEstimates = useMemo(() => {
    const studentKeys = new Set(papers.filter(isStudentPaper).map(p => p.paper_key));
    return filterEstimates(estimates, { paperKeys: studentKeys });
  }, [papers, estimates]);
  const pooledDefault = useMemo(() => randomEffectsMean(defaultEstimates), [defaultEstimates]);

  const allDomains = useMemo(() => {
    const s = new Set();
    estimates.forEach(e => e.learning_domain && s.add(e.learning_domain));
    return DOMAIN_ORDER.filter(d => s.has(d));
  }, [estimates]);

  const allPopulations = useMemo(() => {
    const s = new Set();
    sampledPapers.forEach(p => p.population_category && s.add(p.population_category));
    return POPULATION_ORDER.filter(x => s.has(x)).concat(
      Array.from(s).filter(x => !POPULATION_ORDER.includes(x))
    );
  }, [sampledPapers]);


  const filteredPapers = useMemo(() => {
    return sampledPapers.filter(p => {
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        if (!(p.title?.toLowerCase().includes(q) ||
              p.authors_full?.toLowerCase().includes(q) ||
              p.authors_short?.toLowerCase().includes(q) ||
              p.country?.toLowerCase().includes(q) ||
              p.summary?.toLowerCase().includes(q))) return false;
      }
      if (activePopulations.size > 0 && !activePopulations.has(p.population_category)) return false;
      return true;
    });
  }, [sampledPapers, search, activePopulations]);

  const filteredEstimates = useMemo(() => {
    const paperKeys = new Set(filteredPapers.map(p => p.paper_key));
    return filterEstimates(estimates, { paperKeys, designMode, comparisonType, outcomeMode, activeDomains, timingMode });
  }, [filteredPapers, estimates, designMode, comparisonType, outcomeMode, activeDomains, timingMode]);

  const papersWithEstimates = useMemo(() => {
    const keysInView = new Set(filteredEstimates.map(e => e.paper_key));
    return filteredPapers.filter(p => keysInView.has(p.paper_key));
  }, [filteredPapers, filteredEstimates]);

  // Per-paper average effect over the estimates in the CURRENT view, so
  // cards and Effect sorting match what the plot shows (not the all-outcome
  // static average).
  const viewStats = useMemo(() => {
    const acc = new Map();
    filteredEstimates.forEach(e => {
      const s = acc.get(e.paper_key) || { sum: 0, n: 0, domains: new Set() };
      if (e.learning_domain) s.domains.add(e.learning_domain);
      if (e.effect_size_sd != null) { s.sum += e.effect_size_sd; s.n += 1; }
      acc.set(e.paper_key, s);
    });
    const out = {};
    acc.forEach((s, k) => { out[k] = { mean: s.n ? s.sum / s.n : null, n: s.n, domains: DOMAIN_ORDER.filter(d => s.domains.has(d)) }; });
    return out;
  }, [filteredEstimates]);

  const sortedPapers = useMemo(() => {
    const arr = [...papersWithEstimates];
    arr.sort((a, b) => {
      if (sortBy === "effect") return (viewStats[b.paper_key]?.mean ?? -999) - (viewStats[a.paper_key]?.mean ?? -999);
      if (sortBy === "year") return (b.year || 0) - (a.year || 0);
      return a.authors_short?.localeCompare(b.authors_short);
    });
    return arr;
  }, [papersWithEstimates, sortBy, viewStats]);

  const toggleSet = (set, val, setter) => {
    const next = new Set(set);
    if (next.has(val)) next.delete(val); else next.add(val);
    setter(next);
  };

  const setSample = (mode) => {
    setSampleMode(mode);
    // population chips depend on the sample scope; clear to avoid impossible combos
    setActivePopulations(new Set());
  };

  const nActiveFilters = activeDomains.size + activePopulations.size + (search.trim() ? 1 : 0)
    + (designMode !== "rct" ? 1 : 0) + (sampleMode !== "students" ? 1 : 0)
    + (comparisonType !== "ai_vs_bau" ? 1 : 0) + (outcomeMode !== "without_ai" ? 1 : 0) + (timingMode !== "all" ? 1 : 0);
  const resetFilters = () => {
    setDesignMode("rct");
    setSampleMode("students");
    setActiveDomains(new Set());
    setActivePopulations(new Set());
    setComparisonType("ai_vs_bau");
    setOutcomeMode("without_ai");
    setTimingMode("all");
    setSearch("");
    setInvalidParams([]);
  };

  if (section === "creativity") {
    return <CreativityPage onSection={goSection} />;
  }

  if (selectedPaper) {
    return (
      <div style={{ background: C.paper, minHeight: "100vh" }}>
        <SiteHeader active="learning" onSection={goSection} onHome={closePaper} />
        <ReportCard paper={selectedPaper} estimates={estimates} onBack={closePaper} />
        <Footer />
      </div>
    );
  }

  const fePlot = randomEffectsMean(filteredEstimates);
  const plottedEstimates = filteredEstimates.filter(isPlottableEstimate);
  const plottedStudyCount = new Set(plottedEstimates.map(e => e.paper_key)).size;
  const pooledStudyCount = new Set(filteredEstimates.filter(isPoolableEstimate).map(e => e.paper_key)).size;
  const omittedPlotCount = filteredEstimates.length - plottedEstimates.length;
  const selection = {
    designMode, sampleMode, activeDomains: [...activeDomains], activePopulations: [...activePopulations],
    comparisonType, outcomeMode, timingMode, search, view, plotSort, sortBy,
  };
  const scopeDescription = [
    { rct: "All randomized experiments", lab: "Lab experiments", field: "Field experiments", online: "Online experiments", obs: "Observational studies" }[designMode],
    { students: "student samples", nonstudents: "non-student samples", all: "all samples" }[sampleMode],
    activeDomains.size ? [...activeDomains].join(" / ") : "all learning domains",
    activePopulations.size ? [...activePopulations].join(" / ") : null,
    { ai_vs_bau: "AI vs business-as-usual", ai_vs_active: "AI vs active control", ai_design: "off-the-shelf vs scaffolded AI" }[comparisonType],
    outcomeMode === "without_ai" ? "assessed without AI" : "including AI-assisted assessments",
    { all: "all timings", immediate: "immediate outcomes", delayed: "delayed outcomes" }[timingMode],
    search.trim() ? `search: “${search.trim()}”` : null,
  ].filter(Boolean).join(" · ");

  // ── Browse view ───────────────────────────────────────────────────────────
  return (
    <div style={{ background: C.paper, minHeight: "100vh", color: C.ink }}>
      <SiteHeader active="learning" onSection={goSection} onHome={closePaper} />

      <main className="wrap" style={{ maxWidth: 1140, margin: "0 auto", padding: "0 28px" }}>
        <Hero papers={papers} estimates={estimates} defaultEstimates={defaultEstimates} pooled={pooledDefault} />

        {/* ── Section 01 · The evidence ── */}
        <section id="evidence" style={{ marginTop: 64 }}>
          <SectionHead
            index="01"
            title="The evidence"
            sub="Available standardized effects with uncertainty intervals. Markers are sized by precision (inverse variance); the blue band is the random-effects pooled estimate. Hover for details; click any row to open the study."
          />

          {invalidParams.length > 0 && (
            <p role="status" style={{ fontSize: 13, color: C.neg, lineHeight: 1.6, marginBottom: 14 }}>
              Link options reset: {invalidParams.join(", ")}. Unrecognized choices use their defaults or were removed. Check the selection below.
            </p>
          )}
          {/* Filters */}
          <div style={{
            border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi,
            padding: "4px 20px", marginBottom: 18,
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 0 8px", borderBottom: `1px solid ${C.ruleSoft}`,
            }}>
              <span style={SC({ fontSize: 10, color: C.ink })}>Filter the evidence</span>
              {nActiveFilters > 0 && (
                <button onClick={resetFilters} style={{
                  ...SC({ fontSize: 9.5, color: C.neg }),
                  background: "none", border: "none", cursor: "pointer", textDecoration: "underline",
                }}>Reset all ({nActiveFilters})</button>
              )}
            </div>
            <FilterRow
              label="Design"
              options={[
                { value: "rct",    label: "RCTs (all experiments)" },
                { value: "lab",    label: "Lab experiments" },
                { value: "field",  label: "Field experiments" },
                { value: "online", label: "Online experiments" },
                { value: "obs",    label: "Observational data" },
              ]}
              active={new Set([designMode])}
              onToggle={(v) => setDesignMode(v)}
              isRadio
            />
            <FilterRow
              label="Sample"
              options={[
                { value: "students",    label: "Students" },
                { value: "nonstudents", label: "Non-students" },
                { value: "all",         label: "All samples" },
              ]}
              active={new Set([sampleMode])}
              onToggle={(v) => setSample(v)}
              isRadio
            />
            <FilterRow
              label="Domain"
              options={[{ value: "__all", label: "All" }, ...allDomains]}
              active={activeDomains.size === 0 ? new Set(["__all"]) : activeDomains}
              onToggle={(v) => v === "__all" ? setActiveDomains(new Set()) : toggleSet(activeDomains, v, setActiveDomains)}
              colorMap={Object.fromEntries(Object.entries(DOMAIN).map(([k, v]) => [k, v.color]))}
            />
            <FilterRow
              label="Population"
              options={[{ value: "__all", label: "All" }, ...allPopulations]}
              active={activePopulations.size === 0 ? new Set(["__all"]) : activePopulations}
              onToggle={(v) => v === "__all" ? setActivePopulations(new Set()) : toggleSet(activePopulations, v, setActivePopulations)}
            />
            <FilterRow
              label="Comparison"
              options={[
                { value: "ai_vs_bau",    label: "AI vs business-as-usual" },
                { value: "ai_vs_active", label: "AI vs active control" },
                { value: "ai_design",    label: "Off-the-shelf vs scaffolded AI" },
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
            <FilterRow
              label="Timing"
              options={[
                { value: "all", label: "All timings" },
                { value: "immediate", label: "Immediate" },
                { value: "delayed", label: "Delayed" },
              ]}
              active={new Set([timingMode])}
              onToggle={setTimingMode}
              isRadio
              last
            />
          </div>

          <p data-testid="view-scope" style={{ fontSize: 12, lineHeight: 1.65, color: C.ink2, marginBottom: 9 }}>
            <strong>Current view:</strong> {scopeDescription}.
          </p>
          <p style={{ fontSize: 11.5, lineHeight: 1.6, color: C.ink3, marginBottom: 15 }}>
            Timing follows each paper's coding, not a common follow-up interval. Immediate and delayed views can contain different studies, so their difference does not measure learning decay.
          </p>

          {/* Toolbar */}
          <div className="toolbar" style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 12, gap: 12, flexWrap: "wrap",
          }}>
            <div style={{ display: "flex", gap: 0, border: `1px solid ${C.ink}`, borderRadius: 2, overflow: "hidden" }}>
              {[{ key: "chart", label: "Chart" }, { key: "table", label: "Table" }].map(opt => (
                <button
                  key={opt.key}
                  onClick={() => setView(opt.key)}
                  aria-pressed={view === opt.key}
                  style={{
                    padding: "7px 18px", fontSize: 10.5, fontFamily: F.mono,
                    letterSpacing: "0.1em", textTransform: "uppercase",
                    background: view === opt.key ? C.ink : "transparent",
                    color: view === opt.key ? C.paper : C.ink,
                    border: "none", cursor: "pointer", fontWeight: view === opt.key ? 600 : 400,
                    transition: "all 0.13s",
                  }}>{opt.label}</button>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              {view === "chart" && (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={SC({ fontSize: 9, color: C.ink3 })}>Sort</span>
                  {[["effect", "Effect"], ["precision", "Precision"], ["year", "Year"]].map(([key, label]) => (
                    <button key={key} onClick={() => setPlotSort(key)} aria-pressed={plotSort === key} style={{
                      background: "none", border: "none", cursor: "pointer", padding: "3px 0",
                      fontFamily: F.mono, fontSize: 10.5, letterSpacing: "0.06em", textTransform: "uppercase",
                      color: plotSort === key ? C.ink : C.ink3,
                      fontWeight: plotSort === key ? 600 : 400,
                      borderBottom: plotSort === key ? `2px solid ${C.ink}` : "2px solid transparent",
                    }}>{label}</button>
                  ))}
                </div>
              )}
              <span style={SC({ fontSize: 9.5, color: C.ink3 })} aria-live="polite">
                {view === "chart"
                  ? `${plottedEstimates.length} plotted estimates · ${plottedStudyCount} ${plottedStudyCount === 1 ? "study" : "studies"}`
                  : `${filteredEstimates.length} records · ${papersWithEstimates.length} ${papersWithEstimates.length === 1 ? "study" : "studies"}`}
              </span>
              <GhostBtn small onClick={copyViewLink}>Copy view link</GhostBtn>
              <GhostBtn small onClick={() => downloadCSV(filteredEstimates, papers, { viewUrl: currentViewURL(), selection })}>↓ CSV (filtered)</GhostBtn>
              <GhostBtn small onClick={() => downloadCSV(estimates, papers, { full: true })}>↓ CSV (full dataset)</GhostBtn>
            </div>
          </div>

          <div style={{ marginBottom: 15, fontSize: 11.5, color: C.ink3, lineHeight: 1.6 }}>
            Shared links use the current data, not a frozen result. <a href={`${import.meta.env.BASE_URL}about/#data-releases`} style={{ color: C.accent, textDecoration: "underline" }}>Archived releases</a> preserve the data and calculation code.
            <p role="status">{shareStatus}</p>
            {manualLink && <input aria-label="View link" value={manualLink} readOnly onFocus={event => event.target.select()} style={{ display: "block", width: "100%", marginTop: 7, padding: 9, fontFamily: F.mono, fontSize: 11, border: `1px solid ${C.rule}` }} />}
          </div>

          {view === "chart" ? (
            <>
              {omittedPlotCount > 0 && (
                <p style={{ fontFamily: F.sans, fontSize: 12, color: C.ink2, lineHeight: 1.6, marginBottom: 10 }}>
                  {filteredEstimates.length} matching records from {papersWithEstimates.length} {papersWithEstimates.length === 1 ? "study" : "studies"}.
                  {" "}{omittedPlotCount} {omittedPlotCount === 1 ? "record lacks" : "records lack"} a standardized effect or uncertainty interval and {omittedPlotCount === 1 ? "is" : "are"} available in Table and CSV.
                </p>
              )}
              <ForestPlot estimates={filteredEstimates} papers={papers} onSelectPaper={openPaper} width={1084} sortMode={plotSort} />
              <p style={{ fontFamily: F.sans, fontSize: 11.5, color: C.ink3, lineHeight: 1.6, marginTop: 10, fontStyle: "italic" }}>
                {fePlot
                  ? `Random-effects mean: ${fmtSD(fePlot.mean)} SD (95% CI ${fmtCI(fePlot.lo, fePlot.hi)}), using ${fePlot.k} estimates from ${pooledStudyCount} ${pooledStudyCount === 1 ? "study" : "studies"} (DerSimonian–Laird, τ̂² = ${fePlot.tau2.toFixed(3)}).`
                  : "No pooled estimate: the matching records lack a standardized effect with a positive standard error."}
                {" "}Horizontal lines are 95% confidence intervals. Arrows mark intervals or effects beyond ±1 SD; numeric values retain the full estimate.
                Estimates reporting a CI but no SE are drawn at a fixed size and excluded from pooling.
                Positive values favor the AI condition.
              </p>
            </>
          ) : (
            <>
              <p style={{ fontSize: 11.5, color: C.ink3, marginBottom: 8 }}>On narrow screens, scroll the table horizontally to see the sample, outcome, and timing columns.</p>
              <EstimatesTable estimates={filteredEstimates} papers={papers} onSelectPaper={openPaper} />
            </>
          )}
        </section>

        {/* ── Section 02 · The studies ── */}
        <section id="studies" style={{ marginTop: 72 }}>
          <SectionHead
            index="02"
            title="The studies"
            sub="Each card is one experiment, with its average effect across primary estimates in the current comparison. Open a card for the full study record: design, incentives, every estimate, and the PDF."
            right={(
              <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
                <input
                  type="text"
                  placeholder="Search title, author, country…"
                  aria-label="Search studies by title, author, or country"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    background: C.paperHi, border: `1px solid ${C.rule}`,
                    padding: "7px 12px", fontSize: 12, borderRadius: 2,
                    width: 230, fontFamily: F.sans, color: C.ink, outline: "none",
                  }}
                  onFocus={(e) => e.currentTarget.style.borderColor = C.ink}
                  onBlur={(e) => e.currentTarget.style.borderColor = C.rule}
                />
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={SC({ fontSize: 9, color: C.ink3 })}>Sort</span>
                  {[["effect", "Effect"], ["year", "Year"], ["author", "Author"]].map(([key, label]) => (
                    <button key={key} onClick={() => setSortBy(key)} aria-pressed={sortBy === key} style={{
                      background: "none", border: "none", cursor: "pointer", padding: "3px 0",
                      fontFamily: F.mono, fontSize: 10.5, letterSpacing: "0.06em", textTransform: "uppercase",
                      color: sortBy === key ? C.ink : C.ink3,
                      fontWeight: sortBy === key ? 600 : 400,
                      borderBottom: sortBy === key ? `2px solid ${C.ink}` : "2px solid transparent",
                    }}>{label}</button>
                  ))}
                </div>
              </div>
            )}
          />

          {sortedPapers.length === 0 ? (
            <div style={{
              padding: "64px 20px", textAlign: "center", color: C.ink2, fontFamily: F.sans, fontSize: 14,
              background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
            }}>
              No studies match the current filters. Try clearing some filters.
            </div>
          ) : (
            <div className="grid-cards" style={{
              display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 14,
            }}>
              {sortedPapers.map((p, idx) => (
                <StudyCard key={p.paper_key} paper={p} onClick={openPaper} idx={idx}
                  viewEffect={viewStats[p.paper_key] ? viewStats[p.paper_key].mean : null}
                  viewDomains={viewStats[p.paper_key]?.domains} />
              ))}
            </div>
          )}

          <NotesBand />
        </section>
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  );
}
