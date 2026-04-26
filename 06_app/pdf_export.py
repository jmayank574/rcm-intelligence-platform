from datetime import date

import pandas as pd
from fpdf import FPDF

# National benchmark approximations (CMS Medicare FY 2024)
_NAT_CTP       = 3.5
_NAT_UNDERPAY  = 30.0
_NAT_MORTALITY = 12.0
_NAT_RECOMMEND = 70.0

GRADE_COLORS_RGB = {
    "A — Excellent":     ( 22, 163,  74),
    "B — Good":          ( 37,  99, 235),
    "C — Average":       (217, 119,   6),
    "D — Below Average": (234,  88,  12),
    "F — Critical":      (220,  38,  38),
    "Insufficient Data": (148, 163, 184),
}

_LEVEL_COLORS = {
    "critical": (220,  38,  38),
    "warning":  (217, 119,   6),
    "good":     ( 22, 163,  74),
    "info":     ( 37,  99, 235),
}

_LEVEL_BG = {
    "critical": (255, 241, 242),
    "warning":  (255, 247, 237),
    "good":     (240, 253, 244),
    "info":     (239, 246, 255),
}


def _safe(val, default="N/A"):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return str(default)
    s = str(val)
    for ch, repl in {
        "—": "-", "–": "-",
        "’": "'", "‘": "'",
        "“": '"', "”": '"',
        "•": "*", "·": ".",
        "★": "*", "☆": "*",
        "▲": "^", "▼": "v",
        "·": ".", "®": "(R)",
    }.items():
        s = s.replace(ch, repl)
    return s.encode("latin-1", "replace").decode("latin-1")


def _grade_rgb(grade):
    return GRADE_COLORS_RGB.get(str(grade), (148, 163, 184))


def _fval(d, key):
    v = d.get(key)
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _ival(d, key):
    f = _fval(d, key)
    return None if f is None else int(f)


# ── Narrative generators ──────────────────────────────────────────────────────

def _penalty_conds(hosp: dict) -> list:
    return [name for key, name in [
        ("hf_penalty_flag",  "Heart Failure"),
        ("pn_penalty_flag",  "Pneumonia"),
        ("ami_penalty_flag", "AMI"),
    ] if _ival(hosp, key) == 1]


def _gen_executive_summary(hosp: dict, drg_data: pd.DataFrame, hr_pct: float) -> str:
    name  = hosp.get("provider_name", "This hospital")
    state = hosp.get("provider_state", "")
    grade = str(hosp.get("hospital_360_grade", "?")).strip()[0].upper()
    rcm_g = str(hosp.get("rcm_health_grade",   "?")).strip()[0].upper()
    score = _fval(hosp, "hospital_360_score")
    gap_b = _fval(hosp, "combined_revenue_gap_billions")
    pen   = _ival(hosp, "penalty_count")
    ctp   = _fval(hosp, "inpatient_avg_ctp")

    score_str = f"scoring {score:.0f}/100 " if score else ""
    s1 = (f"{_safe(name)} ({_safe(state)}) holds a {grade} overall performance grade "
          f"{score_str}with an RCM health grade of {rcm_g}.")

    if gap_b is not None:
        sev    = "significant" if gap_b > 0.15 else "moderate" if gap_b > 0.05 else "low"
        driver = ("charge-to-payment ratio pressure"
                  if ctp and ctp > _NAT_CTP else "underpayment and coding variances")
        s2 = (f"The hospital carries {sev} revenue risk with an estimated "
              f"${gap_b:.2f}B in annual revenue gap, driven primarily by {driver}.")
    else:
        s2 = "Revenue gap data is not fully available for this reporting period."

    if hr_pct > 33:
        s3 = (f"Claim denial risk is elevated: {hr_pct:.1f}% of claims are flagged high-risk, "
              f"suggesting systematic documentation or coding issues requiring immediate review.")
    elif hr_pct > 15:
        s3 = (f"Claim denial risk is moderate at {hr_pct:.1f}% high-risk claims; "
              f"targeted CDI improvements are expected to recover meaningful at-risk revenue.")
    else:
        s3 = (f"Claim denial exposure is within acceptable range at {hr_pct:.1f}% high-risk claims, "
              f"though ongoing monitoring is recommended.")

    if pen and pen >= 1:
        conds     = _penalty_conds(hosp)
        cond_str  = ", ".join(conds) if conds else f"{pen} condition(s)"
        s4 = (f"Active CMS HRRP penalties for {cond_str} are compounding financial exposure "
              f"and signal readmission reduction as a near-term priority.")
    else:
        s4 = ("No active CMS HRRP penalties were recorded, a positive indicator for "
              "quality and reimbursement stability.")

    return " ".join([s1, s2, s3, s4])


