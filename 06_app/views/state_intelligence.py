import plotly.express as px
import streamlit as st

from config import GRADE_COLORS, STATES
from db import run_query
from utils import kpi, navigate_to_hospital, render_risk_table, render_table, section_header, style_fig


# ── CACHED LOADERS ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _state_summary(state: str):
    return run_query(f"""
        SELECT hospital_count                  AS hospitals,
               total_discharges,
               avg_ctp_ratio                  AS avg_ctp,
               inpatient_revenue_gap_billions  AS revenue_gap_b,
               outpatient_revenue_gap_billions AS out_gap,
               ROUND(inpatient_revenue_gap_billions + outpatient_revenue_gap_billions, 2)
                   AS total_gap_b,
               underpayment_rate_pct           AS underpayment_rate
        FROM rcm_platform.rcm_gold.dashboard_state_summary
        WHERE provider_state = '{state}'
        LIMIT 1
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _peer_scatter(state: str, hosp_type: str):
    type_sql = f"AND hospital_type = '{hosp_type}'" if hosp_type else ""
    return run_query(f"""
        SELECT provider_id, provider_name, hospital_type,
               rcm_health_score, hospital_360_score,
               overall_star_rating, pct_definitely_recommend,
               hospital_360_grade
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        WHERE provider_state = '{state}'
          AND hospital_360_score IS NOT NULL
          AND rcm_health_score IS NOT NULL
          {type_sql}
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _hospital_id_lookup(state: str):
    return run_query(f"""
        SELECT provider_id, provider_name
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        WHERE provider_state = '{state}'
        ORDER BY inpatient_discharges DESC
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _hospital_table(state: str, hosp_type: str):
    type_sql = f"AND hospital_type = '{hosp_type}'" if hosp_type else ""
    return run_query(f"""
        SELECT provider_name, provider_city, hospital_type,
               inpatient_discharges,
               ROUND(inpatient_avg_ctp,2)     AS inpatient_ctp,
               ROUND(inpatient_avg_gap_pct,1) AS inpatient_gap_pct,
               rcm_health_score, rcm_health_grade,
               hospital_360_score, hospital_360_grade,
               overall_star_rating, pct_definitely_recommend
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        WHERE provider_state = '{state}' {type_sql}
        ORDER BY inpatient_discharges DESC
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _denial_by_hospital(state: str):
    return run_query(f"""
        SELECT h.provider_name,
               ROUND(AVG(d.denial_risk_score),4) AS avg_denial_risk
        FROM rcm_platform.rcm_gold.denial_risk_scores d
        JOIN rcm_platform.rcm_gold.hospital_scorecard h
            ON d.provider_id = h.provider_id
        WHERE h.provider_state = '{state}'
        GROUP BY h.provider_name
        ORDER BY avg_denial_risk DESC LIMIT 15
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _top_drgs(state: str):
    return run_query(f"""
        SELECT drg_code, drg_description,
               SUM(total_discharges)                        AS discharges,
               ROUND(AVG(charge_to_payment_ratio),2)        AS avg_ctp,
               ROUND(SUM(total_revenue_gap)/1e6,2)          AS revenue_gap_millions,
               ROUND(SUM(underpayment_flag)/COUNT(*)*100,1) AS underpayment_rate
        FROM (SELECT DISTINCT provider_id, drg_code, drg_description,
                     total_discharges, charge_to_payment_ratio,
                     total_revenue_gap, underpayment_flag
              FROM rcm_platform.rcm_gold.fact_claims
              WHERE provider_state = '{state}')
        GROUP BY drg_code, drg_description
        ORDER BY revenue_gap_millions DESC LIMIT 15
    """)


# ── PAGE ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# State Intelligence")
    st.markdown("<p class='page-subtitle'>State-level RCM performance "
                "and peer benchmarking</p>", unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    _preset_state = st.session_state.pop("go_to_state", None)
    if _preset_state and _preset_state in STATES:
        st.session_state["si_state_select"] = _preset_state

    selected_state = st.selectbox("State", STATES, key="si_state_select")

    # ── PEER BENCHMARKING SCATTER (hero visual) ───────────────────
    peer = _peer_scatter(selected_state, "")
    if not peer.empty:
        section_header("Peer Benchmarking — 360 Score vs RCM Score — click any point to open Hospital 360")
        fig = px.scatter(peer,
                         x="rcm_health_score", y="hospital_360_score",
                         color="hospital_360_grade",
                         color_discrete_map=GRADE_COLORS,
                         hover_name="provider_name",
                         hover_data={"hospital_type": True,
                                     "overall_star_rating": True,
                                     "pct_definitely_recommend": True,
                                     "hospital_360_grade": False,
                                     "provider_id": False},
                         labels={"rcm_health_score":  "RCM Score",
                                 "hospital_360_score": "360 Score"})
        fig = style_fig(fig,
                        xaxis_title="RCM Health Score (0–100)",
                        yaxis_title="Hospital 360 Score (0–100)",
                        height=400)
        fig.update_layout(
            xaxis=dict(range=[0, 100]),
            yaxis=dict(range=[0, 100]),
            legend=dict(title="Grade", font=dict(size=10)))
        fig.add_shape(type="line", x0=50, y0=0, x1=50, y1=100,
                      line=dict(color="#e2e8f0", width=1, dash="dot"))
        fig.add_shape(type="line", x0=0, y0=50, x1=100, y1=50,
                      line=dict(color="#e2e8f0", width=1, dash="dot"))
        for x, y, txt in [
            (75, 94, "★  Star Performers"),
            (25, 94, "Quality Leaders"),
            (75,  6, "Revenue Focused"),
            (25,  6, "Needs Intervention"),
        ]:
            fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                               font=dict(size=9, color="#94a3b8"), opacity=0.9)
        scatter_event = st.plotly_chart(
            fig, use_container_width=True, on_select="rerun", key="si_peer_scatter"
        )
        try:
            pts = scatter_event.selection.point_indices
            if pts:
                clicked_h = peer.iloc[pts[0]]
                navigate_to_hospital(
                    str(clicked_h["provider_id"]),
                    str(clicked_h["provider_name"]),
                    selected_state,
                )
        except (AttributeError, IndexError, TypeError):
            pass
        st.caption("Hover for details · Click any point to open that hospital's 360 profile. "
                   "Cross-hairs at portfolio midpoint (score = 50).")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── STATE KPIs (3 key metrics, below scatter) ─────────────────
    summary = _state_summary(selected_state)
    if not summary.empty:
        r = summary.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.markdown(kpi("Hospitals",        f"{int(r['hospitals']):,}"),   unsafe_allow_html=True)
        c2.markdown(kpi("Total Revenue Gap", f"${r['total_gap_b']}B"),     unsafe_allow_html=True)
        c3.markdown(kpi("Underpayment Rate", f"{r['underpayment_rate']}%"), unsafe_allow_html=True)
    else:
        st.info(f"No summary data found for {selected_state}.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── HOSPITAL TABLE + DENIAL RISK ─────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        section_header("Hospitals — 360 Scorecard")
        sh = _hospital_table(selected_state, "")
        if not sh.empty:
            render_risk_table(sh, grade_col="hospital_360_grade", height=360)

            nc1, nc2 = st.columns([4, 1])
            with nc1:
                nav_name = st.selectbox(
                    "Navigate to hospital",
                    sh["provider_name"].tolist(),
                    key=f"si_nav_{selected_state}",
                )
            with nc2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("View 360 →", key=f"si_nav_go_{selected_state}",
                             use_container_width=True):
                    hl = _hospital_id_lookup(selected_state)
                    pid_row = hl[hl["provider_name"] == nav_name]
                    pid = str(pid_row.iloc[0]["provider_id"]) if not pid_row.empty else ""
                    navigate_to_hospital(pid, nav_name, selected_state)

            st.download_button(
                "Export",
                data=sh.to_csv(index=False),
                file_name=f"{selected_state}_hospitals.csv",
                mime="text/csv")

    with col2:
        section_header("Denial Risk by Hospital")
        sr = _denial_by_hospital(selected_state)
        if not sr.empty:
            sr_s = sr.sort_values("avg_denial_risk", ascending=True)
            fig = px.bar(sr_s, x="avg_denial_risk", y="provider_name",
                         orientation="h", color="avg_denial_risk",
                         color_continuous_scale=["#fecaca", "#dc2626"],
                         labels={"provider_name":    "",
                                 "avg_denial_risk":  "Denial Risk Score"},
                         category_orders={
                             "provider_name": sr_s["provider_name"].tolist()})
            fig = style_fig(fig, xaxis_title="Avg Denial Risk", height=380)
            fig.update_yaxes(autorange="reversed", tickfont=dict(size=9))
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── TOP DRGs ──────────────────────────────────────────────────
    section_header("Top DRGs by Revenue Leakage")
    sd = _top_drgs(selected_state)
    if not sd.empty:
        render_table(sd, height=360)
        st.download_button(
            "Export",
            data=sd.to_csv(index=False),
            file_name=f"{selected_state}_top_drgs.csv",
            mime="text/csv")
