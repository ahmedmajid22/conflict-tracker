import pytest
from pipeline.processors.cleaner import clean_text, clean, clean_record


def test_strip_html_tags():
    assert clean_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_decode_html_entities():
    assert clean_text("Iran &amp; USA") == "Iran & USA"


def test_normalize_whitespace():
    assert clean_text("too   many    spaces") == "too many spaces"


def test_clean_record_removes_html():
    record = {
        "title":       "<h1>Breaking: Strike</h1>",
        "description": "<p>An <b>airstrike</b> was launched.</p>",
        "raw_hash":    "abc123",
    }
    result = clean_record(record)
    assert result["title"] == "Breaking: Strike"
    assert "airstrike" in result["description"]
    assert "<" not in result["description"]


def test_clean_drops_empty_titles():
    records = [
        {"title": "", "description": "something", "raw_hash": "x1"},
        {"title": "Real title", "description": "desc", "raw_hash": "x2"},
    ]
    result = clean(records)
    assert len(result) == 1
    assert result[0]["title"] == "Real title"