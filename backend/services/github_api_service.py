from dotenv import load_dotenv
import os
import httpx

load_dotenv()

token = os.environ.get("GITHUB_TOKEN")


def get_repo_name(repo_name):
    parsed_repo_name = repo_name.strip().split("/")

    if len(parsed_repo_name) != 2 or not all(parsed_repo_name):
        raise ValueError(
            "Invalid repository name. Expected format: owner/repository"
        )

    owner = parsed_repo_name[0]
    repo = parsed_repo_name[1]

    return owner, repo


async def get_pull_request(repo_name, pull_number):
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")

    if pull_number <= 0:
        raise ValueError("PR number is invalid")

    owner, repo = get_repo_name(repo_name)

    URL = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            URL,
            headers=headers,
            timeout=5
        )

        response.raise_for_status()

        return response.json()


async def get_pull_request_files(repo_name, pull_number):
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")

    if pull_number <= 0:
        raise ValueError("PR number is invalid")

    owner, repo = get_repo_name(repo_name)
    URL = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}/pulls/{pull_number}/files"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            URL,
            headers=headers,
            timeout=5
        )

        response.raise_for_status()

        return response.json()


async def post_pull_request_comment(repo_name, pull_number, body):
    """Post a comment on the PR (uses Issues API to comment on PRs)."""
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