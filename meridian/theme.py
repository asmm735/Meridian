"""MERIDIAN design system.

Every colour lives here. Components refer to CSS variables (var(--ink) etc.)
through class names; nothing else in the code base may contain a hex value.

Usage rule: ~65% ivory/paper, ~25% ink/navy, ~10% accent blue.
Blue is used as printed ink: rules, stamps, route lines, key numbers, focus.
Never as a glow, gradient or large background wash.
"""

# ── Neutrals ────────────────────────────────────────────────────────────────
INK = "#111315"
NAVY = "#1C2B35"
NAVY_2 = "#2A3E50"   # a step lighter than navy, for globe surfaces on navy
IVORY = "#F6F2EA"
PAPER = "#E9E2D6"
PAPER_DEEP = "#D9D0BF"
SLATE = "#71818A"

# ── Accent (sampled from the Meridian symbol) ───────────────────────────────
# Replace ACCENT with the exact hex from the brand symbol; the rest follow.
ACCENT = "#5B9BD5"
ACCENT_DEEP = "#2C6AA0"   # hover / pressed / accent text on ivory (≥5:1)
ACCENT_SOFT = "#E1EDF8"   # pale tint for bands and focus rings

# ── Fonts ───────────────────────────────────────────────────────────────────
FONT_SERIF = "'Cormorant Garamond', 'Iowan Old Style', Georgia, serif"
FONT_SANS = "'Inter', 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "'IBM Plex Mono', 'Courier New', monospace"

FONT_TAGLINE = "'Jost', 'Futura', 'Century Gothic', 'Helvetica Neue', sans-serif"

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=Jost:wght@300;400;500&"
    "family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=Inter:wght@400;500;600&display=swap"
)


def _hex_to_rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))


INK_RGB = _hex_to_rgb(INK)
NAVY_RGB = _hex_to_rgb(NAVY)
IVORY_RGB = _hex_to_rgb(IVORY)
ACCENT_RGB = _hex_to_rgb(ACCENT)

_ROOT = f"""
:root{{
  --ink:{INK}; --navy:{NAVY}; --navy-2:{NAVY_2}; --ivory:{IVORY}; --paper:{PAPER};
  --paper-deep:{PAPER_DEEP}; --slate:{SLATE};
  --accent:{ACCENT}; --accent-deep:{ACCENT_DEEP}; --accent-soft:{ACCENT_SOFT};
  --rule:rgba({INK_RGB},.16); --rule-strong:rgba({INK_RGB},.34);
  --ink-soft:rgba({INK_RGB},.74);
  --error:#9b2f2f; --error-soft:#fff0ee; --success:#216e4e; --success-soft:#e8f4ed;
  --rule-on-navy:rgba({IVORY_RGB},.16);
  --serif:{FONT_SERIF}; --tagline:{FONT_TAGLINE}; --sans:{FONT_SANS}; --mono:{FONT_MONO};
  --shadow-1:0 1px 1px rgba({INK_RGB},.06),0 10px 24px -12px rgba({INK_RGB},.30),0 28px 48px -26px rgba({INK_RGB},.26);
  --shadow-2:0 2px 2px rgba({INK_RGB},.07),0 18px 34px -14px rgba({INK_RGB},.34),0 40px 64px -30px rgba({INK_RGB},.30);
  --shadow-on-navy:0 2px 2px rgba(0,0,0,.25),0 18px 34px -14px rgba(0,0,0,.5);
}}
"""

