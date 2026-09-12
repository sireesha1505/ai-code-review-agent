import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from schemas.ai_review_schema import AIReviewResponse

load_dotenv()

def build_bug_review_prompt(files, retrieved_context):
    prompt = f"""
You are a senior software engineer specializing in detecting
functional bugs in source code.

Repository guidelines relevant to this review:

{retrieved_context}

Review ONLY the changed code provided below.

Focus on actual correctness problems such as:

- Incorrect conditions or branching
- Off-by-one errors
- Incorrect loop behavior
- Null/None handling
- Incorrect state updates
- Incorrect API or database usage
- Race-condition-like logic errors
- Incorrect exception handling
- Invalid assumptions about input
- Resource handling problems that can cause functional failures

Rules:

1. Report only actionable bugs.
2. Do not report stylistic issues.
3. Do not report hypothetical or speculative problems.
4. Do not report security, performance, or maintainability issues
   unless they directly cause a functional bug.
5. Only report bugs that can be reasonably inferred from the
   provided code.
6. Include the exact file and line number when possible.

Repository-specific guidelines should be used as context.
Do not report a bug merely because the code violates a guideline.
Only report it if the violation causes or can reasonably cause
incorrect behavior.

Return the result using this structure:

{{
    "summary": "Brief summary of functional correctness",
    "issues": [
        {{
            "file": "filename",
            "line": 42,
            "severity": "low|medium|high",
            "category": "bug",
            "explanation": "What is wrong and why",
            "suggested_fix": "How to fix it"
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

async def review_bugs(files, retrieved_context):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = build_bug_review_prompt(files, retrieved_context)

    llm = ChatGoogleGenerativeAI(
        model = "gemma-4-31b-it",
        api_key = api_key
    )

    structured_llm = llm.with_structured_output(AIReviewResponse)
    response = await structured_llm.ainvoke(prompt)
    return response
