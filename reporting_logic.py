import streamlit as st
import pandas as pd
import plotly.express as px
import json
from sqlalchemy import text

@st.cache_resource(ttl=60)
def get_report_data_p1(_engine):
    query = """
        SELECT 
            r.applicant_name,
            COALESCE(rev.full_name, r.reviewer_username) as reviewer_name,
            r.final_recommendation,
            r.is_final,
            r.overall_justification
        FROM reviews r
        LEFT JOIN reviewers rev ON r.reviewer_username = rev.username
    """
    try:
        return pd.read_sql(text(query), _engine)
    except:
        return pd.DataFrame()

@st.cache_resource(ttl=60)
def get_report_data_p2(_engine):
    query = """
        SELECT 
            r.applicant_name,
            COALESCE(rev.full_name, r.reviewer_username) as reviewer_name,
            r.responses,
            r.final_recommendation,
            r.is_final,
            r.overall_justification
        FROM phase2_reviews r
        LEFT JOIN reviewers rev ON r.reviewer_username = rev.username
    """
    try:
        return pd.read_sql(text(query), _engine)
    except:
        return pd.DataFrame()

def render_reporting(engine):
    # --- 1. CSS PRINT HACK ---
    st.markdown("""
        <style>
        @media print {
            [data-testid="stSidebar"], header, footer, #MainMenu {
                display: none !important;
            }
            [data-testid="stToast"] {
                display: none !important;
            }
            .stButton {
                display: none !important;
            }
            .main .block-container {
                padding-top: 1rem !important;
                max-width: 100% !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    st.header("📄 Grant Reporting Center")
    
    # Asingkan Laporan kepada 2 Fasa
    tab1, tab2 = st.tabs(["📊 Phase 1: Shortlisting", "🏆 Phase 2: Selection Ranking"])

    # ==========================================
    # --- TAB 1: REPORTING PHASE 1 ---
    # ==========================================
    with tab1:
        df_p1 = get_report_data_p1(engine)

        if df_p1.empty:
            st.info("No Phase 1 data available yet.")
        else:
            with st.expander("🔍 Filter Phase 1 Results"):
                c1, c2 = st.columns(2)
                f_rec = c1.multiselect("Recommendation", df_p1['final_recommendation'].unique(), default=df_p1['final_recommendation'].unique(), key="f1")
                f_rev = c2.multiselect("Reviewer", df_p1['reviewer_name'].unique(), default=df_p1['reviewer_name'].unique(), key="f2")
            
            filtered_df_p1 = df_p1[(df_p1['final_recommendation'].isin(f_rec)) & (df_p1['reviewer_name'].isin(f_rev))]

            if not filtered_df_p1.empty:
                fig1 = px.pie(filtered_df_p1, names='final_recommendation', title="Overall Recommendation Split")
                fig2 = px.bar(filtered_df_p1.groupby(['applicant_name', 'final_recommendation']).size().reset_index(name='count'), 
                              x='applicant_name', y='count', color='final_recommendation', title="Applicant Breakdown")

                col1, col2 = st.columns(2)
                col1.plotly_chart(fig1, use_container_width=True)
                col2.plotly_chart(fig2, use_container_width=True)

                st.divider()
                btn_col1, btn_col2 = st.columns(2)
                if btn_col1.button("🖨️ Generate PDF (Phase 1)", use_container_width=True, type="primary"):
                    st.components.v1.html("<script>window.parent.print();</script>", height=0)
                    st.toast("Opening Print Dialog...")

                btn_col2.download_button(
                    label="📊 Download Phase 1 Data (CSV)",
                    data=filtered_df_p1.to_csv(index=False),
                    file_name="Phase1_RBS_Data.csv",
                    mime="text/csv",
                    use_container_width=True
                )

                st.subheader("📋 Phase 1 Data Summary")
                st.dataframe(filtered_df_p1, use_container_width=True, hide_index=True)
            else:
                st.warning("No data matches the selected filters.")

    # ==========================================
    # --- TAB 2: REPORTING PHASE 2 (SCORING) ---
    # ==========================================
    with tab2:
        df_p2 = get_report_data_p2(engine)

        if df_p2.empty:
            st.info("No Phase 2 data available yet.")
        else:
            # Parse markah (total_score) dari format JSON
            scores = []
            for _, row in df_p2.iterrows():
                score = 0
                try:
                    res_json = json.loads(row['responses'])
                    score = res_json.get('total_score', 0)
                except:
                    pass
                scores.append(score)
            
            df_p2['total_score'] = scores
            
            # Tapis hanya yang sudah dimuktamadkan (is_final = TRUE)
            final_p2_df = df_p2[df_p2['is_final'] == True]
            
            if final_p2_df.empty:
                st.info("Penilai sedang menilai Fasa 2. Belum ada markah muktamad (Finalized).")
            else:
                st.subheader("Leaderboard & Ranking")
                
                # Kira purata markah untuk setiap pemohon
                avg_scores = final_p2_df.groupby('applicant_name')['total_score'].mean().reset_index()
                avg_scores.columns = ['Nama Pemohon', 'Purata Markah (%)']
                avg_scores = avg_scores.sort_values(by='Purata Markah (%)', ascending=False)
                
                # Bar Chart Purata Markah
                fig3 = px.bar(avg_scores, x='Nama Pemohon', y='Purata Markah (%)', 
                              color='Purata Markah (%)', title="Kedudukan Merit Penuh",
                              color_continuous_scale="Blues")
                st.plotly_chart(fig3, use_container_width=True)

                st.divider()
                btn_col3, btn_col4 = st.columns(2)
                if btn_col3.button("🖨️ Generate PDF (Phase 2)", use_container_width=True, type="primary"):
                    st.components.v1.html("<script>window.parent.print();</script>", height=0)
                    st.toast("Opening Print Dialog...")

                btn_col4.download_button(
                    label="📊 Download Phase 2 Leaderboard (CSV)",
                    data=avg_scores.to_csv(index=False),
                    file_name="Phase2_Leaderboard.csv",
                    mime="text/csv",
                    use_container_width=True
                )

                st.subheader("📋 Jadual Keputusan Penuh")
                st.dataframe(
                    avg_scores,
                    column_config={
                        "Purata Markah (%)": st.column_config.NumberColumn(format="%d %%")
                    },
                    use_container_width=True, 
                    hide_index=True
                )
