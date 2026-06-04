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

BIG_FOUR_COMPANIES = ["Deloitte", "KPMG", "PwC", "EY"]

FIELD_PROBLEMS = {
    "artificial intelligence": [
        {
            "prompt": "Write a Python function `cosine_similarity(a, b)` that returns the cosine similarity between two numeric vectors.",
            "starter": "def cosine_similarity(a, b):\n    pass",
            "tests": [
                ("round(cosine_similarity([1, 0], [1, 0]), 4)", 1.0),
                ("round(cosine_similarity([1, 0], [0, 1]), 4)", 0.0),
            ],
        },
        {
            "prompt": "Implement a function `softmax(scores)` that returns a probability distribution list using the softmax function.",
            "starter": "def softmax(scores):\n    pass",
            "tests": [
                ("[round(x,3) for x in softmax([1,1,1])]", [0.333, 0.333, 0.333]),
                ("round(sum(softmax([2,1,0])),3)", 1.0),
            ],
        },
        {
            "prompt": "Write a function `normalize_vector(v)` that returns a unit vector (L2 norm = 1) for a numeric list.",
            "starter": "def normalize_vector(v):\n    pass",
            "tests": [
                ("round(sum([x*x for x in normalize_vector([3,4])]),6)", 1.0),
                ("round(sum([x*x for x in normalize_vector([0,0,0])]),6)", 0.0),
            ],
        },
    ],
    "data science": [
        {
            "prompt": "Write a Python function `rmse(actual, predicted)` that returns the root mean squared error.",
            "starter": "def rmse(actual, predicted):\n    pass",
            "tests": [
                ("rmse([3, 5], [2, 8])", 2.23606797749979),
                ("round(rmse([1, 2, 3], [1, 2, 3]), 4)", 0),
            ],
        },
        {
            "prompt": "Implement `mean_absolute_percentage_error(actual, predicted)` that returns the MAPE percentage.",
            "starter": "def mean_absolute_percentage_error(actual, predicted):\n    pass",
            "tests": [
                ("round(mean_absolute_percentage_error([100,200],[90,210]),2)", 7.5),
            ],
        },
    ],
    "data analyst": [
        {
            "prompt": "Write a Python function `missing_pct(row)` that returns the percentage of missing values in a dictionary.",
            "starter": "def missing_pct(row):\n    pass",
            "tests": [
                ("missing_pct({'a': 1, 'b': None, 'c': 3})", 33.33333333333333),
                ("missing_pct({'a': None, 'b': None})", 100),
            ],
        },
        {
            "prompt": "Create `unique_counts(rows, key)` that returns a dict of value->count for a list of dict rows by key.",
            "starter": "def unique_counts(rows, key):\n    pass",
            "tests": [
                ("unique_counts([{'a':1},{'a':2},{'a':1}], 'a')", {1:2,2:1}),
            ],
        },
    ],
    "machine learning": [
        {
            "prompt": "Write a Python function `l2_penalty(weights, alpha)` that returns alpha times the sum of squared weights.",
            "starter": "def l2_penalty(weights, alpha):\n    pass",
            "tests": [
                ("l2_penalty([0.5, -1.2, 3.0], 0.1)", 1.069),
                ("l2_penalty([1, 2, 3], 0.5)", 7.0),
            ],
        },
        {
            "prompt": "Implement `train_test_split_indices(n, test_frac)` that returns tuple of (train_idx, test_idx) lists given n samples.",
            "starter": "def train_test_split_indices(n, test_frac):\n    pass",
            "tests": [
                ("len(train_test_split_indices(10, 0.2)[0]) + len(train_test_split_indices(10,0.2)[1])", 10),
            ],
        },
    ],
}

