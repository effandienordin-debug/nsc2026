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
    st.markdown("**Format:** `Team ID, School, Group (A/B/C/D), State, PS, Archive Link` (One per line)")
    raw_data = st.text_area("Paste Team List Here", height=200, 
                            placeholder="T1, SMK Aminuddin Baki, A, Selangor, Food Waste, https://drive.link...")
    
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
                    t_id = parts[0].strip()
                    t_school = parts[1].strip() if len(parts) > 1 else None
                    t_group = parts[2].strip().upper() if len(parts) > 2 else None
                    t_state = parts[3].strip() if len(parts) > 3 else None
                    t_ps = parts[4].strip() if len(parts) > 4 else None
                    t_link = parts[5].strip() if len(parts) > 5 else None
                    
                    check = conn.execute(text("SELECT id FROM teams WHERE team_id = :n"), {"n": t_id}).fetchone()
                    if check:
                        duplicates.append(t_id)
                    else:
                        conn.execute(text("""
                            INSERT INTO teams (team_id, school, group_category, state, problem_statement, archive_link) 
                            VALUES (:n, :s, :g, :st, :ps, :l)
                        """), {"n": t_id, "s": t_school, "g": t_group, "st": t_state, "ps": t_ps, "l": t_link})
                        count += 1
        
        if count > 0:
            st.cache_resource.clear()
            st.success(f"✅ Successfully imported {count} teams!")
        if duplicates:
            st.warning(f"⚠️ The following Team IDs already exist and were skipped: {', '.join(duplicates)}")
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
        assign_query = text("""
            SELECT ga.jury_username, COUNT(t.id) as assigned_count
            FROM group_assignments ga
            JOIN teams t ON ga.group_category = t.group_category
            GROUP BY ga.jury_username
        """)
        assign_counts_df = pd.read_sql(assign_query, engine)
        assign_lookup = dict(zip(assign_counts_df['jury_username'], assign_counts_df['assigned_count']))
    except:
        assign_lookup = {}
        
    cols = st.columns(4)
    for i, row in revs_df.iterrows():
        u_name = row['username']
        f_name = row['full_name']
        
        assigned_count = assign_lookup.get(u_name, 0)
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
        st.warning("This action will delete ALL records (Scores, Teams, and Assignments).")
        if st.checkbox("I understand and want to reset.") and st.button("🗄️ Master Reset", type="primary"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM evaluations"))
                conn.execute(text("DELETE FROM group_assignments"))
                conn.execute(text("DELETE FROM teams"))
            st.cache_resource.clear()
            st.success("✅ System Reset!"); time.sleep(2); st.rerun()


# ==========================================
# 3. RENDER MANAGEMENT MENUS
# ==========================================
def render_management(menu, engine, hash_password, delete_item):
    
    if menu == "Team & Assignment Management":
        st.header("📋 Team & Group Assignment Management")
        
        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("🔄 Sync System Data", use_container_width=True):
            st.cache_resource.clear(); st.rerun()
        if col_btn2.button("📚 Bulk Add Teams", use_container_width=True):
            bulk_add_teams_dialog(engine)
            
        with st.expander("➕ Add Single Team"):
            with st.form("add_single_team", clear_on_submit=True):
                t_id = st.text_input("Team ID*")
                t_school = st.text_input("School")
                t_group = st.selectbox("Group*", ["A", "B", "C", "D"])
                t_state = st.text_input("State")
                t_ps = st.text_input("Problem Statement")
                t_link = st.text_input("Archive Link")
                
                if st.form_submit_button("Save Team"):
                    if t_id and t_group:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO teams (team_id, school, group_category, state, problem_statement, archive_link) 
                                    VALUES (:n, :s, :g, :st, :ps, :l)
                                """), {"n": t_id.strip(), "s": t_school.strip(), "g": t_group, "st": t_state.strip(), "ps": t_ps.strip(), "l": t_link.strip()})
                            st.cache_resource.clear()
                            st.success(f"✅ Team '{t_id}' added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                                st.error(f"🚨 Error: Team ID '{t_id}' already exists.")
                            else:
                                st.error(f"❌ System Error: {e}")
                    else:
                        st.error("🚨 Team ID and Group are required.")
            
        st.divider()
        
        tab1, tab2 = st.tabs(["📋 Registered Teams", "👥 Group Assignments (Juries)"])
        
        with tab1:
            apps_df = pd.read_sql("SELECT * FROM teams ORDER BY group_category ASC, team_id ASC", engine)
            st.info(f"📊 **Total Teams Registered:** {len(apps_df)}")
            
            st.markdown("**Team List (Click Edit to modify details)**")
            
            # --- FUNGSI EDIT & DELETE (LOOP DATAFRAME) ---
            for i, row in apps_df.iterrows():
                cols = st.columns([1.5, 3, 1, 1, 1])
                cols[0].write(row['team_id'])
                cols[1].write(row['school'] if row['school'] else "N/A")
                cols[2].write(f"Grp {row['group_category']}")
                
                with cols[3].popover("✏️ Edit"):
                    with st.form(f"edit_{row['id']}", clear_on_submit=False):
                        n_sch = st.text_input("School", value=row['school'] if row['school'] else "")
                        # Urus pilihan default untuk group
                        g_opts = ["A", "B", "C", "D"]
                        g_idx = g_opts.index(row['group_category']) if row['group_category'] in g_opts else 0
                        n_grp = st.selectbox("Group", g_opts, index=g_idx)
                        
                        n_st = st.text_input("State", value=row['state'] if row['state'] else "")
                        n_ps = st.text_input("Problem Statement", value=row['problem_statement'] if row['problem_statement'] else "")
                        n_link = st.text_input("Archive Link", value=row['archive_link'] if row['archive_link'] else "")
                        
                        if st.form_submit_button("Update Team"):
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE teams 
                                    SET school=:sch, group_category=:grp, state=:st, problem_statement=:ps, archive_link=:link 
                                    WHERE id=:id
                                """), {"sch": n_sch, "grp": n_grp, "st": n_st, "ps": n_ps, "link": n_link, "id": row['id']})
                            st.cache_resource.clear()
                            st.toast(f"✅ Team {row['team_id']} updated!")
                            time.sleep(0.5)
                            st.rerun()
                
                if cols[4].button("🗑️", key=f"del_{row['id']}"):
                    delete_item("teams", row['id'])

        with tab2:
            st.markdown("### Assign Juries to Groups")
            st.caption("Juries assigned to a group will automatically evaluate ALL teams within that group.")
            
            revs_df = pd.read_sql("SELECT username, full_name FROM juries", engine)
            try:
                assign_df = pd.read_sql("SELECT group_category, jury_username FROM group_assignments", engine)
            except:
                assign_df = pd.DataFrame(columns=['group_category', 'jury_username'])
                
            jury_options = revs_df['username'].tolist() if not revs_df.empty else []
            jury_map = dict(zip(revs_df['username'], revs_df['full_name']))
            
            try:
                groups = pd.read_sql("SELECT DISTINCT group_category FROM teams WHERE group_category IS NOT NULL", engine)['group_category'].tolist()
            except:
                groups = ["A", "B", "C", "D"]
                
            if not groups:
                groups = ["A", "B", "C", "D"]

            for g in sorted(groups):
                with st.container(border=True):
                    st.subheader(f"Group {g}")
                    
                    current_assigned = assign_df[assign_df['group_category'] == g]['jury_username'].tolist()
                    current_assigned = [r for r in current_assigned if r in jury_options]
                    
                    selected_juries = st.multiselect(
                        f"Assign Juries for Group {g}:", 
                        options=jury_options, 
                        default=current_assigned, 
                        format_func=lambda x: f"{jury_map.get(x, x)}", 
                        key=f"grp_{g}"
                    )
                    
                    if st.button("💾 Save Group Assignment", key=f"sv_grp_{g}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM group_assignments WHERE group_category = :g"), {"g": g})
                            for jury in selected_juries:
                                conn.execute(text("INSERT INTO group_assignments (group_category, jury_username) VALUES (:g, :j)"), 
                                             {"g": g, "j": jury})
                        st.cache_resource.clear()
                        st.toast(f"✅ Assignment for Group {g} saved!"); time.sleep(0.5); st.rerun()

    elif menu == "Jury Management":
        st.header("👤 Jury Management")
        
        col_j1, col_j2 = st.columns(2)
        if col_j1.button("🔄 Sync Jury Data", use_container_width=True):
            st.cache_resource.clear(); st.rerun()
        if col_j2.button("📚 Bulk Add Juries", use_container_width=True):
            bulk_add_reviewers_dialog(engine, hash_password)

        with st.expander("➕ Add Single Jury"):
            with st.form("add_single_jury", clear_on_submit=True):
                j_name = st.text_input("Full Name*")
                j_user = st.text_input("Username*")
                j_pass = st.text_input("Password*", type="password")
                
                if st.form_submit_button("Save Jury"):
                    if j_name and j_user and j_pass:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO juries (username, full_name, password_hash) 
                                    VALUES (:u, :n, :p)
                                """), {"u": j_user.strip(), "n": j_name.strip(), "p": hash_password(j_pass)})
                            st.cache_resource.clear()
                            st.success(f"✅ Jury '{j_name}' added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                                st.error(f"🚨 Error: Username '{j_user}' already exists.")
                            else:
                                st.error(f"❌ System Error: {e}")
                    else:
                        st.error("🚨 All fields are required.")
            
        st.divider()
        df = pd.read_sql("SELECT id, username, full_name FROM juries ORDER BY id ASC", engine)
        for idx, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 4, 2, 1])
                c1.markdown(f"<img src='{get_local_image_base64(row['username'])}' width='40' style='border-radius:50%;'>", unsafe_allow_html=True)
                c2.write(f"**{row['full_name']}**")
                c2.caption(f"Username: {row['username']}")
                
                if c3.button("🔓 Unlock Evaluation", key=f"unlock_{row['id']}", use_container_width=True):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE evaluations SET is_final = FALSE WHERE jury_username = :u"), {"u": row['username']})
                    st.cache_resource.clear()
                    st.toast(f"✅ Access unlocked for {row['full_name']}!")
                    time.sleep(0.5); st.rerun()
                
                if c4.button("🗑️", key=f"dr_{row['id']}", use_container_width=True): 
                    delete_item("juries", row['id'])

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
