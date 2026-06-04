import json
import random

from config import FIELD_PROBLEMS, QUESTION_BANK, ACCOUNTING_FIELD_PROBLEMS, ACCOUNTING_QUESTION_BANK
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


def coding_problem_for(field, level=None):
    normalized = field.strip().lower()
    import random

    if "accounting" in normalized:
        return random.choice(accounting_problems_for_level(level))

    for keyword, problems in FIELD_PROBLEMS.items():
        if keyword in normalized:
            try:
                return random.choice(problems)
            except Exception:
                return problems[0]
    # fallback to a random AI problem
    try:
        return random.choice(FIELD_PROBLEMS["artificial intelligence"])
    except Exception:
        return FIELD_PROBLEMS["artificial intelligence"][0]


def fresh_coding_problem(field, level, company, MODEL_NAME=None, current_prompt=None):
    # Prefer model-generated prompt when available
    normalized = field.strip().lower()
    base_problem = coding_problem_for(field, level)
    if MODEL_NAME:
        try:
            prompt = f"""
            Create one fresh Python coding interview prompt for a {level} {field} role at {company}.
            Return only the prompt text and no markdown. Keep it concise and suitable for a short live coding task.
            """
            response = call_model(prompt, MODEL_NAME)
            question = response.text.strip().strip('"')
            if question and question != (current_prompt or ""):
                return {"prompt": question, "starter": base_problem["starter"], "tests": base_problem["tests"]}
        except Exception:
            pass

    if "accounting" in normalized:
        return choose_unique_problem(accounting_problems_for_level(level), current_prompt) or base_problem

    # Local fallback: generate a fresh variant programmatically so each refresh
    # yields a truly new problem even when no remote model is available.
    try:
        generated = generate_local_coding_variant(field, avoid_prompt=current_prompt)
        if generated:
            return generated
    except Exception:
        pass

    # If we still only have the base problem, try to choose a different existing variant.
    if current_prompt:
        problems = FIELD_PROBLEMS.get(field.strip().lower(), [])
        different = [p for p in problems if p.get("prompt") != current_prompt]
        if different:
            return random.choice(different)

    return base_problem


def accounting_problems_for_level(level=None):
    normalized_level = (level or "").lower()
    if any(keyword in normalized_level for keyword in ["senior", "lead", "staff"]):
        problems = ACCOUNTING_FIELD_PROBLEMS.get("senior", [])
    elif any(keyword in normalized_level for keyword in ["mid", "intermediate"]):
        problems = ACCOUNTING_FIELD_PROBLEMS.get("mid-level", [])
    else:
        problems = ACCOUNTING_FIELD_PROBLEMS.get("entry level", [])

    return problems or ACCOUNTING_FIELD_PROBLEMS.get("entry level", [])


def choose_unique_problem(problems, avoid_prompt=None):
    if not problems:
        return None
    choices = [
        problem
        for problem in problems
        if not avoid_prompt or problem.get("prompt", "").strip() != avoid_prompt.strip()
    ]
    return random.choice(choices or problems)


def generate_local_coding_variant(field, avoid_prompt=None):
    """Create a programmatic coding problem variant for the given field.

    Returns a dict with `prompt`, `starter`, and `tests`.
    """
    normalized = field.strip().lower()
    import random

    def choose_unique(variants):
        choices = [v for v in variants if not avoid_prompt or v["prompt"].strip() != avoid_prompt.strip()]
        if choices:
            return random.choice(choices)
        return random.choice(variants)

    if "artificial intelligence" in normalized or "machine learning" in normalized:
        generators = [
            _gen_cosine_similarity,
            _gen_softmax,
            _gen_normalize_vector,
            _gen_top_k,
            _gen_moving_average,
            _gen_unique_counts,
        ]
        for _ in range(5):
            gen = random.choice(generators)
            generated = gen()
            if not avoid_prompt or generated["prompt"].strip() != avoid_prompt.strip():
                return generated
        return generated

    # fallback: pick a random existing problem variant if available
    problems = FIELD_PROBLEMS.get(normalized)
    if isinstance(problems, list) and problems:
        return choose_unique(problems)
    # final fallback: return a default AI problem
    try:
        ai_problems = FIELD_PROBLEMS["artificial intelligence"]
        return choose_unique(ai_problems)
    except Exception:
        default = {
            "prompt": "Write a function that returns the sum of a list of numbers.",
            "starter": "def sum_list(xs):\n    pass",
            "tests": [("sum_list([1,2,3])", 6)],
        }
        if avoid_prompt and default["prompt"] == avoid_prompt:
            default["prompt"] = "Write a function that multiplies all numbers in a list."
        return default


