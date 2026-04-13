# ============================================================
# RCM Intelligence Platform — Streamlit App
# Databricks Apps deployment
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from databricks import sql
from dotenv import load_dotenv
import os

load_dotenv()

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="RCM Intelligence Platform",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main { background-color: #f8fafc; }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    h1 {
        color: #0f172a !important;
        font-weight: 800 !important;
        font-size: 2rem !important;
        letter-spacing: -0.5px !important;
    }

    h2, h3 {
        color: #1e293b !important;
        font-weight: 600 !important;
    }

    .section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #1e293b;
        margin: 24px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #e2e8f0;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .kpi-label {
        font-size: 0.72rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
        margin: 0 0 6px 0;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .badge-high {
        background: #fee2e2;
        color: #dc2626;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }

    .badge-medium {
        background: #fef3c7;
        color: #d97706;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }

    .badge-low {
        background: #dcfce7;
        color: #16a34a;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# DATABASE CONNECTION
# ============================================================


@st.cache_resource
def get_connection():
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "87fec7c67121429d")
    http_path = os.getenv("DATABRICKS_HTTP_PATH", f"/sql/1.0/warehouses/{warehouse_id}")

    if not host or not token:
        raise ValueError(
            "Missing Databricks configuration. Set DATABRICKS_HOST and DATABRICKS_TOKEN "
            "environment variables before running the app."
        )

    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


@st.cache_data(ttl=3600)
def run_query(query: str) -> pd.DataFrame:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return pd.DataFrame(result, columns=columns)
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()


def kpi(label, value):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """


def style_fig(fig, xaxis_title=None, yaxis_title=None):
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color="#334155", family="Inter, sans-serif", size=12),
        margin=dict(l=10, r=10, t=30, b=30),
        xaxis=dict(
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            tickfont=dict(size=11, color="#64748b"),
        ),
        yaxis=dict(
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            tickfont=dict(size=11, color="#64748b"),
        ),
        hoverlabel=dict(bgcolor="#1e293b", font_size=12, font_color="#f8fafc"),
    )
    if xaxis_title:
        fig.update_xaxes(
            title_text=xaxis_title, title_font=dict(size=12, color="#475569")
        )
    if yaxis_title:
        fig.update_yaxes(
            title_text=yaxis_title, title_font=dict(size=12, color="#475569")
        )
    return fig


def render_table(df, height=400):
    if df.empty:
        return
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## RCM Intelligence")
    st.markdown("*Healthcare Revenue Cycle Management*")
    st.divider()
    page = st.radio(
        "Navigate",
        [
            "Executive Overview",
            "Hospital Analyzer",
            "Claim Risk Scorer",
            "State Intelligence",
        ],
        index=0,
    )
    st.divider()
    st.markdown("**Data**")
    st.markdown("CMS Medicare · 2,945 hospitals · 51 states")
    st.divider()
    st.markdown(
        "[GitHub](https://github.com/jmayank574) · [LinkedIn](https://www.linkedin.com/in/mayank-joshi72)"
    )

if "last_page" not in st.session_state:
    st.session_state.last_page = "Executive Overview"

# ============================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":
    if "last_page" not in st.session_state or st.session_state.last_page != "Executive Overview":
        st.session_state.last_page = "Executive Overview"
        st.cache_data.clear()
    st.markdown("# RCM Intelligence Platform")
    st.markdown("*Real-time Medicare Revenue Cycle Analytics — Powered by Databricks*")
    st.divider()

    kpi_data = run_query("""
        SELECT
            COUNT(DISTINCT provider_id)                        AS total_hospitals,
            COUNT(DISTINCT provider_state)                     AS states_covered,
            ROUND(SUM(total_discharges) / 1e6, 2)              AS total_discharges_m,
            ROUND(AVG(charge_to_payment_ratio), 2)             AS avg_ctp_ratio,
            ROUND(AVG(revenue_gap_pct), 2)                     AS avg_revenue_gap_pct,
            ROUND(SUM(total_revenue_gap) / 1e9, 2)             AS total_revenue_gap_billions,
            ROUND(SUM(underpayment_flag) / COUNT(*) * 100, 2)  AS underpayment_rate_pct
        FROM (
            SELECT DISTINCT provider_id, provider_state, drg_code,
                total_discharges, charge_to_payment_ratio,
                revenue_gap_pct, total_revenue_gap, underpayment_flag
            FROM rcm_platform.rcm_gold.fact_claims
        )
    """)

    if not kpi_data.empty:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(
            kpi("Total Hospitals", f"{int(kpi_data['total_hospitals'].iloc[0]):,}"),
            unsafe_allow_html=True,
        )
        c2.markdown(
            kpi("States", f"{int(kpi_data['states_covered'].iloc[0])}"),
            unsafe_allow_html=True,
        )
        c3.markdown(
            kpi("Discharges", f"{kpi_data['total_discharges_m'].iloc[0]}M"),
            unsafe_allow_html=True,
        )
        c4.markdown(
            kpi("Avg CTP Ratio", f"{kpi_data['avg_ctp_ratio'].iloc[0]}x"),
            unsafe_allow_html=True,
        )
        c5.markdown(
            kpi("Underpayment Rate", f"{kpi_data['underpayment_rate_pct'].iloc[0]}%"),
            unsafe_allow_html=True,
        )
        c6.markdown(
            kpi("Revenue Gap", f"${kpi_data['total_revenue_gap_billions'].iloc[0]}B"),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<p class="section-header">Revenue Gap by State ($B)</p>',
            unsafe_allow_html=True,
        )
        state_data = run_query("""
            SELECT
                provider_state,
                ROUND(SUM(total_revenue_gap) / 1e9, 2) AS revenue_gap_billions
            FROM (
                SELECT DISTINCT provider_id, provider_state, drg_code, total_revenue_gap
                FROM rcm_platform.rcm_gold.fact_claims
            )
            GROUP BY provider_state
            ORDER BY revenue_gap_billions DESC
            LIMIT 20
        """)
        if not state_data.empty:
            fig = px.bar(
                state_data,
                x="provider_state",
                y="revenue_gap_billions",
                color="revenue_gap_billions",
                color_continuous_scale=["#bfdbfe", "#1d4ed8"],
                labels={
                    "provider_state": "State",
                    "revenue_gap_billions": "Revenue Gap ($B)",
                },
            )
            fig = style_fig(fig, xaxis_title="State", yaxis_title="Revenue Gap ($B)")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(
            '<p class="section-header">Top 5 DRGs by Revenue Leakage ($B)</p>',
            unsafe_allow_html=True,
        )
        drg_data = run_query("""
            SELECT
                CAST(drg_code AS STRING) AS drg_code,
                drg_description,
                ROUND(SUM(total_revenue_gap) / 1e9, 2) AS revenue_gap_billions
            FROM (
                SELECT DISTINCT provider_id, drg_code, drg_description, total_revenue_gap
                FROM rcm_platform.rcm_gold.fact_claims
            )
            GROUP BY drg_code, drg_description
            ORDER BY revenue_gap_billions DESC
            LIMIT 5
        """)
        if not drg_data.empty:
            drg_data = drg_data.sort_values("revenue_gap_billions", ascending=False)
            fig = px.bar(
                drg_data,
                x="revenue_gap_billions",
                y="drg_code",
                orientation="h",
                color="revenue_gap_billions",
                color_continuous_scale=["#bfdbfe", "#1d4ed8"],
                hover_data={"drg_description": True},
                labels={"drg_code": "", "revenue_gap_billions": "Revenue Gap ($B)"},
                category_orders={"drg_code": drg_data["drg_code"].tolist()},
            )
            fig = style_fig(fig, xaxis_title="Revenue Gap ($B)")
            fig.update_layout(
                coloraxis_showscale=False,
                yaxis=dict(type="category", tickfont=dict(size=13, color="#334155")),
            )
            fig.update_traces(
                text=drg_data["revenue_gap_billions"].apply(lambda x: f"${x}B"),
                textposition="outside",
                textfont=dict(size=12, color="#334155"),
            )
            st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<p class="section-header">AR Aging — Revenue at Risk ($B)</p>',
            unsafe_allow_html=True,
        )
        ar_data = run_query("""
            SELECT
                ar_aging_bucket,
                ROUND(SUM(revenue_at_risk) / 1e9, 2) AS revenue_at_risk_billions
            FROM rcm_platform.rcm_gold.ar_aging_buckets
            GROUP BY ar_aging_bucket
            ORDER BY
                CASE ar_aging_bucket
                    WHEN '0-30 days' THEN 1
                    WHEN '31-60 days' THEN 2
                    WHEN '61-90 days' THEN 3
                    WHEN '90+ days' THEN 4
                END
        """)
        if not ar_data.empty:
            fig = px.bar(
                ar_data,
                x="ar_aging_bucket",
                y="revenue_at_risk_billions",
                color="ar_aging_bucket",
                color_discrete_sequence=["#86efac", "#60a5fa", "#fb923c", "#f87171"],
                labels={
                    "ar_aging_bucket": "Aging Bucket",
                    "revenue_at_risk_billions": "Revenue at Risk ($B)",
                },
            )
            fig = style_fig(
                fig, xaxis_title="Aging Bucket", yaxis_title="Revenue at Risk ($B)"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(
            '<p class="section-header">Hospital RCM Health Grades</p>',
            unsafe_allow_html=True,
        )
        grade_data = run_query("""
            SELECT rcm_health_grade, COUNT(*) AS hospital_count
            FROM rcm_platform.rcm_gold.hospital_scorecard
            GROUP BY rcm_health_grade
            ORDER BY hospital_count DESC
        """)
        if not grade_data.empty:
            color_map = {
                "A — Excellent": "#16a34a",
                "B — Good": "#2563eb",
                "C — Average": "#d97706",
                "D — Below Average": "#ea580c",
                "F — Critical": "#dc2626",
            }
            fig = px.pie(
                grade_data,
                names="rcm_health_grade",
                values="hospital_count",
                color="rcm_health_grade",
                color_discrete_map=color_map,
                hole=0.45,
            )
            fig = style_fig(fig)
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
                ),
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<p class="section-header">Denial Risk Distribution</p>', unsafe_allow_html=True
    )
    denial_data = run_query("""
        SELECT
            denial_risk_label,
            COUNT(*) AS claim_count,
            ROUND(AVG(denial_risk_score), 4) AS avg_score
        FROM rcm_platform.rcm_gold.denial_risk_scores
        GROUP BY denial_risk_label
        ORDER BY avg_score DESC
    """)
    if not denial_data.empty:
        c1, c2, c3 = st.columns(3)
        cols = [c1, c2, c3]
        for i, row in denial_data.iterrows():
            badge = (
                "badge-high"
                if "High" in row["denial_risk_label"]
                else (
                    "badge-medium"
                    if "Medium" in row["denial_risk_label"]
                    else "badge-low"
                )
            )
            with cols[i]:
                st.markdown(
                    f"""
                <div class="kpi-card" style="text-align:center; padding:24px">
                    <span class="{badge}">{row['denial_risk_label']}</span>
                    <div class="kpi-value" style="margin-top:12px">{int(row['claim_count']):,}</div>
                    <div class="kpi-label" style="margin-top:4px">Claims · Avg Score: {row['avg_score']}</div>
                </div>""",
                    unsafe_allow_html=True,
                )

# ============================================================
# PAGE 2 — HOSPITAL ANALYZER
# ============================================================

elif page == "Hospital Analyzer":
    if "last_page" not in st.session_state or st.session_state.last_page != "Hospital Analyzer":
        st.session_state.last_page = "Hospital Analyzer"
        st.cache_data.clear()
    st.markdown("# Hospital Analyzer")
    st.markdown("*Search any hospital and see their complete RCM scorecard*")
    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input(
            "Search hospital name",
            placeholder="e.g. Mayo Clinic, Cleveland Clinic, Johns Hopkins...",
        )
    with col2:
        state_filter = st.selectbox(
            "Filter by state",
            ["All States"]
            + [
                "AL",
                "AK",
                "AZ",
                "AR",
                "CA",
                "CO",
                "CT",
                "DC",
                "DE",
                "FL",
                "GA",
                "HI",
                "ID",
                "IL",
                "IN",
                "IA",
                "KS",
                "KY",
                "LA",
                "ME",
                "MD",
                "MA",
                "MI",
                "MN",
                "MS",
                "MO",
                "MT",
                "NE",
                "NV",
                "NH",
                "NJ",
                "NM",
                "NY",
                "NC",
                "ND",
                "OH",
                "OK",
                "OR",
                "PA",
                "RI",
                "SC",
                "SD",
                "TN",
                "TX",
                "UT",
                "VT",
                "VA",
                "WA",
                "WV",
                "WI",
                "WY",
            ],
        )

    where_clauses = []
    if search_term:
        where_clauses.append(f"LOWER(h.provider_name) LIKE LOWER('%{search_term}%')")
    if state_filter != "All States":
        where_clauses.append(f"h.provider_state = '{state_filter}'")
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    hospital_data = run_query(f"""
        SELECT
            h.provider_id, h.provider_name, h.provider_state,
            h.provider_city, h.hospital_type, h.hospital_ownership,
            h.total_discharges, h.avg_ctp_ratio, h.avg_revenue_gap_pct,
            h.underpayment_rate_pct, h.rcm_health_score, h.rcm_health_grade,
            ROUND(d.avg_denial_risk_score, 4) AS avg_denial_risk_score,
            d.high_risk_claims, d.medium_risk_claims, d.low_risk_claims
        FROM rcm_platform.rcm_gold.hospital_scorecard h
        LEFT JOIN (
            SELECT provider_id,
                ROUND(AVG(denial_risk_score), 4) AS avg_denial_risk_score,
                SUM(CASE WHEN denial_risk_label = 'High Risk' THEN 1 ELSE 0 END) AS high_risk_claims,
                SUM(CASE WHEN denial_risk_label = 'Medium Risk' THEN 1 ELSE 0 END) AS medium_risk_claims,
                SUM(CASE WHEN denial_risk_label = 'Low Risk' THEN 1 ELSE 0 END) AS low_risk_claims
            FROM rcm_platform.rcm_gold.denial_risk_scores
            GROUP BY provider_id
        ) d ON h.provider_id = d.provider_id
        {where_sql}
        ORDER BY h.total_discharges DESC
        LIMIT 50
    """)

    if not hospital_data.empty:
        st.caption(f"Found {len(hospital_data)} hospitals")
        selected = st.selectbox(
            "Select a hospital", hospital_data["provider_name"].tolist()
        )
        hosp = hospital_data[hospital_data["provider_name"] == selected].iloc[0]

        grade_colors = {
            "A — Excellent": "#16a34a",
            "B — Good": "#2563eb",
            "C — Average": "#d97706",
            "D — Below Average": "#ea580c",
            "F — Critical": "#dc2626",
        }
        grade_color = grade_colors.get(hosp["rcm_health_grade"], "#64748b")
        grade_text_color = "#ffffff"

        st.markdown(
            f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;
                    padding:24px; margin:16px 0; box-shadow:0 1px 3px rgba(0,0,0,0.05)">
            <div style="display:flex; justify-content:space-between; align-items:flex-start">
                <div>
                    <h2 style="color:#0f172a; margin:0; font-size:1.5rem">{hosp['provider_name']}</h2>
                    <p style="color:#64748b; margin:4px 0 8px 0; font-size:0.9rem">
                        {hosp['provider_city']}, {hosp['provider_state']} &nbsp;·&nbsp; {hosp['hospital_type']}
                        <br>{hosp['hospital_ownership']}
                    </p>
                </div>
                <span style="background:{grade_color}; color:{grade_text_color}; padding:6px 20px;
                             border-radius:20px; font-weight:700; font-size:0.85rem; white-space:nowrap">
                    {hosp['rcm_health_grade']}
                </span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(
            kpi("Total Discharges", f"{int(hosp['total_discharges']):,}"),
            unsafe_allow_html=True,
        )
        c2.markdown(
            kpi("Avg CTP Ratio", f"{hosp['avg_ctp_ratio']:.2f}x"),
            unsafe_allow_html=True,
        )
        c3.markdown(
            kpi("Revenue Gap %", f"{hosp['avg_revenue_gap_pct']:.1f}%"),
            unsafe_allow_html=True,
        )
        c4.markdown(
            kpi("Underpayment Rate", f"{hosp['underpayment_rate_pct']:.1f}%"),
            unsafe_allow_html=True,
        )
        c5.markdown(
            kpi("RCM Health Score", f"{hosp['rcm_health_score']:.1f}/100"),
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                '<p class="section-header">Denial Risk Profile</p>',
                unsafe_allow_html=True,
            )
            risk_df = pd.DataFrame(
                {
                    "Risk Level": ["High Risk", "Medium Risk", "Low Risk"],
                    "Claims": [
                        hosp["high_risk_claims"],
                        hosp["medium_risk_claims"],
                        hosp["low_risk_claims"],
                    ],
                }
            )
            fig = px.pie(
                risk_df,
                names="Risk Level",
                values="Claims",
                color="Risk Level",
                color_discrete_map={
                    "High Risk": "#dc2626",
                    "Medium Risk": "#d97706",
                    "Low Risk": "#16a34a",
                },
                hole=0.45,
            )
            fig = style_fig(fig)
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
                ),
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown(
                '<p class="section-header">Denial Risk Score</p>',
                unsafe_allow_html=True,
            )
            risk_score = float(hosp["avg_denial_risk_score"])
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=risk_score,
                    number={"font": {"color": "#0f172a", "size": 48}},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {
                            "range": [0, 1],
                            "tickcolor": "#94a3b8",
                            "tickfont": {"color": "#94a3b8", "size": 10},
                        },
                        "bar": {"color": "#2563eb", "thickness": 0.25},
                        "bgcolor": "#f8fafc",
                        "borderwidth": 1,
                        "bordercolor": "#e2e8f0",
                        "steps": [
                            {"range": [0, 0.3], "color": "#dcfce7"},
                            {"range": [0.3, 0.6], "color": "#fef9c3"},
                            {"range": [0.6, 1.0], "color": "#fee2e2"},
                        ],
                        "threshold": {
                            "line": {"color": "#dc2626", "width": 3},
                            "thickness": 0.75,
                            "value": 0.6,
                        },
                    },
                )
            )
            fig.update_layout(
                paper_bgcolor="#ffffff",
                font=dict(color="#334155"),
                height=280,
                margin=dict(l=20, r=20, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            '<p class="section-header">Top DRGs at This Hospital</p>',
            unsafe_allow_html=True,
        )
        drg_hosp = run_query(f"""
            SELECT DISTINCT
                drg_code, drg_description, total_discharges,
                ROUND(avg_submitted_charge, 2)    AS avg_charge,
                ROUND(avg_medicare_payment, 2)    AS avg_payment,
                ROUND(charge_to_payment_ratio, 2) AS ctp_ratio,
                ROUND(revenue_gap_pct, 1)         AS revenue_gap_pct,
                underpayment_flag
            FROM rcm_platform.rcm_gold.fact_claims
            WHERE provider_id = '{hosp['provider_id']}'
            ORDER BY total_discharges DESC
            LIMIT 20
        """)
        if not drg_hosp.empty:
            render_table(drg_hosp, height=420)
    else:
        st.info("Search for a hospital above to see their RCM profile.")

# ============================================================
# PAGE 3 — CLAIM RISK SCORER
# ============================================================

elif page == "Claim Risk Scorer":
    if "last_page" not in st.session_state or st.session_state.last_page != "Claim Risk Scorer":
        st.session_state.last_page = "Claim Risk Scorer"
        st.cache_data.clear()
    st.markdown("# Claim Risk Scorer")
    st.markdown("*Select a hospital and DRG to get a denial risk prediction*")
    st.divider()

    col1, col2 = st.columns(2)
    selected_provider_id = None
    selected_drg_code = None

    with col1:
        st.markdown(
            '<p class="section-header">Select Hospital</p>', unsafe_allow_html=True
        )
        hospital_list = run_query("""
            SELECT DISTINCT provider_id, provider_name, provider_state
            FROM rcm_platform.rcm_gold.hospital_scorecard
            ORDER BY provider_name
        """)
        if not hospital_list.empty:
            hospital_options = {
                f"{row['provider_name']} ({row['provider_state']})": row["provider_id"]
                for _, row in hospital_list.iterrows()
            }
            selected_hospital = st.selectbox("Hospital", list(hospital_options.keys()))
            selected_provider_id = hospital_options[selected_hospital]

    with col2:
        st.markdown('<p class="section-header">Select DRG</p>', unsafe_allow_html=True)
        if selected_provider_id:
            drg_list = run_query(f"""
                SELECT DISTINCT drg_code, drg_description
                FROM rcm_platform.rcm_gold.fact_claims
                WHERE provider_id = '{selected_provider_id}'
                ORDER BY drg_code
            """)
            if not drg_list.empty:
                drg_options = {
                    f"{row['drg_code']} — {row['drg_description'][:55]}": row[
                        "drg_code"
                    ]
                    for _, row in drg_list.iterrows()
                }
                selected_drg = st.selectbox("DRG", list(drg_options.keys()))
                selected_drg_code = drg_options[selected_drg]
            else:
                st.warning("No DRGs found for this hospital.")
        else:
            st.info("Select a hospital first.")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔍 Get Denial Risk Score", type="primary", use_container_width=True):
        if not selected_provider_id or not selected_drg_code:
            st.warning("Please select both a hospital and a DRG.")
        else:
            with st.spinner("Scoring claim..."):
                score_data = run_query(f"""
                    SELECT
                        d.denial_risk_score, d.denial_risk_label,
                        f.avg_submitted_charge, f.avg_medicare_payment,
                        f.charge_to_payment_ratio, f.revenue_gap_pct,
                        f.total_discharges,
                        h.provider_name, h.provider_state,
                        h.rcm_health_grade, h.rcm_health_score
                    FROM rcm_platform.rcm_gold.denial_risk_scores d
                    JOIN (
                        SELECT DISTINCT provider_id, drg_code, avg_submitted_charge,
                            avg_medicare_payment, charge_to_payment_ratio,
                            revenue_gap_pct, total_discharges
                        FROM rcm_platform.rcm_gold.fact_claims
                    ) f ON d.provider_id = f.provider_id AND d.drg_code = f.drg_code
                    JOIN rcm_platform.rcm_gold.hospital_scorecard h ON d.provider_id = h.provider_id
                    WHERE d.provider_id = '{selected_provider_id}'
                    AND d.drg_code = '{selected_drg_code}'
                    LIMIT 1
                """)

                if not score_data.empty:
                    row = score_data.iloc[0]
                    risk_score = float(row["denial_risk_score"])
                    risk_label = row["denial_risk_label"]

                    if "High" in risk_label:
                        risk_color = "#dc2626"
                        bg_color = "#fee2e2"
                        border_color = "#fecaca"
                        risk_emoji = "🔴"
                        recommendation = "Immediate review required. Check documentation, coding accuracy and prior authorization status before submission."
                    elif "Medium" in risk_label:
                        risk_color = "#d97706"
                        bg_color = "#fef3c7"
                        border_color = "#fde68a"
                        risk_emoji = "🟡"
                        recommendation = "Secondary review recommended. Verify diagnosis codes and discharge summary completeness."
                    else:
                        risk_color = "#16a34a"
                        bg_color = "#dcfce7"
                        border_color = "#bbf7d0"
                        risk_emoji = "🟢"
                        recommendation = (
                            "Low denial risk. Standard submission process applies."
                        )

                    st.markdown(
                        f"""
                    <div style="background:{bg_color}; border:1px solid {border_color};
                                border-radius:12px; padding:32px; text-align:center; margin:16px 0">
                        <div style="font-size:3rem; font-weight:800; color:{risk_color}; letter-spacing:-1px">
                            {risk_emoji} {risk_score:.4f}
                        </div>
                        <div style="font-size:1.1rem; font-weight:700; color:{risk_color}; margin:8px 0">
                            {risk_label}
                        </div>
                        <div style="font-size:0.9rem; color:#475569; margin-top:8px; max-width:500px; margin-left:auto; margin-right:auto">
                            {recommendation}
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    try:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.markdown(kpi("Avg Submitted Charge", f"${row['avg_submitted_charge']:,.0f}"), unsafe_allow_html=True)
                        c2.markdown(kpi("Avg Medicare Payment", f"${row['avg_medicare_payment']:,.0f}"), unsafe_allow_html=True)
                        c3.markdown(kpi("CTP Ratio", f"{row['charge_to_payment_ratio']:.2f}x"), unsafe_allow_html=True)
                        c4.markdown(kpi("Revenue Gap", f"{row['revenue_gap_pct']:.1f}%"), unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error displaying metrics: {e}")

                    st.info(
                        f"**Hospital:** {row['provider_name']} ({row['provider_state']}) · **RCM Grade:** {row['rcm_health_grade']} · **Health Score:** {row['rcm_health_score']:.1f}/100"
                    )
                else:
                    st.warning("No data found for this hospital + DRG combination.")

# ============================================================
# PAGE 4 — STATE INTELLIGENCE
# ============================================================

elif page == "State Intelligence":
    if "last_page" not in st.session_state or st.session_state.last_page != "State Intelligence":
        st.session_state.last_page = "State Intelligence"
        st.cache_data.clear()
    st.markdown("# State Intelligence")
    st.markdown("*Deep dive into any state's Medicare RCM performance*")
    st.divider()

    selected_state = st.selectbox(
        "Select a state",
        [
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DC",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
        ],
    )

    state_kpi = run_query(f"""
        SELECT
            COUNT(DISTINCT provider_id)                        AS hospitals,
            SUM(total_discharges)                              AS discharges,
            ROUND(AVG(charge_to_payment_ratio), 2)             AS avg_ctp,
            ROUND(SUM(total_revenue_gap) / 1e9, 2)             AS revenue_gap_b,
            ROUND(SUM(underpayment_flag) / COUNT(*) * 100, 2)  AS underpayment_rate
        FROM (
            SELECT DISTINCT provider_id, drg_code, total_discharges,
                charge_to_payment_ratio, total_revenue_gap, underpayment_flag
            FROM rcm_platform.rcm_gold.fact_claims
            WHERE provider_state = '{selected_state}'
        )
    """)

    if not state_kpi.empty:
        row = state_kpi.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(
            kpi("Hospitals", f"{int(row['hospitals']):,}"), unsafe_allow_html=True
        )
        c2.markdown(
            kpi("Discharges", f"{int(row['discharges']):,}"), unsafe_allow_html=True
        )
        c3.markdown(kpi("Avg CTP Ratio", f"{row['avg_ctp']}x"), unsafe_allow_html=True)
        c4.markdown(
            kpi("Underpayment Rate", f"{row['underpayment_rate']}%"),
            unsafe_allow_html=True,
        )
        c5.markdown(
            kpi("Revenue Gap", f"${row['revenue_gap_b']}B"), unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(
            '<p class="section-header">Hospitals by RCM Grade</p>',
            unsafe_allow_html=True,
        )
        state_hospitals = run_query(f"""
            SELECT
                provider_name, provider_city,
                total_discharges,
                ROUND(avg_ctp_ratio, 2)       AS ctp_ratio,
                ROUND(avg_revenue_gap_pct, 1) AS revenue_gap_pct,
                rcm_health_score,
                rcm_health_grade
            FROM rcm_platform.rcm_gold.hospital_scorecard
            WHERE provider_state = '{selected_state}'
            ORDER BY total_discharges DESC
        """)
        if not state_hospitals.empty:
            render_table(state_hospitals, height=480)

    with col2:
        st.markdown(
            '<p class="section-header">Denial Risk by Hospital</p>',
            unsafe_allow_html=True,
        )
        state_risk = run_query(f"""
            SELECT
                h.provider_name,
                ROUND(AVG(d.denial_risk_score), 4) AS avg_denial_risk
            FROM rcm_platform.rcm_gold.denial_risk_scores d
            JOIN rcm_platform.rcm_gold.hospital_scorecard h ON d.provider_id = h.provider_id
            WHERE h.provider_state = '{selected_state}'
            GROUP BY h.provider_name
            ORDER BY avg_denial_risk DESC
            LIMIT 15
        """)
        if not state_risk.empty:
            state_risk_sorted = state_risk.sort_values(
                "avg_denial_risk", ascending=True
            )
            fig = px.bar(
                state_risk_sorted,
                x="avg_denial_risk",
                y="provider_name",
                orientation="h",
                color="avg_denial_risk",
                color_continuous_scale=["#fecaca", "#dc2626"],
                labels={
                    "provider_name": "",
                    "avg_denial_risk": "Avg Denial Risk Score",
                },
                category_orders={
                    "provider_name": state_risk_sorted["provider_name"].tolist()
                },
            )
            fig = style_fig(fig, xaxis_title="Avg Denial Risk Score")
            fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<p class="section-header">Top DRGs in This State</p>', unsafe_allow_html=True
    )
    state_drgs = run_query(f"""
        SELECT
            drg_code, drg_description,
            SUM(total_discharges)                             AS discharges,
            ROUND(AVG(charge_to_payment_ratio), 2)            AS avg_ctp,
            ROUND(SUM(total_revenue_gap) / 1e6, 2)            AS revenue_gap_millions,
            ROUND(SUM(underpayment_flag) / COUNT(*) * 100, 1) AS underpayment_rate
        FROM (
            SELECT DISTINCT provider_id, drg_code, drg_description,
                total_discharges, charge_to_payment_ratio,
                total_revenue_gap, underpayment_flag
            FROM rcm_platform.rcm_gold.fact_claims
            WHERE provider_state = '{selected_state}'
        )
        GROUP BY drg_code, drg_description
        ORDER BY revenue_gap_millions DESC
        LIMIT 15
    """)
    if not state_drgs.empty:
        render_table(state_drgs, height=420)
