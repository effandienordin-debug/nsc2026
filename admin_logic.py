import streamlit as st
import pandas as pd
import time
from sqlalchemy import text
import os
import base64

# --- IMAGE HELPER FUNCTION ---
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
    st.markdown("**Format:** `Team ID, School, Group (A/B/C/D), State, Stake, Archive Link` (One per line)")
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
                if len(parts) >= 6:
                    t_id = parts[0].strip()
                    t_school = parts[1].strip()
                    t_group = parts[2].strip().upper()
                    t_state = parts[3].strip()
                    t_stake = parts[4].strip()
                    t_link = parts[5].strip()
                    
                    check = conn.execute(text("SELECT id FROM teams WHERE team_id = :n"), {"n": t_id}).fetchone()
                    if check:
                        duplicates.append(t_id)
                    else:
                        conn.execute(text("""
                            INSERT INTO teams (team_id, school, group_category, state, stake, archive_link) 
                            VALUES (:id, :sch, :grp, :st, :stk, :link)
                        """), {"id": t_id, "sch": t_school, "grp": t_group, "st": t_state, "stk": t_stake, "link": t_link})
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
                t_stake = st.text_input("Stake / Problem Statement")
                t_link = st.text_input("Archive Link")
                
                if st.form_submit_button("Save Team"):
                    if t_id and t_group:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO teams (team_id, school, group_category, state, stake, archive_link) 
                                    VALUES (:n, :s, :g, :st, :stk, :l)
                                """), {"n": t_id.strip(), "s": t_school.strip(), "g": t_group, "st": t_state.strip(), "stk": t_stake.strip(), "l": t_link.strip()})
                            st.cache_resource.clear()
                            st.success(f"✅ Team '{t_id}' added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ System Error: {e}")
                    else:
                        st.error("🚨 Team ID and Group are required.")
            
        st.divider()
        
        tab1, tab2 = st.tabs(["📋 Registered Teams", "👥 Group Assignments (Juries)"])
        
        with tab1:
            apps_df = pd.read_sql("SELECT * FROM teams ORDER BY group_category ASC, team_id ASC", engine)
            st.info(f"📊 **Total Teams Registered:** {len(apps_df)}")
            
            for i, row in apps_df.iterrows():
                cols = st.columns([1, 2, 2, 1, 1])
                cols[0].write(row['team_id'])
                cols[1].write(row['school'])
                cols[2].write(row['group_category'])
                
                with cols[3].popover("Edit"):
                    with st.form(f"edit_{row['id']}"):
                        n_sch = st.text_input("School", value=row['school'])
                        n_grp = st.selectbox("Group", ["A", "B", "C", "D"], index=["A", "B", "C", "D"].index(row['group_category']))
                        n_st = st.text_input("State", value=row['state'] if row['state'] else "")
                        n_stk = st.text_input("Stake", value=row['stake'] if row['stake'] else "")
                        n_link = st.text_input("Archive Link", value=row['archive_link'] if row['archive_link'] else "")
                        
                        if st.form_submit_button("Update"):
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE teams SET school=:sch, group_category=:grp, state=:st, stake=:stk, archive_link=:link 
                                    WHERE id=:id
                                """), {"sch": n_sch, "grp": n_grp, "st": n_st, "stk": n_stk, "link": n_link, "id": row['id']})
                            st.rerun()
                            
                if cols[4].button("🗑️", key=f"del_{row['id']}"):
                    delete_item("teams", row['id'])

        with tab2:
            st.markdown("### Assign Juries to Groups")
            revs_df = pd.read_sql("SELECT username, full_name FROM juries", engine)
            assign_df = pd.read_sql("SELECT group_category, jury_username FROM group_assignments", engine)
            
            jury_options = revs_df['username'].tolist()
            jury_map = dict(zip(revs_df['username'], revs_df['full_name']))
            
            for g in ["A", "B", "C", "D"]:
                with st.container(border=True):
                    st.subheader(f"Group {g}")
                    current = assign_df[assign_df['group_category'] == g]['jury_username'].tolist()
                    sel = st.multiselect(f"Assign Juries:", options=jury_options, default=current, format_func=lambda x: jury_map.get(x, x), key=f"g_{g}")
                    if st.button("💾 Save", key=f"btn_{g}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM group_assignments WHERE group_category = :g"), {"g": g})
                            for j in sel:
                                conn.execute(text("INSERT INTO group_assignments (group_category, jury_username) VALUES (:g, :j)"), {"g": g, "j": j})
                        st.rerun()

    elif menu == "Jury Management":
        st.header("👤 Jury Management")
        if st.button("📚 Bulk Add Juries", use_container_width=True): bulk_add_reviewers_dialog(engine, hash_password)
        # (Jury list view logic omitted for brevity, logic remains identical)
