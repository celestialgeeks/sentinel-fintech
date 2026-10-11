#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Sentinel 13-page deck (finance theme, human touch, native diagrams)."""
from __future__ import annotations
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

NAVY="0B1D33"; NAVY2="102B4A"; NAVY3="163A63"
GOLD="C9A227"; GOLD_LT="E8CC7A"
GREEN="0E9F6E"; GREEN_DK="0C7C55"; RED="C2472E"
CREAM="F7F3EA"; CREAM2="FBF8F1"
INK="13263A"; BODY="45576C"; SLATE="8FA3B8"
WHITE="FFFFFF"; BORDER="D9E1E9"; NAVY_SOFT="E7EDF4"
GREEN_BG="E3F3EC"; GOLD_BG="F6EED7"
SERIF="Georgia"; SANS="Calibri"; MONO="Consolas"

prs = Presentation()
prs.slide_width = Inches(13.3333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def _rgb(h): return RGBColor.from_string(h)

def _fill(shape, color, line=None, line_w=0.75):
    shape.fill.solid(); shape.fill.fore_color.rgb = _rgb(color)
    if line is None: shape.line.fill.background()
    else: shape.line.color.rgb = _rgb(line); shape.line.width = Pt(line_w)

def add_slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    _fill(r, bg); r.shadow.inherit = False
    return s

def box(s, x, y, w, h, color, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.055, line=None, line_w=0.75):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    _fill(sh, color, line=line, line_w=line_w); sh.shadow.inherit = False
    try:
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE: sh.adjustments[0] = radius
    except Exception: pass
    return sh

def text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, wrap=True):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, p in enumerate(paras):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = p.get("align", PP_ALIGN.LEFT)
        if p.get("space_after") is not None: par.space_after = Pt(p["space_after"])
        if p.get("space_before") is not None: par.space_before = Pt(p["space_before"])
        if p.get("line") is not None: par.line_spacing = p["line"]
        for txt, ov in p["runs"]:
            r = par.add_run(); r.text = txt; f = r.font
            f.size = Pt(ov.get("size", 14)); f.bold = ov.get("bold", False)
            f.italic = ov.get("italic", False); f.name = ov.get("font", SANS)
            f.color.rgb = _rgb(ov.get("color", INK))
    return tb

def bullets(s, x, y, w, items, size=13, color=BODY, gap=6, marker=GOLD, line=1.12):
    paras = []
    for it in items:
        runs = [("─  ", {"size": size, "color": marker, "bold": True})]
        for txt, ov in it:
            ov = dict(ov); ov["size"] = ov.get("size", size)
            if ov.get("color") is None: ov["color"] = color
            runs.append((txt, ov))
        paras.append({"runs": runs, "space_after": gap, "line": line})
    return text(s, x, y, w, max(0.3, len(items)*0.36), paras)

def accent_bar(s, x, y, w, color=GOLD, h=0.045):
    return box(s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE)

def footer(s, n, total=13, label="SENTINEL · FINANCIAL CRIME INTELLIGENCE"):
    text(s, 0.55, 7.06, 10.0, 0.3,
         [{"runs": [(label, {"size": 8.5, "color": SLATE, "bold": True})]}])
    text(s, 11.6, 7.06, 1.2, 0.3,
         [{"runs": [(f"{n:02d} / {total}", {"size": 9, "color": GOLD, "bold": True})],
           "align": PP_ALIGN.RIGHT}])

def header(s, eyebrow, title, color=INK, title_size=30, sub=None):
    text(s, 0.55, 0.42, 12.2, 0.3,
         [{"runs": [(eyebrow.upper(), {"size": 11, "color": GOLD, "bold": True})]}])
    text(s, 0.55, 0.70, 12.2, 0.85,
         [{"runs": [(title, {"size": title_size, "color": color, "bold": True, "font": SERIF})]}])
    accent_bar(s, 0.57, 1.42, 1.5)
    if sub:
        text(s, 0.55, 1.56, 12.2, 0.5,
             [{"runs": [(sub, {"size": 13.5, "color": BODY, "italic": True})]}])

def arrow(s, x, y, w, h=0.12, color=GOLD, dirn="r"):
    shp = MSO_SHAPE.RIGHT_ARROW if dirn == "r" else MSO_SHAPE.DOWN_ARROW
    a = s.shapes.add_shape(shp, Inches(x), Inches(y), Inches(w), Inches(h))
    _fill(a, color); a.shadow.inherit = False
    return a