def _gen_cosine_similarity():
    return {
        "prompt": "Write a Python function `cosine_similarity(a, b)` that returns the cosine similarity between two numeric vectors.",
        "starter": "def cosine_similarity(a, b):\n    pass",
        "tests": [
            ("round(cosine_similarity([1, 0], [1, 0]), 4)", 1.0),
            ("round(cosine_similarity([1, 0], [0, 1]), 4)", 0.0),
        ],
    }


def _gen_softmax():
    return {
        "prompt": "Implement a function `softmax(scores)` that returns a probability distribution list using the softmax function.",
        "starter": "def softmax(scores):\n    pass",
        "tests": [
            ("[round(x,3) for x in softmax([1,1,1])]", [0.333, 0.333, 0.333]),
            ("round(sum(softmax([2,1,0])),3)", 1.0),
        ],
    }


def _gen_normalize_vector():
    return {
        "prompt": "Write a function `normalize_vector(v)` that returns a unit vector (L2 norm = 1) for a numeric list.",
        "starter": "def normalize_vector(v):\n    pass",
        "tests": [
            ("round(sum([x*x for x in normalize_vector([3,4])]),6)", 1.0),
            ("round(sum([x*x for x in normalize_vector([0,0,0])]),6)", 0.0),
        ],
    }


def _gen_top_k():
    return {
        "prompt": "Write `top_k(nums, k)` that returns a list of the k largest elements from `nums` in descending order.",
        "starter": "def top_k(nums, k):\n    pass",
        "tests": [
            ("top_k([1,5,3,2], 2)", [5,3]),
            ("top_k([4,4,4], 2)", [4,4]),
        ],
    }


def _gen_moving_average():
    return {
        "prompt": "Implement `moving_average(nums, k)` that returns list of moving averages with window size k.",
        "starter": "def moving_average(nums, k):\n    pass",
        "tests": [
            ("moving_average([1,2,3,4], 2)", [1.5,2.5,3.5]),
            ("moving_average([5,5,5], 3)", [5.0]),
        ],
    }


def _gen_unique_counts():
    return {
        "prompt": "Write `unique_counts(rows, key)` that returns a dict of counts for values of `key` in list of dicts.",
        "starter": "def unique_counts(rows, key):\n    pass",
        "tests": [
            ("unique_counts([{'a':1},{'a':2},{'a':1}], 'a')", {1:2,2:1}),
        ],
    }


def fallback_question(round_name, field, level, company=None):
    # Use accounting question bank for accounting interviews
    if "accounting" in field.strip().lower():
        question_bank = ACCOUNTING_QUESTION_BANK
    else:
        question_bank = QUESTION_BANK
    
    template = random.choice(question_bank.get(round_name, ["Tell me about yourself."]))
    question = template.format(field=field, level=level, company=company or "the firm")
    return question


def build_questions(field, level, company, MODEL_NAME=None, coding_problem=None):
    problem = coding_problem or coding_problem_for(field)
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
        {"round": "Ingenuity Technical", "type": "coding", "question": problem["prompt"]},
        {"round": "Coding Explanation", "type": "audio", "question": audio_questions["coding_explanation"]},
        {"round": "Closing", "type": "audio", "question": audio_questions["closing"]},
    ][:10]
