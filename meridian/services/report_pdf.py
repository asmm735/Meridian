"""Render the final report to PDF (ReportLab). Colours come from theme.py."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle

from .. import theme as T


AGENT_LABELS = {'profile': 'Profile overview', 'university': 'University matches',
                'program': 'Program recommendations', 'financial': 'Estimated costs',
                'scholarship': 'Scholarship opportunities', 'career': 'Career direction',
                'extracurricular': 'Experience strength'}


def result_status(results, key):
    if key in results:
        return 'Available'
    return 'Not available yet'


def document_summary(results):
    evidence = results.get('_documents', [])
    if not evidence:
        return 'No document text was used in this saved analysis. Results use structured profile inputs.'
    lines = []
    for item in evidence:
        lines.append(f"{item['name']}: document text was " +
                     ('used for relevance checks.' if item.get('consumed_by') else 'not used in the analysis.') +
                     (' Text was limited to the first 50,000 characters.' if item.get('truncated') else ''))
    return ' '.join(lines) + ' Documents inform text relevance only; grades, budgets and experience scores come from the saved profile.'


def saved_report_sections(results):
    """Format persisted outputs only; never fill absent results with demo values."""
    sections = []
    for key, title in AGENT_LABELS.items():
        data = results.get(key, {})
        lines = [result_status(results, key)]
        if data:
            if key == 'profile':
                lines.append('Candidate classification: ' + str(data.get('prediction')))
                if data.get('probability') is not None:
                    lines.append(f"Tier 1 class probability: {data['probability']:.1%}; not admission probability.")
            elif key == 'university':
                rows = data.get('matched_universities', [])
                lines.extend(f"{r.get('name')} | {r.get('country')} | selectivity band {r.get('tier')} | typical reported GPA {r.get('gpa', 'not available')} | profile fit {r.get('match_score', 'not available')}" for r in rows)
                if not rows:
                    lines.append('Completed with no matching universities.')
            elif key == 'program':
                lines.append('Programs are ranked by profile fit; this is not an admission prediction.')
                rows = data.get('programs', [])
                lines.extend(f"{i}. {r.get('university')} | {r.get('program_name')} | fit {float(r.get('specialization_fit_score', 0)) * 100:.0f}% | match {float(r.get('match_score', 0)) * 100:.0f}% | {r.get('duration') or 'Duration information is unavailable'} | {r.get('mode') or 'Study format information is unavailable'}" for i, r in enumerate(rows, 1))
                if not rows:
                    lines.append('Completed with no matching programs.')
                lines.extend(str(w) for w in data.get('programs_warnings', []))
            elif key == 'financial':
                for r in data.get('finance', []):
                    lines.append(f"{r.get('university')} | {r.get('program_name')} | annual tuition {r.get('tuition_annual')} | annual living {r.get('living_cost_annual')} | annual total {r.get('total_cost')} {r.get('currency', 'currency unspecified')}.")
                for r in data.get('finance_skipped', []):
                    lines.append(f"Cost information is unavailable for {r.get('university')} | {r.get('program_name')}.")
            elif key == 'scholarship':
                lines.append('Potential awards require confirmation of current eligibility, amount, and deadline with the provider.')
                for r in data.get('scholarships', []):
                    lines.append(f"{r.get('university')} | {r.get('program_name')} | funding gap {r.get('funding_gap') if r.get('funding_gap') is not None else 'unknown'} {r.get('currency', '')}")
                    for award in r.get('recommendations', []):
                        lines.append(f"{award.get('scholarship_name')} | potential coverage {award.get('potential_annual_coverage')} {award.get('currency')} | profile fit {float(award.get('match_score', 0)) * 100:.0f}% | deadline {award.get('deadline') or 'Confirm with provider'}")
                    for review in r.get('eligibility_review', []):
                        lines.append(f"Provider review: {review.get('scholarship_name')} | {review.get('eligibility_match')} | {', '.join(review.get('reasons', []))}")
            elif key == 'career':
                lines.append('Career paths are suggestions based on profile alignment, not employment guarantees.')
                for r in data.get('career_paths', []):
                    lines.append(f"{r.get('career_path')} | alignment {r.get('alignment_score')} | skill gaps: {', '.join(r.get('skill_gaps', [])) or 'none identified'}")
                lines.append(f"Model annual earnings estimate: {data.get('model_estimated_annual_earnings_usd', 'unavailable')} USD; not a salary guarantee.")
            elif key == 'extracurricular':
                lines.append(f"Strength tier: {data.get('strength_tier')} | strength score {data.get('profile_strength_score')} / 100 | achievement pattern {data.get('achievement_archetype')} | research evidence reported: {bool(data.get('has_research_evidence'))}")
        sections.append((title, lines))
    return sections


def render_saved_report_pdf(profile, results):
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    story = []
    def add(text, style='BodyText'):
        story.extend([Paragraph(escape(str(text)), styles[style]), Spacer(1, 7)])
    add('Meridian Study Abroad Report', 'Title')
    add(profile.get('full_name') or 'Student dossier', 'Heading1')
    add(' | '.join(f"{label}: {profile.get(key) or 'Not supplied'}" for label, key in (
        ('Email', 'email'), ('Degree', 'degree_goal'), ('Field', 'field'), ('Intake', 'intake'),
        ('Country', 'match_country'), ('GPA', 'gpa'), ('GPA scale', 'gpa_scale'))))
    add('Analysis summary', 'Heading1')
    add('Saved analysis: ' + str(results.get('_analysed_at', 'date unavailable')))
    add(f"{sum(key in results for key in AGENT_LABELS)} of 7 report sections are available. Missing sections are identified below.")
    add(document_summary(results))
    for title, lines in saved_report_sections(results):
        add(title, 'Heading1')
        for line in lines:
            add(line)
    add('These estimates are not guarantees of admission, funding, employment or salary. Verify costs and eligibility with the institution/provider.')
    SimpleDocTemplate(buffer, pagesize=A4, title='Meridian Study Abroad Report', author='Meridian').build(story)
    return buffer.getvalue()

INK, NAVY, IVORY = HexColor(T.INK), HexColor(T.NAVY), HexColor(T.IVORY)
PAPER, SLATE, ACCENT, ACCENT_DEEP = HexColor(T.PAPER), HexColor(T.SLATE), HexColor(T.ACCENT), HexColor(T.ACCENT_DEEP)

_LOGO = ImageReader(str(Path(__file__).with_name("logo_ivory.png")))

_S = {
    "h": ParagraphStyle("h", fontName="Times-Bold", fontSize=17, leading=20, textColor=INK, spaceBefore=2, spaceAfter=4),
    "eyebrow": ParagraphStyle("e", fontName="Courier-Bold", fontSize=7.5, leading=10, textColor=ACCENT_DEEP, spaceBefore=16, spaceAfter=2),
    "body": ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK, alignment=TA_LEFT),
    "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=9, leading=12, textColor=INK),
    "head": ParagraphStyle("th", fontName="Courier-Bold", fontSize=7, leading=9, textColor=SLATE),
    "key": ParagraphStyle("k", fontName="Times-Bold", fontSize=30, leading=34, textColor=ACCENT_DEEP),
}


def _page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(IVORY); canvas.rect(0, 0, w, h, stroke=0, fill=1)
    canvas.setFillColor(NAVY); canvas.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT); canvas.rect(0, h - 22 * mm, w, 1.2 * mm, stroke=0, fill=1)
    lw = 34 * mm
    canvas.drawImage(_LOGO, 20 * mm, h - 16.5 * mm, width=lw, height=lw * 637 / 2524, mask="auto")
    canvas.setFont("Courier", 7.5); canvas.setFillColor(PAPER)
    canvas.drawRightString(w - 20 * mm, h - 14 * mm, "STUDY ABROAD REPORT")
    canvas.setFillColor(SLATE); canvas.setFont("Courier", 7)
    canvas.drawString(20 * mm, 10 * mm, f"REPORT NO. {doc.report_no}")
    canvas.drawRightString(w - 20 * mm, 10 * mm, f"PAGE {doc.page}")
    canvas.restoreState()


def _section(title: str, no: str):
    return [Paragraph(f"SECTION {no}", _S["eyebrow"]), Paragraph(title, _S["h"])]


def _table(rows, widths, head=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [("LINEBELOW", (0, 0), (-1, -1), 0.3, SLATE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]
    if head:
        style.append(("LINEBELOW", (0, 0), (-1, 0), 0.8, INK))
    t.setStyle(TableStyle(style))
    return t


def render_report_pdf(report: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title="Meridian Study Abroad Report", author="Meridian")
    doc.report_no = report["student"]["report_no"]
    w, h = A4
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(20 * mm, 16 * mm, w - 40 * mm, h - 44 * mm, id="f")], onPage=_page)])
    s = report["student"]
    P = lambda t, st="cell": Paragraph(str(t), _S[st])  # noqa: E731
    H = lambda t: Paragraph(t, _S["head"])  # noqa: E731
    W = w - 40 * mm
    el = [Spacer(1, 4 * mm), Paragraph("YOUR PERSONAL DOSSIER", _S["eyebrow"]),
          Paragraph(s["name"], ParagraphStyle("n", fontName="Times-Bold", fontSize=30, leading=34, textColor=INK)), Spacer(1, 3 * mm),
          _table([[H("TARGET"), H("PROGRAM"), H("INTAKE")], [P(s["target"]), P(s["program"]), P(s["intake"])]], [W / 3] * 3)]

    ps = report["profile_strength"]
    el += _section("Profile strength", "01")
    el += [Paragraph(f"{ps['score']} / 100 - {ps['label']}", _S["key"]), Spacer(1, 2 * mm),
           _table([[H("DIMENSION"), H("SCORE")]] + [[P(d["name"]), P(d["score"])] for d in ps["dimensions"]], [W * .7, W * .3])]

    el += _section("University recommendations", "02")
    el += [_table([[H("UNIVERSITY"), H("PROGRAM"), H("TIER"), H("ADMIT"), H("TUITION")]] +
                  [[P(u["name"]), P(u["program"]), P(u["tier"]), P(u["prob_str"]), P(u["tuition_str"])] for u in report["universities"]],
                  [W * .32, W * .26, W * .14, W * .12, W * .16])]

    el += _section("Program matches", "03")
    el += [_table([[H("UNIVERSITY"), H("PROGRAM"), H("MATCH"), H("DURATION")]] +
                  [[P(p["university"]), P(p["program"]), P(p["match"]), P(p["duration"])] for p in report["programs"]],
                  [W * .22, W * .38, W * .14, W * .26])]

    f = report["financial"]
    el += _section("Cost breakdown", "04")
    if f.get("finance"):
        el += [P(f.get("notice", "Estimated costs are based on available university and program information."), "body"),
               _table([[H("UNIVERSITY"), H("PROGRAM"), H("TUITION"), H("LIVING"), H("TOTAL")]] +
                      [[P(row["university"]), P(row["program_name"]), P(row["tuition_annual"]),
                        P(row["living_cost_annual"]), P(row["total_cost"])] for row in f["finance"]],
                      [W * .22, W * .30, W * .16, W * .16, W * .16])]
    else:
        el += [Paragraph(f"{f['total_str']} per year", _S["key"]), P(f"Budget {f['budget_str']}  |  {f['gap_str']}"), Spacer(1, 2 * mm),
               _table([[H("ITEM"), H("ESTIMATE")]] + [[P(i["name"]), P(i["amount"])] for i in f["items"]], [W * .7, W * .3])]

    el += _section("Scholarships", "05")
    el += [_table([[H("AWARD"), H("VALUE"), H("FIT")]] + [[P(x["name"]), P(x["value"]), P(x["fit"])] for x in report["scholarships"]],
                  [W * .5, W * .32, W * .18])]

    c = report["career"]
    el += _section("Career alignment", "06")
    if c.get("career_paths"):
        el += [P(c.get("notice", "Rule-based career alignment; no employment outcome is asserted."), "body"), Spacer(1, 2 * mm),
               _table([[H("CAREER PATH"), H("ALIGNMENT"), H("SKILL GAPS")]] +
                      [[P(r["career_path"]), P(f"{r['alignment_score']}%"), P(", ".join(r["skill_gaps"]) or "None identified")]
                       for r in c["career_paths"]], [W * .42, W * .18, W * .40])]
    else:
        el += [P(c["summary"], "body"), Spacer(1, 2 * mm),
               _table([[H("ROLE"), H("FIT"), H("SALARY RANGE")]] + [[P(r["role"]), P(f"{r['fit']}%"), P(r["salary"])] for r in c["roles"]],
                      [W * .5, W * .15, W * .35])]

    e = report["extracurricular"]
    el += _section("Extracurricular strength", "07")
    el += [_table([[H("AREA"), H("SCORE")]] + [[P(i["name"]), P(i["score"])] for i in e["items"]], [W * .7, W * .3])]

    el += _section("Key model factors", "08")
    el += [_table([[H("FACTOR"), H("IMPACT")]] + [[P(k["name"]), P(k["impact"])] for k in report["key_factors"]], [W * .75, W * .25]),
           Spacer(1, 4 * mm), P(
               "Model outputs and source-based estimates are not guarantees of admission, funding, employment, or salary. "
               "Rows without verified source coverage are not inferred.",
               "body",
           )]
    doc.build(el)
    return buf.getvalue()