def _gen_financial_narrative(hosp: dict, drg_data: pd.DataFrame, peer: dict) -> str:
    ctp    = _fval(hosp, "inpatient_avg_ctp")
    undpay = _fval(hosp, "inpatient_underpayment_rate")
    parts  = []

    if ctp is not None:
        ratio = ctp / _NAT_CTP
        if ratio > 1.3:
            parts.append(
                f"The charge-to-payment ratio of {ctp:.2f}x is "
                f"{((ratio - 1) * 100):.0f}% above the national average ({_NAT_CTP:.1f}x), "
                f"indicating negotiated payer rates may not reflect actual claim complexity. "
                f"A contract renegotiation analysis targeting top DRGs is warranted.")
        elif ratio > 1.1:
            parts.append(
                f"The CTP ratio of {ctp:.2f}x sits modestly above the national norm ({_NAT_CTP:.1f}x), "
                f"suggesting room to improve payer contract terms for high-volume DRGs.")
        else:
            parts.append(
                f"The CTP ratio of {ctp:.2f}x is in line with the national average ({_NAT_CTP:.1f}x), "
                f"reflecting adequate payer contract alignment.")

    if undpay is not None:
        if undpay > 50:
            parts.append(
                f"An underpayment rate of {undpay:.1f}% - well above the national benchmark of "
                f"{_NAT_UNDERPAY:.0f}% - suggests persistent payer shortfalls recoverable through "
                f"systematic claim auditing and appeals.")
        elif undpay > _NAT_UNDERPAY:
            parts.append(
                f"The underpayment rate of {undpay:.1f}% exceeds national norms ({_NAT_UNDERPAY:.0f}%), "
                f"pointing to payer contract variances worth addressing in the next renewal cycle.")
        else:
            parts.append(
                f"Underpayment exposure ({undpay:.1f}%) is below the national average, "
                f"reflecting healthy payer contract performance.")

    if not drg_data.empty:
        top      = drg_data.iloc[0]
        drg_desc = _safe(str(top.get("drg_description", "")))[:45]
        drg_gap  = _fval(top, "revenue_gap_pct") if hasattr(top, "get") else None
        try:
            drg_gap = float(top.get("revenue_gap_pct"))
        except (TypeError, ValueError):
            drg_gap = None
        if drg_gap:
            parts.append(
                f"The highest-volume DRG ({drg_desc}) carries a {drg_gap:.1f}% revenue gap, "
                f"representing the primary opportunity for targeted coding review.")

    return " ".join(parts) if parts else "Financial performance data is being compiled for this reporting period."


def _gen_clinical_narrative(hosp: dict) -> str:
    mort   = _fval(hosp, "avg_mortality_rate")
    readm  = _fval(hosp, "avg_excess_readmission_ratio")
    better = _ival(hosp, "better_mortality_flag")
    worse  = _ival(hosp, "worse_mortality_flag")
    parts  = []

    if mort is not None:
        if better == 1:
            parts.append(
                f"30-day mortality rate ({mort:.1f}%) is rated better than the national average, "
                f"a strong quality indicator supporting outcomes and value-based care reimbursement.")
        elif worse == 1:
            parts.append(
                f"30-day mortality rate ({mort:.1f}%) is flagged as worse than national, "
                f"a critical signal requiring clinical protocol review and potentially contributing "
                f"to quality-based payment reductions.")
        else:
            parts.append(
                f"30-day mortality rate ({mort:.1f}%) is similar to the national average, "
                f"indicating stable clinical performance relative to peers.")

    if readm is not None:
        if readm > 1.1:
            parts.append(
                f"The excess readmission ratio of {readm:.3f} exceeds 1.0, indicating more "
                f"readmissions than expected and serving as a direct driver of HRRP penalties.")
        elif readm > 1.0:
            parts.append(
                f"Excess readmissions ({readm:.3f}) are slightly above the 1.0 threshold; "
                f"structured discharge planning and care transition programs could reduce this exposure.")
        else:
            parts.append(
                f"Readmission performance ({readm:.3f}) is within the acceptable range, "
                f"reflecting effective post-discharge care protocols.")

    return " ".join(parts) if parts else "Clinical quality data is being compiled for this reporting period."


