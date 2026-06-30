import streamlit as st
import pandas as pd
import time
from sqlalchemy import text
import os
import base64

# --- IMAGE HELPER FUNCTION (Optional) ---
PHOTO_DIR = "evaluator_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)
def get_local_image_base64(username):
    file_path = os.path.join(PHOTO_DIR, f"{username.replace(' ', '_')}.png")
    if os.path.exists(file_path):
        with open(file_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{b64}"
    return "https://cdn-icons-png.flaticon.com/512/149/149071.png"


# ==========================================
# 1. BULK ADD DIALOGS
# ==========================================
@st.dialog("📚 Bulk Add Teams")
def bulk_add_teams_dialog(engine):
    st.markdown("**Format:** `Team Name, School, Group (A/B/C/D), Stake, Archive Link` (One per line)")
    raw_data = st.text_area("Paste Team List Here", height=200, 
                            placeholder="T1, SMK Aminuddin Baki, A, LGM-Soil fertility, https://drive.link...")
    
    if st.button("Import Teams", type="primary"):
        if not raw_data.strip():
            st.error("🚨 Please paste data first.")
            return
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        duplicates = []
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 1:
                    t_name = parts[0]
                    t_school = parts[1] if len(parts) > 1 else None
                    t_group = parts[2].upper() if len(parts) > 2 else None
                    t_stake = parts[3] if len(parts) > 3 else None
                    t_link = parts[4] if len(parts) > 4 else None
                    
                    check = conn.execute(text("SELECT id FROM teams WHERE name = :n"), {"n": t_name}).fetchone()
                    if check:
                        duplicates.append(t_name)
                    else:
                        conn.execute(text("""
                            INSERT INTO teams (name, school, group_category, stake, archive_link) 
                            VALUES (:n, :s, :g, :stk, :l)
                        """), {"n": t_name, "s": t_school, "g": t_group, "stk": t_stake, "l": t_link})
                        count += 1
        
        if count > 0:
            st.cache_resource.clear()
            st.success(f"✅ Successfully imported {count} teams!")
        if duplicates:
            st.warning(f"⚠️ The following team names already exist and were skipped: {', '.join(duplicates)}")
        if count > 0:
            time.sleep(1.5)
            st.rerun()

@st.dialog("📚 Bulk Add Juries")
def bulk_add_reviewers_dialog(engine, hash_password):
    st.markdown("**Format:** `Full Name, Username, Password` (One per line)")
    raw_data = st.text_area("Paste Jury List Here", height=200, placeholder="Dr. Rahmat, rahmat.d, Pass1234!")
    
    if st.button("Import Juries", type="primary"):
        if not raw_data.strip():
            st.error("🚨 Please paste data first.")
            return
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    name, user, pwd = parts[0], parts[1], parts[2]
                    conn.execute(text("INSERT INTO juries (username, full_name, password_hash) VALUES (:u, :n, :p) ON CONFLICT DO NOTHING"), 
                                 {"u": user.strip(), "n": name.strip(), "p": hash_password(pwd.strip())})
                    count += 1
        st.cache_resource.clear()
        st.success(f"✅ Successfully imported {count} juries!")
        time.sleep(1)
        st.rerun()


# ==========================================
# 2. RENDER DASHBOARD (LIVE TRACKER)
# ==========================================
def render_dashboard(engine):
    st.header("📊 Live Evaluation Tracker (NSC 2026)")
    
    if st.button("🔄 Sync Dashboard Data", type="secondary"):
        st.cache_resource.clear()
        st.rerun()
        
    revs_df = pd.read_sql("SELECT username, full_name FROM juries", engine)
    
    if revs_df.empty:
        st.info("ℹ️ No juries registered yet.")
        return

    st.subheader("Jury Status")
    reviews_df = pd.read_sql("SELECT jury_username, is_final FROM evaluations", engine)
    try:
        assign_df = pd.read_sql("SELECT team_name, jury_username FROM team_assignments", engine)
    except:
        assign_df = pd.DataFrame(columns=['team_name', 'jury_username'])
        
    cols = st.columns(4)
    for i, row in revs_df.iterrows():
        u_name = row['username']
        f_name = row['full_name']
        assigned_count = len(assign_df[assign_df['jury_username'] == u_name])
        done_count = len(reviews_df[(reviews_df['jury_username'] == u_name)])
        
        is_done = (done_count >= assigned_count) and assigned_count > 0
        bg, border_col = ("#E6FFFA", '#38B2AC') if is_done else ("#FFFBEB", '#ECC94B')
        if assigned_count == 0: bg, border_col = ("#F3F4F6", '#9CA3AF')
        
        img_data_uri = get_local_image_base64(u_name)
        
        with cols[i % 4]:
            st.markdown(f"""
                <div style="background-color:{bg}; border-top: 5px solid {border_col}; padding:15px; border-radius:8px; text-align:center; margin-bottom:10px;">
                    <img src="{img_data_uri}" style="width:60px; height:60px; border-radius:50%; object-fit:cover;" 
                    onerror="this.src='https://cdn-icons-png.flaticon.com/512/149/149071.png';">
                    <p style="font-weight:bold; margin:5px 0 0 0; color:#333;">{f_name}</p>
                    <p style="font-size:1.1em; font-weight:bold; color:#1E3A8A;">{done_count} / {assigned_count} Completed</p>
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    with st.expander("⚠️ Danger Zone: Save & Reset System"):
        st.warning("This action will delete ALL records (Scores and Teams).")
        if st.checkbox("I understand and want to reset.") and st.button("🗄️ Master Reset", type="primary"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM evaluations"))
                conn.execute(text("DELETE FROM team_assignments"))
                conn.execute(text("DELETE FROM teams"))
            st.cache_resource.clear()
            st.success("✅ System Reset!"); time.sleep(2); st.rerun()


# ==========================================
# 3. RENDER MANAGEMENT MENUS
# ==========================================
def render_management(menu, engine, hash_password, delete_item):
    
    # --- TEAM & ASSIGNMENT MANAGEMENT ---
    if menu == "Team & Assignment Management":
        st.header("📋 Team & Jury Assignment Management")
        
        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("🔄 Sync System Data", use_container_width=True):
            st.cache_resource.clear(); st.rerun()
        if col_btn2.button("📚 Bulk Add Teams", use_container_width=True):
            bulk_add_teams_dialog(engine)
            
        st.divider()
        
        apps_df = pd.read_sql("SELECT id, name, school, group_category, stake FROM teams ORDER BY group_category ASC, name ASC", engine)
        st.info(f"📊 **Total Teams Registered:** {len(apps_df)}")

        revs_df = pd.read_sql("SELECT username, full_name FROM juries", engine)
        try:
            assign_df = pd.read_sql("SELECT team_name, jury_username FROM team_assignments", engine)
        except:
            assign_df = pd.DataFrame(columns=['team_name', 'jury_username'])
            
        jury_options = revs_df['username'].tolist() if not revs_df.empty else []
        jury_map = dict(zip(revs_df['username'], revs_df['full_name']))
        
        # Display by Group (A, B, C, D)
        groups = apps_df['group_category'].unique()
        for g in sorted([x for x in groups if x]):
            st.subheader(f"Group {g}")
            group_df = apps_df[apps_df['group_category'] == g]
            
            for idx, row in group_df.iterrows():
                t_name = row['name']
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 4, 1])
                    c1.write(f"**{t_name}**")
                    c1.caption(f"🏫 {row['school']}")
                    c1.caption(f"🎯 {row['stake']}")
                    
                    current_assigned = assign_df[assign_df['team_name'] == t_name]['jury_username'].tolist()
                    current_assigned = [r for r in current_assigned if r in jury_options]
                    
                    selected_juries = c2.multiselect("Assign Jury:", options=jury_options, default=current_assigned, 
                                                    format_func=lambda x: f"{jury_map.get(x, x)}", key=f"as_{t_name}")
                    
                    if c2.button("💾 Save Assignment", key=f"sv_{t_name}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM team_assignments WHERE team_name = :t"), {"t": t_name})
                            for jury in selected_juries:
                                conn.execute(text("INSERT INTO team_assignments (team_name, jury_username) VALUES (:t, :j)"), 
                                             {"t": t_name, "j": jury})
                        st.cache_resource.clear()
                        st.toast(f"Assignment for {t_name} saved!"); time.sleep(0.5); st.rerun()
                    
                    if c3.button("🗑️ Delete", key=f"dl_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM team_assignments WHERE team_name = :t"), {"t": t_name})
                        delete_item("teams", row['id'])


    # --- JURY MANAGEMENT ---
    elif menu == "Jury Management":
        st.header("👤 Jury Management")
        
        if st.button("📚 Bulk Add Juries"):
            bulk_add_reviewers_dialog(engine, hash_password)
            
        st.divider()
        df = pd.read_sql("SELECT id, username, full_name FROM juries ORDER BY id ASC", engine)
        for idx, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 4, 2, 1])
                c1.markdown(f"<img src='{get_local_image_base64(row['username'])}' width='40' style='border-radius:50%;'>", unsafe_allow_html=True)
                c2.write(f"**{row['full_name']}**")
                c2.caption(f"Username: {row['username']}")
                
                # Unlock button to reset 'is_final'
                if c3.button("🔓 Unlock Evaluation", key=f"unlock_{row['id']}", use_container_width=True):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE evaluations SET is_final = FALSE WHERE jury_username = :u"), {"u": row['username']})
                    st.cache_resource.clear()
                    st.toast(f"✅ Access unlocked for {row['full_name']}!")
                    time.sleep(0.5); st.rerun()
                
                if c4.button("🗑️", key=f"dr_{row['id']}", use_container_width=True): 
                    delete_item("juries", row['id'])


    # --- ADMIN MANAGEMENT ---
    elif menu == "User Management":
        st.header("🔑 System Admin Accounts")
        
        with st.expander("➕ Add Admin"):
            with st.form("add_admin", clear_on_submit=True):
                u = st.text_input("Username*")
                n = st.text_input("Full Name*")
                p = st.text_input("Password*", type="password") 
                r = st.selectbox("Role", ["Admin"])
                if st.form_submit_button("Create Account"):
                    if u and p and n:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO users (username, full_name, role, password_hash) VALUES (:u, :n, :r, :p) ON CONFLICT DO NOTHING"),
                                         {"u": u.strip(), "n": n.strip(), "r": r, "p": hash_password(p)})
                        st.cache_resource.clear()
                        st.success("✅ Admin added successfully!"); time.sleep(1); st.rerun()
                    else:
                        st.error("🚨 Username, Name, and Password are required.")

        st.divider()
        df = pd.read_sql("SELECT id, username, full_name, role FROM users ORDER BY id ASC", engine)
        for idx, row in df.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"👤 **{row['full_name']}** ({row['username']})")
            if row['username'] != st.session_state.get('username'):
                if c2.button("🗑️", key=f"du_{row['id']}"): delete_item("users", row['id'])