_BODY = r"""
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--ivory);color:var(--ink);font-family:var(--sans);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;line-height:1.5}
/* fine paper grain: an accent, not a blanket */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:1;opacity:.55;mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .35 0 0 0 0 .30 0 0 0 0 .25 0 0 0 .07 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
a{color:var(--accent-deep);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
button{font-family:inherit}

/* ── Type ── */
.serif{font-family:var(--serif)}
.mono{font-family:var(--mono);letter-spacing:.18em;text-transform:uppercase;font-size:11px;color:var(--slate);font-weight:500}
.mono.ink{color:var(--ink)} .mono.blue{color:var(--accent-deep)} .mono.on-navy{color:rgba(246,242,234,.62)}
.display{font-family:var(--serif);font-weight:500;line-height:.98;letter-spacing:.02em;font-size:clamp(42px,5.6vw,88px);margin:0}
.tagline{font-family:var(--tagline);font-weight:400;text-transform:uppercase;letter-spacing:.3em;color:var(--navy);font-size:clamp(13px,1.3vw,17px);line-height:2.1;margin:0}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.h1{font-family:var(--serif);font-weight:500;font-size:clamp(34px,4.4vw,58px);line-height:1.05;margin:0}
.h2{font-family:var(--serif);font-weight:500;font-size:clamp(28px,3.2vw,42px);line-height:1.1;margin:0}
.h3{font-family:var(--serif);font-weight:600;font-size:23px;line-height:1.15;margin:0}
.lede{font-size:17px;line-height:1.65;color:var(--ink-soft);max-width:52ch;margin:0}
.body{font-size:15px;line-height:1.65;color:var(--ink-soft);margin:0}
.num-key{font-family:var(--serif);font-weight:600;color:var(--accent-deep);line-height:1}
.on-navy .num-key,.navy .num-key,.cover .num-key{color:var(--accent)}

/* ── Layout ── */
.container{max-width:1200px;margin:0 auto;padding:0 28px;width:100%}
.section{padding:104px 0}
.hero-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.08fr);gap:56px;align-items:center}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
.grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px}
.split{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:28px;align-items:start}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 24px}
.form-grid .wide{grid-column:1/-1}
.navy{background:var(--navy);color:var(--ivory)}
.stack{display:flex;flex-direction:column}
.row{display:flex;align-items:center}
.wrap{flex-wrap:wrap}
.between{justify-content:space-between}

/* ── Surfaces ── */
.sheet{background:var(--ivory);border:1px solid var(--rule);border-radius:3px;box-shadow:var(--shadow-1);position:relative}
.sheet.stacked{box-shadow:0 1px 0 var(--rule),5px 6px 0 -1px var(--paper),5px 6px 0 0 var(--rule),10px 12px 0 -2px var(--paper-deep),var(--shadow-1)}
.sheet.alt{background:var(--paper)}
.sheet-pad{padding:36px}
.rule{height:1px;background:var(--rule);border:0;margin:0}
.rule-blue{width:34px;height:2px;background:var(--accent);border:0;margin:0}

/* ── Navbar ── */
.nav{position:sticky;top:0;z-index:60;background:rgba(246,242,234,.94);border-bottom:1px solid var(--rule)}
.nav-inner{display:flex;align-items:center;justify-content:space-between;height:74px;gap:24px;min-width:0}
.nav-links{display:flex;gap:34px}
.nav-link{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:var(--ink);position:relative;padding:6px 0}
.nav-link::after{content:"";position:absolute;left:0;right:0;bottom:0;height:1.5px;background:var(--accent);transform:scaleX(0);transform-origin:left;transition:transform .3s cubic-bezier(.2,.7,.2,1)}
.nav-link:hover{text-decoration:none}.nav-link:hover::after{transform:scaleX(1)}
.brand{display:flex;align-items:center;gap:12px;color:var(--ink);text-decoration:none}
.brand:hover{text-decoration:none}
.stepper{display:flex;gap:6px;align-items:center;min-width:0;overflow-x:auto;scrollbar-width:none}
.stepper::-webkit-scrollbar{display:none}
.step{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate);padding:6px 10px;border:0;border-bottom:2px solid transparent;background:transparent;cursor:pointer}
.step.done{color:var(--ink)}
.step.active{color:var(--accent-deep);border-bottom-color:var(--accent);font-weight:600}

/* ── Start Journey: passport-tab button ── */
.tab-button{position:relative;display:inline-flex;align-items:center;gap:16px;padding:15px 24px 15px 30px;background:var(--ivory);color:var(--ink);
  border:1.5px solid var(--ink);border-radius:3px 12px 3px 3px;font-family:var(--mono);font-weight:600;font-size:12px;letter-spacing:.22em;text-transform:uppercase;cursor:pointer;overflow:hidden;
  box-shadow:0 1px 0 var(--ink),0 8px 14px -8px rgba(17,19,21,.45);transition:transform .28s cubic-bezier(.2,.7,.2,1),box-shadow .28s cubic-bezier(.2,.7,.2,1)}
.tab-button::before{content:"";position:absolute;left:0;top:0;bottom:0;width:7px;background:var(--accent);transition:width .28s cubic-bezier(.2,.7,.2,1)}
.tab-button::after{content:"";position:absolute;left:7px;right:100%;bottom:0;height:3px;background:var(--accent);transition:right .38s cubic-bezier(.2,.7,.2,1)}
.tab-button:hover{transform:translateY(-3px) rotate(-.4deg);box-shadow:0 1px 0 var(--ink),0 16px 22px -12px rgba(17,19,21,.4)}
.tab-button:hover::before{width:11px}.tab-button:hover::after{right:0}
.tab-button:active{transform:translateY(0) rotate(0);box-shadow:0 1px 0 var(--ink),0 4px 8px -6px rgba(17,19,21,.5)}
.tab-arrow{color:var(--accent-deep);font-size:15px;transition:transform .28s}
.tab-button:hover .tab-arrow{transform:translateX(4px)}
.tab-button.sm{padding:11px 18px 11px 24px;font-size:11px}
.tab-button.solid{background:var(--ink);color:var(--ivory);border-color:var(--ink)}
.tab-button.solid .tab-arrow{color:var(--accent)}
.tab-button.on-navy{background:var(--ivory);color:var(--ink);border-color:var(--ivory);box-shadow:var(--shadow-on-navy)}
.tab-button[disabled]{opacity:.45;cursor:not-allowed;transform:none}
.btn-ghost{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;padding:14px 20px;background:transparent;color:var(--ink);border:1px solid var(--rule-strong);border-radius:3px;cursor:pointer;transition:border-color .2s,transform .2s,color .2s}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent-deep);transform:translateY(-1px)}
.btn-download{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;padding:16px 26px;background:var(--accent-deep);color:var(--ivory);border:0;border-radius:3px;cursor:pointer;
  box-shadow:0 1px 0 var(--ink),0 10px 18px -10px rgba(17,19,21,.6);transition:transform .25s,box-shadow .25s,background .2s}
.btn-download:hover{background:var(--ink);transform:translateY(-2px);box-shadow:0 1px 0 var(--ink),0 16px 22px -12px rgba(17,19,21,.5)}
.btn-download:active{transform:translateY(0)}

/* ── Forms ── */
.field{display:flex;flex-direction:column;gap:8px}
.field-label{font-family:var(--mono);font-size:10.5px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:var(--slate)}
.input{width:100%;font:400 15px/1.4 var(--sans);padding:13px 14px;background:var(--ivory);color:var(--ink);border:1px solid rgba(17,19,21,.3);border-radius:3px;
  box-shadow:inset 0 1px 2px rgba(17,19,21,.07);transition:border-color .2s,box-shadow .2s,background .2s}
.input:hover{border-color:rgba(17,19,21,.6)}
.input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft),inset 0 1px 2px rgba(17,19,21,.05);background:#fff}
textarea.input{min-height:104px;resize:vertical}
.tabs{display:flex;gap:4px;overflow-x:auto;padding:0 2px;border-bottom:1px solid var(--rule-strong);scrollbar-width:thin}
.doc-tab{flex:0 0 auto;padding:12px 13px 11px;background:var(--paper);color:var(--slate);border:1px solid var(--rule);border-bottom:0;border-radius:8px 8px 0 0;
  font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;font-weight:500;cursor:pointer;position:relative;top:1px;transition:color .2s,background .2s,transform .2s;border-top:3px solid transparent}
.doc-tab:hover{color:var(--ink);transform:translateY(-1px)}
.doc-tab.active{background:var(--ivory);color:var(--ink);border-top-color:var(--accent);border-bottom:1px solid var(--ivory);font-weight:600}
.progress{height:3px;background:var(--rule);border-radius:2px;overflow:hidden}
.progress>i{display:block;height:100%;background:var(--accent);transition:width .6s ease}

/* ── Stamps ── */
.stamp{display:inline-block;font-family:var(--mono);font-weight:600;font-size:11.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--accent-deep);border:2px solid var(--accent-deep);padding:6px 11px;border-radius:3px;transform:rotate(-4deg);
  animation:stampIn .55s cubic-bezier(.2,.8,.3,1) both;-webkit-mask-image:linear-gradient(115deg,#000 60%,rgba(0,0,0,.82));mask-image:linear-gradient(115deg,#000 60%,rgba(0,0,0,.82))}
.navy .stamp{color:var(--accent);border-color:var(--accent)}
.stamp.static{animation:none}
.agent-card .stamp{color:var(--accent-deep);border-color:var(--accent-deep)}
.status-failed{display:inline-block;color:var(--error);background:var(--error-soft);border:1px solid var(--error);border-radius:3px;padding:6px 10px;font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase}
.status-unavailable{display:inline-block;color:var(--slate);background:var(--paper);border:1px solid var(--slate);border-radius:3px;padding:6px 10px;font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase}
@keyframes stampIn{0%{opacity:0;transform:rotate(-8deg) scale(1.35)}100%{opacity:1;transform:rotate(-4deg) scale(1)}}

/* ── Hero scene ── */
.scene{position:relative;aspect-ratio:1/.94;width:100%;perspective:1500px}
.scene .desk{position:absolute;inset:3% 0 0 0;border-radius:6px;background:
  radial-gradient(120% 90% at 18% 8%,rgba(255,252,245,.95) 0%,rgba(255,252,245,0) 55%),var(--paper);
  box-shadow:inset 0 0 0 1px var(--rule),var(--shadow-2)}
.layer{position:absolute;will-change:transform;transition:transform .12s linear}
.globe-wrap{right:6%;top:0;width:44%;aspect-ratio:1}
.globe-wrap canvas{position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity 1s ease}
.globe-wrap.live canvas{opacity:1}
.globe-wrap.live .globe-fallback{opacity:0}
.globe-fallback{position:absolute;inset:0;transition:opacity 1s ease;filter:drop-shadow(0 26px 22px rgba(17,19,21,.28))}
.globe-shadow{position:absolute;left:8%;right:8%;bottom:-5%;height:9%;background:radial-gradient(closest-side,rgba(17,19,21,.28),rgba(17,19,21,0));}
.boarding{right:2%;top:33%;width:45%;transform:rotate(4deg);background:var(--ivory);border-radius:4px;box-shadow:var(--shadow-1);border:1px solid var(--rule);overflow:hidden;display:flex}
.boarding .main{flex:1;padding:14px 16px}
.boarding .stub{width:26%;border-left:2px dashed var(--rule-strong);padding:14px 10px;background:var(--accent-soft)}
.boarding .strip{height:6px;background:var(--accent)}
.barcode{height:22px;margin-top:8px;background:repeating-linear-gradient(90deg,var(--ink) 0 2px,transparent 2px 4px,var(--ink) 4px 5px,transparent 5px 8px,var(--ink) 8px 11px,transparent 11px 12px)}
.passport{left:3%;top:5%;width:27%;aspect-ratio:.7;background:var(--navy);border-radius:3px 6px 6px 3px;transform:rotate(-9deg);box-shadow:var(--shadow-2),inset 3px 0 0 rgba(0,0,0,.28),inset -1px 0 0 rgba(255,255,255,.06);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:var(--ivory)}
.passport .emboss{filter:drop-shadow(0 1px 0 rgba(255,255,255,.14)) drop-shadow(0 -1px 0 rgba(0,0,0,.4))}
.dossier{left:3%;bottom:4%;width:54%;transform:rotate(-1.4deg)}
.dossier .folder-tab{position:absolute;left:24px;top:-24px;height:26px;padding:0 18px;display:flex;align-items:center;background:var(--ivory);border:1px solid var(--rule);border-bottom:0;border-radius:6px 6px 0 0}
.dossier .folder{background:var(--ivory);border:1px solid var(--rule);border-radius:3px 4px 4px 3px;box-shadow:var(--shadow-2);padding:22px 24px 22px;position:relative;
  background-image:linear-gradient(90deg,rgba(17,19,21,.07),rgba(17,19,21,0) 3%)}
.dossier .kv{display:grid;grid-template-columns:132px 1fr;padding:7px 0;border-bottom:1px dotted var(--rule-strong);align-items:baseline}
.dossier .kv b{font-family:var(--mono);font-size:12px;font-weight:500;letter-spacing:.08em;color:var(--ink)}
.scene .stamp-abs{left:50%;bottom:0;transform:rotate(-8deg)}
.shortlist{right:3%;bottom:5%;width:29%;background:var(--ivory);border:1px solid var(--rule);box-shadow:var(--shadow-1);padding:12px 14px;transform:rotate(3deg);border-radius:2px}
.shortlist p{margin:5px 0 0;font-family:var(--serif);font-size:15px;font-weight:600;line-height:1.2}

/* ── Timeline / route ── */
.route{position:relative;padding-left:58px}
.route::before{content:"";position:absolute;left:19px;top:14px;bottom:14px;border-left:1.5px dashed var(--accent)}
.agent-row{position:relative;margin-bottom:16px}
.node{position:absolute;left:-49px;top:50%;width:20px;height:20px;margin-top:-10px;border-radius:50%;border:2px solid var(--slate);background:var(--navy);transition:all .4s;display:flex;align-items:center;justify-content:center;color:var(--navy);font-size:11px;font-weight:700}
.node.processing{border-color:var(--accent);background:var(--accent)}
.node.completed{border-color:var(--accent);background:var(--accent)}
.node.failed{border-color:var(--error);background:var(--error);color:var(--ivory)}
.agent-card{position:relative;display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:18px;align-items:center;padding:20px 24px;background:var(--ivory);color:var(--ink);border-radius:3px;border-top:4px solid transparent;
  box-shadow:var(--shadow-on-navy);transition:transform .6s cubic-bezier(.2,.7,.2,1),box-shadow .6s,opacity .6s,border-color .6s,background .6s}
.agent-card.waiting{background:transparent;box-shadow:none;color:rgba(246,242,234,.78);border:1px solid var(--rule-on-navy)}
.agent-card.waiting .body{color:rgba(246,242,234,.55)}
.agent-card.waiting .mono{color:rgba(246,242,234,.55)}
.agent-card.processing{transform:translateY(-4px) rotate(-.4deg);border-top-color:var(--accent);box-shadow:0 24px 44px -18px rgba(0,0,0,.65)}
.agent-card.completed{border-top-color:var(--rule);opacity:1}
.agent-card.failed{border-top-color:var(--error);background:var(--error-soft)}
.agent-card.failed .agent-no,.agent-card.failed .body{color:var(--error)}
.agent-card.waiting:has(.status-unavailable){border-color:var(--rule-on-navy);opacity:.72}
.agent-no{font-family:var(--serif);font-size:30px;font-weight:600;color:var(--slate)}
.agent-card.processing .agent-no,.agent-card.completed .agent-no{color:var(--accent-deep)}
.agent-status{min-width:132px;text-align:right}
.globe-bg{position:absolute;right:-12%;top:8%;width:min(760px,80vw);opacity:.5;pointer-events:none}

/* ── Results ── */
.cover{position:relative;overflow:hidden;background:var(--navy);color:var(--ivory);border-radius:3px;box-shadow:var(--shadow-2);padding:56px 48px}
.cover .watermark{position:absolute;left:-70px;bottom:-90px;opacity:.06;pointer-events:none}
.bar{height:7px;background:rgba(17,19,21,.1);border-radius:1px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--ink);transition:width .8s ease}
.bar.key>i{background:var(--accent)}
.bar.neg>i{background:var(--slate)}
.navy .bar{background:rgba(246,242,234,.16)}
.stacked-bar{display:flex;height:16px;border-radius:1px;overflow:hidden;gap:2px}
.tier{font-family:var(--mono);font-size:10px;letter-spacing:.18em;text-transform:uppercase;padding:3px 8px;border:1px solid var(--rule-strong);border-radius:2px;color:var(--ink)}
.tier.blue{border-color:var(--accent-deep);color:var(--accent-deep)}
table.plain{width:100%;border-collapse:collapse;font-size:14px}
table.plain th{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate);text-align:left;font-weight:500;padding:0 12px 10px 0;border-bottom:1px solid var(--rule-strong)}
table.plain td{padding:12px 12px 12px 0;border-bottom:1px solid var(--rule);vertical-align:top}
.map-wrap{position:relative;aspect-ratio:1000/560;background:var(--paper);border:1px solid var(--rule);border-radius:3px;box-shadow:inset 0 0 0 6px var(--ivory),var(--shadow-1);overflow:hidden}
.map-layer{position:absolute;inset:0}
.map-layer svg{width:100%;height:100%;display:block}
.route-line path{fill:none;stroke:var(--accent);stroke-width:1.2;stroke-dasharray:4 5;opacity:.35;transition:opacity .3s,stroke-width .3s}
.route-line.sel path{stroke-dasharray:none;stroke-width:2.4;opacity:1}
.marker{position:absolute;transform:translate(-50%,-50%);width:14px;height:14px;padding:0;border-radius:50%;background:var(--ink);border:2px solid var(--ivory);cursor:pointer;transition:transform .25s,background .25s;box-shadow:0 2px 3px rgba(17,19,21,.35)}
.marker:hover{transform:translate(-50%,-50%) scale(1.25)}
.marker.sel{width:20px;height:20px;background:var(--accent);box-shadow:0 0 0 4px var(--accent-soft),0 2px 3px rgba(17,19,21,.35)}
.map-label{position:absolute;transform:translate(10px,-50%);font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink);pointer-events:none;white-space:nowrap}
.map-label.sel{color:var(--accent-deep);font-weight:600;transform:translate(16px,-50%)}
.origin{position:absolute;left:1.5%;top:1.5%;background:var(--paper);padding:2px 8px;z-index:2}
.uni-chip{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;padding:8px 12px;border:1px solid var(--rule-strong);background:var(--ivory);border-radius:2px;cursor:pointer;color:var(--ink);transition:all .2s}
.uni-chip:hover{border-color:var(--accent)}
.uni-chip.sel{border-color:var(--accent-deep);background:var(--accent-soft);color:var(--accent-deep);font-weight:600}
.info-card{background:var(--ivory);border:1px solid var(--rule);border-top:4px solid var(--accent);border-radius:3px;box-shadow:var(--shadow-2);padding:26px;animation:slideIn .45s cubic-bezier(.2,.7,.2,1) both}
@keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

/* ── Upload ── */
.upload-root{border:0!important;padding:0!important;width:100%;cursor:pointer}
.drop{border:1.5px dashed var(--rule-strong);border-radius:3px;background:var(--paper);padding:26px 20px;min-height:170px;display:flex;flex-direction:column;justify-content:center;gap:8px;transition:border-color .2s,background .2s,transform .3s}
.drop:hover{border-color:var(--accent);background:var(--accent-soft);transform:translateY(-2px)}
.doc-card{display:grid;grid-template-columns:52px minmax(0,1fr);gap:16px;align-items:center;padding:18px;background:var(--ivory);border:1px solid var(--rule);border-left:4px solid var(--accent);border-radius:3px;box-shadow:var(--shadow-1);animation:slideIn .5s cubic-bezier(.2,.7,.2,1) both}
.file-badge{width:52px;height:64px;background:var(--ivory);border:1px solid var(--rule-strong);border-radius:2px 10px 2px 2px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:7px;font-family:var(--mono);font-size:10px;letter-spacing:.1em;font-weight:600;color:var(--accent-deep);box-shadow:2px 3px 0 var(--paper-deep)}
.trunc{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── Report ── */
.report-page{width:min(820px,100%);margin:0 auto 36px;background:var(--ivory);border:1px solid var(--rule);box-shadow:var(--shadow-2);padding:60px 64px;position:relative;overflow:hidden}
.report-page .wm{position:absolute;right:-30px;bottom:-30px;opacity:.06;pointer-events:none}
.kv-row{display:flex;justify-content:space-between;gap:16px;padding:9px 0;border-bottom:1px dotted var(--rule-strong)}

/* ── Journey-opening transition ── */
.opening{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;background:var(--ivory);animation:fadeIn .35s ease both;pointer-events:auto;isolation:isolate}
.open-scene{perspective:1800px;width:min(340px,70vw);aspect-ratio:.72;position:relative;transform:translateZ(0);will-change:transform}
.open-page{position:absolute;inset:0;background:var(--ivory);border:1px solid var(--rule);box-shadow:var(--shadow-2);padding:32px}
.open-cover{position:absolute;inset:0;background:var(--navy);border-radius:3px 8px 8px 3px;transform-origin:left center;box-shadow:var(--shadow-2);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;color:var(--ivory);
  animation:coverOpen 1.25s cubic-bezier(.65,0,.25,1) .3s both;backface-visibility:hidden}
@keyframes coverOpen{0%{transform:rotateY(0)}100%{transform:rotateY(-158deg)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){
  .opening{animation:fadeIn .2s ease both!important}
  .opening .open-cover{animation:coverOpen .9s cubic-bezier(.65,0,.25,1) both!important}
}
.page-enter{animation:pageEnter .8s cubic-bezier(.2,.7,.2,1) both}
@keyframes pageEnter{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}

/* ── Responsive ── */
@media (max-width:980px){
  .hero-grid,.split{grid-template-columns:minmax(0,1fr)}
  .grid-4{grid-template-columns:repeat(2,minmax(0,1fr))}
  .grid-3{grid-template-columns:minmax(0,1fr)}
  .nav-links{display:none}
  .section{padding:72px 0}
  .stepper .step.hide-sm{display:none}
}
@media (max-width:640px){
  .container{padding:0 18px}
  .grid-2,.grid-4,.form-grid{grid-template-columns:minmax(0,1fr)}
  .sheet-pad{padding:22px}
  .cover{padding:34px 24px}
  .report-page{padding:32px 22px}
  .agent-card{grid-template-columns:34px minmax(0,1fr);}
  .agent-status{grid-column:1/-1;text-align:left}
  .route{padding-left:44px}.node{left:-36px}
  .map-label{display:none}
  .scene{aspect-ratio:1/1.15}
  .passport,.shortlist{display:none}
  .dossier{width:88%;left:6%}
  .boarding{right:4%;top:36%;width:70%}
  .globe-wrap{width:64%}
  .scene .stamp-abs{left:auto;right:6%;bottom:22%}
}
@media print{
  body::before,.no-print,.nav{display:none!important}
  .report-page{box-shadow:none;border:0;margin:0;page-break-after:always;width:100%}
}
@media (prefers-reduced-motion:reduce){
  html:not(.motion-on) *,html:not(.motion-on) *::before,html:not(.motion-on) *::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}
}
html.motion-off *,html.motion-off *::before,html.motion-off *::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}
"""

