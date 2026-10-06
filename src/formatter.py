"""
Message formatting and HTML escaping utilities for Telegram.
"""
import html
from typing import Optional
from max_library.models import Attachment, Message


def escape_html(text: Optional[str]) -> str:
    """Escapes HTML special characters in plain text."""
    if not text:
        return ""
    return html.escape(str(text))


def format_author_header(author_name: str, forward_author_name: Optional[str] = None) -> str:
    """Formats HTML author header with optional forward information."""
    safe_author = escape_html(author_name or "Unknown")
    if forward_author_name:
        safe_fwd = escape_html(forward_author_name)
        return f"<b>{safe_author}</b> <i>(Переслано от: {safe_fwd})</i>"
    return f"<b>{safe_author}</b>"


def format_message_text(
    author_name: str,
    text: Optional[str],
    forward_author_name: Optional[str] = None,
    unhandled_files: Optional[list[str]] = None,
) -> str:
    """Formats complete HTML message text including author, body and unhandled files."""
    header = format_author_header(author_name, forward_author_name)
    parts = [header]

    if text and text.strip():
        parts.append(escape_html(text.strip()))

    if unhandled_files:
        files_str = ", ".join(f"<code>{escape_html(f)}</code>" for f in unhandled_files)
        parts.append(f"📁 <b>Необработанные файлы:</b> {files_str}")

    return "\n\n".join(parts)


def truncate_caption(caption: str, max_length: int = 1024) -> str:
    """Safely truncates caption to Telegram limit."""
    if len(caption) <= max_length:
        return caption
    ellipsis = "..."
    return caption[: max_length - len(ellipsis)] + ellipsis


def truncate_message(text: str, max_length: int = 4096) -> str:
    """Safely truncates message text to Telegram message limit."""
    if len(text) <= max_length:
        return text
    ellipsis = "..."
    return text[: max_length - len(ellipsis)] + ellipsis


def split_into_media_batches(items: list, batch_size: int = 10) -> list[list]:
    """Splits a list of items into chunks of at most batch_size."""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
