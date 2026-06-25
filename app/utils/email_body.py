from html import escape


def email_body_document_content(email_body: str) -> bytes:
    if _looks_like_html(email_body):
        return email_body.encode("utf-8")

    html = (
        "<!doctype html>\n"
        "<html>\n"
        "<head><meta charset=\"utf-8\"><title>Email Body</title></head>\n"
        f"<body><pre>{escape(email_body)}</pre></body>\n"
        "</html>\n"
    )
    return html.encode("utf-8")


def _looks_like_html(value: str) -> bool:
    lowered = value.lower()
    return any(tag in lowered for tag in ("<html", "<body", "<table", "<div", "<p", "<br"))
