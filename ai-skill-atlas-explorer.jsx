import React, { useState, useEffect, useMemo, useRef } from "react";
import PAPERS_RAW from "./src/papers.json";
import ESTIMATES_RAW from "./src/estimates.json";
import CREATIVITY_DATA from "./src/creativity_papers.json";

// ─── Formatters ───
const fmt = (n) => (n == null ? "—" : n.toLocaleString());
const fmtSD = (n) => (n == null ? "—" : (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(2));
const fmtSE = (n) => (n == null ? "—" : n.toFixed(3));
const fmtCI = (lo, hi) => (lo == null || hi == null ? "—" : `[${fmtSD(lo)}, ${fmtSD(hi)}]`);

// ─── Design tokens — "evidence journal": white, ink, hairline rules ───
const C = {
  paper: "#FFFFFF",        // page background
  paperHi: "#FFFFFF",      // raised surface (cards, plot)
  paperDeep: "#F5F4F1",    // recessed surface (hovers, table headers)
  ink: "#1B1A18",          // primary text
  ink2: "#5B5751",         // secondary text
  ink3: "#9B968E",         // tertiary text
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
  "Coding":            { color: "#B36412", symbol: "square"   },
  "Writing":           { color: "#1F5A2F", symbol: "triangle" },
  "Language":          { color: "#24509E", symbol: "cross"    },
  "Science":           { color: "#50555E", symbol: "diamond"  },
  "General knowledge": { color: "#3D3A35", symbol: "diamond"  },
  "Mixed":             { color: "#8E8678", symbol: "circle"   },
};
const DOMAIN_ORDER = ["Math", "Coding", "Writing", "Language", "Science", "General knowledge", "Mixed"];

const POPULATION_ORDER = [
  "Elementary", "Middle school", "High school",
  "Undergraduate", "Graduate", "Adults general", "Professional",
];

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

export const GCSS = `@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..800;1,6..72,400..800&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
* { box-sizing: border-box; margin: 0; }
html { scroll-behavior: smooth; }
body { background: ${C.paper}; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; font-family: ${F.sans}; color: ${C.ink}; }
::selection { background: ${C.ink}; color: ${C.paper}; }
a { color: inherit; text-decoration: none; }
button { font: inherit; }
:focus-visible { outline: 2px solid ${C.accent}; outline-offset: 2px; }
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
`;

// ────────────────────────────────────────────────────────────────────────────
// DerSimonian–Laird random-effects meta-analysis
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

  return { mean: grandMean, se: grandSE, lo: grandMean - 1.96 * grandSE, hi: grandMean + 1.96 * grandSE, k, tau2, Q };
}

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
  const nParticipants = papers.reduce((s, p) => s + (p.n_total || 0), 0);

  const stat = (label, value) => (
    <div key={label} style={{ padding: "16px 22px 15px", borderRight: `1px solid ${C.ruleSoft}` }}>
      <div style={{ fontFamily: F.serif, fontSize: 31, fontWeight: 650, lineHeight: 1, color: C.ink, letterSpacing: "-0.01em" }}>{value}</div>
      <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginTop: 6 }}>{label}</div>
    </div>
  );

  return (
    <section style={{ paddingTop: 52, paddingBottom: 8 }}>
      <div style={{ animation: "fadeUp 0.5s cubic-bezier(.22,1,.36,1) both" }}>
        <div style={SC({ fontSize: 10.5, color: C.ink3 })}>
          Updated June 2026
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
            Experimental evidence on AI and human learning
          </h1>
          <p style={{
            fontFamily: F.sans, fontSize: 16, lineHeight: 1.62, color: C.ink2,
            maxWidth: 560, marginTop: 22,
            animation: "fadeUp 0.55s cubic-bezier(.22,1,.36,1) 0.12s both",
          }}>
            A meta-analysis of randomized experiments on how generative AI affects learning.
            Effect sizes are standardized in standard-deviation units so studies can be
            compared; every estimate links to its source study, and the full dataset is
            downloadable.
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
                Random-effects pooled estimate across {pooled.k} primary estimates:
                AI vs. business-as-usual, learning measured without AI in hand.
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
          <span style={SC({ fontSize: 9.5, color: C.ink3 })}>Each dot is one estimate · effect on learning, in standard deviations</span>
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
        {stat("Randomized studies", fmt(papers.length))}
        {stat("Effect sizes", fmt(estimates.length))}
        {stat("Participants", fmt(nParticipants))}
        {stat("Countries", fmt(nCountries))}
      </div>
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
    <div style={{
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
        {!isRadio && active.size > 0 && (
          <button
            onClick={() => options.forEach(o => active.has(typeof o === "string" ? o : o.value) && onToggle(typeof o === "string" ? o : o.value))}
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
function ForestPlot({ estimates, papers, onSelectPaper, width = 1084, sortMode = "effect" }) {
  const [hovered, setHovered] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const plotable = estimates
    .filter(e => e.effect_size_sd != null && e.se != null && e.se > 0)
    .map(e => ({
      ...e,
      ci_lo: e.ci_lower != null ? e.ci_lower : e.effect_size_sd - 1.96 * e.se,
      ci_hi: e.ci_upper != null ? e.ci_upper : e.effect_size_sd + 1.96 * e.se,
    }));

  const yearOf = (e) => (papers.find(p => p.paper_key === e.paper_key)?.year) || 0;
  const sorted = [...plotable].sort((a, b) => {
    if (sortMode === "precision") return a.se - b.se;
    if (sortMode === "year") return yearOf(b) - yearOf(a) || b.effect_size_sd - a.effect_size_sd;
    return b.effect_size_sd - a.effect_size_sd;
  });

  const re = randomEffectsMean(plotable);

  // Precision-weighted marker sizes
  const sqrtW = plotable.map(e => Math.sqrt(1 / (e.se ** 2)));
  const wLo = Math.min(...sqrtW), wHi = Math.max(...sqrtW);
  const sizeOf = (e) => {
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
  const yScale = (i) => padTop + (i + 0.5) * rowH;
  const xTicks = [-1.0, -0.5, 0, 0.5, 1.0];
  const axisTop = padTop + plotH + pooledH;

  if (plotable.length === 0) {
    return (
      <div style={{
        padding: "64px 20px", textAlign: "center", color: C.ink2, fontFamily: F.sans, fontSize: 14,
        background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2,
      }}>
        No estimates match the current filters.
      </div>
    );
  }

  return (
    <div style={{ position: "relative", background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
      <div className="plot-scroll">
        <div style={{ position: "relative", width, margin: "0 auto" }}>
          <svg width={width} height={totalH} style={{ display: "block" }}>

            {/* Zebra striping across the full row (label, plot, value) */}
            {sorted.map((_e, i) => i % 2 === 1 && (
              <rect key={`zebra-${i}`} x={0} y={padTop + i * rowH} width={width} height={rowH} fill="#F7F6F3" />
            ))}

            {/* Pooled-estimate band across study rows */}
            {re && (
              <rect
                x={xScale(re.lo)} y={padTop}
                width={Math.max(0, xScale(re.hi) - xScale(re.lo))} height={plotH}
                fill={C.accent} opacity={0.07}
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
              <line x1={xScale(re.mean)} y1={padTop} x2={xScale(re.mean)} y2={axisTop} stroke={C.accent} strokeWidth={1} opacity={0.5} />
            )}

            {/* Rows */}
            {sorted.map((e, i) => {
              const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
              const cx = xScale(Math.max(xMin, Math.min(xMax, e.effect_size_sd)));
              const cy = yScale(i);
              const loClamped = e.ci_lo < xMin, hiClamped = e.ci_hi > xMax;
              const ciLoX = xScale(Math.max(xMin, e.ci_lo));
              const ciHiX = xScale(Math.min(xMax, e.ci_hi));
              const isHl = hovered === e.estimate_id;
              let label = e.study_label || e.paper_key;
              if (label.length > 42) label = label.slice(0, 40) + "…";

              return (
                <g key={e.estimate_id}
                  onMouseEnter={() => { setHovered(e.estimate_id); setTooltipPos({ x: cx, y: cy }); }}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => { const p = papers.find(p => p.paper_key === e.paper_key); if (p) onSelectPaper(p); }}
                  style={{ cursor: "pointer" }}
                >
                  <rect x={0} y={cy - rowH / 2} width={width} height={rowH} fill={isHl ? "#EDEBE6" : "transparent"} />
                  <text x={labelW - 6} y={cy + 3.5} fontSize={11} fontFamily={F.sans} fill={isHl ? C.ink : C.ink2} fontWeight={isHl ? 600 : 400} textAnchor="end">
                    {label}
                  </text>
                  {/* CI */}
                  <line x1={ciLoX} y1={cy} x2={ciHiX} y2={cy} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />
                  {!loClamped && <line x1={ciLoX} y1={cy - 3.5} x2={ciLoX} y2={cy + 3.5} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />}
                  {!hiClamped && <line x1={ciHiX} y1={cy - 3.5} x2={ciHiX} y2={cy + 3.5} stroke={dom.color} strokeWidth={1.4} opacity={0.55} />}
                  {loClamped && <polygon points={`${ciLoX},${cy} ${ciLoX + 6},${cy - 3.5} ${ciLoX + 6},${cy + 3.5}`} fill={dom.color} opacity={0.55} />}
                  {hiClamped && <polygon points={`${ciHiX},${cy} ${ciHiX - 6},${cy - 3.5} ${ciHiX - 6},${cy + 3.5}`} fill={dom.color} opacity={0.55} />}
                  {/* Marker, sized by precision */}
                  <Marker shape={dom.symbol} color={dom.color} size={isHl ? sizeOf(e) + 1.2 : sizeOf(e)} cx={cx} cy={cy} />
                  {/* Value column */}
                  <text x={width - padR} y={cy + 3.5} fontSize={11} fontFamily={F.mono}
                    fill={e.effect_size_sd >= 0 ? C.pos : C.neg} fontWeight={isHl ? 600 : 500} textAnchor="end">
                    {fmtSD(e.effect_size_sd)}
                  </text>
                </g>
              );
            })}

            {/* Pooled diamond row */}
            {re && (() => {
              const cy = padTop + plotH + 30;
              return (
                <g>
                  <line x1={0} y1={padTop + plotH + 6} x2={width} y2={padTop + plotH + 6} stroke={C.rule} strokeWidth={1} />
                  <text x={labelW - 6} y={cy + 3.5} fontSize={11.5} fontFamily={F.sans} fontWeight={600} fill={C.ink} textAnchor="end">
                    Pooled estimate (random effects)
                  </text>
                  <polygon
                    points={`${xScale(re.lo)},${cy} ${xScale(re.mean)},${cy - 9} ${xScale(re.hi)},${cy} ${xScale(re.mean)},${cy + 9}`}
                    fill={C.accent}
                  />
                  <text x={width - padR} y={cy + 3.5} fontSize={11.5} fontFamily={F.mono} fill={C.accent} fontWeight={600} textAnchor="end">
                    {fmtSD(re.mean)}
                  </text>
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
                  <span style={rv}>n = {fmt(e.n_total)}</span>
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
    <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2, overflow: "auto", maxHeight: 720 }}>
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
          {sorted.map((e) => {
            const p = paperByKey[e.paper_key];
            const dom = DOMAIN[e.learning_domain] || DOMAIN.Mixed;
            const lo = e.ci_lower != null ? e.ci_lower : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd - 1.96 * e.se : null);
            const hi = e.ci_upper != null ? e.ci_upper : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd + 1.96 * e.se : null);
            return (
              <tr key={e.estimate_id} className="hover-row"
                onClick={() => p && onSelectPaper(p)}
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
                <td style={{ ...td, ...num, color: C.ink2 }}>{fmt(e.n_total)}</td>
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

function StudyCard({ paper, onClick, idx }) {
  const [h, setH] = useState(false);
  const eff = paper.avg_effect;
  const domain = paper.learning_domain_primary || "Mixed";
  const dom = DOMAIN[domain] || DOMAIN.Mixed;

  return (
    <div
      onClick={() => onClick(paper)}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter") onClick(paper); }}
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
            {paper.population_category} · n = {fmt(paper.n_total)}
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
const SUGGEST_MAILTO = "mailto:learning_study@middlebury.edu?subject=The%20AI%20and%20Human%20Skill%20Atlas%20%E2%80%94%20paper%20suggestion&body=Citation%3A%20%0APaper%20PDF%2Flink%3A%20%0AEffect%20size%20(SD)%3A%20%0AStandard%20error%3A%20%0ASample%20size%3A%20%0AOutcome%20%2B%20timing%3A%20%0AComparison%3A%20%0ANotes%3A%20";

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
        </p>
      </div>
      <div style={cell}>
        <div style={{ ...SC({ fontSize: 9.5, color: C.accent }), marginBottom: 9 }}>Suggest a paper</div>
        <p style={{ fontFamily: F.sans, fontSize: 13, lineHeight: 1.62, color: C.ink2 }}>
          Know of a study we missed? Send the citation, effect size, SE, and sample size to{" "}
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
  url    = {https://germanr.github.io/ai-skill-atlas/}
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
              </a>, Middlebury College, with research assistance from Nam Nguyen.
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
          <span style={SC({ fontSize: 9, color: C.ink3 })}>Updated June 2026 · Middlebury College</span>
          <span style={SC({ fontSize: 9, color: C.ink3 })}>germanr.github.io/ai-skill-atlas</span>
        </div>
      </div>
    </footer>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Report card (study detail)
// ────────────────────────────────────────────────────────────────────────────
function EstimateRow({ est, domain, last }) {
  const range = 2.0; // [-1, +1]
  const pct = ((Math.max(-1, Math.min(1, est.effect_size_sd)) + 1) / range) * 100;
  return (
    <div style={{ padding: "16px 22px", borderBottom: last ? "none" : `1px solid ${C.ruleSoft}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "baseline", marginBottom: 4 }}>
        <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 13.5, color: C.ink, lineHeight: 1.4 }}>{est.outcome}</div>
        <div style={{
          fontSize: 17, fontWeight: 600, fontFamily: F.mono, whiteSpace: "nowrap",
          color: est.effect_size_sd >= 0 ? C.pos : C.neg,
        }}>
          {fmtSD(est.effect_size_sd)} <span style={{ fontSize: 10, color: C.ink3, fontWeight: 400 }}>SD</span>
        </div>
      </div>
      <div style={{ fontFamily: F.mono, fontSize: 10.5, color: C.ink3, marginBottom: 12 }}>
        {est.outcome_timing} · n = {fmt(est.n_total)}
        {est.se != null && <> · SE {fmtSE(est.se)}</>}
        {est.ci_lower != null && <> · 95% CI {fmtCI(est.ci_lower, est.ci_upper)}</>}
      </div>
      {/* Number line */}
      <div style={{ position: "relative", height: 16 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 7, height: 1, background: C.rule }} />
        <div style={{ position: "absolute", left: "50%", top: 2, width: 1, height: 11, background: C.ink3 }} />
        {est.ci_lower != null && est.ci_upper != null && (
          <div style={{
            position: "absolute",
            left: `${Math.max(0, ((Math.max(-1, est.ci_lower) + 1) / range) * 100)}%`,
            width: `${Math.min(100, ((Math.min(1, est.ci_upper) - Math.max(-1, est.ci_lower)) / range) * 100)}%`,
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
      {est.treatment && (
        <div style={{ fontSize: 12, color: C.ink2, marginTop: 10, lineHeight: 1.55, fontFamily: F.sans }}>
          <span style={{ fontWeight: 600, color: C.ink }}>{est.treatment}</span>
          <span style={{ color: C.ink3 }}> vs. </span>
          <span>{est.control}</span>
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
    </div>
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
    ["Sample size", fmt(paper.n_total)],
    ["Incentives", paper.incentives],
    ["AI tool", paper.ai_tool],
    ["AI design", paper.ai_design],
    ["Learning domain", paper.learning_domain_primary],
    ["Quality rating", [paper.quality_label, paper.quality_flags && paper.quality_flags !== "none" ? `(${paper.quality_flags})` : null].filter(Boolean).join(" ")],
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
          <h1 style={{
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
        </Section>

        {/* Effect sizes */}
        <Section title={`Effect sizes (${myEsts.length})`}>
          <div style={{ background: C.paperHi, border: `1px solid ${C.rule}`, borderRadius: 2 }}>
            {myEsts.map((e, idx) => (
              <EstimateRow key={e.estimate_id} est={e} domain={dom} last={idx === myEsts.length - 1} />
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
                    <EstimateRow key={e.estimate_id} est={e} domain={dom} last={idx === rows.length - 1} />
                  ))}
                </div>
              ))}
            </div>
            <p style={{ fontSize: 11.5, color: C.ink3, marginTop: 9, fontStyle: "italic", fontFamily: F.sans, lineHeight: 1.5 }}>
              Subgroup rows are excluded from the main forest plot by default; overlay them with the Subgroups filter on the browse page.
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
export function AboutPage({ onBack, nPapers, nEstimates, papers, onSelectPaper }) {
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, []);

  const sortedPapers = [...papers].sort((a, b) => (b.year || 0) - (a.year || 0));
  const nCountries = new Set(papers.map(p => p.country).filter(Boolean)).size;

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
          The Atlas collects randomized experiments on how generative AI affects human learning,
          standardizes their results, and documents each one. It is descriptive by design: the
          interpretation is left to the reader.
        </p>

        <p style={{ ...body, marginTop: 26 }}>
          Generative AI is entering classrooms and workplaces faster than evidence on its effects can
          accumulate. The studies that do exist are scattered across economics, education, computer
          science, and psychology, and each reports results in its own format. This site puts them in
          one place. It currently covers <strong style={{ color: C.ink }}>{nPapers} studies</strong> and{" "}
          <strong style={{ color: C.ink }}>{nEstimates} effect sizes</strong> from randomized experiments
          (plus a small number of well-identified quasi-experiments) in {nCountries} countries, with
          participants ranging from elementary students to working professionals.
        </p>
        <p style={body}>
          Effect sizes are expressed in standard-deviation units of each study's control group wherever
          the underlying paper allows it, so results can be compared across settings. The pooled estimate
          uses the DerSimonian–Laird random-effects model. Every estimate links to a study record that
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
            ["1 · Source of variation", "The study randomly assigns access to generative AI against a no-AI comparison group, or exploits a clean quasi-experiment with an AI-free assessment."],
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

        <h2 style={h2}>What counts as learning</h2>
        {rule}
        <p style={body}>
          Studies measure learning in different ways, and the differences matter when comparing effect
          sizes. A useful organizing device is <strong style={{ color: C.ink }}>Bloom's taxonomy</strong>,
          which orders cognitive skills from lower to higher: remembering, understanding, applying,
          analyzing, evaluating, and creating.
        </p>
        <div style={{ marginTop: 16, border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi }}>
          {[
            ["Lower-order · remember, understand, apply", "Typically measured with test scores (multiple-choice or short-answer items). These are easy to standardize and grade, and they dominate the literature."],
            ["Higher-order · analyze, evaluate, create", "Measured with essays, open-ended problems, or transfer tasks. These are noisier and harder to grade, but closer to the skills education ultimately targets."],
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
          exactly what each study measured.
        </p>

        <h2 style={h2}>How to read the estimates</h2>
        {rule}
        <div style={{ marginTop: 4 }}>
          {[
            ["The pooled mean hides real variation.", "Effects differ by subject, by population, and above all by whether the outcome was measured with or without AI in hand. Read the spread, not only the average."],
            ["Precision varies.", "Some estimates come from large pre-registered field experiments, others from small single-site studies over short horizons. Each study carries a quality label and flags in the data."],
            ["Independence varies.", "Some studies were conducted by, or in collaboration with, the companies whose tools they evaluate. The study records note this where it applies."],
            ["Intervals overlap.", "Most pairs of studies cannot be reliably ranked against each other. The forest plot describes a distribution, not a leaderboard."],
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
                style={{ padding: "13px 10px 13px 0", borderBottom: `1px solid ${C.ruleSoft}`, cursor: "pointer", transition: "background 0.1s" }}
              >
                <div style={{ fontFamily: F.sans, fontSize: 13.5, fontWeight: 600, color: C.ink, lineHeight: 1.45 }}>
                  {p.authors_short} ({p.year}) — "{p.title}"
                  {p.venue && <span style={{ fontWeight: 400, color: C.ink3, fontSize: 11.5, marginLeft: 8, fontStyle: "italic", fontFamily: F.serif }}>{p.venue}</span>}
                </div>
                <div style={{ fontFamily: F.mono, fontSize: 10.5, color: C.ink3, marginTop: 4, letterSpacing: "0.02em" }}>
                  {p.country} · {p.population_category} · {p.lab_vs_field} · {p.study_design} · n = {fmt(p.n_total)}
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
            "Standardization. Effects are expressed in SD units of the control group. Where papers reported raw effects, standard errors were back-calculated from sample sizes or recomputed from control-group SDs.",
            "Pooling. The pooled mean uses the DerSimonian–Laird random-effects estimator; the shaded band in the forest plot is its 95% confidence interval, which reflects between-study heterogeneity.",
            "Learning vs. assisted performance. The default view excludes outcomes measured with AI access (e.g., assisted-practice scores), which capture AI-augmented performance rather than learning. The Outcome filter adds them back.",
            "Comparisons. AI vs. business-as-usual is the default and never pooled with the others. AI vs. active control and off-the-shelf vs. scaffolded AI can each be viewed separately.",
            "Subgroups. Heterogeneity estimates (by gender, prior achievement, topic) are hidden by default to keep the plot readable, and can be overlaid with the Subgroups filter.",
          ].map((t, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "10px 1fr", gap: 14, padding: "12px 0", borderBottom: `1px solid ${C.ruleSoft}` }}>
              <span style={{ color: C.accent, fontFamily: F.mono, fontSize: 13, lineHeight: 1.5 }}>—</span>
              <p style={{ fontFamily: F.sans, fontSize: 13.5, lineHeight: 1.65, color: C.ink2, margin: 0 }}>{t}</p>
            </div>
          ))}
        </div>

        <h2 style={h2}>Data</h2>
        {rule}
        <p style={body}>
          Every estimate can be downloaded as a CSV from the browse page. The export reflects the active
          filters, so clear them to get the complete dataset. The main columns:
        </p>
        <div style={{ marginTop: 16, border: `1px solid ${C.rule}`, borderRadius: 2, background: C.paperHi, padding: "16px 20px" }}>
          <div style={{ ...SC({ fontSize: 9.5, color: C.ink3 }), marginBottom: 12 }}>Data dictionary</div>
          <div style={{ display: "grid", gap: 9 }}>
            {[
              ["paper_key", "Short identifier for the study."],
              ["effect_size_sd", "Effect in control-group SD units; positive favors the treatment condition."],
              ["se", "Standard error of the effect (SD units)."],
              ["ci_lower / ci_upper", "95% confidence interval."],
              ["n_total", "Participants contributing to the estimate."],
              ["learning_domain", "Subject area (math, coding, writing, language, science…)."],
              ["outcome / outcome_timing", "What was measured, and whether immediate or delayed."],
              ["comparison_type", "AI vs. business-as-usual, AI vs. active control, or off-the-shelf vs. scaffolded AI."],
              ["estimand / estimation_method", "Parameter identified (ITT, LATE…) and how it was estimated."],
              ["outcome_with_ai", "Whether the outcome was measured with AI in hand."],
              ["is_subgroup / subgroup", "Whether the row is a heterogeneity estimate, and its label."],
              ["quality_label / quality_flags", "Study-quality rating and any caveats."],
            ].map(([col, desc]) => (
              <div key={col} style={{ display: "grid", gridTemplateColumns: "190px 1fr", gap: 12, alignItems: "baseline" }} className="facts-grid">
                <code style={{ fontFamily: F.mono, fontSize: 11, color: C.ink, fontWeight: 500 }}>{col}</code>
                <span style={{ fontSize: 12.5, color: C.ink2, lineHeight: 1.55, fontFamily: F.sans }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>

        <h2 style={h2}>Updates</h2>
        {rule}
        <p style={body}>
          The atlas is a living resource: new papers, recoded estimates, and methodology changes are
          logged here as they happen.
        </p>
        <div style={{ marginTop: 12 }}>
          {[
            ["June 2026", `Initial public version: ${nPapers} studies and ${nEstimates} effect sizes, with an interactive forest plot, individual study records, CSV export, and this methodology page.`],
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
          </a>{" "}with the citation and a link or PDF. If available, include the effect size in SD units,
          its standard error, the sample size, the outcome and its timing, and the comparison condition.
          Suggestions are evaluated against the inclusion criteria above and nothing else.
        </p>

        <h2 style={h2}>Authorship and independence</h2>
        {rule}
        <p style={body}>
          The atlas is maintained by{" "}
          <a href="https://www.germanr.com" target="_blank" rel="noreferrer" style={{ color: C.ink, fontWeight: 600, borderBottom: `1px solid ${C.ink}` }}>
            Germán Reyes
          </a>{" "}(Middlebury College), with research assistance from Nam Nguyen. One included study,
          Contractor and Reyes (2026), is by the maintainer. It receives no special treatment: the same
          inclusion rules, the same coding, and the same display as every other study.
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
        {paper.authors_short} ({paper.year}){paper.n_total != null ? ` · n = ${paper.n_total.toLocaleString()}` : ""}
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
// Main app
// ────────────────────────────────────────────────────────────────────────────
export default function App() {
  const initialParams = new URLSearchParams(window.location.search);
  const [section, setSection] = useState(initialParams.get("section") === "creativity" ? "creativity" : "learning");
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [search, setSearch] = useState("");
  const [activeDomains, setActiveDomains] = useState(new Set());
  const [activePopulations, setActivePopulations] = useState(new Set());
  const [activeSettings, setActiveSettings] = useState(new Set());
  const [comparisonType, setComparisonType] = useState("ai_vs_bau"); // "ai_vs_bau" | "ai_vs_active" | "ai_design"
  const [outcomeMode, setOutcomeMode] = useState("without_ai");      // "without_ai" | "all"
  const [activeSubgroupValues, setActiveSubgroupValues] = useState(new Set());
  const [sortBy, setSortBy] = useState("effect");
  const [view, setView] = useState("chart");        // "chart" | "table"
  const [plotSort, setPlotSort] = useState("effect"); // "effect" | "precision" | "year"

  // Inject global CSS once
  useEffect(() => {
    const styleEl = document.createElement("style");
    styleEl.innerHTML = GCSS;
    document.head.appendChild(styleEl);
    return () => { document.head.removeChild(styleEl); };
  }, []);

  // Deep link: ?paper=<key> opens that paper's report; history kept in sync
  useEffect(() => {
    const key = new URLSearchParams(window.location.search).get("paper");
    if (key) {
      const p = PAPERS_RAW.find((x) => x.paper_key === key);
      if (p) setSelectedPaper(p);
    }
    const onPop = () => {
      const params = new URLSearchParams(window.location.search);
      const k = params.get("paper");
      setSelectedPaper(k ? PAPERS_RAW.find((x) => x.paper_key === k) || null : null);
      setSection(params.get("section") === "creativity" ? "creativity" : "learning");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const openPaper = (p) => {
    setSelectedPaper(p);
    window.history.pushState({}, "", `${window.location.pathname}?paper=${p.paper_key}`);
  };
  const closePaper = () => {
    setSelectedPaper(null);
    window.history.pushState({}, "", window.location.pathname);
  };
  const goSection = (s) => {
    setSection(s);
    setSelectedPaper(null);
    window.history.pushState({}, "", s === "creativity" ? `${window.location.pathname}?section=creativity` : window.location.pathname);
  };

  const papers = PAPERS_RAW;
  const estimates = ESTIMATES_RAW;

  // Default-view estimates (hero strip + pooled headline): primary, no-AI outcomes, vs. BAU
  const defaultEstimates = useMemo(() => estimates.filter(e =>
    (e.comparison_type || "ai_vs_bau") === "ai_vs_bau" &&
    e.outcome_with_ai !== true &&
    e.is_subgroup !== true
  ), [estimates]);
  const pooledDefault = useMemo(() => randomEffectsMean(defaultEstimates), [defaultEstimates]);

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
      if ((e.comparison_type || "ai_vs_bau") !== comparisonType) return false;
      if (outcomeMode === "without_ai" && e.outcome_with_ai === true) return false;
      if (e.is_subgroup === true) {
        if (!activeSubgroupValues.has(e.subgroup)) return false;
      }
      return true;
    });
  }, [filteredPapers, estimates, comparisonType, outcomeMode, activeSubgroupValues]);

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

  const papersWithEstimates = useMemo(() => {
    const keysInView = new Set(filteredEstimates.map(e => e.paper_key));
    return filteredPapers.filter(p => keysInView.has(p.paper_key));
  }, [filteredPapers, filteredEstimates]);

  const sortedPapers = useMemo(() => {
    const arr = [...papersWithEstimates];
    arr.sort((a, b) => {
      if (sortBy === "effect") return (b.avg_effect ?? -999) - (a.avg_effect ?? -999);
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

  const nActiveFilters = activeDomains.size + activePopulations.size + activeSettings.size + activeSubgroupValues.size
    + (comparisonType !== "ai_vs_bau" ? 1 : 0) + (outcomeMode !== "without_ai" ? 1 : 0);
  const resetFilters = () => {
    setActiveDomains(new Set());
    setActivePopulations(new Set());
    setActiveSettings(new Set());
    setActiveSubgroupValues(new Set());
    setComparisonType("ai_vs_bau");
    setOutcomeMode("without_ai");
    setSearch("");
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
            title="The evidence, estimate by estimate"
            sub="Every effect size on one axis. Markers are sized by precision (inverse variance); the blue band is the random-effects pooled estimate. Hover for details; click any row to open the study."
          />

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
              last={availableSubgroupValues.length === 0}
            />
            {availableSubgroupValues.length > 0 && (
              <FilterRow
                label="Subgroups"
                options={availableSubgroupValues}
                active={activeSubgroupValues}
                onToggle={(v) => toggleSet(activeSubgroupValues, v, setActiveSubgroupValues)}
                last
              />
            )}
          </div>

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
                    <button key={key} onClick={() => setPlotSort(key)} style={{
                      background: "none", border: "none", cursor: "pointer", padding: "3px 0",
                      fontFamily: F.mono, fontSize: 10.5, letterSpacing: "0.06em", textTransform: "uppercase",
                      color: plotSort === key ? C.ink : C.ink3,
                      fontWeight: plotSort === key ? 600 : 400,
                      borderBottom: plotSort === key ? `2px solid ${C.ink}` : "2px solid transparent",
                    }}>{label}</button>
                  ))}
                </div>
              )}
              <span style={SC({ fontSize: 9.5, color: C.ink3 })}>
                {filteredEstimates.length} estimates · {papersWithEstimates.length} studies
              </span>
              <GhostBtn small onClick={() => downloadCSV(filteredEstimates, papers)}>↓ CSV</GhostBtn>
            </div>
          </div>

          {view === "chart" ? (
            <>
              <ForestPlot estimates={filteredEstimates} papers={papers} onSelectPaper={openPaper} width={1084} sortMode={plotSort} />
              <p style={{ fontFamily: F.sans, fontSize: 11.5, color: C.ink3, lineHeight: 1.6, marginTop: 10, fontStyle: "italic" }}>
                Note: Random-effects pooling (DerSimonian–Laird){fePlot ? ` over k = ${fePlot.k} estimates; τ̂² = ${fePlot.tau2.toFixed(3)}` : ""}.
                Horizontal lines are 95% confidence intervals; arrowheads mark intervals truncated at ±1 SD.
                Positive values favor the AI condition.
              </p>
            </>
          ) : (
            <EstimatesTable estimates={filteredEstimates} papers={papers} onSelectPaper={openPaper} />
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
                  {[["effect", "Effect"], ["year", "Year"], ["n", "N"], ["author", "Author"]].map(([key, label]) => (
                    <button key={key} onClick={() => setSortBy(key)} style={{
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
                <StudyCard key={p.paper_key} paper={p} onClick={openPaper} idx={idx} />
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