def _gen_experience_narrative(hosp: dict) -> str:
    star  = _ival(hosp, "overall_star_rating")
    rec   = _fval(hosp, "pct_definitely_recommend")
    parts = []

    if star is not None:
        if star >= 4:
            parts.append(
                f"Patient experience is strong with a {star}-star HCAHPS rating, "
                f"positioning this hospital in the top tier nationally for patient satisfaction.")
        elif star == 3:
            parts.append(
                f"A 3-star HCAHPS rating reflects average patient experience. "
                f"Targeted improvements in nurse communication and responsiveness "
                f"could drive a meaningful rating upgrade.")
        else:
            parts.append(
                f"The {star}-star HCAHPS rating indicates below-average patient experience, "
                f"with reputational, referral, and value-based payment implications.")

    if rec is not None:
        delta = rec - _NAT_RECOMMEND
        if delta >= 10:
            parts.append(
                f"The 'definitely recommend' rate of {rec:.0f}% is {delta:.0f} points above "
                f"the national benchmark ({_NAT_RECOMMEND:.0f}%), a differentiated strength.")
        elif delta < -10:
            parts.append(
                f"At {rec:.0f}%, the recommendation rate lags the national benchmark "
                f"({_NAT_RECOMMEND:.0f}%) by {abs(delta):.0f} points, a priority area for improvement.")
        else:
            parts.append(
                f"Recommendation rates ({rec:.0f}%) are near the national benchmark of {_NAT_RECOMMEND:.0f}%.")

    return " ".join(parts) if parts else "Patient experience data is not available for this reporting period."


