import datetime
import json
import pathlib

from services.code_review_service import (
    filter_changed_files,
    prepare_review_input,
)

from services.github_review_service import (
    post_pull_request_comment,
    post_review_comment,
    list_pull_request_comments,
    list_review_comments,
)

from services.diff_service import (
    get_diff_position,
)

from common.logger import logger
from graph.review_graph import review_graph


async def post_fallback_comment(
    repo_name,
    pull_number,
    file_path,
    line,
    body,
    existing_pr_comments,
):
    """
    Post a PR-level fallback comment while avoiding duplicates.
    """

    fallback_body = (
        f"AI review finding for "
        f"{file_path}:{line}\n\n"
        f"{body}"
    )

    duplicate = any(
        (
            comment.get("body") or ""
        ).strip()
        == fallback_body.strip()
        for comment in existing_pr_comments
    )

    if duplicate:
        logger.info(
            "Skipping duplicate fallback comment for %s:%s",
            file_path,
            line,
        )

        return False

    try:

        await post_pull_request_comment(
            repo_name,
            pull_number,
            fallback_body,
        )

        existing_pr_comments.append(
            {
                "body": fallback_body
            }
        )

        logger.info(
            "Fallback PR comment posted for %s:%s",
            file_path,
            line,
        )

        return True

    except Exception as error:

        logger.error(
            "Fallback PR comment failed | file=%s | line=%s | error=%s",
            file_path,
            line,
            error,
        )

        return False


