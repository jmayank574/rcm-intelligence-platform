from concurrent import futures

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import GRADE_COLORS
from db import run_query
from utils import kpi, kpi_card, navigate_to_hospital, navigate_to_state, section_header, style_fig

_QUERIES = {
    "kpis": "SELECT * FROM rcm_platform.rcm_gold.dashboard_executive_kpis",
    "dd":   "SELECT * FROM rcm_platform.rcm_gold.dashboard_drg_leakage ORDER BY rank",
    "sa":   """
        SELECT provider_state,
               inpatient_revenue_gap_billions,
               outpatient_revenue_gap_billions,
               ROUND(inpatient_revenue_gap_billions + outpatient_revenue_gap_billions, 2)
                   AS total_gap_billions
        FROM rcm_platform.rcm_gold.dashboard_state_summary
        ORDER BY total_gap_billions DESC
    """,
    "ar":   "SELECT * FROM rcm_platform.rcm_gold.dashboard_ar_aging ORDER BY bucket_order",
    "gd":   """
        SELECT * FROM rcm_platform.rcm_gold.dashboard_grade_distribution
        WHERE hospital_360_grade != 'Insufficient Data'
        ORDER BY grade_order
    """,
    "dr":   "SELECT * FROM rcm_platform.rcm_gold.dashboard_denial_risk_summary",
    "qh":   "SELECT * FROM rcm_platform.rcm_gold.dashboard_quality_hcahps_summary LIMIT 1",
    "opp":  "SELECT * FROM rcm_platform.rcm_gold.dashboard_top_opportunities ORDER BY revenue_gap_millions DESC",
}


@st.cache_data(ttl=3600, show_spinner=False)
def _load_all():
    """Run all 8 point-reads in parallel; cache the full result in one hit."""
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {key: pool.submit(run_query, q) for key, q in _QUERIES.items()}
        return {key: f.result() for key, f in future_map.items()}


# ── PAGE RENDER ───────────────────────────────────────────────────────────────

