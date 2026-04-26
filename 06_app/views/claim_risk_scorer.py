import streamlit as st

from config import GRADE_COLORS, STATES
from db import run_query
from utils import kpi_card, section_header


# ── CACHED LOADERS ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _hospital_list(state: str):
    return run_query(f"""
        SELECT DISTINCT provider_id, provider_name
        FROM rcm_platform.rcm_gold.hospital_scorecard
        WHERE provider_state = '{state}'
        ORDER BY provider_name
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _drg_list(provider_id: str):
    return run_query(f"""
        SELECT DISTINCT drg_code, drg_description
        FROM rcm_platform.rcm_gold.fact_claims
        WHERE provider_id = '{provider_id}'
        ORDER BY drg_code
    """)


@st.cache_data(ttl=1800, show_spinner=False)
def _score(provider_id: str, drg_code: str):
    return run_query(f"""
        SELECT d.denial_risk_score, d.denial_risk_label,
            f.avg_submitted_charge, f.avg_medicare_payment,
            f.charge_to_payment_ratio, f.revenue_gap_pct,
            f.total_discharges,
            h.provider_name, h.provider_state,
            h.rcm_health_grade, h.rcm_health_score
        FROM rcm_platform.rcm_gold.denial_risk_scores d
        JOIN (
            SELECT DISTINCT provider_id, drg_code,
                avg_submitted_charge, avg_medicare_payment,
                charge_to_payment_ratio, revenue_gap_pct, total_discharges
            FROM rcm_platform.rcm_gold.fact_claims
        ) f ON d.provider_id = f.provider_id AND d.drg_code = f.drg_code
        JOIN rcm_platform.rcm_gold.hospital_scorecard h
            ON d.provider_id = h.provider_id
        WHERE d.provider_id = '{provider_id}' AND d.drg_code = '{drg_code}'
        LIMIT 1
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _national_drg(drg_code: str):
    return run_query(f"""
        SELECT revenue_gap_billions, avg_ctp_ratio,
               avg_revenue_gap_pct, hospital_count, drg_description
        FROM rcm_platform.rcm_gold.dashboard_drg_leakage
        WHERE CAST(drg_code AS STRING) = '{drg_code}'
        LIMIT 1
    """)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _risk_bar_html(score: float) -> str:
    pct = round(score * 100, 1)
    return (
        '<div style="margin:14px 0 6px 0">'
        '<div style="position:relative;height:10px;border-radius:5px;overflow:visible;'
        'background:linear-gradient(90deg,#dcfce7 0%,#dcfce7 30%,'
        '#fef9c3 30%,#fef9c3 60%,#fee2e2 60%,#fee2e2 100%)">'
        f'<div style="position:absolute;left:{pct}%;top:50%;'
        'transform:translate(-50%,-50%);width:18px;height:18px;'
        'background:#0f172a;border-radius:50%;border:2.5px solid #fff;'
        'box-shadow:0 1px 6px rgba(0,0,0,0.25)"></div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;'
        'font-size:0.6rem;color:#94a3b8;margin-top:5px;font-weight:600">'
        '<span>LOW</span><span>MEDIUM</span><span>HIGH</span>'
        '</div></div>'
    )


def _build_risk_factors(row, nat_row) -> list[dict]:
    factors = []

    ctp        = float(row["charge_to_payment_ratio"])
    gap_pct    = float(row["revenue_gap_pct"])
    grade      = str(row["rcm_health_grade"])
    score      = float(row["denial_risk_score"])
    discharges = int(row["total_discharges"]) if row["total_discharges"] else 0

    if nat_row is not None:
        nat_ctp = float(nat_row["avg_ctp_ratio"])
        nat_gap = float(nat_row["avg_revenue_gap_pct"])

        if ctp > nat_ctp * 1.10:
            excess_pct = round((ctp - nat_ctp) / nat_ctp * 100)
            factors.append({
                "level": "high" if ctp > nat_ctp * 1.30 else "medium",
                "text": (
                    f"CTP ratio {ctp:.2f}x is {excess_pct}% above the national average "
                    f"for this DRG ({nat_ctp:.2f}x) — elevated charge-to-payment spread "
                    f"increases denial probability."
                ),
            })

        if gap_pct > nat_gap + 5:
            factors.append({
                "level": "high" if gap_pct > nat_gap + 15 else "medium",
                "text": (
                    f"Revenue gap {gap_pct:.1f}% exceeds the national average for this "
                    f"DRG ({nat_gap:.1f}%) — indicates above-average underpayment exposure."
                ),
            })

    if grade in ("D", "F"):
        factors.append({
            "level": "high",
            "text": (
                f"Hospital RCM grade {grade} — below-average revenue cycle performance "
                f"at this facility increases overall claim vulnerability."
            ),
        })
    elif grade == "C":
        factors.append({
            "level": "medium",
            "text": (
                f"Hospital RCM grade {grade} — moderate revenue cycle performance. "
                f"Verify payer-specific documentation requirements before submission."
            ),
        })

    if discharges < 50:
        factors.append({
            "level": "medium",
            "text": (
                f"Low case volume ({discharges:,} discharges) at this facility for this DRG — "
                f"limited history may result in stricter payer scrutiny."
            ),
        })

    if score > 0.70 and len(factors) < 3:
        factors.append({
            "level": "high",
            "text": (
                f"Denial risk score {score:.3f} is in the high-risk zone (above 0.60 threshold) "
                f"— this DRG + facility combination has historically poor payment outcomes."
            ),
        })

    order = {"high": 0, "medium": 1}
    factors.sort(key=lambda x: order.get(x["level"], 2))
    return factors[:3]


def _factor_html(factors: list[dict]) -> str:
    if not factors:
        return ""
    rows = []
    for f in factors:
        color = "#dc2626" if f["level"] == "high" else "#d97706"
        bg    = "#fff1f2" if f["level"] == "high" else "#fffbeb"
        bc    = "#fecdd3" if f["level"] == "high" else "#fde68a"
        label = "High" if f["level"] == "high" else "Medium"
        rows.append(
            f'<div style="display:flex;align-items:flex-start;gap:12px;'
            f'background:{bg};border:1px solid {bc};border-left:3px solid {color};'
            f'border-radius:0 8px 8px 0;padding:11px 14px;margin-bottom:8px">'
            f'<div style="background:{color}22;border-radius:4px;padding:2px 8px;'
            f'font-size:0.6rem;font-weight:700;color:{color};text-transform:uppercase;'
            f'letter-spacing:0.4px;white-space:nowrap;margin-top:1px">{label}</div>'
            f'<div style="font-size:0.8rem;color:#334155;line-height:1.6">{f["text"]}</div>'
            f'</div>'
        )
    return "".join(rows)


# ── PAGE ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# Claim Risk Scorer")
    st.markdown("<p class='page-subtitle'>Pre-submission denial risk prediction "
                "— select a hospital and DRG to score a claim</p>",
                unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── 3-column cascade filter ───────────────────────────────────
    f1, f2, f3 = st.columns(3)

    with f1:
        selected_state = st.selectbox("State", STATES)

    hospital_list = _hospital_list(selected_state)

    with f2:
        if hospital_list.empty:
            st.info("No hospitals found for this state.")
            return
        hosp_map = {r["provider_name"]: r["provider_id"]
                    for _, r in hospital_list.iterrows()}
        selected_hosp = st.selectbox("Hospital", list(hosp_map.keys()))
        selected_pid  = hosp_map[selected_hosp]

    drg_list = _drg_list(str(selected_pid))

    with f3:
        if drg_list.empty:
            st.info("No DRGs found for this hospital.")
            return
        drg_map = {
            f"{r['drg_code']} — {str(r['drg_description'])[:52]}": r["drg_code"]
            for _, r in drg_list.iterrows()
        }
        selected_drg_label = st.selectbox("DRG Code", list(drg_map.keys()))
        selected_drg       = drg_map[selected_drg_label]

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    score_data = _score(str(selected_pid), str(selected_drg))

    if score_data.empty:
        st.warning("No scoring data found for this hospital + DRG combination.")
        return

    row        = score_data.iloc[0]
    risk_score = float(row["denial_risk_score"])
    risk_label = str(row["denial_risk_label"])

    # Fetch national DRG data early — used in both risk factors and benchmark strip
    nat     = _national_drg(str(selected_drg))
    nat_row = nat.iloc[0] if not nat.empty else None

    if "High" in risk_label:
        rc, bg, bc = "#dc2626", "#fff1f2", "#fecdd3"
        rec = ("Immediate pre-submission review required. Verify documentation "
               "completeness, coding accuracy, prior authorization, and medical necessity.")
    elif "Medium" in risk_label:
        rc, bg, bc = "#d97706", "#fffbeb", "#fde68a"
        rec = ("Secondary review recommended. Confirm diagnosis codes, "
               "discharge summary completeness, and any payer-specific requirements.")
    else:
        rc, bg, bc = "#16a34a", "#f0fdf4", "#bbf7d0"
        rec = "Low denial risk. Standard submission process applies."

    # ── Hospital + DRG context banner ────────────────────────────
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
        f'padding:12px 18px;margin-bottom:16px;display:flex;'
        f'align-items:center;justify-content:space-between">'
        f'<div>'
        f'<div style="font-size:0.72rem;color:#94a3b8;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px">Scoring</div>'
        f'<div style="font-size:0.9rem;font-weight:700;color:#0f172a">'
        f'{row["provider_name"]}</div>'
        f'<div style="font-size:0.75rem;color:#64748b;margin-top:1px">'
        f'DRG {selected_drg} &nbsp;·&nbsp; {row["provider_state"]}</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
        f'letter-spacing:0.5px;font-weight:700">RCM Score</div>'
        f'<div style="font-size:1.1rem;font-weight:800;color:#0f172a">'
        f'{float(row["rcm_health_score"]):.1f}/100</div>'
        f'<div style="font-size:0.7rem;font-weight:700;'
        f'color:{GRADE_COLORS.get(row["rcm_health_grade"],"#94a3b8")}">'
        f'{row["rcm_health_grade"]}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Risk result ───────────────────────────────────────────────
    r1, r2 = st.columns([1, 3])

    with r1:
        st.markdown(
            f'<div style="background:{bg};border:1px solid {bc};border-radius:10px;'
            f'padding:20px 16px;text-align:center;height:100%">'
            f'<div style="font-size:0.62rem;font-weight:700;color:{rc};'
            f'text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">'
            f'Denial Risk</div>'
            f'<div style="font-size:2.2rem;font-weight:800;color:{rc};'
            f'letter-spacing:-1.5px;line-height:1">{risk_score:.4f}</div>'
            f'<div style="margin-top:8px;display:inline-block;background:{bc};'
            f'color:{rc};padding:3px 10px;border-radius:10px;'
            f'font-size:0.7rem;font-weight:700">{risk_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with r2:
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;'
            f'border-radius:10px;padding:18px 20px;height:100%">'
            f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;'
            f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px">'
            f'Risk Distribution</div>'
            + _risk_bar_html(risk_score) +
            f'<div style="font-size:0.8rem;color:#475569;line-height:1.6;'
            f'margin-top:10px;border-top:1px solid #f1f5f9;padding-top:10px">'
            f'<strong style="color:#0f172a">Recommendation:</strong> {rec}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── Why is this claim at risk? ────────────────────────────────
    factors = _build_risk_factors(row, nat_row)
    if factors:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Why is this Claim at Risk?")
        st.markdown(_factor_html(factors), unsafe_allow_html=True)

    # ── Claim financials ──────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Claim Financials")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("Avg Submitted Charge",
        f"${float(row['avg_submitted_charge']):,.0f}", "Per claim"),
        unsafe_allow_html=True)
    c2.markdown(kpi_card("Avg Medicare Payment",
        f"${float(row['avg_medicare_payment']):,.0f}", "Per claim"),
        unsafe_allow_html=True)
    c3.markdown(kpi_card("CTP Ratio",
        f"{float(row['charge_to_payment_ratio']):.2f}x", "Charge-to-payment"),
        unsafe_allow_html=True)
    c4.markdown(kpi_card("Revenue Gap",
        f"{float(row['revenue_gap_pct']):.1f}%", "Underpayment exposure"),
        unsafe_allow_html=True)

    # ── National DRG benchmark ────────────────────────────────────
    if not nat.empty:
        n = nat.iloc[0]
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
            f'border-left:4px solid #2563eb;border-radius:0 8px 8px 0;'
            f'padding:12px 18px">'
            f'<div style="font-size:0.65rem;font-weight:700;color:#2563eb;'
            f'text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">'
            f'National Benchmark — DRG {selected_drg}</div>'
            f'<div style="display:flex;gap:32px;flex-wrap:wrap">'
            f'<div><div style="font-size:0.62rem;color:#94a3b8;font-weight:600;'
            f'text-transform:uppercase">National Gap</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#0f172a">'
            f'${float(n["revenue_gap_billions"])}B</div></div>'
            f'<div><div style="font-size:0.62rem;color:#94a3b8;font-weight:600;'
            f'text-transform:uppercase">Avg CTP</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#0f172a">'
            f'{float(n["avg_ctp_ratio"]):.2f}x</div></div>'
            f'<div><div style="font-size:0.62rem;color:#94a3b8;font-weight:600;'
            f'text-transform:uppercase">Avg Revenue Gap</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#0f172a">'
            f'{float(n["avg_revenue_gap_pct"]):.1f}%</div></div>'
            f'<div><div style="font-size:0.62rem;color:#94a3b8;font-weight:600;'
            f'text-transform:uppercase">Hospitals Affected</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#0f172a">'
            f'{int(n["hospital_count"]):,}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
