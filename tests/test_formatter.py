"""
Tests for HTML escaping and message formatting.
"""
from src.formatter import (
    escape_html,
    format_author_header,
    format_message_text,
    truncate_caption,
    truncate_message,
)


def test_escape_html():
    raw = '<script>alert("test & demo")</script>'
    escaped = escape_html(raw)
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped


def test_format_author_header_simple():
    header = format_author_header("Иван <Admin>")
    assert header == "<b>Иван &lt;Admin&gt;</b>"


def test_format_author_header_with_forward():
    header = format_author_header("Иван", forward_author_name="Пётр & Co")
    assert header == "<b>Иван</b> <i>(Переслано от: Пётр &amp; Co)</i>"


def test_format_message_text_full():
    text = format_message_text(
        author_name="Алексей",
        text="Привет, <b>мир</b>!",
        forward_author_name=None,
        unhandled_files=["document.pdf", "archive.zip"],
    )
    assert "<b>Алексей</b>" in text
    assert "&lt;b&gt;мир&lt;/b&gt;!" in text
    assert "📁 <b>Необработанные файлы:</b>" in text
    assert "<code>document.pdf</code>" in text
    assert "<code>archive.zip</code>" in text


def test_truncate_helpers():
    long_str = "a" * 2000
    caption = truncate_caption(long_str, max_length=1024)
    assert len(caption) == 1024
    assert caption.endswith("...")

    long_msg = "b" * 5000
    msg = truncate_message(long_msg, max_length=4096)
    assert len(msg) == 4096
    assert msg.endswith("...")
