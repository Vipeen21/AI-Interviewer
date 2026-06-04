import json

from ai_client import call_model
from config import MODEL_NAME, JUDGE_MODEL_NAME
from questions import coding_problem_for


def quick_feedback(question, answer, genai_available=True):
    if not genai_available or not answer:
        return ""
    prompt = f"""
    You are an AI interviewer. Give concise, useful feedback in 2 sentences.
    Question: {question}
    Candidate answer: {answer}
    Focus on clarity, specificity, and interview quality.
    """
    return call_model(prompt, MODEL_NAME).text.strip()


def final_scorecard(st, genai_available=True, call_model_fn=None):
    # call_model_fn: optional override (in tests or when injecting client)
    if genai_available and call_model_fn is None:
        call_model_fn = call_model

    answers = st.session_state.get("answers", [])
    user_code = st.session_state.get("user_code", "").strip()
    code_results = st.session_state.get("code_results", [])
    problem = st.session_state.get("current_coding_problem") or coding_problem_for(st.session_state.get("field", ""))
    starter_code = problem.get("starter", "").strip()

    qa_pairs = []
    for index, question in enumerate(st.session_state.get("questions", [])):
        response = answers[index].strip() if index < len(answers) else ""
        if question.get("type") == "coding":
            if not response:
                has_attempt = bool(code_results) or (user_code and user_code != starter_code)
                response = "Coding answer submitted in editor." if has_attempt else "No answer recorded."
        qa_pairs.append(
            {
                "round": question.get("round"),
                "question": question.get("question"),
                "response": response or "No answer recorded.",
            }
        )

    prompt = f"""
    You are a rigorous but fair interviewer.

    Candidate field: {st.session_state.get('field')}
    Candidate level: {st.session_state.get('level')}
    Target company/context: {st.session_state.get('target_company') or 'General interview'}
    Maximum questions asked: {len(qa_pairs)}

    Interview transcript as JSON:
    {json.dumps(qa_pairs, indent=2)}

    Coding test results:
    {json.dumps(st.session_state.get('code_results', []), indent=2, default=str)}

    Provide a polished scorecard with:
    - Overall score out of 100 using equal weight: 10 marks per question, including the coding/ingenuity technical question
    - Round-wise scores for introduction, behavioral, technical, coding, and communication
    - Strengths
    - Weaknesses
    - Specific improvement plan
    - Final verdict: Strong Hire, Hire, Lean Hire, or No Hire
    - A concise feedback paragraph summarizing the candidate's performance and next improvement steps
    Keep it direct and useful.
    """

    # Try remote scoring then fallback
    try:
        if genai_available:
            return call_model_fn(prompt, JUDGE_MODEL_NAME).text.strip()
        raise RuntimeError("GenAI not available")
    except Exception as exc:
        # Fallback deterministic scorecard
        total = len(qa_pairs)
        answered = sum(
            1
            for q in qa_pairs
            if q.get("response") and q["response"] != "No answer recorded."
        )

        coding_attempted = bool(code_results or (user_code and user_code != starter_code))
        coding_passed = bool(code_results) and all(r.get("passed") for r in code_results)

        rounds = {
            "Introduction": {"points": 0, "possible": 0},
            "Behavioral": {"points": 0, "possible": 0},
            "Technical": {"points": 0, "possible": 0},
            "Coding": {"points": 0, "possible": 0},
            "Communication": {"points": 0, "possible": 0},
        }
        for item in qa_pairs:
            r = (item.get("round") or "").lower()
            resp = item.get("response") or ""
            is_coding_round = r == "coding" or "ingenuity technical" in r
            scored = 1 if (coding_passed if is_coding_round else resp and resp != "No answer recorded.") else 0
            if "intro" in r:
                bucket = "Introduction"
            elif "behavioral" in r:
                bucket = "Behavioral"
            elif is_coding_round:
                bucket = "Coding"
            elif "technical" in r and "design" not in r:
                bucket = "Technical"
            elif "design" in r:
                bucket = "Technical"
            else:
                bucket = "Communication"
            rounds[bucket]["points"] += scored * 10
            rounds[bucket]["possible"] += 10

        normalized = {
            k: int((v["points"] / v["possible"]) * 100) if v["possible"] else 0
            for k, v in rounds.items()
        }
        overall = min(100, sum(v["points"] for v in rounds.values()))

        strengths = [k for k, v in normalized.items() if v >= 70]
        weaknesses = [k for k, v in normalized.items() if v < 40]
        coding_score = normalized["Coding"]
        if coding_score >= 80:
            strengths.append("Coding")
        elif coding_score < 40:
            weaknesses.append("Coding")

        verdict = "No Hire"
        if overall >= 85:
            verdict = "Strong Hire"
        elif overall >= 70:
            verdict = "Hire"
        elif overall >= 55:
            verdict = "Lean Hire"

        improvement = (
            "Practice clear, structured answers; focus on concrete examples; "
            "for coding, write tests and explain tradeoffs."
        )

        feedback_paragraph = (
            f"Answered {answered} of {total} questions. Overall the candidate shows "
            f"{'good' if overall>=70 else 'some'} potential; focus on the areas listed under Weaknesses."
        )

        parts = [
            "**NOTE:** AI scoring failed or quota exceeded; showing a local fallback scorecard.",
            "",
            (
                f"**Answered:** {answered}/{total} | "
                f"**Overall score:** {overall}/100 | "
                f"**Coding attempt:** {'Yes' if coding_attempted else 'No'} | "
                f"**Final verdict:** {verdict}"
            ),
            "",
            "Round-wise scores:",
        ]
        for k, v in normalized.items():
            parts.append(f"- {k}: {v}/100")
        parts += [f"- Coding question score: {10 if coding_passed else 0}/10", "\nStrengths:"]
        parts += [f"- {s}" for s in (strengths or ["None recorded"])][:5]
        parts += ["\nWeaknesses:"]
        parts += [f"- {w}" for w in (weaknesses or ["None recorded"])][:5]
        parts += ["\nImprovement plan:", f"- {improvement}", "\nFeedback:", f"{feedback_paragraph}"]

        return "\n".join(parts)
