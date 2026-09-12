import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from schemas.ai_review_schema import AIReviewResponse

load_dotenv()

def build_maintainability_review_prompt(files, retrieved_context):
    prompt = f"""
You are a senior software engineer specializing in detecting
maintainability issues in source code.

Repository guidelines relevant to this review:

{retrieved_context}

Review ONLY the changed code provided below.

Focus on structural and design problems that materially
increase the difficulty of understanding, modifying, testing,
or extending the code.

Focus on issues such as:

- Highly duplicated code
- Excessive complexity
- Poor separation of responsibilities
- Functions/classes doing too much
- Hard-to-maintain structure
- Tight coupling
- Poor abstractions
- Difficult-to-understand code when it materially affects maintainability

Rules:

1. Report only actionable maintainability issues.
2. Do not report stylistic issues.
3. Do not report hypothetical or speculative problems.
4. Do not report bugs, security, or performance issues
   unless they directly create a maintainability problem.
5. Only report maintainability issues that can be reasonably inferred
   from the provided code.
6. Include the exact file and line number when possible.

Return the result using this structure:

{{
    "summary": "Brief summary of maintainability findings",
    "issues": [
        {{
            "file": "filename",
            "line": 42,
            "severity": "low|medium|high",
            "category": "maintainability",
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

async def review_maintainability(files, retrieved_context):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = build_maintainability_review_prompt(files, retrieved_context)

    llm = ChatGoogleGenerativeAI(
        model = "gemma-4-31b-it",
        api_key = api_key
    )

    structured_llm = llm.with_structured_output(AIReviewResponse)
    response = await structured_llm.ainvoke(prompt)
    return response