async def process_code_review(
    repo_name,
    pull_number,
    commit_sha,
    changed_files_info
):
    logger.info("Repository: %s", repo_name)
    logger.info("PR: %s", pull_number)
    logger.info("Commit: %s", commit_sha)

    try:

        # =========================================================
        # Review start marker
        # =========================================================

        try:

            reviews_dir = (
                pathlib.Path(__file__).resolve().parents[1]
                / "reviews"
            )

            reviews_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            start_path = (
                reviews_dir
                / (
                    f"review_"
                    f"{repo_name.replace('/', '_')}_"
                    f"{pull_number}_start.json"
                )
            )

            start_payload = {
                "repo": repo_name,
                "pull": pull_number,
                "status": "started",
                "ts": datetime.datetime.utcnow().isoformat(),
            }

            start_path.write_text(
                json.dumps(start_payload)
            )

        except Exception as marker_error:

            logger.error("Failed to write review start marker: %s", marker_error)

        # =========================================================
        # Prepare changed files
        # =========================================================

        filtered_files = filter_changed_files(
            changed_files_info
        )

        reviewed_input = prepare_review_input(
            filtered_files
        )

        # filename -> patch
        file_patches = {
            file.get("filename"): file.get("patch")
            for file in filtered_files
        }

        # =========================================================
        # LangGraph state
        # =========================================================

        initial_state = {
            "files": reviewed_input,
            "repository": repo_name,
            "commit_sha": commit_sha,
            "retrieved_contexts": {},

            "bug_review": None,
            "security_review": None,
            "performance_review": None,
            "maintainability_review": None,
            "testing_review": None,

            "final_review": None,
        }

        # =========================================================
        # Run review graph
        # =========================================================

        result = await review_graph.ainvoke(
            initial_state
        )

        llm_response = result["final_review"]

        # =========================================================
        # Build summary
        # =========================================================

        if llm_response.issues:

            lines = [
                "## AI Code Review - Findings",
                "",
            ]

            for i, issue in enumerate(
                llm_response.issues,
                start=1
            ):

                lines.append(
                    f"### {i}. {issue.file}"
                )

                if issue.line:
                    lines.append(
                        f"- **Line:** {issue.line}"
                    )

                lines.append(
                    f"- **Severity:** "
                    f"{issue.severity.value}"
                )

                lines.append(
                    f"- **Category:** "
                    f"{issue.category.value}"
                )

                lines.append(
                    f"- **Explanation:** "
                    f"{issue.explanation}"
                )

                if issue.suggested_fix:

                    lines.append(
                        f"- **Suggested fix:** "
                        f"{issue.suggested_fix}"
                    )

                lines.append("")

            comment_body = "\n".join(
                lines
            )

        else:

            comment_body = (
                "## AI Code Review\n\n"
                + (
                    llm_response.summary
                    or "No details provided."
                )
            )

        # =========================================================
        # Post GitHub comments
        # =========================================================

        try:

            issues = llm_response.issues

            # -----------------------------------------------------
            # Existing PR comments
            # -----------------------------------------------------

            try:

                existing_pr_comments = (
                    await list_pull_request_comments(
                        repo_name,
                        pull_number
                    )
                )

            except Exception as error:

                logger.error("Failed to fetch PR comments: %s", error)

                existing_pr_comments = []

            # -----------------------------------------------------
            # Existing inline comments
            # -----------------------------------------------------

            try:

                existing_review_comments = (
                    await list_review_comments(
                        repo_name,
                        pull_number
                    )
                )

            except Exception as error:

                logger.error("Failed to fetch review comments: %s", error)

                existing_review_comments = []

            # =====================================================
            # Findings exist
            # =====================================================

            if issues:

                for issue in issues:

                    file_path = issue.file
                    line = issue.line

                    body = (
                        f"**Severity:** "
                        f"{issue.severity.value}\n\n"

                        f"**Category:** "
                        f"{issue.category.value}\n\n"

                        f"{issue.explanation}"
                    )

                    # =================================================
                    # Finding has file + line
                    # =================================================

                    if file_path and line:

                        # -------------------------------------------------
                        # Get patch
                        # -------------------------------------------------

                        patch = file_patches.get(
                            file_path
                        )

                        if not patch:

                            logger.warning("No patch found for %s", file_path)

                            await post_fallback_comment(
                                repo_name,
                                pull_number,
                                file_path,
                                line,
                                body,
                                existing_pr_comments,
                            )

                            continue

                        # -------------------------------------------------
                        # Convert file line -> diff position
                        # -------------------------------------------------

                        position = get_diff_position(
                            patch,
                            line
                        )

                        logger.info(
                            "Diff position calculated | file=%s | line=%s | position=%s",
                            file_path,
                            line,
                            position,
                        )

                        # -------------------------------------------------
                        # AI line isn't present in diff
                        # -------------------------------------------------

                        if position is None:

                            logger.warning(
                                "Line %s for %s is not present in the diff.",
                                line,
                                file_path,
                            )

                            await post_fallback_comment(
                                repo_name,
                                pull_number,
                                file_path,
                                line,
                                body,
                                existing_pr_comments,
                            )

                            continue

                        # -------------------------------------------------
                        # Duplicate inline comment
                        # -------------------------------------------------

                        duplicate = any(
                            comment.get("path")
                            == file_path

                            and comment.get("line")
                            == line

                            and (
                                comment.get("body")
                                or ""
                            ).strip()
                            == body.strip()

                            for comment
                            in existing_review_comments
                        )

                        if duplicate:

                            logger.info(
                                "Skipping duplicate inline comment for %s:%s",
                                file_path,
                                line,
                            )

                            continue

                        # -------------------------------------------------
                        # Post inline comment
                        # -------------------------------------------------

                        try:

                            await post_review_comment(
                                repo_name,
                                pull_number,
                                commit_sha,
                                file_path,
                                position,
                                body,
                            )

                            existing_review_comments.append(
                                {
                                    "path": file_path,
                                    "line": line,
                                    "body": body,
                                }
                            )

                            logger.info(
                                "Inline comment posted successfully | file=%s | line=%s | position=%s",
                                file_path,
                                line,
                                position,
                            )

                        except Exception as error:

                            logger.error(
                                "Inline comment failed | file=%s | line=%s | position=%s | error=%s",
                                file_path,
                                line,
                                position,
                                error,
                            )

                            await post_fallback_comment(
                                repo_name,
                                pull_number,
                                file_path,
                                line,
                                body,
                                existing_pr_comments,
                            )

                    # =================================================
                    # Finding without file/line
                    # =================================================

                    else:

                        duplicate = any(
                            (
                                comment.get("body")
                                or ""
                            ).strip()
                            == body.strip()
                            for comment
                            in existing_pr_comments
                        )

                        if duplicate:

                            logger.info("Skipping duplicate PR comment")

                            continue

                        try:

                            await post_pull_request_comment(
                                repo_name,
                                pull_number,
                                body,
                            )

                            existing_pr_comments.append(
                                {
                                    "body": body
                                }
                            )

                            logger.info("PR-level comment posted successfully")

                        except Exception as error:

                            logger.error("Failed to post PR-level comment: %s", error)

            # =====================================================
            # No issues
            # =====================================================

            else:

                body = comment_body

                if body and body.strip():

                    duplicate = any(
                        (
                            comment.get("body")
                            or ""
                        ).strip()
                        == body.strip()
                        for comment
                        in existing_pr_comments
                    )

                    if duplicate:

                        logger.info("Skipping duplicate summary comment")

                    else:

                        try:

                            await post_pull_request_comment(
                                repo_name,
                                pull_number,
                                body,
                            )

                            logger.info("Summary comment posted successfully")

                        except Exception as error:

                            logger.error("Failed to post summary comment: %s", error)

        except Exception as error:

            logger.error("Failed to post PR comments: %s", error)

        return llm_response

    except Exception as error:

        logger.error("===== CODE REVIEW FAILED =====")
        logger.error(str(error))

        raise

    finally:

        # =========================================================
        # Review completion marker
        # =========================================================

        try:

            reviews_dir = (
                pathlib.Path(__file__).resolve().parents[1]
                / "reviews"
            )

            reviews_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            done_path = (
                reviews_dir
                / (
                    f"review_"
                    f"{repo_name.replace('/', '_')}_"
                    f"{pull_number}_done.json"
                )
            )

            done_payload = {
                "repo": repo_name,
                "pull": pull_number,
                "status": "finished",
                "ts": datetime.datetime.utcnow().isoformat(),
            }

            done_path.write_text(
                json.dumps(done_payload)
            )

        except Exception as marker_error:

            logger.error("Failed to write review done marker: %s", marker_error)
