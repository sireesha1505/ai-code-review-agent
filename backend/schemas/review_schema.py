from datetime import datetime
from pydantic import BaseModel


class CodeReviewResponse(BaseModel):
    id: int
    repository: str
    pr_number: int
    commit_sha: str
    review: str
    created_at: datetime

    class Config:
        from_attributes = True