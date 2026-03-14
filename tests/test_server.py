"""Tests for server-level helper functions and new tools."""

import pytest

from obsidian_tasks_mcp.server import _matches_query, _score_match


# ---------------------------------------------------------------------------
# _score_match
# ---------------------------------------------------------------------------


def test_score_exact_phrase():
    assert _score_match("vercel ai sdk integration", "vercel ai sdk") == 100


def test_score_all_tokens():
    assert _score_match("check vercel and sdk usage", "vercel sdk") == 70


def test_score_partial_tokens():
    score = _score_match("check vercel usage", "vercel sdk")
    assert 0 < score < 70


def test_score_no_match():
    assert _score_match("completely unrelated text", "vercel sdk") == 0


def test_score_case_insensitive():
    assert _score_match("Vercel AI SDK", "vercel ai sdk") == 100


# ---------------------------------------------------------------------------
# _matches_query
# ---------------------------------------------------------------------------


def test_matches_query_description():
    task = {"description": "check out vercel ai sdk", "tags": [], "wikilinks": []}
    matched, score = _matches_query(task, "vercel")
    assert matched is True
    assert score > 0


def test_matches_query_tag():
    task = {"description": "some task", "tags": ["micro-mng-todo"], "wikilinks": []}
    matched, score = _matches_query(task, "micro")
    assert matched is True
    assert score >= 50


def test_matches_query_wikilink():
    task = {"description": "[[cal.com]] check", "tags": [], "wikilinks": ["cal.com"]}
    matched, score = _matches_query(task, "cal.com")
    assert matched is True


def test_matches_query_no_match():
    task = {"description": "unrelated task", "tags": [], "wikilinks": []}
    matched, score = _matches_query(task, "vercel")
    assert matched is False
    assert score == 0