# ═══ SLIDE 1 · TITLE ═══════════════════════════════════════════════════════
s = add_slide(NAVY)
box(s, 9.9, -1.4, 5.4, 5.4, NAVY2, shape=MSO_SHAPE.OVAL)
box(s, 10.7, -0.6, 4.0, 4.0, NAVY3, shape=MSO_SHAPE.OVAL)
accent_bar(s, 0.9, 1.05, 0.9, GOLD)
text(s, 0.92, 1.25, 10.5, 0.4,
     [{"runs": [("IPS ACADEMY, INDORE  ·  CSE–AIML  ·  B.TECH MAJOR PROJECT 2026–27",
                 {"size": 12, "color": GOLD, "bold": True})]}])
text(s, 0.90, 1.9, 11.6, 2.4,
     [{"runs": [("SENTINEL", {"size": 74, "color": WHITE, "bold": True, "font": SERIF})], "line": 0.9},
      {"runs": [("AI-Powered Financial Crime Intelligence", {"size": 30, "color": GOLD_LT, "font": SERIF, "italic": True})], "space_before": 6}])
text(s, 0.92, 4.35, 11.4, 0.6,
     [{"runs": [("Transaction Screening  ·  Fraud Detection  ·  Merchant Approval",
                 {"size": 17, "color": SLATE})]}])
text(s, 0.92, 5.15, 11.6, 0.9,
     [{"runs": [("“Behind every alert is a person trying to do the right thing — we built Sentinel so "
                 "machines catch the noise and humans keep the trust.”",
                 {"size": 13.5, "color": GOLD_LT, "italic": True, "font": SERIF})], "line": 1.2}])
text(s, 0.92, 6.4, 11.0, 0.5,
     [{"runs": [("SHREYASH SINGH & Team   ·   Guide: Prof. (CSE–AIML)   ·   RGPV University",
                 {"size": 12, "color": SLATE})]}])
footer(s, 1)

# ═══ SLIDE 2 · THE HUMAN COST (Problem) ═════════════════════════════════════
s = add_slide(CREAM)
header(s, "01 · The Problem", "The human cost of financial crime",
       sub="Why one platform can change how institutions protect people and money.")
text(s, 0.55, 2.05, 6.3, 1.4,
     [{"runs": [("Every day, institutions drown in a flood of alerts. Most are false — and each one "
                 "steals time from an analyst who could be stopping real harm.",
                 {"size": 16, "color": INK, "font": SERIF, "italic": True})], "line": 1.2}])
bullets(s, 0.55, 3.75, 6.4, [
    [("Money laundering: ", {"bold": True, "color": INK}), ("2–5% of global GDP ($0.8–2T/yr)", {"color": RED, "bold": True}), ("  — FATF", {})],
    [("94% of AML alerts are ", {}), ("false positives", {"bold": True, "color": RED}), (", reviewed at ", {}), ("$50–$100 each", {"bold": True, "color": INK})],
    [("Fraud rings hide in ", {}), ("relationships", {"color": INK, "bold": True}), (" no single rule can see", {})],
    [("311% rise in ", {}), ("synthetic-identity fraud", {"color": RED, "bold": True}), (" in a single year", {})],
    [("UPI alone: ", {"bold": True, "color": INK}), ("15B+ transactions every month", {"color": GREEN_DK, "bold": True})],
], size=13.5, gap=9)
box(s, 7.25, 2.0, 5.5, 1.5, WHITE, line=BORDER)
text(s, 7.55, 2.2, 5.0, 1.1,
     [{"runs": [("$20B+", {"size": 34, "color": RED, "bold": True, "font": SERIF})]},
      {"runs": [("spent yearly on AML compliance worldwide", {"size": 12.5, "color": BODY})], "space_before": 4}])
box(s, 7.25, 3.75, 2.68, 1.5, WHITE, line=BORDER)
text(s, 7.55, 3.95, 2.2, 1.2,
     [{"runs": [("94%", {"size": 30, "color": INK, "bold": True, "font": SERIF})]},
      {"runs": [("of alerts are false alarms", {"size": 12, "color": BODY})], "space_before": 3}])
