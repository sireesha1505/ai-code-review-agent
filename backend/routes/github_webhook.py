from fastapi import APIRouter, Request, HTTPException
import os
import hmac
import hashlib
from dotenv import load_dotenv

from services.github_webhook_service import (
    parse_request_body,
    parse_request_event,
    extract_pr_metadata,
    extract_event_action,
)

from services.github_review_service import (
    create_or_update_review_status
)

from infrastructure.queue import enqueue_review_job

from database.connection import SessionLocal
from database.review_storage_service import (
    save_code_review,
    get_code_review_by_commit,
    reset_failed_review,
)

from common.logger import logger


router = APIRouter(
    tags=["github_webhook"],
    prefix="/webhook"
)

load_dotenv()


ACTIONS = {
    "opened",
    "synchronize",
    "reopened",
    "edited"
}


@router.post("/github")
async def accessWebhook(request: Request):

    body = await request.body()

    signature = (
        request.headers.get("X-Hub-Signature-256")
        or request.headers.get("X-Hub-Signature")
    )

    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    event = request.headers.get("X-GitHub-Event")

    if secret:
        if not signature:
            raise HTTPException(
                status_code=401,
                detail="Missing GitHub signature"
            )

        secret_bytes = secret.encode("utf-8")

        digest = hmac.new(
            secret_bytes,
            body,
            hashlib.sha256
        ).hexdigest()

        expected_signature = "sha256=" + digest

        if not hmac.compare_digest(
            expected_signature,
            signature
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid GitHub signature"
            )

    parsed_request_body = parse_request_body(body)

    extracted_event = parse_request_event(event)
    extracted_action = extract_event_action(
        parsed_request_body
    )

    if (
        extracted_event != "pull_request"
        or extracted_action not in ACTIONS
    ):
        return {
            "message": "Event ignored"
        }

    metadata = extract_pr_metadata(
        parsed_request_body
    )

    repo_name = metadata.get("repository")
    pull_number = metadata.get("number")
    commit_sha = metadata.get("commit_sha")

    if not repo_name:
        raise HTTPException(
            status_code=400,
            detail="Repository name missing"
        )

    if not pull_number:
        raise HTTPException(
            status_code=400,
            detail="Pull request number missing"
        )

    if not commit_sha:
        raise HTTPException(
            status_code=400,
            detail="Commit SHA missing"
        )

    pull_number = int(pull_number)

    db = SessionLocal()

    try:
        existing_review = get_code_review_by_commit(
            db=db,
            repository=repo_name,
            pr_number=pull_number,
            commit_sha=commit_sha
        )

        if existing_review:

            if existing_review.status == "completed":
                logger.info(
                    "Completed review already exists | "
                    "review_id=%s | repo=%s | pr=%s | commit=%s",
                    existing_review.id,
                    repo_name,
                    pull_number,
                    commit_sha
                )

                return {
                    "message": "Review already completed",
                    "review_id": existing_review.id,
                    "status": existing_review.status
                }

            if existing_review.status in {
                "queued",
                "processing"
            }:
                logger.info(
                    "Review already in progress | "
                    "review_id=%s | status=%s | repo=%s | pr=%s | commit=%s",
                    existing_review.id,
                    existing_review.status,
                    repo_name,
                    pull_number,
                    commit_sha
                )

                return {
                    "message": "Review already in progress",
                    "review_id": existing_review.id,
                    "status": existing_review.status
                }

            if existing_review.status == "failed":
                review = reset_failed_review(
                    db=db,
                    review_id=existing_review.id
                )

                review_id = review.id

                logger.info(
                    "Retrying failed review | "
                    "review_id=%s | repo=%s | pr=%s | commit=%s",
                    review_id,
                    repo_name,
                    pull_number,
                    commit_sha
                )

            else:
                review = existing_review
                review_id = review.id

        else:
            review = save_code_review(
                db=db,
                repository=repo_name,
                pr_number=pull_number,
                commit_sha=commit_sha,
                review=None
            )

            review_id = review.id

    finally:
        db.close()

    try:
        await create_or_update_review_status(
            repo_name=repo_name,
            pull_number=pull_number,
            status="running",
            commit_sha=commit_sha
        )

    except Exception as e:
        logger.warning(
            "Failed to post review status | "
            "review_id=%s | repo=%s | pr=%s | error=%s",
            review_id,
            repo_name,
            pull_number,
            str(e)
        )

    job = {
        "review_id": review_id,
        "repository": repo_name,
        "pr_number": pull_number,
        "commit_sha": commit_sha
    }

    enqueue_review_job(job)

    logger.info(
        "Review queued | review_id=%s | repo=%s | pr=%s",
        review_id,
        repo_name,
        pull_number
    )

    return {
        "message": "Review queued successfully",
        "review_id": review_id,
        "status": "queued"
    }