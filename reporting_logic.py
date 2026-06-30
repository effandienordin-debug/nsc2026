import streamlit as st
import pandas as pd
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
    
    # Fetch score data from database along with team info
    query = """
        SELECT 
            t.group_category as "Group",
            e.team_name as "Team Name",
            t.school as "School",
            e.jury_username,
            e.total_score
        FROM evaluations e
        JOIN teams t ON e.team_name = t.name
        WHERE e.is_final = TRUE
    """
    
    with engine.connect() as conn:
        try:
            df = pd.read_sql(text(query), conn)
        except Exception as e:
            df = pd.DataFrame()
            st.error(f"Error fetching data: {e}")

    if df.empty:
        st.info("💡 No finalized scores to display yet. Juries need to click 'Final Submit' first.")
    else:
        st.subheader("📊 Jury Scoring Pivot Table")
        
        # Pivot data so Jury Usernames become Columns
        pivot_df = df.pivot_table(
            index=["Group", "Team Name", "School"], 
            columns="jury_username", 
            values="total_score",
            aggfunc='mean'
        ).reset_index()

        # Get jury columns list (excluding index columns)
        jury_cols = [col for col in pivot_df.columns if col not in ["Group", "Team Name", "School"]]
        
        # Add Average Overall column
        pivot_df['Average Overall'] = pivot_df[jury_cols].mean(axis=1).round(2)
        
        # Sort by Group and Highest Average
        pivot_df = pivot_df.sort_values(by=["Group", "Average Overall"], ascending=[True, False])

        st.dataframe(
            pivot_df,
            use_container_width=True, 
            hide_index=True
        )

        st.divider()
        col1, col2 = st.columns(2)
        
        if col1.button("🖨️ Print Report (PDF)", use_container_width=True, type="primary"):
            st.components.v1.html("<script>window.parent.print();</script>", height=0)
            st.toast("Opening print dialog...")

        col2.download_button(
            label="📊 Download Data (CSV)",
            data=pivot_df.to_csv(index=False),
            file_name="NSC2026_Scoring_Report.csv",
            mime="text/csv",
            use_container_width=True
        )