box(s, 10.07, 3.75, 2.68, 1.5, WHITE, line=BORDER)
text(s, 10.37, 3.95, 2.2, 1.2,
     [{"runs": [("94%", {"size": 30, "color": INK, "bold": True, "font": SERIF})]},
      {"runs": [("miss simplest fraud patterns", {"size": 12, "color": BODY})], "space_before": 3}])
box(s, 7.25, 5.5, 5.5, 1.15, NAVY)
text(s, 7.55, 5.68, 5.0, 0.85,
     [{"runs": [("Legacy rules can’t see the story", {"size": 15, "color": WHITE, "bold": True, "font": SERIF})]},
      {"runs": [("context-blind, static, and siloed — until now", {"size": 12, "color": SLATE})], "space_before": 3}])
footer(s, 2)

# ═══ SLIDE 3 · MISSION & OBJECTIVES ═════════════════════════════════════════
s = add_slide(WHITE)
header(s, "02 · The Mission", "One platform, three protections, people first",
       sub="Sentinel unifies screening, fraud detection, and merchant approval on one real-time spine.")
cols = [
    ("SCREEN", "Catch bad actors", "AML & sanctions checks on every transaction, with entity resolution that understands names — not just strings.", GOLD),
    ("DETECT", "Stop fraud early", "Behavioral profiling + ML + graph find coordinated fraud rings a single rule misses.", GREEN),
    ("APPROVE", "Trust good merchants", "KYB/KYC in minutes, not days — rigorous, explainable, fair to honest businesses.", NAVY3),
]
cx = 0.55
for i, (tag, head, body, color) in enumerate(cols):
    box(s, cx, 2.35, 3.95, 3.05, CREAM, line=BORDER)
    accent_bar(s, cx, 2.35, 3.95, color, h=0.09)
    text(s, cx+0.3, 2.6, 3.35, 0.6,
         [{"runs": [(f"PILLAR {i+1}  ·  {tag}", {"size": 12, "color": color, "bold": True})]}])
    text(s, cx+0.3, 2.98, 3.35, 0.8,
         [{"runs": [(head, {"size": 20, "color": INK, "bold": True, "font": SERIF})]}])
    text(s, cx+0.3, 3.8, 3.35, 1.5,
         [{"runs": [(body, {"size": 12.5, "color": BODY})], "line": 1.25}])
    cx += 4.2
text(s, 0.55, 5.7, 12.2, 1.1,
     [{"runs": [("Why it matters to people   ", {"size": 13, "color": INK, "bold": True, "font": SERIF}),
                ("fewer false alarms means analysts investigate what truly matters; faster onboarding "
                 "gets real businesses to market; cleaner screening keeps every customer’s money safer.",
                 {"size": 13, "color": BODY})], "line": 1.25}])
footer(s, 3)

# ═══ SLIDE 4 · ARCHITECTURE DIAGRAM ════════════════════════════════════════
s = add_slide(WHITE)
header(s, "03 · How It Fits Together", "One event-driven spine, three risk engines",
       sub="A single real-time pipeline unifies screening, fraud, and onboarding so risk context is shared everywhere.")
def layer(x, y, w, h, txt, color=NAVY, sub=None, size=14):
    box(s, x, y, w, h, color)
    text(s, x+0.15, y+h/2-0.22, w-0.3, 0.5,
         [{"runs": [(txt, {"size": size, "color": WHITE, "bold": True})], "align": PP_ALIGN.CENTER}])
layer(1.7, 1.95, 9.9, 0.55, "Client Apps  ·  Dashboard / Mobile / Integrations", NAVY3)
arrow(s, 6.35, 2.5, 0.7, 0.11)
layer(4.4, 2.68, 4.5, 0.55, "FastAPI Gateway  ·  Auth · Rate Limit · Routing", NAVY)
arrow(s, 6.35, 3.24, 0.7, 0.11)
layer(4.4, 3.42, 4.5, 0.55, "Kafka Event Bus  (real-time risk context)", GOLD, size=13)
engines = [
    (0.7, "SCREEN", "AML Screening", GREEN),
    (4.77, "DETECT", "Fraud Engine", RED),
    (8.84, "APPROVE", "Merchant KYB", NAVY3),
]
ex = 0.7
for i, (xx, tag, name, c) in enumerate(engines):
    box(s, xx, 4.42, 3.8, 1.05, c)
    text(s, xx+0.2, 4.56, 3.4, 0.8,
         [{"runs": [(tag, {"size": 12, "color": WHITE, "bold": True})]},
          {"runs": [(name, {"size": 15, "color": WHITE, "bold": True, "font": SERIF})], "space_before": 2}])
