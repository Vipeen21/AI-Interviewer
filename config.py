import os

import google.genai as genai

# Basic app constants
MAX_QUESTIONS = 10

FIELD_OPTIONS = [
    "Artificial Intelligence",
    "Data Science",
    "Machine Learning",
    "Data Analyst",
    "Accounting",
]

COMPANY_OPTIONS = [
    "Google",
    "Microsoft",
    "Meta",
    "Amazon",
    "Deloitte",
    "KPMG",
    "PwC",
    "EY",
]

FIELD_PROBLEMS = {
    "artificial intelligence": {
        "prompt": "Write a Python function `cosine_similarity(a, b)` that returns the cosine similarity between two numeric vectors.",
        "starter": "def cosine_similarity(a, b):\n    pass",
        "tests": [
            ("round(cosine_similarity([1, 0], [1, 0]), 4)", 1.0),
            ("round(cosine_similarity([1, 0], [0, 1]), 4)", 0.0),
        ],
    },
    "data science": {
        "prompt": "Write a Python function `rmse(actual, predicted)` that returns the root mean squared error.",
        "starter": "def rmse(actual, predicted):\n    pass",
        "tests": [
            ("rmse([3, 5], [2, 8])", 2.23606797749979),
            ("round(rmse([1, 2, 3], [1, 2, 3]), 4)", 0),
        ],
    },
    "data analyst": {
        "prompt": "Write a Python function `missing_pct(row)` that returns the percentage of missing values in a dictionary.",
        "starter": "def missing_pct(row):\n    pass",
        "tests": [
            ("missing_pct({'a': 1, 'b': None, 'c': 3})", 33.33333333333333),
            ("missing_pct({'a': None, 'b': None})", 100),
        ],
    },
    "machine learning": {
        "prompt": "Write a Python function `l2_penalty(weights, alpha)` that returns alpha times the sum of squared weights.",
        "starter": "def l2_penalty(weights, alpha):\n    pass",
        "tests": [
            ("l2_penalty([0.5, -1.2, 3.0], 0.1)", 1.069),
            ("l2_penalty([1, 2, 3], 0.5)", 7.0),
        ],
    },
    "accounting": {
        "prompt": "Write a Python function `current_ratio(current_assets, current_liabilities)` that returns the current ratio as current_assets divided by current_liabilities.",
        "starter": "def current_ratio(current_assets, current_liabilities):\n    pass",
        "tests": [
            ("current_ratio(15000, 5000)", 3.0),
            ("round(current_ratio(12000, 7500), 2)", 1.6),
        ],
    },
}

QUESTION_BANK = {
    "Introduction": [
        "Introduce yourself and connect your background to a {level} {field} role.",
        "Tell me what made you choose {field}, and what kind of work you want to do next.",
        "Give me a short professional summary, then highlight one achievement relevant to {field}.",
    ],
    "Project": [
        "Walk me through a project that proves your readiness for {field}. What was your role, result, and learning?",
        "Describe one project where you solved a difficult problem in {field}. What tradeoffs did you make?",
        "Tell me about a project you would be proud to discuss with a hiring manager for {field}.",
    ],
    "Behavioral Feedback": [
        "Tell me about a time you received difficult feedback. What changed in your work afterward?",
        "Describe a time your first approach was wrong. How did you recognize it and recover?",
        "Give an example of a time you improved after a mistake or missed expectation.",
    ],
    "Behavioral Communication": [
        "Describe a situation where you had to explain a technical idea to a non-technical stakeholder.",
        "Tell me about a time you had to align people who disagreed on a technical decision.",
        "How do you communicate uncertainty, risk, or limitations in a technical project?",
    ],
    "Technical Fundamentals": [
        "What are the most important fundamentals someone at {level} level should know in {field}, and why?",
        "Explain three core concepts in {field} that you rely on when solving practical problems.",
        "What separates a shallow understanding of {field} from a production-ready understanding?",
    ],
    "Technical Scenario": [
        "Imagine a production system or project in {field} is giving unreliable results. How would you debug it step by step?",
        "A {field} solution works in testing but fails after release. What would you investigate first?",
        "How would you diagnose poor performance, bias, or incorrect outputs in a {field} system?",
    ],
    "Technical Design": [
        "Design a small end-to-end solution for a realistic {field} problem. Include data, logic, evaluation, and deployment concerns.",
        "Design a practical {field} system for a business user. What components, metrics, and risks matter?",
        "How would you take a {field} prototype from notebook or experiment to a reliable application?",
    ],
    "Coding Explanation": [
        "Explain your coding solution aloud. Include the approach, edge cases, and time and space complexity.",
        "Walk me through your code as if I am reviewing it. What decisions did you make and why?",
        "Explain how you would test, optimize, and maintain the coding solution you wrote.",
    ],
    "Closing": [
        "What is one strength you would bring to this role, and what is one skill you are actively improving?",
        "Why should the interviewer feel confident moving you to the next round?",
        "What would you want to learn or prove in your first 90 days in this role?",
    ],
}


def get_api_key():
    """Read the Gemini API key from Streamlit secrets or the environment."""
    try:
        # Keep this lightweight; Streamlit will import this module at runtime.
        import streamlit as st

        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


GEMINI_API_KEY = get_api_key()
genai_client = genai.client.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL_NAME = "gemini-2.5-flash"
JUDGE_MODEL_NAME = "gemini-2.5-pro"
