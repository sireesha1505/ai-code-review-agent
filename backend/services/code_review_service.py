REVIEWABLE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".go",
    ".rs",
}

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from schemas.ai_review_schema import AIReviewResponse
load_dotenv()

def filter_changed_files(files):
    reviewable_files = []

    for file in files:
        filename = file.get("filename", "")

        if any(filename.endswith(ext) for ext in REVIEWABLE_EXTENSIONS):
            reviewable_files.append(file)

    return reviewable_files

def prepare_review_input(files):
    review_files = []

    for file in files:
        review_files.append({
            "filename": file.get("filename"),
            "patch": file.get("patch")
        })

    return review_files

def build_review_prompt(files):
    prompt = """
            You are an experienced software engineer performing a code review.

            Review the following changed files from a GitHub Pull Request.

            Look for:
            - Bugs
            - Security issues
            - Performance problems
            - Bad practices
            - Maintainability issues
            - Missing error handling
            - Test issues

            For every issue provide:
            - File
            - Line
            - Severity
            - Explanation
            - Suggested fix

            Only report actionable issues.
            Return the review using the following structure:

            {
                "summary": "Brief overall review summary",
                "issues": [
                    {
                        "file": "filename",
                        "line": 42,
                        "severity": "low|medium|high",
                        "category": "bug|security|performance|maintainability|error_handling|testing",
                        "explanation": "description of the issue",
                        "suggested_fix": "suggested fix for the issue"
                    }
                ]
            }

            Only report actionable issues.
            Do not report issues that are purely stylistic or based on speculation.

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

async def review_code(prompt):
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    llm=ChatGoogleGenerativeAI(model="gemma-4-31b-it", api_key = API_KEY)
    structured_llm = llm.with_structured_output(
        AIReviewResponse
    )
    result = await structured_llm.ainvoke(prompt)

    return result