ACCOUNTING_FIELD_PROBLEMS = {
    "entry level": [
        {
            "prompt": "A company has Current Assets of $500,000 and Current Liabilities of $200,000. Calculate the Current Ratio. Give only the numerical answer.",
            "starter": "Current Assets: $500,000\nCurrent Liabilities: $200,000\n\n# Numerical answer only:",
            "tests": [
                ("'2.5'", "2.5"),
            ],
        },
        {
            "prompt": "Company X has Total Debt of $300,000 and Shareholder Equity of $700,000. Calculate the Debt-to-Equity Ratio. Give only the numerical answer.",
            "starter": "Total Debt: $300,000\nShareholder Equity: $700,000\n\n# Numerical answer only:",
            "tests": [
                ("'0.43'", "0.43"),
            ],
        },
        {
            "prompt": "A product costs $50 to produce and sells for $120. Calculate the Gross Profit Margin percentage. Give only the numerical answer.",
            "starter": "Cost of Goods Sold (COGS): $50\nSelling Price: $120\n\n# Numerical answer only:",
            "tests": [
                ("'58.33%'", "58.33%"),
            ],
        },
        {
            "prompt": "A company has Net Income of $150,000 and Average Shareholder Equity of $1,000,000. Calculate Return on Equity (ROE) percentage. Give only the numerical answer.",
            "starter": "Net Income: $150,000\nAverage Shareholder Equity: $1,000,000\n\n# Numerical answer only:",
            "tests": [
                ("'15%'", "15%"),
            ],
        },
    ],
    "mid-level": [
        {
            "prompt": "Company has Total Assets of $2,000,000, Total Liabilities of $800,000, and Net Income of $300,000. Calculate Return on Assets (ROA) and Equity Multiplier. Give only the numerical answers, one per line.",
            "starter": "Total Assets: $2,000,000\nTotal Liabilities: $800,000\nNet Income: $300,000\n\n# Numerical answers only, one per line:",
            "tests": [
                ("'15%'", "15%"),
                ("'1.67'", "1.67"),
            ],
        },
        {
            "prompt": "An investor buys a stock at $80 and the company earned $4 per share this year. Calculate the P/E Ratio. Give only the numerical answer.",
            "starter": "Stock Price: $80\nEarnings Per Share (EPS): $4\n\n# Numerical answer only:",
            "tests": [
                ("'20'", "20"),
            ],
        },
        {
            "prompt": "A company reports EBIT of $500,000, Interest Expense of $50,000, Taxes of $90,000. Calculate EBITDA if Depreciation & Amortization is $60,000. Give only the numerical answer.",
            "starter": "EBIT: $500,000\nInterest Expense: $50,000\nTaxes: $90,000\nDepreciation & Amortization: $60,000\n\n# Numerical answer only:",
            "tests": [
                ("'560000'", "560000"),
            ],
        },
        {
            "prompt": "Two investments: A yields 8% annually with 3% inflation, B yields 10% with 5% inflation. Calculate the Real Rate of Return for both. Give only the numerical answers, one per line.",
            "starter": "Investment A: 8% nominal, 3% inflation\nInvestment B: 10% nominal, 5% inflation\n\n# Numerical answers only, one per line:",
            "tests": [
                ("'5%'", "5%"),
                ("'5%'", "5%"),
            ],
        },
    ],
    "senior": [
        {
            "prompt": "A Big 4 audit case: Company has Operating Cash Flow of $1.2M, Capital Expenditures of $300K, Dividends of $150K. Calculate Free Cash Flow and Free Cash Flow after dividends. Give only the numerical answers, one per line.",
            "starter": "Operating Cash Flow: $1,200,000\nCapital Expenditures: $300,000\nDividends: $150,000\n\n# Numerical answers only, one per line:",
            "tests": [
                ("'900000'", "900000"),
                ("'750000'", "750000"),
            ],
        },
        {
            "prompt": "Prepare a DuPont Analysis: Net Profit Margin 8%, Asset Turnover 2.0x, Equity Multiplier 2.5x. Calculate ROE. Give only the numerical answer.",
            "starter": "Net Profit Margin: 8%\nAsset Turnover: 2.0x\nEquity Multiplier: 2.5x\n\n# Numerical answer only:",
            "tests": [
                ("'40%'", "40%"),
            ],
        },
        {
            "prompt": "A company trades at $100 with EPS $5, Book Value per Share $25, and Growth Rate 10%. Calculate P/E, Price-to-Book, and PEG. Give only the numerical answers, one per line.",
            "starter": "Stock Price: $100\nEPS: $5\nBook Value per Share: $25\nExpected Growth Rate: 10%\n\n# Numerical answers only, one per line:",
            "tests": [
                ("'20'", "20"),
                ("'4.0'", "4.0"),
                ("'2.0'", "2.0"),
            ],
        },
        {
            "prompt": "A target company has annual revenue of $50M, and the acquirer pays $200M for the business. Calculate the EV/Revenue multiple. Give only the numerical answer.",
            "starter": "Target Revenue: $50,000,000\nAcquisition Price: $200,000,000\n\n# Numerical answer only:",
            "tests": [
                ("'4.0x'", "4.0x"),
            ],
        },
    ],
}

