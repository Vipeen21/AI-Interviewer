import contextlib
import html
import io
import json
import os
import re

import streamlit as st
from streamlit_mic_recorder import mic_recorder

from config import MAX_QUESTIONS, FIELD_OPTIONS, COMPANY_OPTIONS, BIG_FOUR_COMPANIES, GEMINI_API_KEY, MODEL_NAME, JUDGE_MODEL_NAME
from state import init_state, save_answer, answer_for, reset_interview
from questions import build_questions, fresh_audio_question, fresh_coding_problem, coding_problem_for
from audio import speak_question
from ai_client import process_audio_with_gemini
from coding import execute_code
from scoring import final_scorecard

st.set_page_config(page_title="AI Audio Interviewer", layout="wide")

# Initialize session state
init_state(st)

st.title("AI Interviewer")
st.caption("10 questions, multiple rounds, audio answers, coding, and final scoring.")

st.markdown(
    """
    <style>
      .question-panel {
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 14px 16px;
        margin: 10px 0 14px;
        background: #ffffff;
      }
      .question-label {
        display: block;
        margin-bottom: 6px;
        color: #475569;
        font: 600 0.86rem system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      .question-text {
        color: #0f172a;
        font: 1rem/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        overflow-wrap: anywhere;
        white-space: normal;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_question_text(label, text):
    safe_text = html.escape(str(text)).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="question-panel">
          <span class="question-label">{html.escape(label)}</span>
          <div class="question-text">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def numeric_tokens(text):
    return re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?x?", str(text), flags=re.IGNORECASE)


def normalize_numeric_token(token):
    cleaned = token.replace(",", "").strip().lower()
    suffix = ""
    if cleaned.endswith("%") or cleaned.endswith("x"):
        suffix = cleaned[-1]
        cleaned = cleaned[:-1]
    return float(cleaned), suffix


def answer_region(candidate_answer):
    marker = "# Numerical answer"
    if marker in candidate_answer:
        return candidate_answer.split(marker, 1)[1]
    return candidate_answer


def accounting_answer_results(candidate_answer, expected_answers):
    submitted = numeric_tokens(answer_region(candidate_answer))
    results = []
    for index, expected in enumerate(expected_answers):
        expected_token = numeric_tokens(expected)[0]
        submitted_token = submitted[index] if index < len(submitted) else ""
        passed = False
        if submitted_token:
            try:
                submitted_value, submitted_suffix = normalize_numeric_token(submitted_token)
                expected_value, expected_suffix = normalize_numeric_token(expected_token)
                passed = abs(submitted_value - expected_value) <= 0.01
            except ValueError:
                passed = False
        results.append(
            {
                "expression": f"Answer {index + 1}",
                "expected": expected_token,
                "actual": submitted_token or "No numeric answer found",
                "passed": passed,
            }
        )
    return results


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
        possible_companies = BIG_FOUR_COMPANIES if st.session_state.field == "Accounting" else COMPANY_OPTIONS
        st.session_state.company_choice = (
            st.session_state.target_company
            if st.session_state.target_company in possible_companies
            else possible_companies[0]
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
        company_options = BIG_FOUR_COMPANIES if field == "Accounting" else COMPANY_OPTIONS
        target_company = st.selectbox(
            "Target company",
            company_options,
            key="company_choice",
        )
    with col2:
        level = st.selectbox(
            "Interview level",
            ["Entry Level", "Junior", "Mid-Level", "Senior", "Lead/Staff"],
            key="level_choice",
        )

    if st.button("Start Interview", type="primary"):
        st.session_state.field = field
        st.session_state.level = level
        st.session_state.target_company = target_company
        initial_problem = coding_problem_for(field, level)
        st.session_state.questions = build_questions(field, level, target_company, MODEL_NAME, coding_problem=initial_problem)
        st.session_state.answers = [""] * len(st.session_state.questions)
        st.session_state.current_question = 0
        st.session_state.code_output = ""
        st.session_state.code_results = []
        st.session_state.user_code = ""
        st.session_state.current_coding_problem = initial_problem
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
    render_question_text("Interviewer", current["question"])
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
        is_accounting_field = "accounting" in st.session_state.field.strip().lower()
        problem = st.session_state.get("current_coding_problem")
        if not problem:
            problem = coding_problem_for(st.session_state.field, st.session_state.level)
            st.session_state.current_coding_problem = problem
        code_value = st.session_state.user_code or problem["starter"]
        if st.button("Ask New Problem", help="Generate or refresh the technical prompt for this field."):
            new_problem = fresh_coding_problem(
                st.session_state.field,
                st.session_state.level,
                st.session_state.target_company,
                MODEL_NAME,
                current_prompt=current["question"],
            )
            if new_problem["prompt"] == current["question"]:
                # Ensure refresh actually changes the prompt when possible.
                new_problem = fresh_coding_problem(
                    st.session_state.field,
                    st.session_state.level,
                    st.session_state.target_company,
                    MODEL_NAME,
                    current_prompt=current["question"],
                )
            st.session_state.questions[current_index]["question"] = new_problem["prompt"]
            st.session_state.current_coding_problem = new_problem
            st.session_state.user_code = ""
            st.session_state.code_output = ""
            st.session_state.code_results = []
            save_answer(st, current_index, "")
            st.rerun()

        st.markdown("**Editor**")
        if is_accounting_field:
            st.caption("Enter only the numerical answer. For multiple answers, put each number on a new line.")
        user_code = st.text_area(
            "Enter only the numerical answer" if is_accounting_field else "Write your Python solution",
            value=code_value,
            height=280,
            label_visibility="collapsed",
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Run", type="primary"):
                st.session_state.user_code = user_code
                if is_accounting_field:
                    expected_answers = [str(expected) for _, expected in problem["tests"]]
                    results = accounting_answer_results(user_code, expected_answers)
                    passed = all(result["passed"] for result in results)
                    st.session_state.code_results = results
                    st.session_state.code_output = "Correct answer." if passed else "Incorrect answer. Check your numerical response."
                    if passed:
                        st.success("Correct answer.")
                    else:
                        st.error("Incorrect answer. Check your numerical response.")
                else:
                    passed, output, results = execute_code(user_code, problem["tests"])
                    st.session_state.code_output = output or ("All tests passed." if passed else "Tests failed.")
                    st.session_state.code_results = results
                    if passed:
                        st.success("All visible tests passed.")
                    else:
                        st.error("Some tests failed. Review the output and try again.")
        with col2:
            if st.button("Save Answer"):
                st.session_state.user_code = user_code
                save_answer(st, current_index, user_code if is_accounting_field else "Coding answer submitted in editor.")
                st.success("Answer saved.")

        if st.session_state.code_output:
            if is_accounting_field:
                st.markdown("**Result**")
                st.write(st.session_state.code_output)
            else:
                st.markdown("**Console output**")
                st.code(st.session_state.code_output)
        if st.session_state.code_results and not is_accounting_field:
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
        answered_count = sum(1 for answer in st.session_state.answers if answer and str(answer).strip())
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
            render_question_text("Question", question["question"])
            if question["type"] == "coding":
                st.code(st.session_state.user_code or "No code submitted.", language="python")
            else:
                st.write(answer_for(st, index - 1) or "No answer recorded.")

    if st.button("Restart Interview"):
        reset_interview(st, init_state)
        st.rerun()
