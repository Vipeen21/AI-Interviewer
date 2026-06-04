import contextlib
import io


def execute_code(user_code, tests):
    stdout = io.StringIO()
    exec_globals = {"__builtins__": __builtins__}

    try:
        with contextlib.redirect_stdout(stdout):
            exec("import math\nimport statistics\nimport numpy as np\nimport pandas as pd", exec_globals)
            exec(user_code, exec_globals)

        results = []
        all_passed = True
        for expression, expected in tests:
            actual = eval(expression, exec_globals)
            passed = actual == expected
            if isinstance(actual, float) and isinstance(expected, float):
                passed = abs(actual - expected) < 1e-9
            all_passed = all_passed and passed
            results.append(
                {
                    "expression": expression,
                    "expected": expected,
                    "actual": actual,
                    "passed": passed,
                }
            )
        return all_passed, stdout.getvalue(), results
    except Exception as exc:
        return False, str(exc), []