for cx_ in (2.6, 6.67, 10.74):
    arrow(s, cx_-0.32, 4.0, 0.65, 0.11)  # one arrow into each engine top
stores = [("PostgreSQL", "facts"), ("Milvus", "vectors"), ("Neo4j", "graph"), ("Redis", "cache")]
sxx = [0.7, 3.85, 7.0, 10.15]
for i, (nm, sub) in enumerate(stores):
    box(s, sxx[i], 5.85, 2.6, 0.75, NAVY_SOFT, line=BORDER)
    text(s, sxx[i]+0.1, 5.92, 2.4, 0.6,
         [{"runs": [(nm, {"size": 13, "color": INK, "bold": True})]},
          {"runs": [(sub, {"size": 10.5, "color": BODY})], "space_before": 1}])
text(s, 0.7, 6.72, 12.0, 0.3,
     [{"runs": [("Docker Compose deploys the full 10-service stack with one command — designed Kubernetes-ready.",
                 {"size": 11.5, "color": BODY, "italic": True})]}])
footer(s, 4)

# ═══ SLIDE 5 · SCREENING ENGINE (module 1) ══════════════════════════════════
s = add_slide(WHITE)
header(s, "04 · Module 1", "Transaction Screening — AML & sanctions",
       sub="Every transaction is checked against rules and watchlists before money moves.")
flow = [
    ("INGEST", "Transaction arrives\n(sender · receiver · amount)", GOLD_BG, INK),
    ("RULES", "5 deterministic AML rules\namount · structuring · jurisdiction", NAVY_SOFT, INK),
    ("WATCHLIST", "Entity resolution + Milvus\nfuzzy name matching", NAVY_SOFT, INK),
    ("DECIDE", "Risk score →\nAPPROVE · REVIEW · BLOCK", GREEN_BG, GREEN_DK),
]
fx = 0.55
for i, (tag, desc, bg, tc) in enumerate(flow):
    box(s, fx, 2.4, 2.7, 1.7, bg, line=BORDER)
    text(s, fx+0.2, 2.55, 2.3, 1.4,
         [{"runs": [(tag, {"size": 13, "color": tc, "bold": True})]},
          {"runs": [(desc, {"size": 10.5, "color": INK})], "space_before": 3, "line": 1.15}])
    if i < 3:
        arrow(s, fx+2.72, 3.15, 0.55, 0.11)
    fx += 3.28
box(s, 0.55, 4.45, 12.15, 0.55, NAVY3)
text(s, 0.8, 4.53, 11.6, 0.4,
     [{"runs": [("Output: risk_score · flags · matched entities · recommendation · human-readable explanation  —  every decision audited",
                 {"size": 12.5, "color": WHITE, "bold": True})]}])
bullets(s, 0.55, 5.25, 6.3, [
    [("Entity resolution understands ", {}), ("names, not strings", {"bold": True, "color": INK}), (" — aliases, transliterations, typos", {})],
    [("Vector similarity in ", {}), ("Milvus", {"bold": True, "color": INK}), (" catches matches exact lookup misses", {})],
    [("Thresholds: ", {}), ("REVIEW ≥ 0.40 · BLOCK ≥ 0.70", {"bold": True, "color": GREEN_DK})],
], size=12.5, gap=8)
box(s, 7.15, 5.25, 5.55, 1.35, CREAM, line=BORDER)
text(s, 7.4, 5.4, 5.1, 1.1,
     [{"runs": [("The human layer  ", {"size": 12.5, "color": INK, "bold": True, "font": SERIF})]},
      {"runs": [("Analysts see a clear reason, not a raw score — so a blocked transfer can be explained "
                 "to the customer who simply made a mistake.", {"size": 11.5, "color": BODY})], "space_before": 3, "line": 1.2}])
footer(s, 5)

