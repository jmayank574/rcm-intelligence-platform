import pandas as pd
import streamlit as st


def kpi(label, value, small=False):
    val_class = "kpi-value-sm" if small else "kpi-value"
    return (f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="{val_class}">{value}</div>'
            f'</div>')


def kpi_card(title, value, subtitle=None):
    sub = f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ""
    return (f'<div class="kpi-card">'
            f'<div class="kpi-label">{title}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'{sub}'
            f'</div>')


def kpi_benchmark(label, value, benchmark_text, status="neutral"):
    """KPI card with a benchmark context line. status: 'good' | 'bad' | 'warn' | 'neutral'"""
    color = {"good": "#16a34a", "bad": "#dc2626", "warn": "#d97706"}.get(status, "#64748b")
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div style="font-size:0.62rem;color:{color};margin-top:4px;'
        f'font-weight:600;line-height:1.4">{benchmark_text}</div>'
        f'</div>'
    )


def insight_card(text):
    st.markdown(f'<div class="insight-card">{text}</div>', unsafe_allow_html=True)


def section_header(text):
    st.markdown(f'<p class="section-label">{text}</p>', unsafe_allow_html=True)


def style_fig(fig, xaxis_title=None, yaxis_title=None, height=260):
    fig.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#334155", family="Inter, sans-serif", size=11),
        margin=dict(l=8, r=8, t=24, b=24),
        height=height,
        xaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0",
                   tickfont=dict(size=10, color="#64748b")),
        yaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0",
                   tickfont=dict(size=10, color="#64748b")),
        hoverlabel=dict(bgcolor="#1e293b", font_size=11, font_color="#f8fafc"),
    )
    if xaxis_title:
        fig.update_xaxes(title_text=xaxis_title,
                         title_font=dict(size=11, color="#475569"))
    if yaxis_title:
        fig.update_yaxes(title_text=yaxis_title,
                         title_font=dict(size=11, color="#475569"))
    return fig


def render_table(df, height=320):
    if df.empty:
        return
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)


def render_risk_table(df, grade_col=None, height=320):
    """Render a dataframe with row-level color coding based on a grade column."""
    if df.empty:
        return
    if grade_col and grade_col in df.columns:
        _bg = {"A": "#f0fdf4", "B": "#eff6ff", "C": "#fffbeb",
               "D": "#fff7ed", "F": "#fff1f2"}
        def _row_style(row):
            g = str(row.get(grade_col, "")).strip()[:1].upper()
            bg = _bg.get(g, "")
            return [f"background-color: {bg}" if bg else ""] * len(row)
        st.dataframe(df.style.apply(_row_style, axis=1),
                     use_container_width=True, height=height, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, height=height, hide_index=True)


def navigate_to_hospital(provider_id: str, provider_name: str, state: str):
    """Set session state for cross-page hospital navigation and trigger rerun."""
    st.session_state["go_to_state"]         = state
    st.session_state["go_to_hospital_id"]   = str(provider_id)
    st.session_state["go_to_hospital_name"] = provider_name
    st.session_state["last_page"]           = "Hospital 360"
    st.rerun()


def navigate_to_state(state: str):
    """Set session state for cross-page state navigation and trigger rerun."""
    st.session_state["go_to_state"] = state
    st.session_state["last_page"]   = "State Intelligence"
    st.rerun()


def safe_val(row, col, fmt=None, fallback="N/A"):
    try:
        v = row[col]
        if pd.isna(v):
            return fallback
        return fmt(v) if fmt else v
    except Exception:
        return fallback
