import streamlit as st
import pandas as pd
import json
import time
from sqlalchemy import text

# --- 1. CACHED DATA FETCHING ---
@st.cache_resource(ttl=60)
def get_assigned_teams(_engine, username):
    query = text("""
        SELECT t.* FROM teams t
        JOIN team_assignments ta ON t.name = ta.team_name
        WHERE ta.jury_username = :u
    """)
    df = pd.read_sql(query, _engine, params={"u": username})
    return df

# --- 2. RENDER JURY DASHBOARD & GALLERY ---
def render_review_form(engine, get_malaysia_time, render_scoring_fields):
    st.markdown("## 📋 NSC 2026: State Level Judging")
    st.info("""
    Penilaian Pasukan dibahagikan kepada dua komponen: **Scientific Report (50%)** dan **Video Submission (50%)**.
    Sila rujuk pautan arkib (*Archive Link*) yang disertakan untuk dokumen pasukan.
    """)
    st.divider()
    
    with st.container(border=True):
        col_icon, col_greet = st.columns([1, 10])
        col_icon.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=65)
        col_greet.markdown(f"### Selamat kembali, {st.session_state.full_name}!")
        col_greet.caption(f"🔬 Logged in as: {st.session_state.username} | Role: Jury")

    # Check status lock (jika juri dah buat FINAL SUBMIT)
    is_locked = pd.read_sql(text("SELECT COUNT(*) FROM evaluations WHERE jury_username = :u AND is_final = TRUE"), 
                            engine, params={"u": st.session_state.username}).iloc[0,0] > 0

    if st.session_state.get('active_review_app'):
        # ==========================================
        # --- INDIVIDUAL TEAM REVIEW PAGE ---
        # ==========================================
        team_name = st.session_state.active_review_app
        
        # Ambil detail pasukan
        team = pd.read_sql(text("SELECT * FROM teams WHERE name = :n"), engine, params={"n": team_name}).iloc[0]
        
        # Ambil rekod penilaian sedia ada (jika ada draf)
        rev = pd.read_sql(text("SELECT * FROM evaluations WHERE jury_username = :u AND team_name = :t"), 
                          engine, params={"u": st.session_state.username, "t": team_name})
        
        prev_resp = {} 
        if not rev.empty and rev.iloc[0]['responses']:
            try:
                prev_resp = json.loads(rev.iloc[0]['responses'])
            except:
                prev_resp = {}

        # Paparan Maklumat Pasukan
        with st.container(border=True):
            st.subheader(f"Pasukan: {team_name}")
            col1, col2 = st.columns(2)
            col1.markdown(f"**🏫 Sekolah:** {team['school'] if team['school'] else 'N/A'}")
            col1.markdown(f"**🏷️ Group/Kategori:** {team['group_category'] if team['group_category'] else 'N/A'}")
            col2.markdown(f"**🎯 Stake / Problem Statement:** {team['stake'] if team['stake'] else 'N/A'}")
            
            if team['archive_link']:
                st.markdown(f"🔗 **[Klik Sini untuk Dokumen & Video Pasukan]({team['archive_link']})**")
            else:
                st.warning("⚠️ Tiada pautan dokumen (Archive Link) disertakan.")

        # Paparan Borang Penilaian
        with st.form("eval_form"):
            # Panggil fungsi borang dari form_components.py
            res = render_scoring_fields(prev_resp, rev.iloc[0].to_dict() if not rev.empty else {}, disabled=is_locked)
            
            if not is_locked and st.form_submit_button("💾 Save Draft / Simpan", use_container_width=True, type="primary"):
                
                # Semak kelengkapan
                is_incomplete = res["recommendation"] is None or not res["justification"].strip()
                
                if is_incomplete:
                    st.error("⚠️ Sila buat pilihan Final Recommendation dan tulis Ulasan Tambahan sebelum menyimpan.")
                else:
                    with engine.begin() as conn:
                        if not rev.empty:
                            conn.execute(text("""
                                UPDATE evaluations 
                                SET responses=:r, report_score=:rs, video_score=:vs, total_score=:ts, 
                                    final_recommendation=:fr, overall_justification=:oj, updated_at=:t 
                                WHERE id=:id
                            """), {
                                "r": json.dumps(res["responses"]), 
                                "rs": res["report_score"], 
                                "vs": res["video_score"], 
                                "ts": res["total_score"],
                                "fr": res["recommendation"], 
                                "oj": res["justification"], 
                                "t": get_malaysia_time(), 
                                "id": int(rev.iloc[0]['id'])
                            })
                        else:
                            conn.execute(text("""
                                INSERT INTO evaluations (jury_username, team_name, responses, report_score, video_score, total_score, final_recommendation, overall_justification, submitted_at, updated_at) 
                                VALUES (:u, :t_name, :r, :rs, :vs, :ts, :fr, :oj, :t, :t)
                            """), {
                                "u": st.session_state.username, 
                                "t_name": team_name, 
                                "r": json.dumps(res["responses"]),
                                "rs": res["report_score"], 
                                "vs": res["video_score"], 
                                "ts": res["total_score"],
                                "fr": res["recommendation"], 
                                "oj": res["justification"], 
                                "t": get_malaysia_time()
                            })
                    
                    st.cache_resource.clear() 
                    st.toast(f"✅ Penilaian {team_name} disimpan!")
                    st.session_state.active_review_app = None
                    st.rerun()

        if st.button("⬅️ Kembali ke Senarai Pasukan", use_container_width=True):
            st.session_state.active_review_app = None
            st.rerun()
            
    else:
        # ==========================================
        # --- GALLERY VIEW (SENARAI PASUKAN) ---
        # ==========================================
        teams = get_assigned_teams(engine, st.session_state.username)
        
        if teams.empty:
            st.info("Tiada pasukan ditugaskan kepada anda buat masa ini.")
        else:
            rev_records = pd.read_sql(text("""
                SELECT team_name, report_score, video_score, total_score, final_recommendation, overall_justification 
                FROM evaluations WHERE jury_username = :u
            """), engine, params={"u": st.session_state.username})
            
            reviews_lookup = rev_records.set_index('team_name').to_dict('index')
            
            st.subheader("Senarai Pasukan Ditugaskan")
            
            # Grid 4 Column
            for i in range(0, len(teams), 4):
                cols = st.columns(4)
                for j in range(4):
                    if i+j < len(teams):
                        row = teams.iloc[i+j]
                        with cols[j]:
                            with st.container(border=True):
                                st.markdown(f"<h4 style='text-align:center;'>{row['name']}</h4>", unsafe_allow_html=True)
                                st.caption(f"🏫 {row['school'] if row['school'] else 'N/A'}")
                                
                                if row['name'] in reviews_lookup:
                                    r_data = reviews_lookup[row['name']]
                                    st.markdown(f"**Status:** :green[✅ Dinilai]")
                                    st.markdown(f"**Rpt:** {r_data['report_score']:.1f} | **Vid:** {r_data['video_score']:.1f}")
                                    st.markdown(f"**Total:** :blue[{r_data['total_score']:.1f} / 100]")
                                else:
                                    st.markdown("**Status:** :orange[⏳ Menunggu]")
                                    st.caption("Belum dinilai.")
                                
                                if st.button("Nilai / Edit", key=f"go_{row['id']}", use_container_width=True, disabled=is_locked):
                                    st.session_state.active_review_app = row['name']
                                    st.rerun()

            # --- BUTANG RESET & FINAL SUBMIT ---
            if not is_locked and len(reviews_lookup) > 0:
                st.divider()
                c_reset, c_submit = st.columns(2)
                
                with c_reset.expander("⚠️ Kosongkan Draf"):
                    st.warning("Amaran: Ini akan memadam SEMUA markah anda yang belum di-submit.")
                    if st.button("🗑️ Yes, Clear My Drafts", use_container_width=True):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM evaluations WHERE jury_username = :u AND is_final = FALSE"), 
                                         {"u": st.session_state.username})
                        st.cache_resource.clear()
                        st.toast("✅ Semua draf anda telah dibersihkan!")
                        time.sleep(1)
                        st.rerun()

                with c_submit:
                    # Boleh Final Submit kalau semua pasukan dah dinilai
                    if len(reviews_lookup) >= len(teams):
                        if st.button(f"🚀 FINAL SUBMIT ALL REVIEWS", type="primary", use_container_width=True):
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE evaluations SET is_final = TRUE WHERE jury_username = :u"), {"u": st.session_state.username})
                            st.cache_resource.clear()
                            st.balloons()
                            st.rerun()
                    else:
                        st.info(f"Sila lengkapkan semua {len(teams)} penilaian sebelum hantar secara rasmi.")
