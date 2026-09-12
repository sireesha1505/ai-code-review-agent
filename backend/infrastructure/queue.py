from infrastructure.connection import redis_client
import json
import time

QUEUE_NAME = "review_queue"
DELAYED_QUEUE_NAME  = "review_delayed_queue"

def enqueue_review_job(job: dict):
    job["retry_count"] = 0

    redis_client.rpush(
        QUEUE_NAME,
        json.dumps(job)
    )

def get_retry_delay(retry_count: int) -> int:
    return 2**retry_count

def enqueue_delayed_review_job(job: dict, delay: int):
    retry_at = time.time() + delay

    redis_client.zadd(
        DELAYED_QUEUE_NAME,
        {
            json.dumps(job): retry_at
        }
    )

def move_delayed_jobs_to_queue():
    now = time.time()

    jobs = redis_client.zrangebyscore(
        DELAYED_QUEUE_NAME,
        0,
        now
    )

    for job in jobs:
        redis_client.rpush(
            QUEUE_NAME,
            job
        )

        redis_client.zrem(
            DELAYED_QUEUE_NAME,
            job
        )