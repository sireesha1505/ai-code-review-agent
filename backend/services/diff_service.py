
def get_diff_position(
    patch: str,
    target_line: int
) -> int | None:
    """
    Convert a file line number into GitHub's diff position.

    GitHub's `position` is the number of lines after the
    `@@ ... @@` hunk header, counting both added, deleted,
    and context lines.

    Returns:
        int:
            GitHub diff position.

        None:
            If the target line is not present in the patch.
    """

    if not patch or target_line <= 0:
        return None

    current_file_line = None
    position = 0

    for diff_line in patch.splitlines():
        if diff_line.startswith("@@"):

            # Example:
            # @@ -10,7 +10,8 @@
            #
            # We only care about the new-file starting line.
            parts = diff_line.split()

            if len(parts) < 3:
                return None

            new_file_range = parts[2]

            # Example:
            # +10,8
            new_file_start = new_file_range.split(",")[0]

            current_file_line = int(
                new_file_start.replace("+", "")
            )

            continue
        if current_file_line is None:
            continue

        if diff_line.startswith("\\"):
            continue

        position += 1

        if diff_line.startswith("+"):

            if current_file_line == target_line:
                return position

            current_file_line += 1

        elif diff_line.startswith("-"):
            continue
        else:

            if current_file_line == target_line:
                return position

            current_file_line += 1

    return None