ACCOUNTING_QUESTION_BANK = {
    "Introduction": [
        "Introduce yourself and your experience with accounting, auditing, or finance at a {level} level. What drew you to a Big Four firm like {company}?",
        "Walk us through your background in accounting or finance. What's your strongest accounting competency, and why do you want to join {company}?",
        "Tell us about your accounting education and professional certifications (CPA, CMA, etc.). How do they prepare you for a role at {company}?",
    ],
    "Project": [
        "Describe your most complex audit or accounting engagement. What was your role, what challenges did you face, and what was the outcome?",
        "Walk me through a time you identified a material accounting issue or control weakness. How did you communicate it and what was resolved?",
        "Tell me about a financial analysis or modeling project you led. What was the business impact and what did you learn?",
    ],
    "Behavioral Feedback": [
        "Tell me about a time a senior partner or manager gave you critical feedback on your accounting work. How did you respond and what changed?",
        "Describe a situation where your first audit conclusion was wrong. How did you identify the error and what did you do?",
        "Give an example of when you had to revise your tax position or accounting treatment after further research or discussion.",
    ],
    "Behavioral Communication": [
        "Describe a time you had to explain a complex accounting or tax concept to a non-finance client or senior executive. How did you simplify it?",
        "Tell me about a time you had to push back on a client's proposed accounting treatment. How did you handle the disagreement professionally?",
        "Walk me through how you communicate audit findings or control recommendations to a {level} {company} finance leadership team.",
    ],
    "Technical Fundamentals": [
        "Explain the key differences between accrual and cash accounting. Why do GAAP and IFRS require accrual accounting for financial reporting?",
        "Walk me through the accounting cycle: journal entries, ledgers, trial balance, adjustments, and financial statements. How do errors propagate?",
        "What are the main components of a balance sheet? Explain the relationship between assets, liabilities, and equity, and how they must balance.",
    ],
    "Technical Scenario": [
        "A client recognizes revenue on a long-term contract but has not received payment. How do you assess the accounting treatment under ASC 606 or IFRS 15?",
        "A company is considering acquisition accounting. What are the key decisions around purchase price allocation, goodwill, and intangible assets?",
        "Your audit identified a large year-end journal entry from the finance team with unusual approval. How would you investigate and document your procedures?",
    ],
    "Technical Design": [
        "Design an internal control framework for a mid-market company's revenue cycle. What key controls and risk areas would you address?",
        "You are advising a growing startup on accounting policies and controls. What are the priority areas for financial reporting maturity and compliance?",
        "Design a tax planning strategy for a multinational client balancing aggressive positioning with audit and compliance risk.",
    ],
    "Coding Explanation": [
        "Walk me through your financial metric calculations. What formulas did you use, what assumptions did you make, and how would you validate the results?",
        "Explain your approach to the accounting case. How did you organize the data, what was your analytical process, and what insights did you derive?",
        "Describe any accounting or valuation methodology you applied in your calculations. How would you document this for a regulatory review?",
    ],
    "Closing": [
        "What is one accounting domain where you excel and one area where you want to build expertise in the first 90 days at {company}?",
        "Why should a Big Four partner be confident promoting you to the next level, and what sets you apart in an audit or advisory engagement?",
        "What would success look like for you in your first year at {company}, and how does this role align with your long-term career goals in accounting or finance?",
    ],
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
