def init_state(st):
    defaults = {
        "step": "setup",
        "field": "",
        "level": "Entry Level",
        "target_company": "",
        "questions": [],
        "current_question": 0,
        "answers": [],
        "code_output": "",
        "code_results": [],
        "user_code": "",
        "final_report": "",
        "final_feedback": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_answer(st, question_index, transcript):
    answers = list(st.session_state.get("answers", []))
    while len(answers) < len(st.session_state.get("questions", [])):
        answers.append("")
    answers[question_index] = transcript
    st.session_state["answers"] = answers


def answer_for(st, question_index):
    if question_index < len(st.session_state.get("answers", [])):
        return st.session_state["answers"][question_index]
    return ""


def reset_interview(st, init_state_fn):
    for key in [
        "questions",
        "answers",
        "current_question",
        "code_output",
        "code_results",
        "user_code",
        "final_report",
        "final_feedback",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    init_state_fn(st)
    st.session_state["step"] = "setup"
