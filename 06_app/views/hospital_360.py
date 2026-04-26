import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import GRADE_COLORS, STATES
from db import run_query
from utils import insight_card, kpi, kpi_benchmark, kpi_card, render_table, safe_val, section_header


@st.cache_data(show_spinner=False)
def _build_pdf(hosp_dict: dict, peer_dict: dict) -> bytes:
    from pdf_export import generate_hospital_pdf
    return generate_hospital_pdf(hosp_dict, peer_dict)


@st.cache_data(ttl=3600, show_spinner=False)
def _hospital_list(state: str):
    return run_query(f"""
        SELECT provider_id, provider_name
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        WHERE provider_state = '{state}'
        ORDER BY inpatient_discharges DESC
    """)


@st.cache_data(ttl=1800, show_spinner=False)
def _hospital_data(provider_id: str):
    return run_query(f"""
        SELECT
            h.provider_id, h.provider_name, h.provider_state, h.provider_city,
            h.hospital_type, h.hospital_ownership,
            h.inpatient_discharges, h.inpatient_avg_ctp,
            h.inpatient_avg_gap_pct, h.inpatient_underpayment_rate,
            h.inpatient_revenue_gap_millions,
            h.outpatient_beneficiaries, h.outpatient_avg_ctp,
            h.outpatient_avg_gap_pct, h.outpatient_underpayment_rate,
            h.outpatient_revenue_gap_millions,
            h.combined_revenue_gap_billions, h.combined_avg_ctp,
            h.rcm_health_score, h.rcm_health_grade,
            h.hospital_360_score, h.hospital_360_grade, h.data_completeness,
            h.overall_star_rating, h.nurse_star_rating, h.doctor_star_rating,
            h.cleanliness_star_rating, h.quietness_star_rating,
            h.medication_comm_star_rating, h.discharge_info_star_rating,
            h.recommend_star_rating,
            h.pct_definitely_recommend, h.pct_probably_recommend, h.pct_not_recommend,
            h.nurse_linear_score, h.doctor_linear_score,
            h.cleanliness_linear_score, h.quietness_linear_score,
            h.recommend_linear_score, h.overall_rating_linear_score,
            h.avg_mortality_rate, h.avg_readmission_rate,
            h.mort_30_hf, h.mort_30_pn, h.mort_30_ami, h.mort_30_stk,
            h.readm_ratio_hf, h.readm_ratio_pn,
            h.readm_ratio_ami, h.readm_ratio_hip_knee,
            h.readm_ratio_copd, h.readm_ratio_cabg,
            h.avg_excess_readmission_ratio, h.penalty_count,
            h.hf_penalty_flag, h.pn_penalty_flag, h.ami_penalty_flag,
            h.psi_90_safety, h.hf_mortality_vs_national,
            h.better_mortality_flag, h.worse_mortality_flag,
            ROUND(d.avg_denial_risk_score,4) AS avg_denial_risk_score,
            d.high_risk_claims, d.medium_risk_claims, d.low_risk_claims
        FROM rcm_platform.rcm_gold.hospital_360_scorecard h
        LEFT JOIN (
            SELECT provider_id,
                ROUND(AVG(denial_risk_score),4) AS avg_denial_risk_score,
                SUM(CASE WHEN denial_risk_label='High Risk'   THEN 1 ELSE 0 END) AS high_risk_claims,
                SUM(CASE WHEN denial_risk_label='Medium Risk' THEN 1 ELSE 0 END) AS medium_risk_claims,
                SUM(CASE WHEN denial_risk_label='Low Risk'    THEN 1 ELSE 0 END) AS low_risk_claims
            FROM rcm_platform.rcm_gold.denial_risk_scores
            GROUP BY provider_id
        ) d ON h.provider_id = d.provider_id
        WHERE h.provider_id = '{provider_id}'
        LIMIT 1
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _peer_avg(state: str):
    return run_query(f"""
        SELECT
            ROUND(AVG(inpatient_avg_ctp),2)          AS state_avg_ctp,
            ROUND(AVG(hospital_360_score),1)          AS state_avg_360,
            ROUND(AVG(inpatient_underpayment_rate),1) AS state_avg_underpayment,
            COUNT(*)                                  AS total_hospitals
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        WHERE provider_state = '{state}'
        AND inpatient_avg_ctp IS NOT NULL
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _benchmarks(provider_id: str):
    return run_query(f"""
        SELECT * FROM rcm_platform.rcm_gold.dashboard_national_benchmarks
        WHERE provider_id = '{provider_id}'
    """)


@st.cache_data(ttl=1800, show_spinner=False)
def _drg_data(provider_id: str):
    return run_query(f"""
        SELECT DISTINCT drg_code, drg_description, total_discharges,
            ROUND(avg_submitted_charge,2)    AS avg_charge,
            ROUND(avg_medicare_payment,2)    AS avg_payment,
            ROUND(charge_to_payment_ratio,2) AS ctp_ratio,
            ROUND(revenue_gap_pct,1)         AS revenue_gap_pct,
            underpayment_flag
        FROM rcm_platform.rcm_gold.fact_claims
        WHERE provider_id = '{provider_id}'
        ORDER BY total_discharges DESC LIMIT 20
    """)


def render():
    st.markdown("# Hospital 360")
    st.markdown("<p class='page-subtitle'>Complete hospital intelligence — "
                "financial exposure, CMS program risk, and patient experience</p>",
                unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    _preset_state = st.session_state.pop("go_to_state",         None)
    _preset_name  = st.session_state.pop("go_to_hospital_name", None)
    _preset_id    = st.session_state.pop("go_to_hospital_id",   None)

    if _preset_state and _preset_state in STATES:
        st.session_state["h360_state_select"] = _preset_state

    col1, col2 = st.columns(2)
    with col1:
        selected_state = st.selectbox("State", STATES, key="h360_state_select")

    hospital_list = _hospital_list(selected_state)

    if hospital_list.empty:
        st.info("No hospitals found for this state.")
        return

    hosp_names = hospital_list["provider_name"].tolist()
    if _preset_id:
        id_match = hospital_list[hospital_list["provider_id"].astype(str) == str(_preset_id)]
        if not id_match.empty:
            _preset_name = id_match.iloc[0]["provider_name"]
    if _preset_name and _preset_name in hosp_names:
        st.session_state["h360_hospital_select"] = _preset_name

    with col2:
        selected_name = st.selectbox("Hospital", hosp_names, key="h360_hospital_select")

    selected_id = hospital_list.loc[
        hospital_list["provider_name"] == selected_name, "provider_id"
    ].iloc[0]

    hospital_data = _hospital_data(str(selected_id))

    if not hospital_data.empty:
        hosp = hospital_data.iloc[0]

        grade_360   = hosp["hospital_360_grade"]
        score_360   = hosp["hospital_360_score"]
        grade_color = GRADE_COLORS.get(grade_360, "#94a3b8")
        score_str   = f"{score_360:.1f}" if pd.notna(score_360) else "N/A"

        # ── PEER + BENCHMARKS (cached per state / provider) ──────
        peer_avg   = _peer_avg(hosp['provider_state'])
        benchmarks = _benchmarks(str(selected_id))
        peer_dict = peer_avg.iloc[0].to_dict() if not peer_avg.empty else {}

        # ── HOSPITAL CARD ─────────────────────────────────────────
        _penalty = safe_val(hosp, "penalty_count", None, None)
        _penalty_badge = (
            '<span style="background:#fee2e2;color:#dc2626;padding:3px 10px;'
            'border-radius:10px;font-size:0.7rem;font-weight:700;margin-left:6px">'
            'CMS Penalties</span>'
        ) if _penalty is not None and int(_penalty) >= 1 else ""

        _underpay = hosp['inpatient_underpayment_rate']
        _underpay_badge = (
            '<span style="background:#fef3c7;color:#d97706;padding:3px 10px;'
            'border-radius:10px;font-size:0.7rem;font-weight:700;margin-left:6px">'
            'High Underpayment</span>'
        ) if pd.notna(_underpay) and float(_underpay) > 60 else ""

        col_info, col_score = st.columns([4, 1])
        with col_info:
            st.markdown(
                f'<div class="hospital-card">'
                f'<div style="font-size:1.05rem;font-weight:700;color:#0f172a;margin-bottom:4px">'
                f'{hosp["provider_name"]}</div>'
                f'<div style="font-size:0.77rem;color:#64748b;margin-bottom:10px">'
                f'{hosp["provider_city"]}, {hosp["provider_state"]}'
                f' &nbsp;·&nbsp; {hosp["hospital_type"]}'
                f' &nbsp;·&nbsp; {hosp["hospital_ownership"]}</div>'
                f'<span style="background:{GRADE_COLORS.get(hosp["rcm_health_grade"],"#94a3b8")};'
                f'color:#fff;padding:3px 10px;border-radius:10px;'
                f'font-size:0.7rem;font-weight:700;margin-right:6px">'
                f'RCM: {hosp["rcm_health_grade"]}</span>'
                f'<span style="background:{grade_color};color:#fff;'
                f'padding:3px 10px;border-radius:10px;font-size:0.7rem;font-weight:700">'
                f'360: {grade_360}</span>'
                f'{_penalty_badge}{_underpay_badge}'
                f'</div>',
                unsafe_allow_html=True)

        with col_score:
            st.markdown(f"""
            <div class="score-card">
                <div class="kpi-label">360 Score</div>
                <div style="font-size:2.4rem;font-weight:800;
                            color:{grade_color};letter-spacing:-1.5px;line-height:1.1">
                    {score_str}</div>
                <div style="font-size:0.65rem;color:#94a3b8;margin-top:2px">
                    out of 100 &nbsp;·&nbsp; {hosp['data_completeness']} data</div>
            </div>""", unsafe_allow_html=True)

        # ── PDF EXPORT ────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        pdf_bytes = _build_pdf(hosp.to_dict(), peer_dict)
        st.download_button(
            label="Export Hospital Intelligence Brief (PDF)",
            data=pdf_bytes,
            file_name=f"{hosp['provider_name'].replace(' ', '_')}_meridian_brief.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        # ── EXECUTIVE SUMMARY ─────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Executive Summary")
        ins1, ins2, ins3 = st.columns(3)

        with ins1:
            _und = safe_val(hosp, "inpatient_underpayment_rate", None, None)
            _ctp = safe_val(hosp, "inpatient_avg_ctp", None, None)
            if _und is not None and _ctp is not None:
                _und_f = float(_und); _ctp_f = float(_ctp)
                _fin_signal = "elevated" if _und_f > 60 or _ctp_f > 4.0 else "moderate"
                insight_card(
                    f"<strong>Financial:</strong> "
                    f"{'High' if _fin_signal == 'elevated' else 'Moderate'} revenue leakage — "
                    f"underpayment rate <strong>{_und_f:.1f}%</strong> and "
                    f"CTP ratio <strong>{_ctp_f:.1f}x</strong>. "
                    f"{'Review contract terms and payer mix.' if _fin_signal == 'elevated' else 'Revenue capture is within acceptable range.'}"
                )
            else:
                insight_card("<strong>Financial:</strong> Financial performance data unavailable.")

        with ins2:
            _worse = safe_val(hosp, "worse_mortality_flag", None, None)
            _better = safe_val(hosp, "better_mortality_flag", None, None)
            _mort = safe_val(hosp, "avg_mortality_rate", None, None)
            if _mort is not None:
                _mort_f = float(_mort)
                if _worse is not None and int(_worse) == 1:
                    _mort_label  = "worse than national average"
                    _mort_action = "Quality improvement focus recommended."
                elif _better is not None and int(_better) == 1:
                    _mort_label  = "better than national average"
                    _mort_action = "Strong clinical performance."
                else:
                    _mort_label  = "similar to national average"
                    _mort_action = "Monitor for sustained performance."
                insight_card(
                    f"<strong>Clinical:</strong> Avg 30-day mortality "
                    f"<strong>{_mort_f:.1f}%</strong> — "
                    f"{_mort_label}. {_mort_action}"
                )
            else:
                insight_card("<strong>Clinical:</strong> Clinical quality data not available for this hospital.")

        with ins3:
            _star = safe_val(hosp, "overall_star_rating", None, None)
            _rec  = safe_val(hosp, "pct_definitely_recommend", None, None)
            if _star is not None and _rec is not None:
                _star_f = float(_star); _rec_f = float(_rec)
                _exp_signal = ("strong" if _star_f >= 4 and _rec_f >= 75
                               else "low" if _star_f <= 2 or _rec_f < 60
                               else "average")
                _exp_action = ("Patients are highly satisfied."        if _exp_signal == "strong"
                               else "Patient satisfaction needs improvement." if _exp_signal == "low"
                               else "Room to improve patient satisfaction scores.")
                insight_card(
                    f"<strong>Patient Experience:</strong> "
                    f"<strong>{'★' * int(_star_f)}{'☆' * (5 - int(_star_f))}</strong> rating — "
                    f"<strong>{_rec_f:.0f}%</strong> would definitely recommend. "
                    f"{_exp_action}"
                )
            else:
                insight_card("<strong>Patient Experience:</strong> HCAHPS data not available for this hospital.")

        # ── RISK DASHBOARD ────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Risk Dashboard")
        rd1, rd2, rd3 = st.columns(3)

        with rd1:
            _combined = safe_val(hosp, "combined_revenue_gap_billions", None, None)
            _inpat_m  = safe_val(hosp, "inpatient_revenue_gap_millions", None, None)
            _outpat_m = safe_val(hosp, "outpatient_revenue_gap_millions", None, None)
            if _combined is not None:
                _rev_f   = float(_combined)
                _rev_col = "#dc2626" if _rev_f > 0.1 else "#d97706"
                _sub_str = ""
                if _inpat_m is not None and _outpat_m is not None:
                    _sub_str = (f"Inpatient ${float(_inpat_m):.1f}M"
                                f" &nbsp;·&nbsp; Outpatient ${float(_outpat_m):.1f}M")
                st.markdown(f"""
                <div class="risk-card">
                    <div class="risk-card-label">Revenue at Risk</div>
                    <div class="risk-card-value" style="color:{_rev_col}">
                        ${_rev_f:.2f}B</div>
                    <div class="risk-card-breakdown">{_sub_str}</div>
                    <div class="risk-card-sub">Combined inpatient + outpatient gap</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(kpi("Revenue at Risk", "N/A"), unsafe_allow_html=True)

        with rd2:
            _pen     = safe_val(hosp, "penalty_count", None, None)
            _hf_p    = safe_val(hosp, "hf_penalty_flag", None, None)
            _pn_p    = safe_val(hosp, "pn_penalty_flag", None, None)
            _ami_p   = safe_val(hosp, "ami_penalty_flag", None, None)
            if _pen is not None:
                _pen_i   = int(_pen)
                _pen_col = "#dc2626" if _pen_i >= 2 else "#d97706" if _pen_i == 1 else "#16a34a"
                _pen_lbl = (f"{_pen_i} condition{'s' if _pen_i != 1 else ''} penalized"
                            if _pen_i > 0 else "No active penalties")
                _flags = []
                if _hf_p  is not None and int(_hf_p)  == 1: _flags.append("HF")
                if _pn_p  is not None and int(_pn_p)  == 1: _flags.append("PN")
                if _ami_p is not None and int(_ami_p) == 1: _flags.append("AMI")
                _hrrp_str = "HRRP: " + " · ".join(_flags) if _flags else "No HRRP flags"
                st.markdown(f"""
                <div class="risk-card">
                    <div class="risk-card-label">CMS Penalty Exposure</div>
                    <div class="risk-card-value" style="color:{_pen_col}">
                        {_pen_i}</div>
                    <div class="risk-card-breakdown">{_pen_lbl}</div>
                    <div class="risk-card-sub">{_hrrp_str}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(kpi("CMS Penalty Exposure", "N/A"), unsafe_allow_html=True)

        with rd3:
            _hr = safe_val(hosp, "high_risk_claims",  None, None)
            _mr = safe_val(hosp, "medium_risk_claims", None, None)
            _lr = safe_val(hosp, "low_risk_claims",    None, None)
            _ds = safe_val(hosp, "avg_denial_risk_score", None, None)
            if _hr is not None and _mr is not None and _lr is not None:
                _tot    = int(_hr) + int(_mr) + int(_lr)
                _hr_pct = round(int(_hr) / _tot * 100, 1) if _tot > 0 else 0
                _dr_col = "#dc2626" if _hr_pct > 33 else "#d97706" if _hr_pct > 20 else "#16a34a"
                _ds_str = f"Avg score {float(_ds):.4f} · {int(_hr):,} claims flagged" if _ds is not None else f"{int(_hr):,} claims flagged"
                st.markdown(f"""
                <div class="risk-card">
                    <div class="risk-card-label">Denial Risk</div>
                    <div class="risk-card-value" style="color:{_dr_col}">
                        {_hr_pct:.1f}%</div>
                    <div class="risk-card-breakdown">of claims are high risk</div>
                    <div class="risk-card-sub">{_ds_str}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(kpi("Denial Risk", "N/A"), unsafe_allow_html=True)

        # ── PERFORMANCE RADAR ────────────────────────────────────────
        if not benchmarks.empty:
            radar_fig = _radar_chart(benchmarks.iloc[0])
            if radar_fig is not None:
                st.markdown("<br>", unsafe_allow_html=True)
                section_header("Performance Radar — National Percentile Ranks")
                st.caption(
                    "Each axis shows this hospital's national percentile (0 = worst, "
                    "100 = best). Denial Protection, Revenue Efficiency, and Payment "
                    "Adequacy are inverted so larger always means better."
                )
                st.plotly_chart(radar_fig, use_container_width=True)

        # ── NATIONAL PERCENTILE RANKS ─────────────────────────────
        if not benchmarks.empty:
            bm = benchmarks.iloc[0]

            def pct_card(label, pct_col, val_col, fmt, higher_is_better=True):
                try:
                    pct = float(bm[pct_col])
                    val = fmt(float(bm[val_col]))
                    color = ("#16a34a" if (pct >= 60 if higher_is_better else pct <= 40)
                             else "#dc2626" if (pct <= 30 if higher_is_better else pct >= 70)
                             else "#d97706")
                    return (
                        f'<div class="kpi-card">'
                        f'<div class="kpi-label">{label}</div>'
                        f'<div class="kpi-value-sm">{val}</div>'
                        f'<div style="font-size:0.72rem;color:{color};font-weight:700;'
                        f'margin-top:3px">{pct:.0f}<sup>th</sup> national percentile</div>'
                        f'</div>'
                    )
                except Exception:
                    return kpi(label, "N/A", small=True)

            st.markdown("<br>", unsafe_allow_html=True)
            section_header("National Percentile Ranks")
            n1, n2, n3 = st.columns(3)
            n4, n5, n6 = st.columns(3)
            n1.markdown(pct_card("360 Score",        "hospital_360_percentile",
                "hospital_360_score",   lambda v: f"{v:.1f}",  True),  unsafe_allow_html=True)
            n2.markdown(pct_card("RCM Health Score",  "rcm_health_percentile",
                "rcm_health_score",     lambda v: f"{v:.1f}",  True),  unsafe_allow_html=True)
            n3.markdown(pct_card("CTP Ratio",         "ctp_percentile",
                "inpatient_avg_ctp",    lambda v: f"{v:.2f}x", False), unsafe_allow_html=True)
            n4.markdown(pct_card("Underpayment Rate", "underpayment_percentile",
                "inpatient_underpayment_rate", lambda v: f"{v:.1f}%", False), unsafe_allow_html=True)
            n5.markdown(pct_card("Denial Risk Score", "denial_risk_percentile",
                "avg_denial_risk_score", lambda v: f"{v:.4f}", False), unsafe_allow_html=True)
            n6.markdown(pct_card("Revenue Gap",       "revenue_gap_percentile",
                "combined_revenue_gap_billions", lambda v: f"${v:.2f}B", False), unsafe_allow_html=True)

        # ── TABS ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs([
            "Financial", "CMS Programs", "Patient Experience", "Denial Intelligence"])

        with tab1:
            _render_financial_tab(hosp)

        with tab2:
            _render_cms_tab(hosp)

        with tab3:
            _render_experience_tab(hosp)

        with tab4:
            _render_denial_tab(hosp)

    else:
        st.info("Search for a hospital above to see their 360 profile.")


# ── RADAR CHART ───────────────────────────────────────────────────────────────

def _radar_chart(bm) -> go.Figure | None:
    cats = [
        "Financial<br>Health", "Overall<br>Performance",
        "Denial<br>Protection", "Revenue<br>Efficiency",
        "Payment<br>Adequacy",
    ]
    try:
        vals = [
            float(bm["rcm_health_percentile"]),
            float(bm["hospital_360_percentile"]),
            100 - float(bm["denial_risk_percentile"]),
            100 - float(bm["revenue_gap_percentile"]),
            100 - float(bm["underpayment_percentile"]),
        ]
    except Exception:
        return None

    vals_c = vals + [vals[0]]
    cats_c = cats + [cats[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[50] * len(vals_c), theta=cats_c,
        fill="toself",
        fillcolor="rgba(148,163,184,0.07)",
        line=dict(color="#cbd5e1", width=1.5, dash="dot"),
        name="National Median",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c,
        fill="toself",
        fillcolor="rgba(37,99,235,0.12)",
        line=dict(color="#2563eb", width=2.5),
        name="This Hospital",
        hovertemplate="%{theta}: %{r:.0f}th percentile<extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickvals=[25, 50, 75, 100],
                ticktext=["25th", "50th", "75th", "100th"],
                tickfont=dict(size=8, color="#94a3b8"),
                gridcolor="#f1f5f9",
                linecolor="#e2e8f0",
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color="#334155"),
                linecolor="#e2e8f0",
                gridcolor="#f1f5f9",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="center", x=0.5, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=50),
        height=340,
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ── TAB RENDERERS ────────────────────────────────────────────────────────────

def _render_financial_tab(hosp):
    _NAT_CTP   = 3.5
    _NAT_UNDP  = 30.0

    section_header("Inpatient Performance")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("Discharges",
        f"{int(hosp['inpatient_discharges']):,}", "Inpatient volume"),
        unsafe_allow_html=True)

    _ctp = hosp['inpatient_avg_ctp']
    _ctp_status = "bad" if _ctp > _NAT_CTP * 1.2 else "warn" if _ctp > _NAT_CTP else "good"
    c2.markdown(kpi_benchmark("CTP Ratio", f"{_ctp:.2f}x",
        f"Natl avg {_NAT_CTP}x — {'above' if _ctp > _NAT_CTP else 'below'} benchmark",
        status=_ctp_status), unsafe_allow_html=True)

    _und = hosp['inpatient_underpayment_rate']
    _und_status = "bad" if _und > _NAT_UNDP * 1.5 else "warn" if _und > _NAT_UNDP else "good"
    c3.markdown(kpi_benchmark("Underpayment Rate", f"{_und:.1f}%",
        f"Natl avg {_NAT_UNDP}% — {'above' if _und > _NAT_UNDP else 'below'} benchmark",
        status=_und_status), unsafe_allow_html=True)

    c4.markdown(kpi_card("Revenue Gap",
        safe_val(hosp, "inpatient_revenue_gap_millions", lambda v: f"${v:.1f}M"),
        "Inpatient leakage"),
        unsafe_allow_html=True)

    _out_ben = safe_val(hosp, "outpatient_beneficiaries", None, None)
    _out_ctp = safe_val(hosp, "outpatient_avg_ctp", None, None)
    _out_und = safe_val(hosp, "outpatient_underpayment_rate", None, None)
    _out_gap = safe_val(hosp, "outpatient_revenue_gap_millions", None, None)

    if any(v is not None for v in [_out_ben, _out_ctp, _out_und, _out_gap]):
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Outpatient Performance")
        o1, o2, o3, o4 = st.columns(4)
        o1.markdown(kpi_card("Beneficiaries",
            f"{int(_out_ben):,}" if _out_ben is not None else "N/A",
            "Outpatient volume"),
            unsafe_allow_html=True)
        o2.markdown(kpi_card("CTP Ratio",
            f"{float(_out_ctp):.2f}x" if _out_ctp is not None else "N/A",
            "Charge-to-payment"),
            unsafe_allow_html=True)
        o3.markdown(kpi_card("Underpayment Rate",
            f"{float(_out_und):.1f}%" if _out_und is not None else "N/A",
            "Claims paid below cost"),
            unsafe_allow_html=True)
        o4.markdown(kpi_card("Revenue Gap",
            f"${float(_out_gap):.1f}M" if _out_gap is not None else "N/A",
            "Outpatient leakage"),
            unsafe_allow_html=True)

    drg_hosp = _drg_data(str(hosp['provider_id']))

    if not drg_hosp.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Top 3 DRGs Driving Revenue Loss")
        top3 = drg_hosp.head(3)
        d1, d2, d3 = st.columns(3)
        for col_obj, (_, drow) in zip([d1, d2, d3], top3.iterrows()):
            _ctp_v = drow.get("ctp_ratio")
            _gap_v = drow.get("revenue_gap_pct")
            _desc  = str(drow.get("drg_description", ""))
            _short = _desc[:48] + "…" if len(_desc) > 48 else _desc
            col_obj.markdown(kpi_card(
                f"DRG {drow.get('drg_code', '')}",
                f"{int(drow.get('total_discharges', 0)):,} cases",
                f"CTP {_ctp_v:.2f}x · Gap {_gap_v:.1f}% · {_short}"
                if _ctp_v and _gap_v else _short
            ), unsafe_allow_html=True)

        with st.expander("View all DRGs"):
            render_table(drg_hosp, height=320)
            st.download_button(
                "Export DRGs",
                data=drg_hosp.to_csv(index=False),
                file_name=f"{hosp['provider_name'].replace(' ', '_')}_drgs.csv",
                mime="text/csv")


def _render_cms_tab(hosp):
    if pd.isna(hosp['avg_mortality_rate']):
        st.info("CMS quality data not available for this hospital.")
        return

    _w = safe_val(hosp, "worse_mortality_flag",  None, None)
    _b = safe_val(hosp, "better_mortality_flag", None, None)
    if _w is not None and int(_w) == 1:
        _interp       = "Above national average mortality — clinical improvement focus recommended."
        _interp_color = "#dc2626"
    elif _b is not None and int(_b) == 1:
        _interp       = "Below national average mortality — strong clinical performance."
        _interp_color = "#16a34a"
    else:
        _interp       = "Mortality rates are similar to national average."
        _interp_color = "#d97706"
    st.markdown(
        f'<div style="font-size:0.8rem;font-weight:600;color:{_interp_color};'
        f'margin-bottom:14px">{_interp}</div>',
        unsafe_allow_html=True)

    # ── HRRP ──────────────────────────────────────────────────────
    section_header(
        "HRRP — Excess Readmission Ratios "
        "(below 1.0 = better than expected · above 1.0 = penalty risk)")

    def readm_kpi(label, col):
        v = safe_val(hosp, col, None, None)
        if v is None:
            return kpi(label, "N/A", small=True)
        fv    = float(v)
        color = "#dc2626" if fv > 1.0 else "#16a34a" if fv < 1.0 else "#d97706"
        badge = "Above expected — penalty risk" if fv > 1.0 else "Below expected" if fv < 1.0 else "At expected"
        return (f'<div class="kpi-card">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value-sm" style="color:{color}">{fv:.3f}</div>'
                f'<div style="font-size:0.65rem;color:{color};font-weight:600;margin-top:2px">'
                f'{badge}</div></div>')

    r1, r2, r3 = st.columns(3)
    r1.markdown(readm_kpi("Heart Failure",  "readm_ratio_hf"),       unsafe_allow_html=True)
    r2.markdown(readm_kpi("Pneumonia",      "readm_ratio_pn"),       unsafe_allow_html=True)
    r3.markdown(readm_kpi("Heart Attack",   "readm_ratio_ami"),      unsafe_allow_html=True)

    r4, r5, r6 = st.columns(3)
    r4.markdown(readm_kpi("Hip / Knee",     "readm_ratio_hip_knee"), unsafe_allow_html=True)
    r5.markdown(readm_kpi("COPD",           "readm_ratio_copd"),     unsafe_allow_html=True)
    r6.markdown(readm_kpi("CABG",           "readm_ratio_cabg"),     unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    avg_ratio   = safe_val(hosp, "avg_excess_readmission_ratio", None, None)
    penalty     = safe_val(hosp, "penalty_count", None, None)
    psi_90      = safe_val(hosp, "psi_90_safety", None, None)

    s1, s2, s3 = st.columns(3)

    if avg_ratio is not None:
        ratio_color = ("#dc2626" if float(avg_ratio) > 1.0
                       else "#16a34a" if float(avg_ratio) < 1.0
                       else "#d97706")
        s1.markdown(f"""<div class="kpi-card" style="text-align:center">
            <div class="kpi-label">Avg Excess Readmission Ratio</div>
            <div class="kpi-value" style="color:{ratio_color}">
                {float(avg_ratio):.3f}</div>
            <div style="font-size:0.65rem;color:{ratio_color};font-weight:600;margin-top:2px">
                {"above expected" if float(avg_ratio) > 1.0
                 else "below expected" if float(avg_ratio) < 1.0 else "at expected"}</div>
        </div>""", unsafe_allow_html=True)

    if penalty is not None:
        pen_color = ("#dc2626" if int(penalty) >= 3
                     else "#d97706" if int(penalty) >= 1
                     else "#16a34a")
        s2.markdown(f"""<div class="kpi-card" style="text-align:center">
            <div class="kpi-label">CMS Penalty Count</div>
            <div class="kpi-value" style="color:{pen_color}">
                {int(penalty)}</div>
            <div style="font-size:0.65rem;color:{pen_color};font-weight:600;margin-top:2px">
                {"conditions penalized" if int(penalty) > 0 else "no active penalties"}</div>
        </div>""", unsafe_allow_html=True)

    if psi_90 is not None:
        s3.markdown(kpi("Patient Safety (PSI-90)", f"{float(psi_90):.3f}", small=True),
                    unsafe_allow_html=True)

    # ── 30-DAY MORTALITY ──────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("30-Day Mortality Rates (lower is better)")
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(kpi("Heart Failure", safe_val(hosp, "mort_30_hf",  lambda v: f"{v:.1f}%")),
                unsafe_allow_html=True)
    m2.markdown(kpi("Pneumonia",     safe_val(hosp, "mort_30_pn",  lambda v: f"{v:.1f}%")),
                unsafe_allow_html=True)
    m3.markdown(kpi("Heart Attack",  safe_val(hosp, "mort_30_ami", lambda v: f"{v:.1f}%")),
                unsafe_allow_html=True)
    m4.markdown(kpi("Stroke",        safe_val(hosp, "mort_30_stk", lambda v: f"{v:.1f}%")),
                unsafe_allow_html=True)

    nat_color = ("#dc2626" if hosp['worse_mortality_flag']  == 1
                 else "#16a34a" if hosp['better_mortality_flag'] == 1
                 else "#d97706")
    nat_label = ("Worse than national"  if hosp['worse_mortality_flag']  == 1
                 else "Better than national" if hosp['better_mortality_flag'] == 1
                 else "Similar to national")
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
        f'padding:12px 20px;margin-top:10px;display:flex;'
        f'align-items:center;justify-content:space-between">'
        f'<div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;'
        f'letter-spacing:0.8px;font-weight:700">Avg 30-Day Mortality</div>'
        f'<div style="display:flex;align-items:baseline;gap:10px">'
        f'<span style="font-size:1.5rem;font-weight:800;color:{nat_color};letter-spacing:-0.5px">'
        f'{hosp["avg_mortality_rate"]:.1f}%</span>'
        f'<span style="font-size:0.78rem;color:{nat_color};font-weight:600">'
        f'{nat_label}</span>'
        f'</div></div>',
        unsafe_allow_html=True)


def _render_experience_tab(hosp):
    if pd.isna(hosp['overall_star_rating']):
        st.info("Patient experience data not available for this hospital.")
        return

    stars     = int(hosp['overall_star_rating'])
    star_disp = "★" * stars + "☆" * (5 - stars)
    _rec_val  = safe_val(hosp, 'pct_definitely_recommend', lambda v: f'{v:.0f}%')

    pe1, pe2 = st.columns(2)
    pe1.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Overall Star Rating</div>
        <div style="font-size:1.6rem;color:#f59e0b;letter-spacing:2px;margin:4px 0 2px 0">
            {star_disp}</div>
        <div class="kpi-subtitle">{stars} out of 5 stars (HCAHPS)</div>
    </div>""", unsafe_allow_html=True)
    pe2.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Definitely Recommend</div>
        <div class="kpi-value">{_rec_val}</div>
        <div class="kpi-subtitle">of patients would definitely recommend</div>
    </div>""", unsafe_allow_html=True)

    section_header("Domain Star Ratings")
    c1, c2, c3, c4 = st.columns(4)

    def star_kpi(label, col):
        v = safe_val(hosp, col, None, None)
        if v is None:
            return kpi(label, "N/A", small=True)
        s = int(v)
        return kpi(label, "★" * s + "☆" * (5 - s), small=True)

    c1.markdown(star_kpi("Nurse Communication",  "nurse_star_rating"),  unsafe_allow_html=True)
    c2.markdown(star_kpi("Doctor Communication", "doctor_star_rating"), unsafe_allow_html=True)
    c3.markdown(star_kpi("Cleanliness",          "cleanliness_star_rating"), unsafe_allow_html=True)
    c4.markdown(star_kpi("Quietness",            "quietness_star_rating"),   unsafe_allow_html=True)

    _n_lin = safe_val(hosp, "nurse_linear_score",        None, None)
    _d_lin = safe_val(hosp, "doctor_linear_score",       None, None)
    _c_lin = safe_val(hosp, "cleanliness_linear_score",  None, None)
    _q_lin = safe_val(hosp, "quietness_linear_score",    None, None)
    _r_lin = safe_val(hosp, "recommend_linear_score",    None, None)
    _o_lin = safe_val(hosp, "overall_rating_linear_score", None, None)

    if any(v is not None for v in [_n_lin, _d_lin, _c_lin, _q_lin, _r_lin, _o_lin]):
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("HCAHPS Linear Mean Scores (0–100 · used in CMS HVBP scoring)")
        l1, l2, l3 = st.columns(3)
        l4, l5, l6 = st.columns(3)
        l1.markdown(kpi("Nurse Communication",
            f"{float(_n_lin):.1f}" if _n_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)
        l2.markdown(kpi("Doctor Communication",
            f"{float(_d_lin):.1f}" if _d_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)
        l3.markdown(kpi("Cleanliness",
            f"{float(_c_lin):.1f}" if _c_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)
        l4.markdown(kpi("Quietness",
            f"{float(_q_lin):.1f}" if _q_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)
        l5.markdown(kpi("Recommend",
            f"{float(_r_lin):.1f}" if _r_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)
        l6.markdown(kpi("Overall Rating",
            f"{float(_o_lin):.1f}" if _o_lin is not None else "N/A", small=True),
            unsafe_allow_html=True)

    _rec_pct = safe_val(hosp, "pct_probably_recommend", None, None)
    _not_rec = safe_val(hosp, "pct_not_recommend",      None, None)
    if _rec_pct is not None or _not_rec is not None:
        with st.expander("Recommend breakdown"):
            pb1, pb2 = st.columns(2)
            if _rec_pct is not None:
                pb1.markdown(kpi("Probably Recommend",
                    f"{float(_rec_pct):.0f}%", small=True),
                    unsafe_allow_html=True)
            if _not_rec is not None:
                pb2.markdown(kpi("Would Not Recommend",
                    f"{float(_not_rec):.0f}%", small=True),
                    unsafe_allow_html=True)


def _render_denial_tab(hosp):
    _hr = safe_val(hosp, "high_risk_claims",   None, None)
    _mr = safe_val(hosp, "medium_risk_claims",  None, None)
    _lr = safe_val(hosp, "low_risk_claims",     None, None)
    if _hr is not None and _mr is not None and _lr is not None:
        _total_claims = int(_hr) + int(_mr) + int(_lr)
        _hr_pct = round(int(_hr) / _total_claims * 100, 1) if _total_claims > 0 else 0
        if _hr_pct > 33:
            insight_card(
                f"<strong>Denial Risk Alert:</strong> <strong>{_hr_pct}%</strong> of claims "
                f"({int(_hr):,}) are high risk — pre-submission review recommended."
            )
        else:
            insight_card(
                f"<strong>Denial Risk:</strong> <strong>{_hr_pct}%</strong> of claims "
                f"({int(_hr):,}) are high risk — within manageable range."
            )

    c1, c2 = st.columns(2)
    with c1:
        section_header("Risk Distribution")
        _total_c = int(_hr) + int(_mr) + int(_lr)
        if _total_c > 0:
            def _dseg(label, cnt, color, text_color):
                pct = round(int(cnt) / _total_c * 100, 1)
                return (
                    f'<div style="flex:{pct};background:{color};'
                    f'display:flex;flex-direction:column;align-items:center;'
                    f'justify-content:center;padding:14px 8px;min-width:50px">'
                    f'<div style="font-size:0.6rem;font-weight:700;color:{text_color};'
                    f'text-transform:uppercase;letter-spacing:0.5px">{label}</div>'
                    f'<div style="font-size:1.2rem;font-weight:800;color:{text_color};'
                    f'letter-spacing:-0.5px;margin:2px 0">{int(cnt):,}</div>'
                    f'<div style="font-size:0.65rem;font-weight:600;color:{text_color};'
                    f'opacity:0.75">{pct}%</div>'
                    f'</div>'
                )
            st.markdown(
                '<div style="display:flex;border-radius:8px;overflow:hidden;'
                'border:1px solid #e2e8f0;height:90px;margin-top:8px">'
                + _dseg("High",   _hr, "#fee2e2", "#dc2626")
                + _dseg("Medium", _mr, "#fef9c3", "#92400e")
                + _dseg("Low",    _lr, "#dcfce7", "#166534")
                + '</div>',
                unsafe_allow_html=True,
            )

    with c2:
        section_header("Denial Risk Score")
        risk_score = float(hosp["avg_denial_risk_score"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_score,
            number={"font": {"color": "#0f172a", "size": 36},
                    "valueformat": ".3f"},
            domain={"x": [0, 1], "y": [0.15, 1]},
            gauge={
                "axis": {"range": [0, 1], "tickcolor": "#94a3b8",
                          "tickfont": {"color": "#94a3b8", "size": 9}},
                "bar":  {"color": "#2563eb", "thickness": 0.25},
                "bgcolor": "#f8fafc",
                "borderwidth": 1, "bordercolor": "#e2e8f0",
                "steps": [
                    {"range": [0,   0.3], "color": "#dcfce7"},
                    {"range": [0.3, 0.6], "color": "#fef9c3"},
                    {"range": [0.6, 1.0], "color": "#fee2e2"},
                ],
                "threshold": {"line": {"color": "#dc2626", "width": 2},
                               "thickness": 0.75, "value": 0.6},
            },
        ))
        fig.update_layout(paper_bgcolor="#ffffff",
                           font=dict(color="#334155"),
                           height=260,
                           margin=dict(l=20, r=20, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