def _gen_action_plan(hosp: dict, drg_data: pd.DataFrame, hr_pct: float, peer: dict) -> list:
    actions = []
    ctp    = _fval(hosp, "inpatient_avg_ctp")
    undpay = _fval(hosp, "inpatient_underpayment_rate")
    pen    = _ival(hosp, "penalty_count")
    rec    = _fval(hosp, "pct_definitely_recommend")
    readm  = _fval(hosp, "avg_excess_readmission_ratio")
    gap_m  = _fval(hosp, "inpatient_revenue_gap_millions")

    # Priority 1: highest financial impact
    if ctp and ctp > _NAT_CTP * 1.2:
        top_drg = ""
        if not drg_data.empty:
            top_drg = f", starting with {_safe(str(drg_data.iloc[0].get('drg_description', '')))[:38]}"
        recovery = f" Target a 10-15% rate improvement to recover ~${gap_m * 0.4:.1f}M annually." if gap_m else ""
        actions.append((
            "Payer Contract Renegotiation",
            f"CTP ratio of {ctp:.2f}x is {((ctp / _NAT_CTP - 1) * 100):.0f}% above national norms. "
            f"Conduct a payer-by-payer contract audit{top_drg}.{recovery}"
        ))
    elif gap_m and gap_m > 5:
        actions.append((
            "Revenue Gap Recovery Program",
            f"${gap_m:.1f}M annual revenue gap represents a recoverable opportunity. "
            f"Initiate a systematic claim audit of underpaid accounts with focused attention "
            f"on the top 3 DRGs by revenue gap percentage."
        ))

    # Priority 2: clinical quality and penalties
    if pen and pen >= 1:
        conds    = _penalty_conds(hosp)
        cond_str = " and ".join(conds) if conds else f"{pen} penalized condition(s)"
        actions.append((
            "HRRP Readmission Reduction Protocol",
            f"Active CMS penalties for {cond_str} are directly reducing reimbursement. "
            f"Implement structured discharge planning and 30-day follow-up call programs. "
            f"A 10% readmission reduction typically removes penalty exposure within 2 reporting cycles."
        ))
    elif readm and readm > 1.0:
        actions.append((
            "Discharge Planning Enhancement",
            f"Excess readmission ratio of {readm:.3f} exceeds the 1.0 threshold. "
            f"Review post-discharge care coordination and implement structured follow-up "
            f"programs to reduce near-term HRRP penalty risk."
        ))

    # Priority 3: denial risk or patient experience
    if hr_pct > 20:
        actions.append((
            "High-Risk Claim Remediation",
            f"{hr_pct:.1f}% of claims are flagged high-risk. Deploy clinical documentation "
            f"improvement (CDI) specialists to high-volume DRGs and implement pre-bill review "
            f"workflows. Focus initial effort on the top 3 DRGs by denial exposure."
        ))
    elif rec and rec < (_NAT_RECOMMEND - 10):
        delta = _NAT_RECOMMEND - rec
        actions.append((
            "Patient Experience Improvement Initiative",
            f"Recommendation rate of {rec:.0f}% lags the national benchmark by {delta:.0f} points. "
            f"Focus on nurse communication, responsiveness, and discharge information HCAHPS domains, "
            f"which carry the highest correlation with overall recommendation improvement."
        ))
    elif undpay and undpay > _NAT_UNDERPAY:
        actions.append((
            "Underpayment Recovery Audit",
            f"Underpayment rate of {undpay:.1f}% exceeds the national average. "
            f"Engage a revenue recovery team to audit the last 12 months of underpaid claims "
            f"and implement prospective contract compliance monitoring."
        ))

    return actions[:3]


# ── PDF class ─────────────────────────────────────────────────────────────────

class MeridianPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(15, 23, 42)
        self.cell(95, 7, "MERIDIAN", align="L")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 116, 139)
        self.cell(95, 7,
            f"Hospital Intelligence Brief  -  {date.today().strftime('%B %d, %Y')}",
            align="R")
        self.ln(8)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(148, 163, 184)
        self.cell(0, 4,
            "Data sourced from CMS Medicare Claims, HCAHPS Survey, and CMS Quality Programs. "
            "For informational and benchmarking purposes only.",
            align="C")

    def section_title(self, text):
        self.check_space(20)
        y = self.get_y()
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, y + 2, 200, y + 2)
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(148, 163, 184)
        self.set_xy(10, y)
        self.cell(0, 6, _safe(text).upper(), align="L")
        self.ln(7)

    def kpi_box(self, x, y, w, h, label, value, sub=None,
                value_color=(15, 23, 42), font_size=12):
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, "DF")
        self.set_draw_color(*value_color)
        self.set_line_width(0.7)
        self.line(x, y, x + w, y)
        self.set_line_width(0.2)
        self.set_xy(x + 3, y + 3)
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(148, 163, 184)
        self.cell(w - 6, 3.5, _safe(label).upper())
        self.set_xy(x + 3, y + 7)
        self.set_font("Helvetica", "B", font_size)
        self.set_text_color(*value_color)
        self.cell(w - 6, font_size * 0.55, _safe(value))
        if sub:
            sub_y = y + 7 + font_size * 0.55 + 1.5
            self.set_xy(x + 3, sub_y)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(100, 116, 139)
            self.cell(w - 6, 3.5, _safe(sub))

    def check_space(self, needed: float):
        """Add a page break if fewer than `needed` mm remain on the current page."""
        if self.get_y() + needed > self.page_break_trigger:
            self.add_page()

    def narrative(self, text: str):
        self.check_space(15)
        saved_lm    = self.l_margin
        self.l_margin = 10
        self.set_x(10)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(51, 65, 85)
        self.multi_cell(190, 4.5, _safe(text))
        self.l_margin = saved_lm
        self.ln(3)

    def exec_summary_block(self, text: str):
        self.check_space(50)
        safe_text = _safe(text)
        x, y = 10, self.get_y()
        h    = 44  # generous fixed height for 4-sentence summary

        self.set_fill_color(239, 246, 255)
        self.set_draw_color(219, 234, 254)
        self.set_line_width(0.2)
        self.rect(x, y, 190, h, "DF")
        self.set_fill_color(37, 99, 235)
        self.rect(x, y, 2, h, "F")

        self.set_xy(x + 5, y + 3)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(37, 99, 235)
        self.cell(0, 4, "EXECUTIVE SUMMARY")

        saved_lm    = self.l_margin
        self.l_margin = x + 5
        self.set_xy(x + 5, y + 8)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(30, 58, 138)
        self.multi_cell(182, 4.5, safe_text)
        self.l_margin = saved_lm
        self.set_y(y + h + 5)

    def alert_row(self, level: str, title: str, body: str):
        self.check_space(14)
        col = _LEVEL_COLORS.get(level, (148, 163, 184))
        bg  = _LEVEL_BG.get(level, (248, 250, 252))
        x, y = 10, self.get_y()

        self.set_fill_color(*bg)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.rect(x, y, 190, 11, "DF")
        self.set_fill_color(*col)
        self.rect(x, y, 2, 11, "F")

        self.set_xy(x + 5, y + 1.5)
        self.set_font("Helvetica", "B", 5.5)
        self.set_text_color(*col)
        self.cell(14, 3.5, level.upper())

        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(15, 23, 42)
        self.set_xy(x + 20, y + 1.5)
        self.cell(165, 3.5, _safe(title))

        self.set_xy(x + 20, y + 5.5)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(71, 85, 105)
        self.cell(165, 3.5, _safe(body)[:115])
        self.ln(13)

    def action_item(self, number: int, title: str, body: str):
        self.check_space(22)
        x, y = 10, self.get_y()

        self.set_fill_color(37, 99, 235)
        self.rect(x, y, 7, 7, "F")
        self.set_xy(x, y)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(255, 255, 255)
        self.cell(7, 7, str(number), align="C")

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(15, 23, 42)
        self.set_xy(x + 10, y + 0.5)
        self.cell(175, 5, _safe(title))
        self.ln(6)

        saved_lm    = self.l_margin
        self.l_margin = x + 10
        self.set_x(x + 10)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(71, 85, 105)
        self.multi_cell(175, 4, _safe(body))
        self.l_margin = saved_lm
        self.ln(4)


# ── Main PDF generator ────────────────────────────────────────────────────────

