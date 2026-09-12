import base64
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_API_URL = "https://api.github.com"

RAG_EXTENSIONS = {
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
}

IGNORED_PATH_PARTS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
}


def is_relevant_file(path: str) -> bool:
    parts = path.split("/")

    if any(part in IGNORED_PATH_PARTS for part in parts):
        return False

    _, extension = os.path.splitext(path)

    return extension.lower() in RAG_EXTENSIONS


async def fetch_repository_documents(
    owner: str,
    repo: str,
    commit_sha: str
):
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    documents = []

    async with httpx.AsyncClient(
        base_url=GITHUB_API_URL,
        headers=headers,
        timeout=20.0,
    ) as client:

        response = await client.get(
            f"/repos/{owner}/{repo}/git/trees/{commit_sha}",
            params={"recursive": "1"},
        )

        response.raise_for_status()

        tree = response.json().get("tree", [])

        for item in tree:

            if item.get("type") != "blob":
                continue

            file_path = item.get("path", "")

            if not is_relevant_file(file_path):
                continue

            response = await client.get(
                f"/repos/{owner}/{repo}/contents/{file_path}",
                params={"ref": commit_sha},
            )

            if response.status_code == 404:
                continue

            response.raise_for_status()

            data = response.json()
            content = data.get("content", "")

            if not content:
                continue

            try:
                decoded_content = base64.b64decode(
                    content
                ).decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                continue

            if not decoded_content.strip():
                continue

            documents.append(
                {
                    "path": file_path,
                    "content": decoded_content,
                }
            )

    return documents