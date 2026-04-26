GRADE_COLORS = {
    "A — Excellent":     "#16a34a",
    "B — Good":          "#2563eb",
    "C — Average":       "#d97706",
    "D — Below Average": "#ea580c",
    "F — Critical":      "#dc2626",
    "Insufficient Data": "#94a3b8",
}

STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    .main { background-color: #f8fafc; }
    .block-container { padding: 1.5rem 2rem 2rem 2rem !important; }
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: none;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] hr {
        border-color: #1e293b !important;
        margin: 12px 0 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        padding: 7px 10px 7px 12px !important;
        border-radius: 6px !important;
        border-left: 3px solid transparent !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: #64748b !important;
        transition: background 0.15s, border-color 0.15s, color 0.15s !important;
        margin-bottom: 2px !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #94a3b8 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: rgba(37,99,235,0.14) !important;
        border-left-color: #3b82f6 !important;
        color: #f1f5f9 !important;
        font-weight: 600 !important;
    }
    h1 {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 0 !important;
    }
    h2, h3 {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    .page-subtitle {
        color: #64748b;
        font-size: 0.82rem;
        margin-top: 2px;
        margin-bottom: 0;
    }
    .divider {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 12px 0 16px 0;
    }
    .section-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 16px 0 8px 0;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .kpi-label {
        font-size: 0.65rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
        margin: 0 0 4px 0;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    .kpi-value-sm {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        line-height: 1.2;
    }
    .badge {
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-high   { background:#fee2e2; color:#dc2626; }
    .badge-medium { background:#fef3c7; color:#d97706; }
    .badge-low    { background:#dcfce7; color:#16a34a; }
    .hospital-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 10px 0;
    }
    .score-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        margin-top: 10px;
        height: 100%;
    }
    /* ── Sidebar search ─────────────────────────────────────── */
    [data-testid="stSidebar"] .stTextInput input {
        background: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: #0f172a !important;
        font-size: 0.76rem !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
    }
    [data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #475569 !important;
    }
    [data-testid="stSidebar"] .stTextInput label {
        font-size: 0.62rem !important;
        color: #475569 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }
    /* Search result buttons in sidebar */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] .stButton > button {
        background: rgba(255,255,255,0.04) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        font-size: 0.71rem !important;
        text-align: left !important;
        padding: 5px 9px !important;
        margin-bottom: 2px !important;
        font-weight: 500 !important;
        border-radius: 5px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] .stButton > button:hover {
        background: rgba(59,130,246,0.12) !important;
        color: #93c5fd !important;
        border-color: rgba(59,130,246,0.25) !important;
    }
    /* ── View/nav buttons inside main content ────────────────── */
    .stButton > button[kind="secondary"] {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        padding: 4px 12px !important;
        border-radius: 6px !important;
    }
    /* ── Clickable chart hint ────────────────────────────────── */
    .chart-hint {
        font-size: 0.68rem;
        color: #94a3b8;
        margin-top: -8px;
        margin-bottom: 8px;
        font-style: italic;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stTabs [data-baseweb="tab"] {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
    }
    .stAlert { font-size: 0.82rem !important; }
    p { font-size: 0.82rem !important; }
    .stDataFrame { font-size: 0.78rem !important; }
    .kpi-subtitle {
        font-size: 0.65rem;
        color: #64748b;
        margin-top: 4px;
        font-weight: 500;
        line-height: 1.4;
    }
    .insight-card {
        background: #f8fafc;
        border-left: 4px solid #2563eb;
        border-radius: 0 6px 6px 0;
        padding: 12px 16px;
        font-size: 0.8rem !important;
        color: #1e293b;
        margin: 0 0 8px 0;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .risk-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 18px 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .risk-card-label {
        font-size: 0.62rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .risk-card-value {
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -1.5px;
        line-height: 1.05;
        margin: 0;
    }
    .risk-card-breakdown {
        font-size: 0.72rem;
        color: #475569;
        font-weight: 600;
        margin-top: 5px;
    }
    .risk-card-sub {
        font-size: 0.65rem;
        color: #94a3b8;
        margin-top: 2px;
        line-height: 1.4;
    }
    .stDownloadButton > button {
        background: #0f172a !important;
        color: #f8fafc !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.2px !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
    }
    .stDownloadButton > button:hover {
        background: #1e293b !important;
    }
    /* Sign-out button in sidebar */
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        background: rgba(255,255,255,0.05) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 6px !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        padding: 7px 0 !important;
        letter-spacing: 0.2px !important;
        transition: background 0.15s, color 0.15s !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(239,68,68,0.12) !important;
        color: #f87171 !important;
        border-color: rgba(239,68,68,0.25) !important;
    }
</style>
"""
