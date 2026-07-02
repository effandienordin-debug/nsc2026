import streamlit as st
import pandas as pd
import io
import json
from sqlalchemy import text

def render_reporting(engine):
    # --- PRINT CSS ---
    st.markdown("""
        <style>
        @media print {
            [data-testid="stSidebar"], header, footer, #MainMenu { display: none !important; }
            .stButton, [data-testid="stToast"] { display: none !important; }
            .main .block-container { padding-top: 1rem !important; max-width: 100% !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.header("📄 Scoring Reporting Center (NSC 2026)")
    
    # Ambil data termasuk responses (JSON) dan pecahkan skor
    query = """
        SELECT 
            t.group_category as "Group",
            e.team_id as "Team ID",
            t.school as "School",
            e.jury_username as "Jury",
            e.responses,
            e.report_score as "Report Score",
            e.video_score as "Video Score",
            e.total_score as "Total Score"
        FROM evaluations e
        JOIN teams t ON e.team_id = t.team_id
        WHERE e.is_final = TRUE
    """
    
    with engine.connect() as conn:
        try:
            raw_df = pd.read_sql(text(query), conn)
        except Exception as e:
            raw_df = pd.DataFrame()
            st.error(f"Error fetching data: {e}")

    if raw_df.empty:
        st.info("💡 No finalized scores to display yet.")
    else:
        # ==========================================
        # 1. PROCESS DETAILED RUBRICS DATA
        # ==========================================
        def parse_responses(val):
            try:
                return json.loads(val) if val else {}
            except:
                return {}

        # Parse JSON kepada dictionary
        raw_df['parsed'] = raw_df['responses'].apply(parse_responses)
        
        # Flatten dictionary menjadi lajur-lajur berasingan
        parsed_df = pd.json_normalize(raw_df['parsed'])
        
        # Gabungkan data asal dengan lajur rubrik baru
        detailed_df = pd.concat([raw_df.drop(columns=['responses', 'parsed']), parsed_df], axis=1)
        
        # Susun lajur supaya kemas
        base_cols = ["Group", "Team ID", "School", "Jury"]
        score_cols = ["Report Score", "Video Score", "Total Score"]
        rubric_cols = [col for col in parsed_df.columns]
        
        detailed_df = detailed_df[base_cols + rubric_cols + score_cols]
        detailed_df = detailed_df.sort_values(by=["Group", "Team ID", "Jury"])

        # ==========================================
        # 2. PROCESS AVERAGE / SUMMARY DATA
        # ==========================================
        # Kira purata keseluruhan mengikut pasukan
        avg_df = detailed_df.groupby(["Group", "Team ID", "School"])['Total Score'].mean().reset_index()
        avg_df.rename(columns={'Total Score': 'Average Overall'}, inplace=True)
        avg_df['Average Overall'] = avg_df['Average Overall'].round(2)
        
        # Buat pivot table (lajur = nama juri)
        pivot_df = raw_df.pivot_table(
            index=["Group", "Team ID", "School"], 
            columns="Jury", 
            values="Total Score",
            aggfunc='mean'
        ).reset_index()
        
        # Gabungkan Purata ke dalam Pivot Table
        summary_df = pd.merge(pivot_df, avg_df, on=["Group", "Team ID", "School"])
        # Susun kedudukan mengikut Kumpulan dan Markah Purata Tertinggi
        summary_df = summary_df.sort_values(by=["Group", "Average Overall"], ascending=[True, False])


        # ==========================================
        # 3. DISPLAY ON DASHBOARD
        # ==========================================
        st.subheader("📊 1. Laporan Purata Keseluruhan (Ranking)")
        st.caption("Memaparkan jumlah markah dari setiap juri berserta purata. Disusun mengikut markah purata tertinggi di dalam kumpulan.")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("📝 2. Laporan Terperinci (Markah Rubrik Individu)")
        st.caption("Pecahan terperinci bagi setiap item rubrik yang dinilai oleh setiap juri.")
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)

        st.divider()
        
        # ==========================================
        # 4. DOWNLOAD & PRINT SECTION
        # ==========================================
        col1, col2, col3 = st.columns(3)
        
        col1.button("🖨️ Print Report (PDF)", on_click=lambda: st.components.v1.html("<script>window.parent.print();</script>", height=0), use_container_width=True, type="primary")

        # Masukkan ke dalam Excel dengan DUA sheet berbeza
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            summary_df.to_excel(writer, index=False, sheet_name='Average Summary')
            detailed_df.to_excel(writer, index=False, sheet_name='Detailed Rubrics')
        
        col2.download_button(
            label="📊 Download (Excel)",
            data=buffer,
            file_name="NSC2026_Scoring_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # Muat turun data terperinci sahaja untuk CSV
        col3.download_button(
            label="📄 Download Detailed (CSV)",
            data=detailed_df.to_csv(index=False),
            file_name="NSC2026_Detailed_Scores.csv",
            mime="text/csv",
            use_container_width=True
        )
