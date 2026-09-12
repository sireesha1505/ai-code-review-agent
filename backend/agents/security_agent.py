import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from schemas.ai_review_schema import AIReviewResponse

load_dotenv()

def build_security_review_prompt(files, retrieved_context):
    prompt = f"""
You are a senior software engineer specializing in detecting
security vulnerabilities in source code.

Repository guidelines relevant to this review:

{retrieved_context}

Review ONLY the changed code provided below.

Focus on actual correctness problems such as:

- Hardcoded secrets/API keys
- SQL injection
- Command injection
- Path traversal
- Unsafe deserialization
- Authentication/authorization issues
- Sensitive information exposure
- Insecure handling of user input
- Dangerous use of eval/exec
- Missing security controls where clearly required

Rules:

1. Report only actionable security issues.
2. Do not report stylistic issues.
3. Do not report hypothetical or speculative problems.
4. Do not report bugs, performance, or maintainability issues
   create a security vulnerability.
5. Only report securities that can be reasonably inferred from the
   provided code.
6. Include the exact file and line number when possible.

Return the result using this structure:

{{
    "summary": "Brief summary of security findings",
    "issues": [
        {{
            "file": "filename",
            "line": 42,
            "severity": "low|medium|high",
            "category": "security",
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

async def review_security(files, retrieved_context):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = build_security_review_prompt(files, retrieved_context)

    llm = ChatGoogleGenerativeAI(
        model = "gemma-4-31b-it",
        api_key = api_key
    )

    structured_llm = llm.with_structured_output(AIReviewResponse)
    response = await structured_llm.ainvoke(prompt)
    return response
