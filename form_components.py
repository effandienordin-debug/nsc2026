import streamlit as st

def get_radio_index(prev_dict, key):
    if not prev_dict: return None
    val = prev_dict.get(key)
    return 0 if val == "Yes" else (1 if val == "No" else None)

def render_scoring_fields(prev_resp=None, prev_data=None, disabled=False):
    if prev_resp is None: prev_resp = {}
    if prev_data is None: prev_data = {}

    st.subheader("📊 NSC 2026 Evaluation Form")
    st.info("💡 Please select a scale from 1 (Very Weak) to 5 (Very Good). The system will calculate the weighted score automatically.")

    # --- HELPER FUNCTION TO RENDER ROWS ---
    def render_rubric_row(q_key, label, full_marks, desc_dict):
        st.markdown(f"**{label} (Maximum: {full_marks} marks)**")
        
        with st.expander("💡 View Rubric Scale Details"):
            for scale, desc in desc_dict.items():
                st.write(f"**Scale {scale}:** {desc}")
                
        # Get previous scale value (default to 1 if not present)
        current_scale = int(prev_resp.get(q_key, 1))
        
        selected_scale = st.radio(
            "Select Scale:",
            [1, 2, 3, 4, 5],
            index=[1, 2, 3, 4, 5].index(current_scale) if current_scale in [1, 2, 3, 4, 5] else 0,
            horizontal=True,
            key=f"rad_{q_key}",
            disabled=disabled
        )
        
        # Calculate score: (Selected Scale / 5) * Full Marks
        calculated_score = (selected_scale / 5.0) * full_marks
        st.caption(f"Calculated Score: **{calculated_score:.1f} / {full_marks}**")
        st.divider()
        
        return selected_scale, calculated_score

    responses = {}
    total_report_score = 0
    total_video_score = 0

    # ==========================================
    # PART A: SCIENTIFIC REPORT (50%)
    # ==========================================
    st.markdown("### A. Scientific Report (50%)")
    
    abs_scale, abs_score = render_rubric_row("q_abstract", "1. Abstract", 10, {
        1: "Abstract is incomplete",
        2: "Abstract is poorly described",
        3: "Abstract is described but not comprehensive",
        4: "Abstract is described comprehensively",
        5: "Abstract is comprehensive and very well organised"
    })
    responses["q_abstract"] = abs_scale; total_report_score += abs_score

    intro_scale, intro_score = render_rubric_row("q_intro", "2. Introduction", 5, {
        1: "Introduction is not related to the background of study",
        2: "Introduction is moderately related to the background of study",
        3: "Introduction is related to the background of study",
        4: "Introduction is specifically related to the background of study",
        5: "Introduction is specifically related to the background of work, and contains a critical discussion"
    })
    responses["q_intro"] = intro_scale; total_report_score += intro_score

    method_scale, method_score = render_rubric_row("q_method", "3. Methodology", 10, {
        1: "No definite methodology has been described",
        2: "The methodology described is unreliable",
        3: "A reliable methodology is described",
        4: "A clear and reliable methodology is described",
        5: "A clear and reliable methodology which fulfils the objectives of the study is described"
    })
    responses["q_method"] = method_scale; total_report_score += method_score

    result_scale, result_score = render_rubric_row("q_result", "4. Results and Discussions", 15, {
        1: "Results do not meet the project’s objectives",
        2: "All/ few results validate some of the project’s objectives with inaccurate or wrong discussion and analysis",
        3: "Few results validate some of the project’s objectives with partially correct discussion and analysis",
        4: "All/ most results validate some of the project’s objectives with correct discussion and analysis",
        5: "All results validate all of the project’s objectives with correct discussion and analysis"
    })
    responses["q_result"] = result_scale; total_report_score += result_score

    conc_scale, conc_score = render_rubric_row("q_conc", "5. Conclusions", 10, {
        1: "The conclusion is not based on the experiment’s data, and the objectives are not addressed.",
        2: "The conclusion is based on the data but does not answer the experiment’s objectives.",
        3: "The conclusion is based on the collected and analysed data but does not fully answer the objectives.",
        4: "The conclusion is based on the collected and analysed data, and it partially answers the objectives.",
        5: "The conclusion is based on the collected and analysed data and directly answers the objectives."
    })
    responses["q_conc"] = conc_scale; total_report_score += conc_score


    # ==========================================
    # PART B: VIDEO SUBMISSION (50%)
    # ==========================================
    st.markdown("### B. Video Submission (50%)")
    
    synth_scale, synth_score = render_rubric_row("q_synth", "1. 3-Minute Synthesis", 5, {
        1: "Fails to synthesize info; video is disorganized and significantly over time.",
        2: "Poorly organized; misses key phases or rushes significantly to finish.",
        3: "Synthesizes info with acceptable organization but exceeds time limit",
        4: "Effectively synthesizes complex activities into a clear report within time",
        5: "Exceptional synthesis; delivers comprehensive findings exactly in 3 minutes"
    })
    responses["q_synth"] = synth_scale; total_video_score += synth_score

    scicom_scale, scicom_score = render_rubric_row("q_scicom", "2. Scientific Communication", 8, {
        1: "The explanation is unclear, disorganised, and lacks scientific accuracy, making it difficult to understand",
        2: "The explanation is somewhat disorganised and contains inaccuracies, making it hard to follow",
        3: "The explanation is mostly clear and accurate but may lack some organisational elements or details",
        4: "The explanation is clear, well-structured, and accurate, with good depth in scientific content",
        5: "The explanation is exceptionally clear, well-structured, and highly accurate, demonstrating deep understanding of the scientific principles involved"
    })
    responses["q_scicom"] = scicom_scale; total_video_score += scicom_score

    v_result_scale, v_result_score = render_rubric_row("q_v_result", "3. Results & Findings", 10, {
        1: "Results do not meet objectives; wrong discussion or missing data",
        2: "Results validate some objectives but with inaccurate analysis.",
        3: "Most results validate objectives with correct analysis/discussion.",
        4: "All results validate objectives with proper, detailed discussion.",
        5: "All results validate objectives with excellent, critical analysis"
    })
    responses["q_v_result"] = v_result_scale; total_video_score += v_result_score

    scidisc_scale, scidisc_score = render_rubric_row("q_scidisc", "4. Scientific Discussion", 7, {
        1: "Provides little or no explanation of the scientific principles, technical issues, or challenges. Discussion is unclear and lacks depth.",
        2: "Provides a limited explanation of relevant scientific principles and technical issues. Some key points are missing or unclear.",
        3: "Explains the main scientific principles, technical issues, and challenges with moderate depth. Some explanations may lack clarity or completeness.",
        4: "Provides a thorough explanation of most relevant scientific principles, technical issues, and challenges. Discussion is clear and organized.",
        5: "Provides a comprehensive, well-organized, and insightful discussion of all relevant scientific principles, technical issues, and challenges. Demonstrates clear, detailed understanding of the subject."
    })
    responses["q_scidisc"] = scidisc_scale; total_video_score += scidisc_score

    creativity_scale, creativity_score = render_rubric_row("q_create", "5. Creativity in Problem-Solving", 6, {
        1: "Does not apply creative techniques or materials to solve problems; lacks innovation",
        2: "Shows some creativity but relies on conventional methods; minimal problem-solving initiative",
        3: "Applies some creative techniques or modifications but mostly follows standard approaches",
        4: "Demonstrates creativity by applying novel techniques or approaches to solve problems effectively",
        5: "Demonstrates exceptional creativity, applying innovative techniques and novel solutions to overcome constraints or challenges"
    })
    responses["q_create"] = creativity_scale; total_video_score += creativity_score

    team_scale, team_score = render_rubric_row("q_team", "6. Teamwork & Synergy", 5, {
        1: "Progress not satisfactory; no evidence of shared discussion or ideas.",
        2: "Demonstrates less interest and fewer ideas in solving the given task.",
        3: "Demonstrate interest and ideas in solving the task with some effort",
        4: "Demonstrate interest, initiative, and effort in solving the task as a unit.",
        5: "Seamless synergy; demonstrates excellent initiative and shared ideas."
    })
    responses["q_team"] = team_scale; total_video_score += team_score

    impact_scale, impact_score = render_rubric_row("q_impact", "7. Impact Justification", 5, {
        1: "Does not explain why the experiment is important or what it adds to existing knowledge",
        2: "Explains the experiment's impact poorly, with little relevance or depth",
        3: "Gives a basic explanation of the experiment’s impact, but lacks strong reasoning or details",
        4: "Provides a clear explanation of the experiment’s impact and its relevance beyond basic expectations",
        5: "Gives a thorough, convincing explanation of how the experiment contributes to new knowledge or addresses important issues"
    })
    responses["q_impact"] = impact_scale; total_video_score += impact_score

    safety_scale, safety_score = render_rubric_row("q_safety", "8. Safety & Ethics", 4, {
        1: "Does not follow any safety rules or ethical practices",
        2: "Safety rules or ethical practices are mostly ignored",
        3: "Follows some safety rules and ethical practices",
        4: "Follows most safety rules and ethical practices",
        5: "Strictly follows all safety rules and ethical practices"
    })
    responses["q_safety"] = safety_scale; total_video_score += safety_score


    # ==========================================
    # FINAL CALCULATION & SUMMARY
    # ==========================================
    grand_total = total_report_score + total_video_score
    
    st.markdown(f"<h3 style='text-align: right; color: #1E3A8A;'>🎯 Total Score: {grand_total:.1f} / 100</h3>", unsafe_allow_html=True)
    st.divider()

    st.subheader("Final Evaluation Summary")
    rec_val = prev_data.get('final_recommendation')
    recommendation = st.radio(
        "Final Recommendation (Support/Do Not Support) *", 
        ["Yes", "No"], 
        index=(0 if rec_val in ["Yes", "YES"] else (1 if rec_val in ["No", "NO"] else None)), 
        horizontal=True, 
        disabled=disabled
    )
    justification = st.text_area("Additional Remarks (Required) *", value=prev_data.get('overall_justification', ""), disabled=disabled, placeholder="Provide some comments about this team...")
    
    # Return data to be saved to database
    return {
        "responses": responses, 
        "report_score": total_report_score,
        "video_score": total_video_score,
        "total_score": grand_total,
        "recommendation": recommendation, 
        "justification": justification
    }
