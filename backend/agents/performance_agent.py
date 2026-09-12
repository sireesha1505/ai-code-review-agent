import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from schemas.ai_review_schema import AIReviewResponse

load_dotenv()

def build_performance_review_prompt(files, retrieved_context):
    prompt = f"""
You are a senior software engineer specializing in detecting
performance issues in source code.

Repository guidelines relevant to this review:

{retrieved_context}

Review ONLY the changed code provided below.

Focus on actual correctness problems such as:

- O(n²) or worse when a significantly better complexity is clearly possible
  and the input size makes the difference meaningful
- Unnecessary database queries
- Repeated expensive operations
- Memory-heavy operations
- Inefficient loops
- Excessive API/network calls
- Missing pagination where relevant
- Unnecessary recomputation

Rules:

1. Report only actionable performance issues.
2. Do not report stylistic issues.
3. Do not report hypothetical or speculative problems.
4. Do not report bugs, security, or maintainability issues
unless they directly cause a performance issue.
5. Only report performance issues that can be reasonably inferred from the
   provided code.
6. Include the exact file and line number when possible.

Return the result using this structure:

{{
    "summary": "Brief summary of performance findings",
    "issues": [
        {{
            "file": "filename",
            "line": 42,
            "severity": "low|medium|high",
            "category": "performance",
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

async def review_performance(files, retrieved_context):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = build_performance_review_prompt(files, retrieved_context)

    llm = ChatGoogleGenerativeAI(
        model = "gemma-4-31b-it",
        api_key = api_key
    )

    structured_llm = llm.with_structured_output(AIReviewResponse)
    response = await structured_llm.ainvoke(prompt)
    return response
