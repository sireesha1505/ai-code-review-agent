from typing import TypedDict

from schemas.ai_review_schema import AIReviewResponse


class ReviewState(TypedDict):

    files: list[dict]
    commit_sha: str
    repository: str

    retrieved_contexts: dict[str, str]

    bug_review: AIReviewResponse | None
    security_review: AIReviewResponse | None
    performance_review: AIReviewResponse | None
    maintainability_review: AIReviewResponse | None
    testing_review: AIReviewResponse | None

    final_review: AIReviewResponse | None