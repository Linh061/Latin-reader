"""
Dictionary lookup using SQLite database (words.db).

Queries lemmas table for word definitions/meanings.
"""
import os, sqlite3
from typing import Optional, List

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
                "meaning": r["meaning"] or "",
            })
        return out


_default: Optional[Dictionary] = None

def get_dictionary() -> Dictionary:
    global _default
    if _default is None:
        _default = Dictionary()
    return _default

def lookup(key: str) -> List[dict]:
    return get_dictionary().lookup(key)
