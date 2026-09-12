from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from database.connection import Base


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id = Column(Integer, primary_key=True, index=True)

    repository = Column(String, nullable=False)

    pr_number = Column(Integer, nullable=False)

    commit_sha = Column(String, nullable=False)

    review = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="queued")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    retry_count = Column(Integer, nullable=False, default=0)

    error_message = Column(Text, nullable=True)

    duration_ms = Column(Integer, nullable=True)