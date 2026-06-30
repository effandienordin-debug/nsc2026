import streamlit as st
import extra_streamlit_components as stx
import json
import time
from sqlalchemy import text
from datetime import datetime, timedelta

# Import modul tempatan
from database_utils import engine, init_db, check_password, hash_password, get_malaysia_time, delete_item
from admin_logic import render_dashboard, render_management
from reviewer_logic import render_review_form
from reporting_logic import render_reporting
from form_components import render_scoring_fields

# --- 1. DATABASE INITIALIZATION ---
init_db()

st.set_page_config(page_title="NSC 2026 Judging System", layout="wide")

# --- 2. COOKIE MANAGER SETUP ---
if 'cookie_manager' not in st.session_state:
    st.session_state.cookie_manager = stx.CookieManager(key="nsc_mgr")

cookie_manager = st.session_state.cookie_manager

# --- 3. PROCESS PENDING COOKIE ACTIONS ---
if st.session_state.get('pending_login_cookie'):
    cookie_manager.set('nsc_session_data', st.session_state.pending_login_cookie, expires_at=datetime.now() + timedelta(days=1))
    del st.session_state['pending_login_cookie']

if st.session_state.get('pending_logout'):
    try:
        cookie_manager.delete('nsc_session_data')
    except KeyError:
        pass 
    del st.session_state['pending_logout']

# --- 4. INIT AUTH STATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 5. AUTO LOGIN FROM COOKIE ---
if not st.session_state.authenticated:
    if st.session_state.get('just_logged_out_flag'):
        st.session_state.just_logged_out_flag = False
    else:
        session_data = cookie_manager.get('nsc_session_data')
        if session_data:
            try:
                if isinstance(session_data, str):
                    session_data = json.loads(session_data)
                st.session_state.update({
                    "authenticated": True,
                    "username": session_data.get('username'),
                    "role": session_data.get('role'),
                    "full_name": session_data.get('full_name')
                })
            except Exception:
                pass

# --- 6. LOGIN INTERFACE ---
if not st.session_state.authenticated:
    st.title("🔐 NSC 2026 Login")
    with st.form("login_form"):
        login_role = st.radio("Log in as:", ["Jury", "Admin"], horizontal=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.form_submit_button("Login", use_container_width=True):
            with engine.connect() as conn:
                if login_role == "Admin":
                    query = text("SELECT password_hash, 'Admin' as role, full_name FROM users WHERE username = :u")
                else:
                    query = text("SELECT password_hash, 'Jury' as role, full_name FROM juries WHERE username = :u")

                res = conn.execute(query, {"u": u}).fetchone()

                if res and check_password(p, res[0]):
                    st.session_state.update({
                        "authenticated": True,
                        "username": u,
                        "role": res[1],
                        "full_name": res[2]
                    })
                    
                    st.session_state.pending_login_cookie = json.dumps({
                        "username": u,
                        "role": res[1],
                        "full_name": res[2]
                    })

                    st.success(f"Login successful! Welcome {res[2]}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid credentials or wrong role selected.")
    st.stop()

# --- 7. SIDEBAR & LOGOUT ---
with st.sidebar:
    st.title(f"👤 {st.session_state.full_name}")
    st.caption(f"Logged in as: {st.session_state.role}")

    if st.session_state.role == "Admin":
        opts = ["Dashboard", "Reporting", "Team & Assignment Management", "Jury Management", "User Management"]
        menu = st.radio("Navigation", opts)
    else:
        opts = ["Evaluation Dashboard"]
        menu = st.radio("Navigation", opts)

    st.divider()

    if st.button("Logout", use_container_width=True, type="primary"):
        st.session_state.clear()
        st.session_state.pending_logout = True
        st.session_state.just_logged_out_flag = True
        st.rerun()

# --- 8. MODULE ROUTING ---
if menu == "Dashboard":
    render_dashboard(engine)
elif menu == "Reporting": 
    render_reporting(engine)
elif menu in ["User Management", "Jury Management", "Team & Assignment Management"]:
    render_management(menu, engine, hash_password, delete_item)
elif menu == "Evaluation Dashboard":
    render_review_form(engine, get_malaysia_time, render_scoring_fields)
