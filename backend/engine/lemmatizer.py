"""
Fast Latin lemmatizer using pre-built SQLite database (words.db).

Built by scripts/build_db.py from whitakers-words/DICTLINE.GEN.
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


class Lemmatizer:
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

    def lemmatize(self, word: str) -> List[dict]:
        """Return list of {lemma, lemma_form, part_of_speech, meaning, translation, morphology}."""
        self._ready()
        w = norm(word.lower().strip())
        c = self.conn.cursor()
        c.execute("""
            SELECT l.lemma, l.pos, l.meaning, f.morphology
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form = ?
            LIMIT 20
        """, (w,))
        seen = set()
        out = []
        for r in c.fetchall():
            lemma = r["lemma"]
            if lemma in seen:
                continue
            seen.add(lemma)
            out.append({
                "lemma": lemma,
                "lemma_form": lemma,
                "part_of_speech": r["pos"],
                "meaning": r["meaning"] or "",
                "translation": r["meaning"] or "",
                "morphology": r["morphology"] or "",
            })
        return out


_default: Optional[Lemmatizer] = None

def get_lemmatizer() -> Lemmatizer:
    global _default
    if _default is None:
        _default = Lemmatizer()
    return _default

def lemmatize(word: str, lang: str = "en") -> List[dict]:
    """Lemmatize a Latin word. lang is accepted for API compatibility but
    Whitaker's Words only provides English translations."""
    return get_lemmatizer().lemmatize(word)