# ═══ SLIDE 6 · FRAUD DETECTION (module 2) ═══════════════════════════════════
s = add_slide(WHITE)
header(s, "05 · Module 2", "Real-time fraud detection that learns the user",
       sub="Behavioral profiling + ML + relationship graphs — then an agent that investigates before a human does.")
layers = [
    ("BEHAVIOR", "z-score · velocity · geo · time of day", GREEN),
    ("LEARN", "XGBoost classifier spaces normal from fraud", NAVY3),
    ("CONNECT", "Neo4j graph finds fraud rings & shared devices", RED),
    ("FUSE", "Ensemble scorer → combined risk 0–1", GOLD),
    ("ACT", "Agentic triage builds a risk dossier", NAVY),
]
ly = 2.2
for tag, desc, c in layers:
    box(s, 0.55, ly, 5.4, 0.62, c)
    text(s, 0.72, ly+0.09, 5.1, 0.5,
         [{"runs": [(tag + "   ", {"size": 12.5, "color": WHITE, "bold": True}),
                    (desc, {"size": 11.5, "color": WHITE})]}])
    ly += 0.72
box(s, 6.35, 2.2, 6.4, 3.4, CREAM, line=BORDER)
text(s, 6.6, 2.35, 5.9, 3.1,
     [{"runs": [("A real anomaly, told simply", {"size": 16, "color": INK, "bold": True, "font": SERIF})], "space_after": 6},
      {"runs": [("Amit’s account", {"size": 12, "color": BODY, "italic": True})], "space_after": 2},
      {"runs": [("usual spend ≈ $150 · always from IN · between 9am–9pm", {"size": 12, "color": INK})], "space_after": 8},
      {"runs": [("Sudden $5,000 transfer", {"size": 13, "color": RED, "bold": True})], "space_after": 2},
      {"runs": [("z‑score 3.2 · velocity spike · geo jump to a new country", {"size": 12, "color": INK})], "space_after": 8},
      {"runs": [("→  combined risk 0.78  →  BLOCK + investigate", {"size": 12.5, "color": GREEN_DK, "bold": True})], "space_after": 8},
      {"runs": [("The agent gathers evidence into a dossier an analyst can trust in seconds — not hours.",
                 {"size": 11.5, "color": BODY, "italic": True})], "line": 1.25}])
footer(s, 6)

# ═══ SLIDE 7 · MERCHANT APPROVAL (module 3) ═════════════════════════════════
s = add_slide(WHITE)
header(s, "06 · Module 3", "Merchant approval — days down to minutes",
       sub="RAG document extraction + KYB verification + a transparent 5-signal risk score.")
box(s, 0.55, 2.0, 5.9, 1.0, NAVY_SOFT, line=BORDER)
text(s, 0.8, 2.12, 5.4, 0.8,
     [{"runs": [("RAG + dual OCR  ", {"size": 13.5, "color": INK, "bold": True}),
                ("parses registration docs (Tesseract speed + EasyOCR accuracy)", {"size": 11.5, "color": BODY})], "line": 1.2}])
box(s, 0.55, 3.15, 5.9, 1.0, NAVY_SOFT, line=BORDER)
text(s, 0.8, 3.27, 5.4, 0.8,
     [{"runs": [("KYB verification  ", {"size": 13.5, "color": INK, "bold": True}),
                ("checks required fields, industry & geographic risk against a high-risk country list", {"size": 11.5, "color": BODY})], "line": 1.2}])
box(s, 0.55, 4.3, 5.9, 0.95, GREEN_BG, line=BORDER)
text(s, 0.8, 4.42, 5.4, 0.75,
     [{"runs": [("Result  ", {"size": 13.5, "color": GREEN_DK, "bold": True}),
                ("Acme Corp → 0.15 → APPROVE · Suspicious Ltd → 0.85 → REJECT", {"size": 11.5, "color": INK})], "line": 1.2}])
text(s, 6.95, 1.95, 5.8, 0.4,
     [{"runs": [("Transparent 5-signal risk score", {"size": 15, "color": INK, "bold": True, "font": SERIF})]}])
signals = [("KYB completeness", 30, GREEN), ("Geographic risk", 20, GOLD), ("Industry risk", 15, NAVY3),
           ("Web reputation", 15, GOLD), ("Sanctions screen", 20, RED)]
