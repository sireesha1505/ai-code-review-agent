import json
from urllib.parse import parse_qs, unquote_plus


def parse_request_body(body, content_type=None):
    # request.body() returns bytes; handle bytes and empty bodies safely
    if not body:
        return {}

    # If body is bytes, decode to string
    if isinstance(body, (bytes, bytearray)):
        try:
            text = body.decode("utf-8")
        except Exception:
            text = body.decode("utf-8", errors="ignore")
    else:
        text = str(body)

    if not text.strip():
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some webhooks send form-encoded payloads like: payload=%7B...%7D
        # Older webhook senders sometimes POST form-encoded bodies even
        # when `Content-Type` is not set correctly. For debugging and
        # compatibility, always attempt to parse a `payload` field from
        # form-encoded bodies when JSON decoding fails.
        try:
            qs = parse_qs(text, keep_blank_values=True)
            if "payload" in qs and qs["payload"]:
                payload_text = qs["payload"][0]
                # parse_qs already percent-decodes, but be defensive
                try:
                    parsed = json.loads(payload_text)
                    return parsed
                except json.JSONDecodeError:
                    try:
                        parsed = json.loads(unquote_plus(payload_text))
                        return parsed
                    except json.JSONDecodeError:
                        return {}
        except Exception:
            return {}
        return {}


def parse_request_event(event):
    if event == "pull_request":
        return "pull_request"
    elif event == "push":
        return "push"
    else:
        return "unknown_event"


def extract_event_action(parsed_body):
    return parsed_body.get("action")


def extract_pr_metadata(parsed_body):
    pull_request = parsed_body.get("pull_request", {})
    repository = parsed_body.get("repository", {})

    return {
        "number": pull_request.get("number"),
        "repository": repository.get("full_name"),
        "commit_sha": pull_request.get("head", {}).get("sha"),
        "title": pull_request.get("title"),
        "state": pull_request.get("state"),
        "url": pull_request.get("html_url"),
        "user": pull_request.get("user", {}).get("login")
    }

def extract_file_changes(files):
    extracted_file_changes = []

    for  file  in files:
        extracted_file_changes.append({
            "filename": file.get("filename"),
            "status": file.get("status"),
            "additions": file.get("additions"),
            "deletions": file.get("deletions"),
            "patch": file.get("patch")
        })

    return extracted_file_changes