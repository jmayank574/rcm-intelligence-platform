import streamlit as st

_LOGIN_CSS = """
<style>
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes breathe {
    0%, 100% { opacity: 0.35; }
    50%       { opacity: 0.9; }
}

html, body { overflow: hidden !important; height: 100vh !important; }
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section {
    overflow: hidden !important;
    height: 100vh !important;
}
/* Full-page dark background with layered radial glows */
[data-testid="stAppViewContainer"] > .main {
    height: 100vh !important;
    overflow: hidden !important;
    background-color: #070d1a !important;
    background-image:
        radial-gradient(ellipse at 15% 55%, rgba(37,99,235,0.28) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 20%, rgba(16,185,129,0.1) 0%, transparent 45%),
        radial-gradient(ellipse at 55% 90%, rgba(139,92,246,0.07) 0%, transparent 40%),
        radial-gradient(circle, rgba(255,255,255,0.025) 1px, transparent 1px) !important;
    background-size: 100% 100%, 100% 100%, 100% 100%, 28px 28px !important;
}
/* Narrow centered column for the form */
[data-testid="stAppViewContainer"] > .main .block-container {
    padding: 0 !important;
    max-width: 400px !important;
    height: 100vh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stSidebar"] { display: none !important; }

/* Form card */
[data-testid="stForm"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 16px !important;
    padding: 32px 28px 28px 28px !important;
    backdrop-filter: blur(12px) !important;
}
/* Dark inputs */
.stTextInput { margin-bottom: 10px !important; }
.stTextInput input {
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-size: 0.88rem !important;
    padding: 11px 14px !important;
    background: rgba(255,255,255,0.05) !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    caret-color: #0f172a !important;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s !important;
}
.stTextInput input::placeholder { color: rgba(148,163,184,0.45) !important; }
.stTextInput input:-webkit-autofill,
.stTextInput input:-webkit-autofill:focus {
    -webkit-text-fill-color: #0f172a !important;
    box-shadow: 0 0 0 100px rgba(255,255,255,0.05) inset !important;
}
.stTextInput input:focus {
    border-color: rgba(59,130,246,0.55) !important;
    background: rgba(255,255,255,0.08) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.14) !important;
}
.stTextInput label {
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    color: rgba(255,255,255,0.75) !important;
    letter-spacing: 0.6px !important;
    text-transform: uppercase !important;
}
/* Password eye icon */
[data-testid="stTextInput"] button svg { stroke: rgba(148,163,184,0.5) !important; }
/* Submit button */
.stForm [data-testid="stFormSubmitButton"] > button {
    width: 100% !important;
    background: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    padding: 13px 0 !important;
    margin-top: 8px !important;
    cursor: pointer !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 0 28px rgba(37,99,235,0.45) !important;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s !important;
}
.stForm [data-testid="stFormSubmitButton"] > button:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 0 40px rgba(37,99,235,0.6) !important;
    transform: translateY(-1px) !important;
}
.stForm [data-testid="stFormSubmitButton"] > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 0 20px rgba(37,99,235,0.35) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] { padding: 0 !important; }
</style>
"""

_STATS = [
    ("2,900+", "Hospitals"),
    ("$47B",   "Revenue Gap"),
    ("51",     "States"),
    ("98%",    "Fidelity"),
]


def _wordmark_html() -> str:
    return (
        '<div style="text-align:center;margin-bottom:32px;'
        'animation:fadeUp 0.55s ease both">'

        '<div style="font-size:2rem;font-weight:800;color:#f8fafc;'
        'letter-spacing:-1.2px;line-height:1;margin-bottom:6px">Meridian</div>'

        '<div style="font-size:0.6rem;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:2.5px;font-weight:700">RCM Intelligence Platform</div>'

        '<div style="width:32px;height:2px;background:linear-gradient(90deg,'
        '#2563eb,#3b82f6);border-radius:2px;margin:12px auto 0 auto"></div>'

        '</div>'
    )


def _stats_html() -> str:
    cells = "".join(
        f'<div style="text-align:center">'
        f'<div style="font-size:1rem;font-weight:700;color:#e2e8f0;'
        f'letter-spacing:-0.3px">{v}</div>'
        f'<div style="font-size:0.55rem;color:#334155;text-transform:uppercase;'
        f'letter-spacing:0.8px;margin-top:2px;font-weight:600">{l}</div>'
        f'</div>'
        for v, l in _STATS
    )
    return (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;margin-top:24px;padding:16px 20px;'
        'background:rgba(255,255,255,0.02);'
        'border:1px solid rgba(255,255,255,0.05);'
        'border-radius:10px;animation:fadeUp 0.55s 0.25s ease both">'
        + cells +
        '</div>'
    )


def _footer_html() -> str:
    return (
        '<div style="text-align:center;margin-top:20px;'
        'animation:fadeUp 0.55s 0.3s ease both">'
        '<div style="display:inline-flex;align-items:center;gap:6px">'
        '<div style="width:5px;height:5px;border-radius:50%;background:#16a34a;'
        'animation:breathe 2.5s ease-in-out infinite"></div>'
        '<span style="font-size:0.6rem;color:#1e3a5f;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.8px">'
        'Powered by CMS Medicare FY&nbsp;2024'
        '</span>'
        '</div>'
        '</div>'
    )


def render_login() -> None:
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    st.markdown(_wordmark_html(), unsafe_allow_html=True)

    # Error banner
    if st.session_state.get("login_error"):
        st.markdown(
            '<div style="background:rgba(220,38,38,0.1);'
            'border:1px solid rgba(220,38,38,0.25);'
            'border-left:3px solid #dc2626;border-radius:8px;'
            'padding:10px 14px;font-size:0.78rem;color:#fca5a5;'
            'margin-bottom:14px;font-weight:500;'
            'animation:fadeUp 0.3s ease both">'
            'Incorrect username or password.'
            '</div>',
            unsafe_allow_html=True,
        )

    # Form
    with st.form("login_form", clear_on_submit=False):
        username  = st.text_input("Username", placeholder="Enter your username")
        password  = st.text_input("Password", type="password",
                                  placeholder="••••••••")
        submitted = st.form_submit_button("Sign in to Meridian")

    if submitted:
        _attempt_login(username.strip(), password)

    st.markdown(_stats_html(), unsafe_allow_html=True)
    st.markdown(_footer_html(), unsafe_allow_html=True)


def _attempt_login(username: str, password: str) -> None:
    try:
        users = st.secrets.get("users", {})
    except Exception:
        users = {}

    user_cfg = users.get(username)
    if user_cfg and user_cfg.get("password") == password:
        st.session_state.authenticated = True
        st.session_state.username      = username
        st.session_state.full_name     = user_cfg.get("full_name", username)
        st.session_state.title         = user_cfg.get("title", "")
        st.session_state.role          = user_cfg.get("role", "Analyst")
        st.session_state.landing       = user_cfg.get("landing", "Executive Overview")
        st.session_state.login_error   = False
        st.rerun()
    else:
        st.session_state.login_error = True
        st.rerun()


def check_auth() -> bool:
    return st.session_state.get("authenticated", False)


def get_landing_page() -> str:
    return st.session_state.get("landing", "Executive Overview")


def get_user_info() -> dict:
    return {
        "username":  st.session_state.get("username", ""),
        "full_name": st.session_state.get("full_name", ""),
        "title":     st.session_state.get("title", ""),
        "role":      st.session_state.get("role", ""),
    }


def logout() -> None:
    for key in ("authenticated", "username", "full_name", "title", "role",
                "landing", "login_error", "last_page"):
        st.session_state.pop(key, None)
    st.rerun()
