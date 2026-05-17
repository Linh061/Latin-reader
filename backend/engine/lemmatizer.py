"""
Fast Latin lemmatizer using pre-built SQLite database (words.db).

Supports exact match + fuzzy search (Levenshtein distance + Latin phonetic normalization).
"""
import os
import sqlite3
from typing import Optional, List

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "words.db")

# ── Diacritic normalization ────────────────────────────────────────────────

LATIN_MAP = {
    'ā': 'a', 'ă': 'a', 'ǎ': 'a', 'â': 'a', 'à': 'a',
    'ē': 'e', 'ĕ': 'e', 'ě': 'e', 'ê': 'e', 'è': 'e',
    'ī': 'i', 'ĭ': 'i', 'î': 'i', 'ì': 'i',
    'ō': 'o', 'ŏ': 'o', 'ǒ': 'o', 'ô': 'o', 'ò': 'o',
    'ū': 'u', 'ŭ': 'u', 'ǔ': 'u', 'û': 'u', 'ù': 'u',
    'ȳ': 'y', 'ў': 'y',
    'Ā': 'A', 'Ă': 'A', 'Â': 'A', 'À': 'A',
    'Ē': 'E', 'Ĕ': 'E', 'Ê': 'E', 'È': 'E',
    'Ī': 'I', 'Ĭ': 'I', 'Ì': 'I',
    'Ō': 'O', 'Ŏ': 'O', 'Ô': 'O', 'Ò': 'O',
    'Ū': 'U', 'Ŭ': 'U', 'Û': 'U', 'Ù': 'U',
}


def norm(s: str) -> str:
    """Strip Latin diacritics."""
    return ''.join(LATIN_MAP.get(c, c) for c in s)


# ── Latin phonetic normalization ───────────────────────────────────────────
# Handles common orthographic variants in Latin

_PHONETIC_MAP = str.maketrans({
    'æ': 'e',
    'œ': 'e',
    'Æ': 'E',
    'Œ': 'E',
})


def _phonetic_norm(s: str) -> str:
    """Normalize Latin spelling variants for fuzzy matching.

    ae → e, oe → e, ph → f, th → t, ch → c, y → i, ti+V → ci+V
    """
    s = s.translate(_PHONETIC_MAP)
    s = s.replace('ph', 'f').replace('Ph', 'F').replace('PH', 'F')
    s = s.replace('th', 't').replace('Th', 'T').replace('TH', 'T')
    s = s.replace('ch', 'c').replace('Ch', 'C').replace('CH', 'C')
    s = s.replace('y', 'i').replace('Y', 'I')
    # ti + vowel → ci + vowel (but not after s, x, t)
    import re
    s = re.sub(r'(?<![sSxXtT])ti([aeou])', r'ci\1', s)
    s = re.sub(r'(?<![sSxXtT])t[iI]([aeou])', r'ci\1', s)
    return s


# ── Levenshtein distance ───────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(
                curr[j] + 1,        # deletion
                prev[j + 1] + 1,    # insertion
                prev[j] + cost,     # substitution
            ))
        prev = curr
    return prev[-1]


# ── Lemmatizer ─────────────────────────────────────────────────────────────

class Lemmatizer:
    def __init__(self, db: str = DB):
        self.db = db
        self.conn: Optional[sqlite3.Connection] = None
        # In-memory caches for fuzzy search (loaded lazily)
        self._all_forms: Optional[List[str]] = None
        self._all_forms_phon: Optional[List[str]] = None

    def _ready(self):
        if self.conn is not None:
            return
        if not os.path.exists(self.db):
            raise FileNotFoundError(f"DB missing: {self.db}")
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row

    def _load_forms(self):
        """Load all forms into memory for fuzzy search."""
        if self._all_forms is not None:
            return
        self._ready()
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT form FROM forms")
        self._all_forms = [row[0] for row in c.fetchall()]
        self._all_forms_phon = [_phonetic_norm(f) for f in self._all_forms]

    def lemmatize(self, word: str) -> List[dict]:
        """Exact match: return list of {lemma, lemma_form, part_of_speech, meaning, translation, morphology}."""
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

    def fuzzy_search(self, word: str, max_distance: int = 2, max_results: int = 10) -> List[dict]:
        """Fuzzy search: find forms within Levenshtein distance, using phonetic normalization.

        Returns list of {form, lemma, pos, meaning, distance}.
        """
        self._ready()
        self._load_forms()

        w = norm(word.lower().strip())
        w_phon = _phonetic_norm(w)

        # Collect candidates within distance
        candidates = []
        for i, f in enumerate(self._all_forms):
            # Try phonetic distance first (handles ae/e, ph/f, etc.)
            d = _levenshtein(w_phon, self._all_forms_phon[i])
            if d <= max_distance:
                candidates.append((d, f))

        # Sort by distance, then alphabetically
        candidates.sort(key=lambda x: (x[0], x[1]))
        candidates = candidates[:max_results]

        if not candidates:
            return []

        # Look up lemma info for each candidate form
        c = self.conn.cursor()
        out = []
        seen_lemmas = set()
        for dist, form in candidates:
            c.execute("""
                SELECT l.lemma, l.pos, l.meaning
                FROM forms f
                JOIN lemmas l ON f.lemma_id = l.id
                WHERE f.form = ?
                LIMIT 5
            """, (form,))
            for r in c.fetchall():
                lemma = r["lemma"]
                if lemma in seen_lemmas:
                    continue
                seen_lemmas.add(lemma)
                out.append({
                    "form": form,
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "distance": dist,
                })
                if len(out) >= max_results:
                    break
            if len(out) >= max_results:
                break

        return out

    def prefix_search(self, word: str, max_results: int = 10) -> List[dict]:
        """Prefix match: find forms starting with the given word."""
        self._ready()
        w = norm(word.lower().strip())
        c = self.conn.cursor()
        c.execute("""
            SELECT DISTINCT f.form, l.lemma, l.pos, l.meaning
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form LIKE ?
            LIMIT ?
        """, (w + '%', max_results))
        out = []
        seen = set()
        for r in c.fetchall():
            lemma = r["lemma"]
            if lemma in seen:
                continue
            seen.add(lemma)
            out.append({
                "form": r["form"],
                "lemma": r["lemma"],
                "part_of_speech": r["pos"],
                "meaning": r["meaning"] or "",
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


def fuzzy_search(word: str, max_distance: int = 2, max_results: int = 10) -> List[dict]:
    """Fuzzy search for a Latin word form."""
    return get_lemmatizer().fuzzy_search(word, max_distance, max_results)


def prefix_search(word: str, max_results: int = 10) -> List[dict]:
    """Prefix search for a Latin word form."""
    return get_lemmatizer().prefix_search(word, max_results)