_BODY += r"""
/* ── Cursor + depth effects ── */
#cursor-ring{position:fixed;left:-18px;top:-18px;width:36px;height:36px;border:1.5px solid rgba(17,19,21,.55);border-radius:50%;pointer-events:none;z-index:300;opacity:0;
  transition:width .25s,height .25s,margin .25s,border-color .25s,background .25s,opacity .3s;will-change:transform}
#cursor-ring.hot{width:58px;height:58px;margin:-11px 0 0 -11px;border-color:var(--accent);background:rgba(91,155,213,.12)}
#cursor-ring.dark{border-color:rgba(246,242,234,.7)}
#cursor-ring.dark.hot{border-color:var(--accent)}
#cursor-dot{position:fixed;left:-3px;top:-3px;width:6px;height:6px;border-radius:50%;background:var(--accent-deep);pointer-events:none;z-index:301;opacity:0;transition:opacity .3s}
#cursor-dot.dark{background:var(--accent)}
.sheet::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;opacity:0;transition:opacity .35s;
  background:radial-gradient(380px circle at var(--mx,50%) var(--my,50%),rgba(255,255,255,.6),rgba(255,255,255,0) 62%)}
.sheet:hover::after{opacity:1}
.js .sheet.reveal{transform:perspective(1400px) rotateX(9deg) translateY(46px);transform-origin:50% 100%}
.js .sheet.reveal.in{transform:none}
.globe-dash{max-width:540px}
.globe-col{position:relative}
.chip{position:absolute;z-index:3;background:var(--ivory);color:var(--ink);padding:10px 14px 10px 16px;border-radius:2px;border-left:3px solid var(--accent);box-shadow:var(--shadow-on-navy);white-space:nowrap}
.chip b{display:block;font-family:var(--serif);font-size:22px;font-weight:600;line-height:1.1;margin-top:3px}
.globe3d.globe-mini{position:fixed;right:22px;bottom:22px;width:132px;aspect-ratio:1;z-index:45;pointer-events:none;opacity:0}
.globe-mini .globe-fallback{display:none}
.globe-fallback .m{transform-box:fill-box;transform-origin:center;animation:meridSpin 7s ease-in-out infinite}
.globe-fallback .rt{stroke-dasharray:5 6;animation:dashMove 1.6s linear infinite}
@keyframes meridSpin{0%,100%{transform:scaleX(1)}50%{transform:scaleX(.1)}}
@keyframes dashMove{to{stroke-dashoffset:-44}}
@media (max-width:980px){.chip{display:none}.globe-mini{width:96px}}
@media (pointer:coarse){#cursor-ring,#cursor-dot{display:none}}

/* ── Motion layer: globes, scroll reveal, chrome ── */
.globe3d{position:relative}
.globe3d canvas{position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity 1s ease;touch-action:pan-y}
.globe3d.live canvas{opacity:1}
.globe3d.live .globe-fallback{opacity:0}
.globe-dash{width:100%;max-width:470px;aspect-ratio:1;margin:0 auto}
.globe-dash .globe-fallback{position:absolute;inset:0}
.globe-hint{position:absolute;left:0;right:0;bottom:-6px;text-align:center}
.globe-band{position:absolute;right:-12%;top:50%;width:min(600px,58vw);aspect-ratio:1;transform:translateY(-50%);pointer-events:none;opacity:.95}
.globe-agents{position:absolute;right:-6%;top:8%;width:min(620px,70vw);aspect-ratio:1;pointer-events:none}
.globe-agents .globe-fallback,.globe-band .globe-fallback{position:absolute;inset:0}
.cover-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:32px;align-items:center;position:relative;z-index:2}
#scroll-progress{position:fixed;left:0;top:0;height:3px;width:100%;background:var(--accent);transform:scaleX(0);transform-origin:left;z-index:120;pointer-events:none}
.js .reveal{opacity:0;transform:translateY(34px) scale(.985);transition:opacity .9s cubic-bezier(.2,.7,.2,1),transform .9s cubic-bezier(.2,.7,.2,1);transition-delay:var(--d,0s)}
.js .reveal.in{opacity:1;transform:none}
.js .reveal .bar>i{transform:scaleX(0);transform-origin:left;transition:transform 1.3s cubic-bezier(.2,.7,.2,1) .3s}
.js .reveal.in .bar>i{transform:scaleX(1)}
.js .reveal .stacked-bar>div{transform:scaleX(0);transform-origin:left;transition:transform 1.1s cubic-bezier(.2,.7,.2,1) .3s}
.js .reveal.in .stacked-bar>div{transform:scaleX(1)}
.js .reveal .tier,.js .reveal table.plain tr{transition:opacity .6s ease .4s}
[data-tilt]{transform-style:preserve-3d;will-change:transform}
.section-index{position:fixed;right:22px;top:50%;transform:translateY(-50%);z-index:40;display:none;flex-direction:column;gap:14px;align-items:flex-end}
.section-index a{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate);text-decoration:none}
.section-index a i{width:8px;height:8px;border-radius:50%;border:1.5px solid var(--slate);background:var(--ivory);transition:all .3s}
.section-index a span{opacity:0;transform:translateX(6px);transition:all .3s;background:var(--ivory);padding:3px 8px;border:1px solid var(--rule);border-radius:2px;color:var(--ink)}
.section-index a:hover span,.section-index a.active span{opacity:1;transform:none}
.section-index a.active i{background:var(--accent);border-color:var(--accent);transform:scale(1.35)}
@media (min-width:1360px){.section-index{display:flex}}
@media (max-width:980px){.cover-grid{grid-template-columns:minmax(0,1fr)}.globe-band{opacity:.5;right:-30%}}
html.motion-off.js .reveal,html.motion-off.js .reveal .bar>i,html.motion-off.js .reveal .stacked-bar>div{opacity:1!important;transform:none!important}
#motion-toggle{position:fixed;left:auto!important;right:18px;top:auto;bottom:18px;z-index:130;font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;padding:9px 13px;background:var(--ivory);color:var(--ink);border:1px solid var(--rule-strong);border-radius:2px;cursor:pointer;box-shadow:var(--shadow-1)}
#motion-toggle:hover{border-color:var(--accent);color:var(--accent-deep)}
#motion-toggle.attn{border-color:var(--accent-deep);background:var(--accent-soft);color:var(--accent-deep);font-weight:600}
#debug-panel{position:fixed;left:18px;top:84px;z-index:400;background:var(--ink);color:var(--ivory);font:11px/1.6 var(--mono);padding:12px 14px;border-radius:3px;max-width:360px;white-space:pre-wrap}
@media (max-width:980px){.nav-inner{height:auto;min-height:74px;flex-wrap:wrap;padding-top:12px;padding-bottom:12px}.stepper{order:3;flex:1 1 100%;width:100%;padding-bottom:2px}.nav-logout{margin-left:auto;white-space:nowrap}}
@media (max-width:600px){#motion-toggle{right:12px;bottom:12px;max-width:calc(100vw - 24px);font-size:9px;padding:8px 10px}.nav-inner{gap:12px}.nav-logout{font-size:10px;padding:8px 10px}}
"""

EARLY_JS = (
    "(function(){var d=document.documentElement;d.classList.add('js');var p=null;"
    "try{p=localStorage.getItem('meridian-motion')}catch(e){}"
    "var os=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;"
    "d.classList.add((p==='on'||(p!=='off'&&!os))?'motion-on':'motion-off');})();"
)

GLOBAL_CSS = _ROOT + _BODY
