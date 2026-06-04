import json

from ai_client import call_model
from config import MODEL_NAME, JUDGE_MODEL_NAME


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

    qa_pairs = []
    for index, question in enumerate(st.session_state.get("questions", [])):
        response = st.session_state.get("answers", [])[index] if index < len(st.session_state.get("answers", [])) else ""
        if question.get("type") == "coding":
            response = st.session_state.get("user_code") or "No code submitted."
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
    - Overall score out of 100
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
        answered = sum(1 for q in qa_pairs if q.get("response") and q.get("response") != "No answer recorded.")
        answer_ratio = answered / total if total else 0

        rounds = {"Introduction": 0, "Behavioral": 0, "Technical": 0, "Coding": 0, "Communication": 0}
        for item in qa_pairs:
            r = (item.get("round") or "").lower()
            resp = item.get("response") or ""
            scored = 1 if resp and resp != "No answer recorded." else 0
            if "intro" in r:
                rounds["Introduction"] += scored
            elif "behavioral" in r:
                rounds["Behavioral"] += scored
            elif "technical" in r and "design" not in r:
                rounds["Technical"] += scored
            elif "design" in r:
                rounds["Technical"] += scored
            elif "coding" in r:
                rounds["Coding"] += scored
            else:
                rounds["Communication"] += scored

        normalized = {k: min(100, int((v / max(1, total)) * 100)) for k, v in rounds.items()}

        coding_score = 0
        code_results = st.session_state.get("code_results", [])
        if code_results:
            passed = all(r.get("passed") for r in code_results)
            coding_score = 100 if passed else 50

        overall = int((answer_ratio * 70) + (coding_score / 100.0 * 30))

        strengths = [k for k, v in normalized.items() if v >= 70]
        weaknesses = [k for k, v in normalized.items() if v < 40]
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

        parts = [f"Overall score: {overall}/100", "\nRound-wise scores:"]
        for k, v in normalized.items():
            parts.append(f"- {k}: {v}/100")
        parts += [f"- Coding: {coding_score}/100", "\nStrengths:"]
        parts += [f"- {s}" for s in (strengths or ["None recorded"])][:5]
        parts += ["\nWeaknesses:"]
        parts += [f"- {w}" for w in (weaknesses or ["None recorded"])][:5]
        parts += ["\nImprovement plan:", f"- {improvement}", "\nFinal verdict:", f"- {verdict}", "\nFeedback:", f"{feedback_paragraph}"]

        parts.insert(0, "NOTE: AI scoring failed or quota exceeded; showing a local fallback scorecard.")
        return "\n".join(parts)
