"""
Dictionary lookup using SQLite database (words.db).

Queries lemmas table for word definitions/meanings.
The meaning field from DICTLINE.GEN contains Whitaker's annotation codes
(e.g. "X X X A O" for age/area/frequency) which are stripped for display.
"""
import os, re, sqlite3
from typing import List, Optional

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "words.db")

LATIN_MAP = {
    'ā':'a','ă':'a','ǎ':'a','â':'a','à':'a',
    'ē':'e','ĕ':'e','ě':'e','ê':'e','è':'e',
    'ī':'i','ĭ':'i','î':'i','ì':'i',
    'ō':'o','ŏ':'o','ǒ':'o','ô':'o','ò':'o',
    'ū':'u','ŭ':'u','ǔ':'u','û':'u','ù':'u',
    'ȳ':'y','ў':'y',
    'Ā':'A','Ă':'A','Â':'A','À':'A',
    'Ē':'E','Ĕ':'E','Ê':'E','È':'E',
    'Ī':'I','Ĭ':'I','Ì':'I',
    'Ō':'O','Ŏ':'O','Ô':'O','Ò':'O',
    'Ū':'U','Ŭ':'U','Û':'U','Ù':'U',
}

# Pattern to strip Whitaker's annotation codes
# Example: "X X X C G" (age area frequency source)
_ANNOT_RE = re.compile(
    r'\b[ABCDFX]\s[ABCDFX]\s[ABCDFX]\s[ABCDEFGHIJKLMNOPQRSTUVWXYZ]\s[A-Z]\b'
)


def _clean_meaning(raw: str) -> str:
    """Strip Whitaker's annotation codes like 'X X X C G' from meaning."""
    if not raw:
        return ""
    # Remove the 5-char annotation code pattern
    cleaned = _ANNOT_RE.sub('', raw).strip()
    # Also remove leading/trailing junk like "(abb. ...);"
    # but keep everything after the first meaningful definition
    # Remove patterns like "; [Absolvo, Antiquo => free, reject];"
    cleaned = re.sub(r';\s*\[.*?\]\s*', '; ', cleaned)
    # Strip leading/trailing semicolons and whitespace
    cleaned = cleaned.strip('; ')
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def norm(s: str) -> str:
    """Strip Latin diacritics."""
    return ''.join(LATIN_MAP.get(c, c) for c in s)


class Dictionary:
    def __init__(self, db: str = DB):
        self.db = db
        self.conn: Optional[sqlite3.Connection] = None

    def _ready(self):
        if self.conn is not None:
            return
        if not os.path.exists(self.db):
            raise FileNotFoundError(f"DB missing: {self.db}")
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row

    def lookup(self, key: str) -> List[dict]:
        """Look up a lemma key; return [{key, part_of_speech, meaning}]."""
        self._ready()
        k = norm(key.strip().lower())
        c = self.conn.cursor()
        c.execute("""
            SELECT lemma, pos, meaning
            FROM lemmas
            WHERE lemma = ?
            ORDER BY pos
        """, (k,))
        out = []
        for r in c.fetchall():
            out.append({
                "key": r["lemma"],
                "part_of_speech": r["pos"],
                "meaning": _clean_meaning(r["meaning"] or ""),
            })
        return out

    def reverse_lookup(self, english_word: str, max_results: int = 30) -> List[dict]:
        """English → Latin reverse lookup: search lemmas by English meaning.

        Returns [{key, part_of_speech, meaning}] where meaning contains the
        English search term.
        """
        self._ready()
        w = english_word.strip().lower()
        if not w:
            return []
        c = self.conn.cursor()
        c.execute("""
            SELECT lemma, pos, meaning
            FROM lemmas
            WHERE meaning LIKE ?
            ORDER BY lemma
            LIMIT ?
        """, (f'%{w}%', max_results))
        out = []
        seen = set()
        for r in c.fetchall():
            lemma = r["lemma"]
            if lemma in seen:
                continue
            seen.add(lemma)
            out.append({
                "key": lemma,
                "part_of_speech": r["pos"],
                "meaning": _clean_meaning(r["meaning"] or ""),
            })
        return out


def get_dictionary() -> Dictionary:
    return Dictionary()

def lookup(key: str) -> List[dict]:
    return get_dictionary().lookup(key)

def reverse_lookup(word: str, max_results: int = 30) -> List[dict]:
    return get_dictionary().reverse_lookup(word, max_results)
