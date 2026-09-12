import os

from agents.bug_agent import review_bugs
from agents.security_agent import review_security
from agents.performance_agent import review_performance
from agents.maintainability_agent import review_maintainability
from agents.testing_agent import review_testing

from graph.state import ReviewState
from rag.github_document_loader import fetch_repository_documents
from rag.document_loader import (
    get_rag_documents,
    split_documents,
)
from rag.vector_store import create_vector_store

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from schemas.ai_review_schema import AIReviewResponse

load_dotenv()


async def bug_review_node(state: ReviewState,):
    result = await review_bugs(
        state["files"],
        state["retrieved_contexts"]["bug"]
    )

    return {
        "bug_review": result
    }


async def security_review_node(state: ReviewState):
    result = await review_security(
        state["files"],
        state["retrieved_contexts"]["security"]
    )

    return {
        "security_review": result
    }


async def performance_review_node(state: ReviewState):
    result = await review_performance(
        state["files"],
        state["retrieved_contexts"]["performance"]
    )

    return {
        "performance_review": result
    }


async def maintainability_review_node(state: ReviewState):
    result = await review_maintainability(
        state["files"],
        state["retrieved_contexts"]["maintainability"]
    )
    
    return {
        "maintainability_review": result
    }


async def testing_review_node(state: ReviewState):
    
    result = await review_testing(
        state["files"],
        state["retrieved_contexts"]["testing"]
    )
    
    return {
        "testing_review": result
    }

async def final_review_node(state: ReviewState):
    reviews = [
        state["bug_review"],
        state["security_review"],
        state["performance_review"],
        state["maintainability_review"],
        state["testing_review"],
    ]

    review_data = []

    for review in reviews:
        if review:
            review_data.append(review.model_dump())

    prompt = f"""
You are the final reviewer for an AI code review system.

Multiple specialized agents reviewed the same code change.

Your job is to produce the final code review.

Tasks:
- Combine the findings from all agents.
- Remove duplicate findings.
- Resolve conflicting findings when necessary.
- Keep only actionable and well-supported issues.
- Preserve the correct severity and category.
- Provide a concise overall summary.

Do not invent new issues that are not supported by the agent findings.

Return the result using the required structured format.

Specialized agent findings:
{review_data}
"""

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    llm = ChatGoogleGenerativeAI(
        model="gemma-4-31b-it",
        api_key=api_key
    )

    structured_llm = llm.with_structured_output(AIReviewResponse)

    final_review = await structured_llm.ainvoke(prompt)

    return {
        "final_review": final_review
    }

async def rag_node(state: ReviewState):

    repository = state["repository"]

    owner, repo = repository.split("/", 1)

    # 1. Fetch repository documents
    fetched_documents = await fetch_repository_documents(
        owner,
        repo,
        state["commit_sha"]
    )

    # 2. Use repository documents or fallback
    documents = get_rag_documents(
        fetched_documents
    )

    # 3. Split documents
    chunks = split_documents(
        documents
    )

    # 4. Create vector store
    vector_store = create_vector_store(
        chunks
    )

    # 5. Create retriever
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 3}
    )

    # 6. Build PR code context
    code = "\n\n".join(
        f"File: {file['filename']}\n"
        f"{file.get('patch', '')}"
        for file in state["files"]
    )

    agent_queries = {
        "bug": f"""
Find repository guidelines relevant to:

- bugs
- incorrect behavior
- edge cases
- error handling

Code change:

{code}
""",

        "security": f"""
Find repository guidelines relevant to:

- security
- authentication
- authorization
- secrets
- credentials
- input validation
- database security

Code change:

{code}
""",

        "performance": f"""
Find repository guidelines relevant to:

- performance
- database efficiency
- scalability
- caching
- algorithms
- resource usage

Code change:

{code}
""",

        "maintainability": f"""
Find repository guidelines relevant to:

- code structure
- readability
- type hints
- separation of responsibilities
- duplication
- maintainability

Code change:

{code}
""",

        "testing": f"""
Find repository guidelines relevant to:

- unit testing
- edge cases
- error paths
- mocking
- test coverage

Code change:

{code}
""",
    }

    retrieved_contexts = {}

    for agent_name, query in agent_queries.items():

        results = retriever.invoke(query)

        retrieved_contexts[agent_name] = "\n\n".join(
            document.page_content
            for document in results
        )

    return {
        "retrieved_contexts": retrieved_contexts
    }