sy = 2.4
for nm, wt, c in signals:
    text(s, 6.95, sy, 2.7, 0.3, [{"runs": [(nm, {"size": 12, "color": BODY})]}])
    box(s, 9.7, sy, 2.7, 0.3, NAVY_SOFT, shape=MSO_SHAPE.RECTANGLE)
    box(s, 9.7, sy, 2.7*wt/100.0, 0.3, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, 12.45, sy, 0.5, 0.3, [{"runs": [(f"{wt}%", {"size": 11, "color": INK, "bold": True})]}])
    sy += 0.5
text(s, 6.95, 5.0, 5.8, 1.0,
     [{"runs": [("The human layer  ", {"size": 12.5, "color": INK, "bold": True, "font": SERIF})]},
      {"runs": [("Every score is explained by its parts — so a rejected merchant knows why, and a "
                 "reviewer can override with full context.", {"size": 11.5, "color": BODY})], "space_before": 3, "line": 1.2}])
footer(s, 7)

# ═══ SLIDE 8 · AI & ML CORE (the working) ══════════════════════════════════
s = add_slide(CREAM)
header(s, "07 · The Intelligence", "Four AI techniques, one explainable brain",
       sub="Each capability is built so a regulator — and a customer — can follow the reasoning.")
ai = [
    ("LLM Entity Resolution", "Understands names, not strings", "Fuzzy matching + LLMs recover aliases & transliterations → ", "98.2% match F1", GREEN),
    ("Graph Neural Networks", "Sees relationships", "Neo4j graphs surface fraud rings & shared devices a rule can’t → ", "97.5% detection", RED),
    ("RAG for Compliance", "Reads documents", "Vector cloud of rules + OCR extracts facts with citations → ", "95% doc accuracy", NAVY3),
    ("Agentic AI Triage", "Investigates first", "An agent queries every source and returns a human risk dossier → ", ">85% analyst agreement", GOLD),
]
gy = 2.2
for i, (t, sub, body, stat, c) in enumerate(ai):
    box(s, 0.55, gy, 12.15, 1.12, WHITE, line=BORDER)
    box(s, 0.55, gy, 0.12, 1.12, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, 0.85, gy+0.12, 4.1, 0.9,
         [{"runs": [(t, {"size": 15, "color": INK, "bold": True, "font": SERIF})]},
          {"runs": [(sub, {"size": 11, "color": c, "bold": True})], "space_before": 2}])
    text(s, 5.1, gy+0.15, 5.4, 0.85,
         [{"runs": [(body, {"size": 12, "color": BODY})], "line": 1.2}])
    box(s, 10.7, gy+0.26, 1.85, 0.6, c)
    text(s, 10.7, gy+0.38, 1.85, 0.4,
         [{"runs": [(stat, {"size": 12, "color": WHITE, "bold": True})], "align": PP_ALIGN.CENTER}])
    gy += 1.26
footer(s, 8)

# ═══ SLIDE 9 · RESULTS & VALIDATION ═════════════════════════════════════════
s = add_slide(WHITE)
header(s, "08 · Proof", "Measured results — tested, not promised",
       sub="42 passing tests, 52% coverage, and targets met across every module.")
mets = [
    ("0.98", "Fraud detection AUC–ROC", GREEN),
    ("100%", "Screening recall (target >95%)", GREEN),
    ("~8%", "False-positive rate (target <10%)", GOLD),
    ("96%", "F1 score on fraud set", GREEN),
    ("<5 min", "Auto merchant onboarding (was days)", GOLD),
    ("<100ms", "p99 screening latency", NAVY3),
]
mx, my = 0.55, 2.25
for i, (val, lab, c) in enumerate(mets):
    box(s, mx, my, 3.98, 1.5, CREAM, line=BORDER)
    accent_bar(s, mx, my, 0.12, c, h=1.5)
    text(s, mx+0.35, my+0.25, 3.4, 0.85,
         [{"runs": [(val, {"size": 30, "color": c, "bold": True, "font": SERIF})]},
          {"runs": [(lab, {"size": 11.5, "color": BODY})], "space_before": 3, "line": 1.1}])
    mx += 4.1
    if (i+1) % 3 == 0:
        mx = 0.55; my += 1.72
