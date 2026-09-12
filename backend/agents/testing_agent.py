import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from schemas.ai_review_schema import AIReviewResponse

load_dotenv()


def build_testing_review_prompt(files, retrieved_context):
    prompt = f"""
You are a senior software engineer specializing in reviewing
automated tests and identifying testing gaps in source code.

Repository guidelines relevant to this review:

{retrieved_context}

Focus ONLY on whether the changed behavior is adequately tested.

Identify:
- Missing tests for newly introduced or modified behavior
- Missing important edge-case tests
- Missing error-path tests
- Missing tests for important branches
- Missing boundary-condition tests
- Missing tests for invalid or unexpected inputs
- Tests that do not actually validate the changed behavior
- Regression risks caused by insufficient test coverage

Do NOT evaluate whether the implementation itself is:
- buggy
- insecure
- slow
- poorly structured
- difficult to maintain

Those concerns are handled by other specialized agents.

If another agent would report a security, performance, bug,
or maintainability problem, do NOT repeat that problem.

Only report the testing consequence.

For example:

BAD:
"The function is vulnerable to SQL injection, so it needs tests."

GOOD:
"The newly introduced function has no tests covering special-character
or unexpected input. Add tests covering normal input and relevant
boundary/invalid input cases."

Rules:

1. Report only actionable testing issues.
2. Do not report stylistic issues.
3. Do not report hypothetical or speculative problems.
4. Do not duplicate findings that belong to other review categories.
5. Do not explain the underlying bug, security vulnerability,
   performance problem, or maintainability problem.
6. Only report testing issues that can be reasonably inferred from
   the provided code.
7. Do not assume that a test is missing unless the provided changes
   give enough evidence to identify a meaningful testing gap.
8. Include the exact file and line number when possible.
9. Every reported issue must explain what test is missing and what
   behavior that test should validate.

Return the result using this structure:

{{
    "summary": "Brief summary of testing findings",
    "issues": [
        {{
            "file": "filename",
            "line": 42,
            "severity": "low|medium|high",
            "category": "testing",
            "explanation": "What testing gap exists and why it matters",
            "suggested_fix": "What test should be added or improved"
        }}
    ]
}}

Changed files:

"""

    for file in files:
        prompt += f"""
File: {file.get("filename")}

Patch:
{file.get("patch")}

-------------------------
"""

    return prompt


async def review_testing(files, retrieved_context):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    prompt = build_testing_review_prompt(files, retrieved_context)

    llm = ChatGoogleGenerativeAI(
        model="gemma-4-31b-it",
        api_key=api_key
    )

    structured_llm = llm.with_structured_output(
        AIReviewResponse
    )

    response = await structured_llm.ainvoke(prompt)

    return response