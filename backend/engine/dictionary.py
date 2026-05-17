"""
Dictionary lookup using grep on pre-built text index files.

Architecture:
  - lemmas.txt: lemma|pos|meaning  (for lookup)
  - meaning_index.txt: word|lemma|pos|meaning  (for reverse_lookup)
  - grep is used for all queries — sub-millisecond on these file sizes

To rebuild indexes (after updating words.db):
    python -m engine.build_dict
"""
import os
import re
import subprocess
import logging
from typing import List

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(__file__))
LEMMAS_FILE = os.path.join(BASE, "cache", "lemmas.txt")
MEANING_INDEX_FILE = os.path.join(BASE, "cache", "meaning_index.txt")


def _grep_first_col(pattern: str, filepath: str, max_results: int = 30) -> List[tuple[str, str, str]]:
    """Run grep for exact match on first column (pipe-separated).

    Returns [(lemma, pos, meaning), ...].
    """
    if not os.path.exists(filepath):
        logger.error("Index file not found: %s", filepath)
        return []
    # Escape grep special chars
    safe = pattern.replace("'", "'\\''").replace("|", "\\|").replace(".", "\\.").replace("*", "\\*")
    try:
        result = subprocess.run(
            ["grep", "-m", str(max_results), f"^{safe}|", filepath],
            capture_output=True, text=True, timeout=5
        )
    except subprocess.TimeoutExpired:
        logger.error("grep timeout for pattern: %s", pattern)
        return []

    out = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) >= 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def _grep_anywhere(pattern: str, filepath: str, max_results: int = 30) -> List[tuple[str, str, str]]:
    """Run grep for exact match on first column (pipe-separated).

    For meaning_index.txt, first column is the English word.
    Returns deduplicated [(lemma, pos, meaning), ...].
    """
    if not os.path.exists(filepath):
        logger.error("Index file not found: %s", filepath)
        return []
    safe = pattern.replace("'", "'\\''").replace("|", "\\|").replace(".", "\\.").replace("*", "\\*")
    try:
        result = subprocess.run(
            ["grep", "-m", str(max_results), f"^{safe}|", filepath],
            capture_output=True, text=True, timeout=5
        )
    except subprocess.TimeoutExpired:
        logger.error("grep timeout for pattern: %s", pattern)
        return []

    seen = set()
    out = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) >= 4:
            lemma = parts[1]
            if lemma in seen:
                continue
            seen.add(lemma)
            out.append((parts[1], parts[2], parts[3]))
            if len(out) >= max_results:
                break
    return out


def lookup(key: str) -> List[dict]:
    """Look up a lemma key; return [{key, part_of_speech, meaning}]."""
    k = key.strip().lower()
    if not k:
        return []
    rows = _grep_first_col(k, LEMMAS_FILE)
    return [
        {"key": r[0], "part_of_speech": r[1], "meaning": r[2]}
        for r in rows
    ]


def reverse_lookup(english_word: str, max_results: int = 30) -> List[dict]:
    """English → Latin reverse lookup via grep on meaning_index.txt.

    Returns [{key, part_of_speech, meaning}] where meaning contains the
    English search term.
    """
    w = english_word.strip().lower()
    if not w:
        return []
    rows = _grep_anywhere(w, MEANING_INDEX_FILE, max_results)
    return [
        {"key": r[0], "part_of_speech": r[1], "meaning": r[2]}
        for r in rows
    ]


def get_dictionary():
    return None
