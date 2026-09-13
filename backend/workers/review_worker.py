from infrastructure.connection import redis_client
import json
import asyncio
import time

from services.review_service import process_code_review
from services.github_review_service import create_or_update_review_status

from database.connection import SessionLocal
from database.review_storage_service import (
    update_review_result,
    update_review_status,
    update_retry_count,
    update_review_failure,
    update_review_duration,
    get_stale_processing_reviews,
    reset_stale_review,
    refresh_review_heartbeat,
)

from services.github_api_service import get_pull_request_files

from infrastructure.queue import (
    get_retry_delay,
    enqueue_delayed_review_job,
    enqueue_review_job,
    QUEUE_NAME,
    move_delayed_jobs_to_queue,
)

from common.logger import logger


MAX_RETRIES = 3
STALE_REVIEW_MINUTES = 10
HEARTBEAT_INTERVAL_SECONDS = 60


def recover_stale_reviews():

    db = SessionLocal()

    try:
        stale_reviews = get_stale_processing_reviews(
            db=db,
            stale_minutes=STALE_REVIEW_MINUTES,
        )

        for review in stale_reviews:

            if review.retry_count >= MAX_RETRIES:
                update_review_failure(
                    db=db,
                    review_id=review.id,
                    error_message="Review became stale after worker interruption",
                )

                logger.error(
                    "Stale review failed permanently | "
                    "review_id=%s | retries=%s",
                    review.id,
                    review.retry_count,
                )

                continue

            reset_review = reset_stale_review(
                db=db,
                review_id=review.id,
            )

            if not reset_review:
                continue

            job = {
                "review_id": reset_review.id,
                "repository": reset_review.repository,
                "pr_number": reset_review.pr_number,
                "commit_sha": reset_review.commit_sha,
                "retry_count": reset_review.retry_count,
            }

            enqueue_review_job(job)

            logger.warning(
                "Stale review recovered | "
                "review_id=%s | retry=%s",
                reset_review.id,
                reset_review.retry_count,
            )

    except Exception as e:
        db.rollback()

        logger.error(
            "Failed to recover stale reviews | error=%s",
            str(e),
        )

    finally:
        db.close()


async def heartbeat_loop(review_id: int, stop_event: asyncio.Event):

    while not stop_event.is_set():

        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

            if stop_event.is_set():
                break

            db = SessionLocal()

            try:
                refresh_review_heartbeat(
                    db=db,
                    review_id=review_id,
                )

            finally:
                db.close()

        except Exception as e:
            logger.warning(
                "Review heartbeat failed | "
                "review_id=%s | error=%s",
                review_id,
                str(e),
            )


async def process_review(job_data):

    review_id = job_data["review_id"]
    repo_name = job_data["repository"]
    pull_number = job_data["pr_number"]
    commit_sha = job_data["commit_sha"]

    retry_count = job_data.get("retry_count", 0)

    logger.info(
        "Review started | review_id=%s | repo=%s | pr=%s | attempt=%s",
        review_id,
        repo_name,
        pull_number,
        retry_count + 1,
    )

    db = SessionLocal()
    start_time = time.perf_counter()

    heartbeat_stop_event = asyncio.Event()
    heartbeat_task = None

    try:
        update_review_status(
            db=db,
            review_id=review_id,
            status="processing",
        )

        heartbeat_task = asyncio.create_task(
            heartbeat_loop(
                review_id,
                heartbeat_stop_event,
            )
        )

        changed_files_info = await get_pull_request_files(
            repo_name,
            pull_number,
        )

        logger.info(
            "Fetched PR files | review_id=%s | files=%s",
            review_id,
            len(changed_files_info),
        )

        llm_response = await process_code_review(
            repo_name,
            pull_number,
            commit_sha,
            changed_files_info,
        )

        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        review_json = llm_response.model_dump_json()

        update_review_duration(
            db=db,
            review_id=review_id,
            duration_ms=duration_ms,
        )

        update_review_result(
            db=db,
            review_id=review_id,
            review=review_json,
            status="completed",
        )

        try:
            await create_or_update_review_status(
                repo_name=repo_name,
                pull_number=pull_number,
                status="completed",
                commit_sha=commit_sha,
                issue_count=len(llm_response.issues),
            )

        except Exception as status_error:
            logger.warning(
                "Failed to post completion status | "
                "review_id=%s | repo=%s | error=%s",
                review_id,
                repo_name,
                str(status_error),
            )

        logger.info(
            "Review completed | review_id=%s | duration_ms=%s",
            review_id,
            duration_ms,
        )

    except Exception as e:

        db.rollback()

        if retry_count < MAX_RETRIES:

            next_retry_count = retry_count + 1
            delay = get_retry_delay(retry_count)

            job_data["retry_count"] = next_retry_count

            update_retry_count(
                db=db,
                review_id=review_id,
                retry_count=next_retry_count,
            )

            update_review_status(
                db=db,
                review_id=review_id,
                status="queued",
            )

            enqueue_delayed_review_job(
                job_data,
                delay,
            )

            logger.warning(
                "Review retry scheduled | "
                "review_id=%s | retry=%s/%s | delay=%ss | error=%s",
                review_id,
                next_retry_count,
                MAX_RETRIES,
                delay,
                str(e),
            )

        else:

            duration_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            update_review_failure(
                db=db,
                review_id=review_id,
                error_message=str(e),
            )

            update_review_duration(
                db=db,
                review_id=review_id,
                duration_ms=duration_ms,
            )

            try:
                await create_or_update_review_status(
                    repo_name=repo_name,
                    pull_number=pull_number,
                    status="failed",
                    commit_sha=commit_sha,
                )

            except Exception as status_error:
                logger.warning(
                    "Failed to post failure status | "
                    "review_id=%s | repo=%s | error=%s",
                    review_id,
                    repo_name,
                    str(status_error),
                )

            logger.error(
                "Review failed permanently | "
                "review_id=%s | retries=%s | error=%s",
                review_id,
                retry_count,
                MAX_RETRIES,
                str(e),
            )

    finally:

        heartbeat_stop_event.set()

        if heartbeat_task:
            await heartbeat_task

        db.close()


def start_worker():

    while True:

        move_delayed_jobs_to_queue()

        recover_stale_reviews()

        job = redis_client.blpop(
            QUEUE_NAME,
            timeout=1,
        )

        if not job:
            continue

        job_data = json.loads(job[1])

        try:
            asyncio.run(
                process_review(job_data)
            )

        except Exception as e:
            logger.error(
                "Unhandled worker error | error=%s",
                str(e),
            )


if __name__ == "__main__":
    start_worker()