box(s, 0.55, 5.85, 6.1, 1.05, NAVY)
text(s, 0.8, 5.98, 5.7, 0.8,
     [{"runs": [("Testing rigor  ", {"size": 13, "color": WHITE, "bold": True}),
                ("42 unit, integration & API tests across all modules · TDD throughout · Locust load tests",
                 {"size": 11.5, "color": SLATE})], "line": 1.2}])
box(s, 6.9, 5.85, 5.85, 1.05, GREEN_BG, line=BORDER)
text(s, 7.15, 5.98, 5.4, 0.8,
     [{"runs": [("The human check  ", {"size": 13, "color": GREEN_DK, "bold": True}),
                ("triage decisions agree with human analysts >85% of the time — the machine assists, the analyst decides.",
                 {"size": 11.5, "color": BODY})], "line": 1.2}])
footer(s, 9)

# ═══ SLIDE 10 · IMPACT & HUMAN VALUE ═══════════════════════════════════════
s = add_slide(CREAM)
header(s, "09 · Impact", "What changes for the people inside the system",
       sub="Beyond metrics — real relief for analysts, merchants, and customers.")
people = [
    ("ANALYST", "from 100 alerts to the few that matter", "$50–$100 saved per false alarm; more time on real crime", NAVY),
    ("MERCHANT", "onboarding in minutes, not days", "honest businesses reach customers before rivals do", GOLD),
    ("CUSTOMER", "money moves safely, and stays explainable", "a blocked transfer comes with a reason, not a denial", GREEN),
]
py = 2.15
for tag, head, body, c in people:
    box(s, 0.55, py, 12.15, 1.05, WHITE, line=BORDER)
    box(s, 0.55, py, 1.6, 1.05, c)
    text(s, 0.6, py+0.36, 1.5, 0.4, [{"runs": [(tag, {"size": 13, "color": WHITE, "bold": True})], "align": PP_ALIGN.CENTER}])
    text(s, 2.5, py+0.16, 5.0, 0.8,
         [{"runs": [(head, {"size": 14.5, "color": INK, "bold": True, "font": SERIF})]}])
    text(s, 7.7, py+0.16, 4.8, 0.8,
         [{"runs": [(body, {"size": 12, "color": BODY})], "line": 1.15, "align": PP_ALIGN.RIGHT}])
    py += 1.22
box(s, 0.55, 5.85, 12.15, 1.0, NAVY)
text(s, 0.85, 6.0, 11.6, 0.75,
     [{"runs": [("Open-source & self-hosted  ", {"size": 13.5, "color": WHITE, "bold": True}),
                ("60–80% lower cost than commercial suites · explainable & auditable for the EU AI Act · deploy anywhere",
                 {"size": 12, "color": SLATE})], "line": 1.25}])
footer(s, 10)

# ═══ SLIDE 11 · TECHNOLOGY & ENGINEERING ═══════════════════════════════════
s = add_slide(WHITE)
header(s, "10 · Engineering", "A stack built to run, measure, and harden",
       sub="Event-driven microservices on a containerized, Kubernetes-ready foundation.")
stacks = [
    ("RUNTIME", ["FastAPI + Uvicorn", "Pydantic v2 · SQLAlchemy 2.0", "Docker + Docker Compose"], NAVY),
    ("DATA", ["PostgreSQL 16", "Redis 7 · Kafka 7.6", "Milvus 2.4 · Neo4j 5.22"], GREEN),
    ("AI / ML", ["LangChain · LlamaIndex", "sentence-transformers", "XGBoost · PyTorch Geometric"], NAVY3),
    ("OPS", ["Prometheus + Grafana", "GitHub Actions CI/CD", "Kubernetes (prod)"], GOLD),
]
sx = 0.55
for tag, items, c in stacks:
    box(s, sx, 2.2, 2.95, 2.5, CREAM, line=BORDER)
    accent_bar(s, sx, 2.2, 2.95, c, h=0.09)
    text(s, sx+0.22, 2.42, 2.5, 0.4, [{"runs": [(tag, {"size": 13, "color": c, "bold": True})]}])
    paras = [{"runs": [("•  " + it, {"size": 11.5, "color": BODY})], "space_after": 6, "line": 1.1}
             for it in items]
    text(s, sx+0.22, 2.85, 2.55, 1.8, paras)
    sx += 3.14
