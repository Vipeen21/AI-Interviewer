import json
import random

from config import FIELD_PROBLEMS, QUESTION_BANK
from ai_client import call_model


def parse_json_questions(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1)
    return json.loads(cleaned)


def generate_ai_audio_questions(field, level, company, genai_client=None, MODEL_NAME=None):
    # keep function shape compatible with previous usage; actual genai client is used inside call_model
    try:
        prompt = f"""
        Create fresh interview questions for a {level} {field} interview at {company}.
        Return only valid JSON with these exact keys:
        introduction, project, behavioral_feedback, behavioral_communication,
        technical_fundamentals, technical_scenario, technical_design,
        coding_explanation, closing.
        Each value must be one concise interview question.
        Do not include markdown.
        Make the questions match {company}'s interview style where reasonable, but do not claim to use private company questions.
        Make them different from generic examples and suitable for audio interviewing.
        """
        response = call_model(prompt, MODEL_NAME)
        data = parse_json_questions(response.text)
        required = [
            "introduction",
            "project",
            "behavioral_feedback",
            "behavioral_communication",
            "technical_fundamentals",
            "technical_scenario",
            "technical_design",
            "coding_explanation",
            "closing",
        ]
        if all(isinstance(data.get(key), str) and data[key].strip() for key in required):
            return data
    except Exception:
        return None
    return None


def fresh_audio_question(field, level, company, round_name, MODEL_NAME=None):
    try:
        prompt = f"""
        Ask one fresh {round_name} interview question for a {level} {field} candidate interviewing at {company}.
        Return only the question text. Make it specific, concise, and different from common boilerplate.
        Match {company}'s interview style where reasonable, but do not claim to use private company questions.
        """
        response = call_model(prompt, MODEL_NAME)
        question = response.text.strip().strip('"')
        if question:
            return question
    except Exception:
        pass
    # fallback to static bank
    template = random.choice(QUESTION_BANK.get(round_name, ["Tell me about yourself."]))
    return template.format(field=field, level=level)


def coding_problem_for(field):
    normalized = field.strip().lower()
    for keyword, problem in FIELD_PROBLEMS.items():
        if keyword in normalized:
            return problem
    return FIELD_PROBLEMS["artificial intelligence"]


def fallback_question(round_name, field, level, company=None):
    template = random.choice(QUESTION_BANK.get(round_name, ["Tell me about yourself."]))
    question = template.format(field=field, level=level)
    if company:
        return f"{question} Please frame your answer for a {company} interview."
    return question


def build_questions(field, level, company, MODEL_NAME=None):
    problem = coding_problem_for(field)
    generated = generate_ai_audio_questions(field, level, company, MODEL_NAME=MODEL_NAME)

    audio_questions = generated or {
        "introduction": fallback_question("Introduction", field, level, company),
        "project": fallback_question("Project", field, level, company),
        "behavioral_feedback": fallback_question("Behavioral Feedback", field, level, company),
        "behavioral_communication": fallback_question("Behavioral Communication", field, level, company),
        "technical_fundamentals": fallback_question("Technical Fundamentals", field, level, company),
        "technical_scenario": fallback_question("Technical Scenario", field, level, company),
        "technical_design": fallback_question("Technical Design", field, level, company),
        "coding_explanation": fallback_question("Coding Explanation", field, level, company),
        "closing": fallback_question("Closing", field, level, company),
    }

    return [
        {"round": "Introduction", "type": "audio", "question": audio_questions["introduction"]},
        {"round": "Project", "type": "audio", "question": audio_questions["project"]},
        {"round": "Behavioral Feedback", "type": "audio", "question": audio_questions["behavioral_feedback"]},
        {"round": "Behavioral Communication", "type": "audio", "question": audio_questions["behavioral_communication"]},
        {"round": "Technical Fundamentals", "type": "audio", "question": audio_questions["technical_fundamentals"]},
        {"round": "Technical Scenario", "type": "audio", "question": audio_questions["technical_scenario"]},
        {"round": "Technical Design", "type": "audio", "question": audio_questions["technical_design"]},
        {"round": "Coding", "type": "coding", "question": problem["prompt"]},
        {"round": "Coding Explanation", "type": "audio", "question": audio_questions["coding_explanation"]},
        {"round": "Closing", "type": "audio", "question": audio_questions["closing"]},
    ][:10]