def render():
    st.markdown("# Executive Overview")
    st.markdown("<p class='page-subtitle'>National Medicare revenue cycle performance "
                "— portfolio-level intelligence across 3,000+ hospitals</p>",
                unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    data = _load_all()
    kpi_data = data["kpis"]
    dd       = data["dd"]
    sa       = data["sa"]
    ar       = data["ar"]
    gd       = data["gd"]
    dr       = data["dr"]
    qh       = data["qh"]
    opp      = data["opp"]

    if not dd.empty:
        dd["drg_code"] = dd["drg_code"].astype(str)

    # ── A. PORTFOLIO INTELLIGENCE BRIEF ──────────────────────────
    if not kpi_data.empty and not dd.empty:
        r     = kpi_data.iloc[0]
        top_d = dd.iloc[0]
        d_desc  = str(top_d['drg_description'])
        d_short = d_desc[:50] + "…" if len(d_desc) > 50 else d_desc

        high_pct_val = 0
        if not dr.empty:
            total_c  = int(dr['claim_count'].sum())
            high_row = dr[dr['denial_risk_label'].str.contains("High", na=False)]
            high_pct_val = round(int(high_row['claim_count'].sum()) / total_c * 100, 1) if total_c else 0

        state_clause = ""
        if not sa.empty:
            ts = sa.iloc[0]
            state_clause = (f" <strong>{ts['provider_state']}</strong> leads regional exposure "
                            f"at <strong>${ts['total_gap_billions']}B</strong> combined gap.")

        risk_phrase = ("Pre-submission review recommended across portfolio."
                       if high_pct_val > 33 else
                       "Denial patterns within manageable range.")

        st.markdown(
            f'<div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);'
            f'border:1px solid #334155;border-left:4px solid #3b82f6;'
            f'border-radius:0 10px 10px 0;padding:16px 22px;margin-bottom:20px">'
            f'<div style="font-size:0.6rem;font-weight:700;color:#3b82f6;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">'
            f'Portfolio Intelligence Brief</div>'
            f'<div style="font-size:0.88rem;color:#e2e8f0;line-height:1.7">'
            f'Portfolio carries <strong>${r["combined_gap_billions"]}B</strong> in unrealized '
            f'revenue across <strong>{int(r["total_hospitals"]):,}</strong> hospitals. '
            f'DRG {top_d["drg_code"]} ({d_short}) is the single largest exposure at '
            f'<strong>${top_d["revenue_gap_billions"]}B</strong>.{state_clause} '
            f'<strong>{high_pct_val}%</strong> of claims flagged high-risk — {risk_phrase}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── B. PORTFOLIO METRICS ──────────────────────────────────────
    section_header("Portfolio Metrics")
    if not kpi_data.empty:
        r = kpi_data.iloc[0]
        p1, p2, p3 = st.columns(3)
        p1.markdown(kpi_card("Combined Revenue Gap", f"${r['combined_gap_billions']}B",
                              "Unrealized revenue"),     unsafe_allow_html=True)
        p2.markdown(kpi_card("Avg CTP Ratio",         f"{r['avg_ctp_ratio']}x",
                              "Charge-to-payment"),      unsafe_allow_html=True)
        p3.markdown(kpi_card("Underpayment Rate",     f"{r['underpayment_rate_pct']}%",
                              "Claims paid below cost"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        s1.markdown(kpi("Total Hospitals",  f"{int(r['total_hospitals']):,}",     small=True), unsafe_allow_html=True)
        s2.markdown(kpi("States Covered",   f"{int(r['states_covered'])}",        small=True), unsafe_allow_html=True)
        s3.markdown(kpi("Total Discharges", f"{r['total_discharges_millions']}M", small=True), unsafe_allow_html=True)
    else:
        st.warning("Portfolio metrics unavailable — dashboard tables may need refresh.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── C. US CHOROPLETH MAP + GRADE DISTRIBUTION ─────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        section_header("Revenue Gap by State ($B) — click any state to drill down")
        if not sa.empty:
            fig = go.Figure(go.Choropleth(
                locations=sa['provider_state'],
                z=sa['total_gap_billions'],
                locationmode='USA-states',
                colorscale=[[0, '#dbeafe'], [0.5, '#3b82f6'], [1, '#1e3a8a']],
                colorbar=dict(
                    title=dict(text="Gap ($B)", font=dict(size=10, color="#334155")),
                    thickness=12, len=0.65,
                    tickfont=dict(size=9, color="#334155"),
                ),
                hovertemplate='<b>%{location}</b><br>Total Gap: $%{z:.2f}B'
                              '<br><i>Click to open State Intelligence</i><extra></extra>',
            ))
            fig.update_layout(
                geo=dict(scope='usa', bgcolor='rgba(0,0,0,0)',
                         lakecolor='rgba(248,250,252,1)', landcolor='#f1f5f9',
                         showlakes=True, showcoastlines=False, showframe=False),
                margin=dict(l=0, r=0, t=10, b=0), height=300,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif", color="#334155"),
            )
            map_event = st.plotly_chart(
                fig, use_container_width=True, on_select="rerun", key="exec_choropleth"
            )
            try:
                pts = map_event.selection.point_indices
                if pts:
                    navigate_to_state(sa.iloc[pts[0]]["provider_state"])
            except (AttributeError, IndexError, TypeError):
                pass

    with col2:
        section_header("Hospital Grade Distribution")
        if not gd.empty:
            gd_s = gd.sort_values("grade_order")
            fig = px.bar(gd_s, x="hospital_count", y="hospital_360_grade",
                         orientation="h", color="hospital_360_grade",
                         color_discrete_map=GRADE_COLORS, text="hospital_count",
                         labels={"hospital_count": "", "hospital_360_grade": ""})
            fig = style_fig(fig, height=280)
            fig.update_traces(textposition="outside", textfont=dict(size=10))
            fig.update_layout(showlegend=False,
                               yaxis=dict(tickfont=dict(size=11, color="#334155")),
                               xaxis=dict(showticklabels=False, showgrid=False))
            st.plotly_chart(fig, use_container_width=True)

    # ── D. TOP DRGs ───────────────────────────────────────────────
    section_header("Top DRGs by Revenue Leakage")
    if not dd.empty:
        dd_plot = dd.sort_values("revenue_gap_billions", ascending=False).head(10)
        fig = px.bar(dd_plot, x="revenue_gap_billions", y="drg_code",
                     orientation="h", color="revenue_gap_billions",
                     color_continuous_scale=["#bfdbfe", "#1d4ed8"],
                     hover_data={"drg_description": True},
                     labels={"drg_code": "", "revenue_gap_billions": "Gap ($B)"},
                     category_orders={"drg_code": dd_plot["drg_code"].tolist()})
        fig = style_fig(fig, xaxis_title="Revenue Gap ($B)")
        fig.update_layout(coloraxis_showscale=False,
                           yaxis=dict(type="category",
                                      tickfont=dict(size=11, color="#334155")))
        fig.update_traces(
            text=dd_plot["revenue_gap_billions"].apply(lambda x: f"${x}B"),
            textposition="outside", textfont=dict(size=10))
        st.plotly_chart(fig, use_container_width=True)

    # ── E. AR AGING ───────────────────────────────────────────────
    section_header("AR Aging — Revenue at Risk ($B)")
    if not ar.empty:
        fig = px.bar(ar, x="ar_aging_bucket", y="revenue_at_risk_billions",
                     color="ar_aging_bucket",
                     color_discrete_sequence=["#86efac", "#fde68a", "#fb923c", "#f87171"],
                     text="revenue_at_risk_billions",
                     labels={"ar_aging_bucket": "", "revenue_at_risk_billions": "($B)"})
        fig = style_fig(fig, height=230)
        fig.update_traces(texttemplate="$%{y}B", textposition="outside",
                          textfont=dict(size=10))
        fig.update_layout(showlegend=False)
        if len(ar) >= 4:
            last = ar.iloc[-1]
            fig.add_annotation(
                x=last['ar_aging_bucket'], y=float(last['revenue_at_risk_billions']),
                text="Recovery risk", showarrow=True, arrowhead=2, arrowcolor="#dc2626",
                font=dict(size=9, color="#dc2626"), ay=-36, ax=0)
        st.plotly_chart(fig, use_container_width=True)

    # ── F. QUALITY + DENIAL RISK ──────────────────────────────────
    section_header("National Quality and Patient Experience")
    if not qh.empty:
        r = qh.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi("Avg 30-Day Mortality Rate",  f"{r['national_avg_mortality_rate']}%", small=True), unsafe_allow_html=True)
        c2.markdown(kpi("Avg Patient Star Rating",    f"{r['national_avg_star_rating']} / 5", small=True), unsafe_allow_html=True)
        c3.markdown(kpi("Would Definitely Recommend", f"{r['national_avg_pct_recommend']}%",  small=True), unsafe_allow_html=True)
        c4.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Mortality vs National Benchmark</div>
            <div style="margin-top:6px;font-size:0.8rem;color:#334155;line-height:1.6">
                <span style="color:#16a34a;font-weight:700">{int(r['hospitals_better_mortality'])} better</span>
                &nbsp;·&nbsp;
                <span style="color:#dc2626;font-weight:700">{int(r['hospitals_worse_mortality'])} worse</span>
                <br><span style="color:#94a3b8;font-size:0.72rem">than national average</span>
            </div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("Denial Risk Distribution")
    if not dr.empty:
        total = int(dr["claim_count"].sum())
        rows  = {r["denial_risk_label"]: r for _, r in dr.iterrows()}

        def _seg(label, color, text_color):
            row = next((v for k, v in rows.items() if label in k), None)
            if row is None:
                return "", 0
            cnt = int(row["claim_count"])
            pct = round(cnt / total * 100, 1) if total else 0
            seg = (f'<div style="flex:{pct};background:{color};'
                   f'display:flex;flex-direction:column;align-items:center;'
                   f'justify-content:center;padding:14px 8px;min-width:60px">'
                   f'<div style="font-size:0.62rem;font-weight:700;color:{text_color};'
                   f'text-transform:uppercase;letter-spacing:0.6px">{label}</div>'
                   f'<div style="font-size:1.3rem;font-weight:800;color:{text_color};'
                   f'letter-spacing:-0.5px;margin:2px 0">{cnt:,}</div>'
                   f'<div style="font-size:0.65rem;font-weight:600;color:{text_color};'
                   f'opacity:0.75">{pct}%</div>'
                   f'</div>')
            return seg, pct

        high_seg, high_pct = _seg("High",   "#fee2e2", "#dc2626")
        med_seg,  _        = _seg("Medium", "#fef9c3", "#92400e")
        low_seg,  _        = _seg("Low",    "#dcfce7", "#166534")

        alert = ""
        if high_pct > 33:
            alert = (f'<div style="background:#fff1f2;border:1px solid #fecdd3;'
                     f'border-left:3px solid #dc2626;border-radius:6px;'
                     f'padding:9px 14px;margin-bottom:10px;font-size:0.78rem;'
                     f'color:#be123c;font-weight:500">'
                     f'<strong>{high_pct}% of claims are high-risk for denial</strong> '
                     f'— pre-submission review is recommended across the portfolio.</div>')

        st.markdown(
            alert +
            '<div style="display:flex;border-radius:8px;overflow:hidden;'
            'border:1px solid #e2e8f0;height:80px">'
            + high_seg + med_seg + low_seg + '</div>',
            unsafe_allow_html=True,
        )

    # ── G. TOP RECOVERY OPPORTUNITIES ────────────────────────────
    if not opp.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Top Recovery Opportunities")
        st.caption(
            "Highest-value hospital + DRG combinations with elevated denial risk "
            "— click View → to open the full Hospital 360 profile."
        )
        opp["drg_code"] = opp["drg_code"].astype(str)
        for idx, o in opp.iterrows():
            drisk      = float(o['avg_denial_risk'])
            risk_color = "#dc2626" if drisk > 0.6 else "#d97706" if drisk > 0.4 else "#16a34a"
            risk_label = "High Risk" if drisk > 0.6 else "Medium Risk" if drisk > 0.4 else "Elevated"
            desc       = str(o['drg_description'])
            desc_short = desc[:58] + "…" if len(desc) > 58 else desc
            pid        = str(o["provider_id"]) if "provider_id" in o else ""

            oc1, oc2 = st.columns([9, 1])
            with oc1:
                st.markdown(
                    f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
                    f'border-radius:8px;padding:12px 16px;'
                    f'display:flex;align-items:center;justify-content:space-between">'
                    f'<div style="flex:1;min-width:0">'
                    f'<div style="font-size:0.82rem;font-weight:700;color:#0f172a;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                    f'{o["provider_name"]}</div>'
                    f'<div style="font-size:0.72rem;color:#64748b;margin-top:2px">'
                    f'{o["provider_state"]} &nbsp;·&nbsp; DRG {o["drg_code"]} — {desc_short}</div>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:16px;margin-left:16px">'
                    f'<div style="text-align:right">'
                    f'<div style="font-size:0.6rem;color:#94a3b8;text-transform:uppercase;'
                    f'font-weight:600;letter-spacing:0.4px">Revenue Gap</div>'
                    f'<div style="font-size:1rem;font-weight:700;color:#0f172a">'
                    f'${o["revenue_gap_millions"]:.1f}M</div>'
                    f'</div>'
                    f'<div style="background:{risk_color}1a;border:1px solid {risk_color}40;'
                    f'border-radius:6px;padding:5px 12px;text-align:center;min-width:80px">'
                    f'<div style="font-size:0.6rem;color:{risk_color};font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:0.4px">{risk_label}</div>'
                    f'<div style="font-size:0.85rem;font-weight:700;color:{risk_color}">'
                    f'{drisk:.3f}</div>'
                    f'</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with oc2:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button("View →", key=f"opp_view_{idx}", use_container_width=True):
                    navigate_to_hospital(pid, str(o["provider_name"]), str(o["provider_state"]))
            st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)
