from pathlib import PurePath


def safe_attachment_filename(filename: str | None) -> str:
    candidate = PurePath(filename or "attachment").name.strip()
    return candidate or "attachment"
