import streamlit as st
import pandas as pd
import io
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
    
    query = """
        SELECT 
            t.group_category as "Group",
            e.team_id as "Team ID",
            t.school as "School",
            e.jury_username,
            e.total_score
        FROM evaluations e
        JOIN teams t ON e.team_id = t.team_id
        WHERE e.is_final = TRUE
    """
    
    with engine.connect() as conn:
        try:
            df = pd.read_sql(text(query), conn)
        except Exception as e:
            df = pd.DataFrame()
            st.error(f"Error fetching data: {e}")

    if df.empty:
        st.info("💡 No finalized scores to display yet.")
    else:
        st.subheader("📊 Jury Scoring Pivot Table")
        
        pivot_df = df.pivot_table(
            index=["Group", "Team ID", "School"], 
            columns="jury_username", 
            values="total_score",
            aggfunc='mean'
        ).reset_index()

        jury_cols = [col for col in pivot_df.columns if col not in ["Group", "Team ID", "School"]]
        pivot_df['Average Overall'] = pivot_df[jury_cols].mean(axis=1).round(2)
        pivot_df = pivot_df.sort_values(by=["Group", "Average Overall"], ascending=[True, False])

        st.dataframe(pivot_df, use_container_width=True, hide_index=True)

        st.divider()
        
        # --- DOWNLOAD & PRINT SECTION ---
        col1, col2, col3 = st.columns(3)
        
        col1.button("🖨️ Print Report (PDF)", on_click=lambda: st.components.v1.html("<script>window.parent.print();</script>", height=0), use_container_width=True, type="primary")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            pivot_df.to_excel(writer, index=False, sheet_name='Scoring Report')
        
        col2.download_button(
            label="📊 Download (Excel)",
            data=buffer,
            file_name="NSC2026_Scoring_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        col3.download_button(
            label="📄 Download (CSV)",
            data=pivot_df.to_csv(index=False),
            file_name="NSC2026_Scoring_Report.csv",
            mime="text/csv",
            use_container_width=True
        )
