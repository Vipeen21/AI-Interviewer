import contextlib
import io
import json
import os

import streamlit as st
from streamlit_mic_recorder import mic_recorder

from config import MAX_QUESTIONS, FIELD_OPTIONS, COMPANY_OPTIONS, GEMINI_API_KEY, MODEL_NAME, JUDGE_MODEL_NAME
from state import init_state, save_answer, answer_for, reset_interview
from questions import build_questions, fresh_audio_question, coding_problem_for
from audio import speak_question
from ai_client import process_audio_with_gemini
from coding import execute_code
from scoring import final_scorecard

st.set_page_config(page_title="AI Audio Interviewer", layout="wide")

# Initialize session state
init_state(st)

st.title("AI Interviewer")
st.caption("10 questions, multiple rounds, audio answers, coding, and final scoring.")

if not GEMINI_API_KEY:
    st.warning(
        "Add your Gemini API key as `GEMINI_API_KEY` in Streamlit secrets or your environment to enable transcription and scoring."
    )

if st.session_state.step == "setup":
    st.subheader("Interview Setup")
    if "field_choice" not in st.session_state:
        st.session_state.field_choice = (
            st.session_state.field
            if st.session_state.field in FIELD_OPTIONS
            else "Artificial Intelligence"
        )
    if "company_choice" not in st.session_state:
        st.session_state.company_choice = (
            st.session_state.target_company
            if st.session_state.target_company in COMPANY_OPTIONS
            else "Google"
        )
    if "level_choice" not in st.session_state:
        st.session_state.level_choice = (
            st.session_state.level
            if st.session_state.level in ["Entry Level", "Junior", "Mid-Level", "Senior", "Lead/Staff"]
            else "Entry Level"
        )

    col1, col2 = st.columns(2)
    with col1:
        field = st.selectbox(
            "Interview field",
            FIELD_OPTIONS,
            key="field_choice",
        )
        target_company = st.selectbox(
            "Target company",
            COMPANY_OPTIONS,
            key="company_choice",
        )
    with col2:
        level = st.selectbox(
            "Interview level",
            ["Entry Level", "Junior", "Mid-Level", "Senior", "Lead/Staff"],
            key="level_choice",
        )

    if st.button("Start 10-Question Interview", type="primary"):
        st.session_state.field = field
        st.session_state.level = level
        st.session_state.target_company = target_company
        st.session_state.questions = build_questions(field, level, target_company, MODEL_NAME)
        st.session_state.answers = [""] * len(st.session_state.questions)
        st.session_state.current_question = 0
        st.session_state.code_output = ""
        st.session_state.code_results = []
        st.session_state.user_code = ""
        st.session_state.final_report = ""
        st.session_state.step = "interview"
        st.rerun()

elif st.session_state.step == "interview":
    questions = st.session_state.questions
    current_index = st.session_state.current_question
    current = questions[current_index]
    question_number = current_index + 1

    progress = question_number / len(questions)
    st.progress(progress, text=f"Question {question_number} of {len(questions)}")

    st.subheader(f"{current['round']} Round")
    st.markdown(f"**Interviewer:** {current['question']}")
    if current["type"] == "audio":
        if st.button("Ask New Question (Text + Audio)", help="Generate a fresh question for this same round."):
            st.session_state.questions[current_index]["question"] = fresh_audio_question(
                st.session_state.field,
                st.session_state.level,
                st.session_state.target_company,
                current["round"],
            )
            save_answer(st, current_index, "")
            st.rerun()
    speak_question(current["question"], question_number)

    if current["type"] == "coding":
        problem = coding_problem_for(st.session_state.field)
        code_value = st.session_state.user_code or problem["starter"]
        st.markdown("**Coding editor**")
        user_code = st.text_area(
            "Write your Python solution",
            value=code_value,
            height=280,
            label_visibility="collapsed",
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Run Coding Tests", type="primary"):
                passed, output, results = execute_code(user_code, problem["tests"])
                st.session_state.user_code = user_code
                st.session_state.code_output = output or ("All tests passed." if passed else "Tests failed.")
                st.session_state.code_results = results
                if passed:
                    st.success("All visible tests passed.")
                else:
                    st.error("Some tests failed. Review the output and try again.")
        with col2:
            if st.button("Save Coding Answer"):
                st.session_state.user_code = user_code
                save_answer(st, current_index, "Coding answer submitted in editor.")
                st.success("Coding answer saved.")

        if st.session_state.code_output:
            st.markdown("**Console output**")
            st.code(st.session_state.code_output)
        if st.session_state.code_results:
            st.markdown("**Test results**")
            for result in st.session_state.code_results:
                status = "Passed" if result["passed"] else "Failed"
                st.write(
                    f"{status}: `{result['expression']}` -> expected `{result['expected']}`, got `{result['actual']}`"
                )
    else:
        st.info("Record your answer, then stop recording. The app will transcribe your response.")
        # Allow the user to type an answer instead of recording audio
        type_toggle_key = f"type_answer_{current_index}"
        use_typing = st.checkbox("Answer by typing instead of recording", key=type_toggle_key)

        if use_typing:
            typed_value = answer_for(st, current_index) or ""
            typed_answer = st.text_area(
                "Type your answer",
                value=typed_value,
                height=200,
                key=f"typed_{current_index}",
            )
            if st.button("Save Typed Answer"):
                save_answer(st, current_index, typed_answer)
                st.success("Typed answer saved.")
        else:
            audio = mic_recorder(
                start_prompt="Record Answer",
                stop_prompt="Stop Recording",
                just_once=False,
                key=f"recorder_{current_index}",
            )

            if audio:
                with st.spinner("Transcribing your answer..."):
                    try:
                        transcript = process_audio_with_gemini(audio["bytes"])
                        save_answer(st, current_index, transcript)
                        st.success("Answer recorded.")
                    except Exception as exc:
                        st.error(f"Could not process audio: {exc}")

        existing_answer = answer_for(st, current_index)
        if existing_answer:
            st.markdown("**Your transcribed answer**")
            st.write(existing_answer)

    st.divider()
    nav1, nav2, nav3 = st.columns([1, 1, 2])
    with nav1:
        if st.button("Previous", disabled=current_index == 0):
            st.session_state.current_question -= 1
            st.rerun()
    with nav2:
        next_label = "Finish Interview" if current_index == len(questions) - 1 else "Next"
        if st.button(next_label, type="primary"):
            if current_index == len(questions) - 1:
                st.session_state.step = "feedback"
            else:
                st.session_state.current_question += 1
            st.rerun()
    with nav3:
        answered_count = sum(1 for answer in st.session_state.answers if answer)
        if st.session_state.user_code:
            answered_count = max(answered_count, 1)
        st.caption(f"Saved responses: {answered_count}/{len(questions)}")

elif st.session_state.step == "feedback":
    st.subheader("Final Interview Scorecard")

    if not st.session_state.final_report:
        with st.spinner("Scoring the full interview..."):
            st.session_state.final_report = final_scorecard(st)

    st.markdown(st.session_state.final_report)

    with st.expander("Review saved answers"):
        for index, question in enumerate(st.session_state.questions, start=1):
            st.markdown(f"**Q{index}. {question['round']}**")
            st.write(question["question"])
            if question["type"] == "coding":
                st.code(st.session_state.user_code or "No code submitted.", language="python")
            else:
                st.write(answer_for(st, index - 1) or "No answer recorded.")

    if st.button("Restart Interview"):
        reset_interview(st, init_state)
        st.rerun()
