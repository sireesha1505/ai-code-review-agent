from infrastructure.connection import redis_client
import json
import asyncio
import time

from services.review_service import process_code_review
from database.connection import SessionLocal
from database.review_storage_service import (
    update_review_result,
    update_review_status,
    update_retry_count,
    update_review_failure,
    update_review_duration,
)
from services.github_api_service import get_pull_request_files
from infrastructure.queue import (
    get_retry_delay,
    enqueue_delayed_review_job,
    QUEUE_NAME,
    move_delayed_jobs_to_queue,
)
from common.logger import logger


MAX_RETRIES = 3


def start_worker():
    while True:
        move_delayed_jobs_to_queue()

        job = redis_client.blpop(
            QUEUE_NAME,
            timeout=1,
        )

        if not job:
            continue

        job_data = json.loads(job[1])

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

        try:
            update_review_status(
                db=db,
                review_id=review_id,
                status="processing",
            )

            changed_files_info = asyncio.run(
                get_pull_request_files(
                    repo_name,
                    pull_number,
                )
            )

            logger.info(
                "Fetched PR files | review_id=%s | files=%s",
                review_id,
                len(changed_files_info),
            )

            llm_response = asyncio.run(
                process_code_review(
                    repo_name,
                    pull_number,
                    commit_sha,
                    changed_files_info,
                )
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

                logger.error(
                    "Review failed permanently | "
                    "review_id=%s | retries=%s | error=%s",
                    review_id,
                    retry_count,
                    str(e),
                )

        finally:
            db.close()


if __name__ == "__main__":
    start_worker()