#!/bin/sh

alembic upgrade head

python -m workers.review_worker &

exec uvicorn main:app --host 0.0.0.0 --port 8000