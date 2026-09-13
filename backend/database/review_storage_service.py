from datetime import datetime, timedelta, timezone

from database.models import CodeReview
from sqlalchemy.orm import Session


def save_code_review(
    db: Session,
    repository: str,
    pr_number: int,
    commit_sha: str,
    review: str | None
):
    code_review = CodeReview(
        repository=repository,
        pr_number=pr_number,
        commit_sha=commit_sha,
        review=review,
        status="queued"
    )

    db.add(code_review)
    db.commit()
    db.refresh(code_review)

    return code_review


def get_code_reviews(
    db: Session,
    repository: str,
    pr_number: int
):
    return (
        db.query(CodeReview)
        .filter(
            CodeReview.repository == repository,
            CodeReview.pr_number == pr_number
        )
        .order_by(CodeReview.created_at.desc())
        .all()
    )


def get_code_review_by_id(
    db: Session,
    review_id: int
):
    return (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )


def get_code_review_by_commit(
    db: Session,
    repository: str,
    pr_number: int,
    commit_sha: str
):
    return (
        db.query(CodeReview)
        .filter(
            CodeReview.repository == repository,
            CodeReview.pr_number == pr_number,
            CodeReview.commit_sha == commit_sha,
        )
        .order_by(CodeReview.created_at.desc())
        .first()
    )


def update_review_result(
    db: Session,
    review_id: int,
    review: str,
    status: str
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.review = review
    code_review.status = status
    code_review.error_message = None

    db.commit()
    db.refresh(code_review)

    return code_review


def update_review_status(
    db: Session,
    review_id: int,
    status: str
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.status = status

    db.commit()
    db.refresh(code_review)

    return code_review


def update_retry_count(
    db: Session,
    review_id: int,
    retry_count: int
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.retry_count = retry_count

    db.commit()
    db.refresh(code_review)

    return code_review


def update_review_failure(
    db: Session,
    review_id: int,
    error_message: str
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.status = "failed"
    code_review.error_message = error_message

    db.commit()
    db.refresh(code_review)

    return code_review


def update_review_duration(
    db: Session,
    review_id: int,
    duration_ms: int
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.duration_ms = duration_ms

    db.commit()
    db.refresh(code_review)

    return code_review


def reset_failed_review(
    db: Session,
    review_id: int
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    code_review.status = "queued"
    code_review.review = None
    code_review.retry_count = 0
    code_review.error_message = None
    code_review.duration_ms = None

    db.commit()
    db.refresh(code_review)

    return code_review


def get_stale_processing_reviews(
    db: Session,
    stale_minutes: int = 10
):
    cutoff_time = datetime.now(timezone.utc) - timedelta(
        minutes=stale_minutes
    )

    return (
        db.query(CodeReview)
        .filter(
            CodeReview.status == "processing",
            CodeReview.updated_at < cutoff_time,
        )
        .all()
    )


def reset_stale_review(
    db: Session,
    review_id: int
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    if code_review.status != "processing":
        return None

    code_review.status = "queued"
    code_review.retry_count += 1

    db.commit()
    db.refresh(code_review)

    return code_review


def refresh_review_heartbeat(
    db: Session,
    review_id: int
):
    code_review = (
        db.query(CodeReview)
        .filter(CodeReview.id == review_id)
        .first()
    )

    if not code_review:
        return None

    if code_review.status != "processing":
        return None

    code_review.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(code_review)

    return code_review