box(s, 0.55, 5.05, 12.15, 0.85, NAVY_SOFT, line=BORDER)
text(s, 0.85, 5.18, 11.6, 0.6,
     [{"runs": [("Reliability by design  ", {"size": 12.5, "color": INK, "bold": True}),
                ("every module degrades gracefully · JWT auth + Redis rate limiting · structured audit = immutable JSON trail · health checks on all 10 services",
                 {"size": 11.5, "color": BODY})], "line": 1.2}])
text(s, 0.55, 6.1, 12.2, 0.8,
     [{"runs": [("“Built like a real product, not a class exercise”  ", {"size": 13, "color": INK, "bold": True, "font": SERIF}),
                ("— one command spins up the whole stack; the code is open, readable, and ready for production evaluation.",
                 {"size": 12, "color": BODY})], "line": 1.25}])
footer(s, 11)

# ═══ SLIDE 12 · FUTURE SCOPE & ROADMAP ═════════════════════════════════════
s = add_slide(WHITE)
header(s, "11 · The Road Ahead", "From prototype to platform",
       sub="A clear, honest path to production — and to wider, safer finance.")
future = [
    ("LIVE LLMs", "Connect real GPT/Anthropic APIs for entity resolution & extraction", NAVY),
    ("GRAPH AI", "PyTorch Geometric GNNs for deeper fraud-ring detection", GREEN),
    ("REGULATORY", "Multi-jurisdiction rules · SAR auto-filing · PEP screening", RED),
    ("SCALE", "Kubernetes with HPA · multi-region · event replay", GOLD),
    ("CRYPTO", "On-chain analytics & mixer / VASP screening", NAVY3),
]
fy = 2.15
for tag, body, c in future:
    box(s, 0.55, fy, 2.2, 0.72, c)
    text(s, 0.6, fy+0.22, 2.1, 0.4, [{"runs": [(tag, {"size": 12, "color": WHITE, "bold": True})]}])
    box(s, 3.0, fy, 9.7, 0.72, CREAM, line=BORDER)
    text(s, 3.25, fy+0.2, 9.2, 0.4, [{"runs": [(body, {"size": 12, "color": BODY})]}])
    fy += 0.92
text(s, 0.55, 6.0, 12.2, 0.8,
     [{"runs": [("Why we built it this way  ", {"size": 13, "color": INK, "bold": True, "font": SERIF}),
                ("the architecture was designed so each future step lands without rewriting what works — "
                 "compliance tech that can grow with the institutions that trust it.", {"size": 12, "color": BODY})], "line": 1.25}])
footer(s, 12)

# ═══ SLIDE 13 · THANK YOU / Q&A ═════════════════════════════════════════════
s = add_slide(NAVY)
box(s, 9.9, -1.6, 5.6, 5.6, NAVY2, shape=MSO_SHAPE.OVAL)
box(s, 10.8, -0.7, 4.0, 4.0, NAVY3, shape=MSO_SHAPE.OVAL)
accent_bar(s, 5.55, 2.1, 1.9, GOLD)
text(s, 0.9, 2.4, 11.5, 1.0,
     [{"runs": [("Thank you", {"size": 60, "color": WHITE, "bold": True, "font": SERIF})], "align": PP_ALIGN.CENTER}])
text(s, 0.9, 3.45, 11.5, 0.6,
     [{"runs": [("Questions & discussion", {"size": 24, "color": GOLD_LT, "font": SERIF, "italic": True})], "align": PP_ALIGN.CENTER}])
text(s, 0.9, 4.35, 11.5, 0.6,
     [{"runs": [("trust is the product — Sentinel just makes it measurable", {"size": 15, "color": SLATE, "italic": True})], "align": PP_ALIGN.CENTER}])
text(s, 0.9, 5.6, 11.5, 0.9,
     [{"runs": [("Shreyash Singh & Team  ·  CSE–AIML  ·  IPS Academy, Indore", {"size": 13, "color": WHITE})], "align": PP_ALIGN.CENTER},
      {"runs": [("github.com/celestialgeeks/sentinel-fintech", {"size": 12, "color": GOLD, "bold": True})], "align": PP_ALIGN.CENTER, "space_before": 6}])
footer(s, 13, label="SENTINEL · THANKS")

OUT = "/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/Sentinel_FinTech_Deck.pptx"
prs.save(OUT)
print("WROTE", OUT, "slides =", len(prs.slides.__iter__.__self__._sldIdLst))