def generate_hospital_pdf(hosp: dict, peer: dict) -> bytes:
    from db import run_query

    drg_data = run_query(f"""
        SELECT DISTINCT drg_code, drg_description, total_discharges,
            ROUND(charge_to_payment_ratio, 2) AS ctp_ratio,
            ROUND(revenue_gap_pct, 1)         AS revenue_gap_pct
        FROM rcm_platform.rcm_gold.fact_claims
        WHERE provider_id = '{hosp.get("provider_id", "")}'
        ORDER BY total_discharges DESC LIMIT 3
    """)

    grade_360   = hosp.get("hospital_360_grade",  "Insufficient Data")
    rcm_grade   = hosp.get("rcm_health_grade",    "Insufficient Data")
    grade_color = _grade_rgb(grade_360)
    rcm_color   = _grade_rgb(rcm_grade)
    _s360       = _fval(hosp, "hospital_360_score")
    score_val   = f"{_s360:.1f}" if _s360 is not None else "N/A"
    pen         = _ival(hosp, "penalty_count")

    _hr    = _ival(hosp, "high_risk_claims")
    _mr    = _ival(hosp, "medium_risk_claims")
    _lr    = _ival(hosp, "low_risk_claims")
    _total = (_hr or 0) + (_mr or 0) + (_lr or 0)
    hr_pct = round((_hr or 0) / _total * 100, 1) if _total > 0 else 0.0

    exec_summary   = _gen_executive_summary(hosp, drg_data, hr_pct)
    fin_narrative  = _gen_financial_narrative(hosp, drg_data, peer)
    clin_narrative = _gen_clinical_narrative(hosp)
    exp_narrative  = _gen_experience_narrative(hosp)
    actions        = _gen_action_plan(hosp, drg_data, hr_pct, peer)

    # Build critical findings (up to 3)
    findings = []
    gap_b  = _fval(hosp, "combined_revenue_gap_billions")
    readm  = _fval(hosp, "avg_excess_readmission_ratio")
    star   = _ival(hosp, "overall_star_rating")

    if gap_b is not None:
        lv   = "critical" if gap_b > 0.15 else "warning" if gap_b > 0.05 else "good"
        note = ("exceeds critical threshold" if gap_b > 0.15
                else "above moderate threshold" if gap_b > 0.05 else "within acceptable range")
        findings.append((lv, "Revenue at Risk", f"${gap_b:.2f}B annual revenue gap - {note}"))

    if hr_pct > 0:
        lv   = "critical" if hr_pct > 33 else "warning" if hr_pct > 15 else "good"
        note = ("systematic documentation issues likely" if hr_pct > 33
                else "targeted CDI review recommended" if hr_pct > 15 else "within normal range")
        findings.append((lv, "Claim Denial Risk", f"{hr_pct:.1f}% high-risk claims - {note}"))

    if pen is not None:
        lv   = "critical" if pen >= 2 else "warning" if pen == 1 else "good"
        note = "directly reducing reimbursement rates" if pen >= 1 else "no penalties recorded"
        findings.append((lv, "CMS Penalty Exposure",
                         f"{pen} active HRRP penalt{'ies' if pen != 1 else 'y'} - {note}"))

    if len(findings) < 3 and readm is not None:
        lv   = "warning" if readm > 1.0 else "good"
        note = "above threshold - HRRP risk" if readm > 1.0 else "within acceptable range"
        findings.append((lv, "Readmission Performance", f"Excess ratio: {readm:.3f} - {note}"))

    if len(findings) < 3 and star is not None:
        lv   = "good" if star >= 4 else "warning" if star == 3 else "critical"
        note = ("top tier nationally" if star >= 4
                else "average - improvement opportunities" if star == 3 else "below average")
        findings.append((lv, "Patient Experience", f"{star}-star HCAHPS rating - {note}"))

    findings = findings[:3]

    # ── Build PDF ─────────────────────────────────────────────────────────────
    pdf = MeridianPDF()
    pdf.set_margins(10, 15, 10)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # 1. HOSPITAL IDENTITY
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(140, 8, _safe(hosp.get("provider_name", "")), align="L")
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*grade_color)
    pdf.cell(50, 8, score_val, align="R")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(140, 5,
        f"{_safe(hosp.get('provider_city', ''))}, "
        f"{_safe(hosp.get('provider_state', ''))}"
        f"  -  {_safe(hosp.get('hospital_type', ''))}"
        f"  -  {_safe(hosp.get('hospital_ownership', ''))}",
        align="L")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(50, 5, "out of 100  -  360 Score", align="R")
    pdf.ln(7)

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(*rcm_color)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(26, 5, f"RCM: {_safe(rcm_grade)}", fill=True, align="C")
    pdf.set_x(pdf.get_x() + 2)
    pdf.set_fill_color(*grade_color)
    pdf.cell(26, 5, f"360: {_safe(grade_360)}", fill=True, align="C")
    if pen and pen >= 1:
        pdf.set_x(pdf.get_x() + 3)
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(220, 38, 38)
        pdf.cell(30, 5, f"CMS Penalties: {pen}", fill=True, align="C")
    pdf.ln(10)

    # 2. EXECUTIVE SUMMARY
    pdf.exec_summary_block(exec_summary)

    # 3. CRITICAL FINDINGS
    if findings:
        pdf.section_title("Critical Findings")
        for lv, title, body in findings:
            pdf.alert_row(lv, title, body)
        pdf.ln(2)

    # 4. FINANCIAL INTELLIGENCE
    pdf.section_title("Financial Intelligence")
    pdf.narrative(fin_narrative)

    _disc     = _fval(hosp, "inpatient_discharges")
    _ctp      = _fval(hosp, "inpatient_avg_ctp")
    _undpay   = _fval(hosp, "inpatient_underpayment_rate")
    _combined = _fval(hosp, "combined_revenue_gap_billions")
    _gap_m    = _fval(hosp, "inpatient_revenue_gap_millions")

    _box_h = 22
    pdf.check_space(_box_h + 8)
    fin_y = pdf.get_y()
    if _disc:
        pdf.kpi_box(10,  fin_y, 44, _box_h, "Inpatient Discharges", f"{int(_disc):,}", font_size=11)
    if _ctp:
        ctp_col = (220, 38, 38) if _ctp > 5 else (217, 119, 6) if _ctp > 4 else (22, 163, 74)
        pdf.kpi_box(57,  fin_y, 44, _box_h, "CTP Ratio",
                    f"{_ctp:.2f}x", f"Nat avg: {_NAT_CTP:.1f}x", value_color=ctp_col, font_size=11)
    if _undpay:
        und_col = (220, 38, 38) if _undpay > 60 else (217, 119, 6) if _undpay > 40 else (22, 163, 74)
        pdf.kpi_box(104, fin_y, 44, _box_h, "Underpayment Rate",
                    f"{_undpay:.1f}%", f"Nat avg: {_NAT_UNDERPAY:.0f}%",
                    value_color=und_col, font_size=11)
    if _combined:
        rev_col = (220, 38, 38) if _combined > 0.1 else (217, 119, 6) if _combined > 0.05 else (22, 163, 74)
        sub_rev = f"Inpatient ${_gap_m:.1f}M" if _gap_m else ""
        pdf.kpi_box(151, fin_y, 44, _box_h, "Total Revenue Gap",
                    f"${_combined:.2f}B", sub_rev, value_color=rev_col, font_size=11)
    pdf.set_y(fin_y + _box_h + 6)

    if not drg_data.empty:
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 4, "TOP DRGS BY DISCHARGE VOLUME", align="L")
        pdf.ln(5)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(71, 85, 105)
        for hdr, w in [("DRG", 18), ("Description", 94), ("Cases", 24), ("CTP", 22), ("Gap %", 22)]:
            pdf.cell(w, 5, hdr, border=1, fill=True,
                     align="C" if hdr not in ("DRG", "Description") else "L")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(30, 41, 59)
        for _, row in drg_data.iterrows():
            _ctp_v = row.get("ctp_ratio")
            _gap_v = row.get("revenue_gap_pct")
            pdf.cell(18, 5, _safe(row.get("drg_code", "")), border=1)
            pdf.cell(94, 5, _safe(row.get("drg_description", ""))[:52], border=1)
            pdf.cell(24, 5, f"{int(row.get('total_discharges', 0)):,}", border=1, align="C")
            pdf.cell(22, 5, f"{float(_ctp_v):.2f}x" if _ctp_v else "N/A", border=1, align="C")
            pdf.cell(22, 5, f"{float(_gap_v):.1f}%" if _gap_v else "N/A", border=1, align="C")
            pdf.ln(5)

    pdf.ln(5)

    # 5. CLINICAL RISK
    _mort   = _fval(hosp, "avg_mortality_rate")
    _readm  = _fval(hosp, "avg_excess_readmission_ratio")
    _psi    = _fval(hosp, "psi_90_safety")
    _better = _ival(hosp, "better_mortality_flag")
    _worse  = _ival(hosp, "worse_mortality_flag")

    pdf.section_title("Clinical Risk")
    pdf.narrative(clin_narrative)

    if _mort:
        pdf.check_space(26)
        clin_y   = pdf.get_y()
        mort_col = ((22, 163, 74) if _better == 1 else
                    (220, 38, 38) if _worse  == 1 else (217, 119, 6))
        mort_sub = ("Better than national" if _better == 1 else
                    "Worse than national"  if _worse  == 1 else "Similar to national")
        pdf.kpi_box(10,  clin_y, 58, 22, "Avg 30-Day Mortality",
                    f"{_mort:.1f}%", mort_sub, mort_col, font_size=11)
        if _readm:
            readm_col = (220, 38, 38) if _readm > 1 else (22, 163, 74)
            pdf.kpi_box(72,  clin_y, 58, 22, "Excess Readmission Ratio",
                        f"{_readm:.3f}", "Threshold: 1.000",
                        value_color=readm_col, font_size=11)
        if _psi:
            pdf.kpi_box(134, clin_y, 58, 22, "Patient Safety (PSI-90)",
                        f"{_psi:.3f}", font_size=11)
        pdf.set_y(clin_y + 26)

    pdf.ln(3)

    # 6. PATIENT EXPERIENCE
    _star = _ival(hosp, "overall_star_rating")
    _rec  = _fval(hosp, "pct_definitely_recommend")

    if _star:
        pdf.section_title("Patient Experience (HCAHPS)")
        pdf.narrative(exp_narrative)
        pdf.check_space(26)
        exp_y   = pdf.get_y()
        star_col = (22, 163, 74) if _star >= 4 else (217, 119, 6) if _star == 3 else (220, 38, 38)
        star_str = f"{_star}/5  " + ("*" * _star) + ("-" * (5 - _star))
        pdf.kpi_box(10, exp_y, 58, 22, "Overall Star Rating",
                    star_str, value_color=star_col, font_size=11)
        if _rec:
            rec_col = (22, 163, 74) if _rec >= _NAT_RECOMMEND else (217, 119, 6)
            pdf.kpi_box(72, exp_y, 58, 22, "Definitely Recommend",
                        f"{_rec:.0f}%", f"Nat avg: {_NAT_RECOMMEND:.0f}%",
                        value_color=rec_col, font_size=11)
        pdf.set_y(exp_y + 26)
        pdf.ln(3)

    # 7. PRIORITY ACTION PLAN
    if actions:
        pdf.section_title("Priority Action Plan")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 4, "Three highest-impact interventions based on this hospital's risk profile:")
        pdf.ln(7)
        for i, (title, body) in enumerate(actions, 1):
            pdf.action_item(i, title, body)

    # 8. PEER BENCHMARKING
    if peer:
        _total_h = peer.get("total_hospitals")
        _state   = hosp.get("provider_state", "")
        header   = f"Peer Benchmarking - {_state}"
        try:
            if _total_h and not pd.isna(float(_total_h)):
                header += f" ({int(_total_h)} hospitals)"
        except (TypeError, ValueError):
            pass
        pdf.section_title(header)

        def _peer_row(label, hosp_val, state_val, fmt, higher_is_better):
            try:
                hv = float(hosp_val)
                sv = float(state_val)
                if pd.isna(hv) or pd.isna(sv):
                    return
                delta = hv - sv
                good  = delta > 0 if higher_is_better else delta < 0
                col   = (22, 163, 74) if good else (220, 38, 38)
                arrow = "^" if delta > 0 else "v"
                pdf.set_font("Helvetica", "", 7.5)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(55, 6, _safe(label))
                pdf.set_font("Helvetica", "B", 7.5)
                pdf.set_text_color(15, 23, 42)
                pdf.cell(30, 6, fmt(hv))
                pdf.set_font("Helvetica", "", 7.5)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(40, 6, f"State avg: {fmt(sv)}")
                pdf.set_font("Helvetica", "B", 7.5)
                pdf.set_text_color(*col)
                pdf.cell(0, 6, f"{arrow} {fmt(abs(delta))}")
                pdf.ln(6)
            except Exception:
                pass

        _peer_row("360 Score",
                  hosp.get("hospital_360_score"),       peer.get("state_avg_360"),
                  lambda v: f"{v:.1f}",   higher_is_better=True)
        _peer_row("Inpatient CTP Ratio",
                  hosp.get("inpatient_avg_ctp"),         peer.get("state_avg_ctp"),
                  lambda v: f"{v:.2f}x",  higher_is_better=False)
        _peer_row("Underpayment Rate",
                  hosp.get("inpatient_underpayment_rate"), peer.get("state_avg_underpayment"),
                  lambda v: f"{v:.1f}%",  higher_is_better=False)

    return bytes(pdf.output())
