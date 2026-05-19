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
    """Run grep for match anywhere in the line (case-insensitive).

    For meaning_index.txt, searches the entire line (English word + meaning text).
    Returns deduplicated [(lemma, pos, meaning), ...].
    """
    if not os.path.exists(filepath):
        logger.error("Index file not found: %s", filepath)
        return []
    safe = pattern.replace("'", "'\\''").replace("|", "\\|").replace(".", "\\.").replace("*", "\\*")
    try:
        result = subprocess.run(
            ["grep", "-i", "-m", str(max_results * 3), f"{safe}", filepath],
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
    English search term. Tries to return real inflected forms from the
    forms table instead of lemma stems (e.g. "chemia" instead of "chemi").
    """
    w = english_word.strip().lower()
    if not w:
        return []
    rows = _grep_anywhere(w, MEANING_INDEX_FILE, max_results)
    results = []
    for r in rows:
        lemma = r[0]
        # Try to find a real inflected form from forms table
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "words.db")
            conn = sqlite3.connect(db_path)
            cur = conn.execute("""
                SELECT f.form FROM forms f
                JOIN lemmas l ON f.lemma_id = l.id
                WHERE l.lemma = ?
                LIMIT 1;
            """, (lemma,))
            form_row = cur.fetchone()
            conn.close()
            display_key = form_row[0] if form_row else lemma
        except Exception:
            display_key = lemma
        results.append({
            "key": display_key,
            "part_of_speech": r[1],
            "meaning": r[2],
        })
    return results


def get_dictionary():
    return None
