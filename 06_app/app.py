import streamlit as st

from auth import check_auth, get_landing_page, get_user_info, logout, render_login
from config import CSS
from views.claim_risk_scorer import render as render_claim_risk_scorer
from views.executive_overview import render as render_executive_overview
from views.hospital_360 import render as render_hospital_360
from views.state_intelligence import render as render_state_intelligence


@st.cache_data(ttl=3600, show_spinner=False)
def _all_hospitals():
    """Load all hospital names once for sidebar search — client-side filtering."""
    from db import run_query
    return run_query("""
        SELECT provider_id, provider_name, provider_state
        FROM rcm_platform.rcm_gold.hospital_360_scorecard
        ORDER BY inpatient_discharges DESC
    """)

st.set_page_config(
    page_title="Meridian · RCM Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

if not check_auth():
    render_login()
    st.stop()

st.markdown(CSS, unsafe_allow_html=True)

PAGES = {
    "Executive Overview":  render_executive_overview,
    "Hospital 360":        render_hospital_360,
    "Claim Risk Scorer":   render_claim_risk_scorer,
    "State Intelligence":  render_state_intelligence,
}

if "last_page" not in st.session_state:
    st.session_state.last_page = get_landing_page()

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px 0">
        <div style="font-size:1.2rem;font-weight:800;color:#f8fafc;
                    letter-spacing:-0.5px;line-height:1.1">
            Meridian</div>
        <div style="font-size:0.65rem;color:#475569;margin-top:3px;
                    text-transform:uppercase;font-weight:600;letter-spacing:0.6px">
            RCM Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    default_idx = list(PAGES.keys()).index(st.session_state.last_page) \
        if st.session_state.last_page in PAGES else 0

    page = st.radio(
        "Navigate",
        list(PAGES.keys()),
        index=default_idx,
        label_visibility="collapsed",
    )

    st.divider()

    # ── Global hospital search ────────────────────────────────
    search_q = st.text_input(
        "Quick find hospital",
        placeholder="Hospital name...",
        key="sidebar_search",
    )
    if search_q and len(search_q.strip()) >= 3:
        all_hosps = _all_hospitals()
        if not all_hosps.empty:
            q_lower = search_q.strip().lower()
            matched = all_hosps[
                all_hosps["provider_name"].str.lower().str.contains(q_lower, na=False)
            ].head(5)
            for _, r in matched.iterrows():
                label = r["provider_name"]
                label = (label[:28] + "…") if len(label) > 28 else label
                if st.button(f"{label} ({r['provider_state']})",
                             key=f"srch_{r['provider_id']}",
                             use_container_width=True):
                    st.session_state["go_to_state"]         = r["provider_state"]
                    st.session_state["go_to_hospital_id"]   = str(r["provider_id"])
                    st.session_state["go_to_hospital_name"] = r["provider_name"]
                    st.session_state["last_page"]           = "Hospital 360"
                    st.rerun()

    st.divider()

    user = get_user_info()
    st.markdown(
        f'<div style="padding:10px 4px 8px 4px">'
        f'<div style="font-size:0.75rem;font-weight:700;color:#cbd5e1;'
        f'line-height:1.3">{user["full_name"]}</div>'
        f'<div style="font-size:0.65rem;color:#475569;margin-top:2px;'
        f'font-weight:500">{user["title"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("Sign out", use_container_width=True):
        logout()

    st.markdown("""
    <div style="font-size:0.65rem;color:#334155;line-height:1.8;margin-top:8px">
        CMS Medicare &nbsp;·&nbsp; FY 2024
    </div>
    """, unsafe_allow_html=True)

st.session_state.last_page = page
PAGES[page]()
