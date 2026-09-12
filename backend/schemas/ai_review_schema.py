from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ReviewSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"


class ReviewIssue(BaseModel):
    file: str
    line: Optional[int] = None
    severity: ReviewSeverity
    category: ReviewCategory
    explanation: str
    suggested_fix: Optional[str] = None


class AIReviewResponse(BaseModel):
    summary: str
    issues: list[ReviewIssue]