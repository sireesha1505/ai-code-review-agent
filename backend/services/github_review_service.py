from dotenv import load_dotenv
import os
import httpx

from common.logger import logger
from services.github_api_service import get_repo_name

load_dotenv()
token = os.getenv("GITHUB_TOKEN")


async def post_pull_request_comment(repo_name, pull_number, body):
	"""Post a PR-level comment (issues comments endpoint)."""
	if not token:
		raise RuntimeError("GITHUB_TOKEN is not configured")

	owner, repo = get_repo_name(repo_name)
	URL = f"https://api.github.com/repos/{owner}/{repo}/issues/{pull_number}/comments"

	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github+json"
	}

	async with httpx.AsyncClient() as client:
		response = await client.post(URL, headers=headers, json={"body": body}, timeout=10)
		response.raise_for_status()
		return response.json()


async def list_pull_request_comments(repo_name, pull_number):
	"""List PR-level comments for deduplication checks."""
	if not token:
		raise RuntimeError("GITHUB_TOKEN is not configured")

	owner, repo = get_repo_name(repo_name)
	URL = f"https://api.github.com/repos/{owner}/{repo}/issues/{pull_number}/comments"

	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github+json"
	}

	async with httpx.AsyncClient() as client:
		response = await client.get(URL, headers=headers, timeout=10)
		response.raise_for_status()
		return response.json()


async def post_review_comment(repo_name, pull_number, commit_sha, file_path, poisition, comment_body):
	"""Post an inline PR review comment on a specific file/line."""
	if not token:
		raise RuntimeError("GITHUB_TOKEN is not configured")

	if pull_number <= 0:
		raise ValueError("PR number is invalid")

	if poisition<=0:
		raise ValueError("GitHub diff position must be positive")

	owner, repo = get_repo_name(repo_name)

	URL = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"

	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github+json"
	}

	payload = {
		"body": comment_body,
		"commit_id": commit_sha,
		"path": file_path,
		"position": poisition
	}

	async with httpx.AsyncClient() as client:
		response = await client.post(
			URL,
			headers=headers,
			json=payload,
			timeout=10
		)

		logger.info("GitHub inline comment status: %s", response.status_code)
		logger.info("GitHub inline comment response: %s", response.text)

		response.raise_for_status()

		return response.json()


async def list_review_comments(repo_name, pull_number):
	"""List inline review comments for a PR to avoid duplicates."""
	if not token:
		raise RuntimeError("GITHUB_TOKEN is not configured")

	owner, repo = get_repo_name(repo_name)
	URL = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"

	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github+json"
	}

	async with httpx.AsyncClient() as client:
		response = await client.get(URL, headers=headers, timeout=10)
		response.raise_for_status()
		return response.json()

async def update_pull_request_comment(
    repo_name,
    comment_id: int,
    body: str
):
    """Update an existing PR-level comment."""
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")

    owner, repo = get_repo_name(repo_name)

    URL = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}/issues/comments/{comment_id}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            URL,
            headers=headers,
            json={"body": body},
            timeout=10
        )

        response.raise_for_status()
        return response.json()

STATUS_MARKER = "<!-- ai-code-review-status -->"


def find_review_status_comment(comments):
    for comment in comments:
        body = comment.get("body") or ""

        if STATUS_MARKER in body:
            return comment

    return None

async def create_or_update_review_status(
    repo_name,
    pull_number,
    status,
    commit_sha,
    issue_count=None
):
    comments = await list_pull_request_comments(
        repo_name,
        pull_number
    )

    existing_comment = find_review_status_comment(comments)

    if status == "running":
        body = f"""## 🤖 AI Code Review — In Progress

I'm analyzing this pull request for:

- Bugs
- Security issues
- Performance problems
- Maintainability
- Testing gaps

⏳ **Please wait while the review is running.**

{STATUS_MARKER}

Commit: `{commit_sha}`
"""

    elif status == "completed":
        body = f"""## ✅ AI Code Review — Completed

The AI review has finished successfully.

**Findings:** {issue_count or 0}

Inline findings and PR-level comments have been posted below.

{STATUS_MARKER}

Commit: `{commit_sha}`
"""

    else:
        body = f"""## ❌ AI Code Review — Failed

The AI review could not be completed.

Please try again.

{STATUS_MARKER}

Commit: `{commit_sha}`
"""

    if existing_comment:
        return await update_pull_request_comment(
            repo_name,
            existing_comment["id"],
            body
        )

    return await post_pull_request_comment(
        repo_name,
        pull_number,
        body
    )