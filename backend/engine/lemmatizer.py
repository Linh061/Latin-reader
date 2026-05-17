"""
Fast Latin lemmatizer using sqlite3 CLI (thread-safe).

Supports exact match + fuzzy search (Levenshtein distance + Latin phonetic normalization).
Uses sqlite3 CLI subprocess instead of Python sqlite3 bindings to avoid
thread-safety issues with Flask's debug mode.
"""
import os
import subprocess
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

_PHONETIC_MAP = str.maketrans({
    'æ': 'e',
    'œ': 'e',
    'Æ': 'E',
    'Œ': 'E',
})


def _phonetic_norm(s: str) -> str:
    """Normalize Latin spelling variants for fuzzy matching."""
    s = s.translate(_PHONETIC_MAP)
    s = s.replace('ph', 'f').replace('Ph', 'F').replace('PH', 'F')
    s = s.replace('th', 't').replace('Th', 'T').replace('TH', 'T')
    s = s.replace('ch', 'c').replace('Ch', 'C').replace('CH', 'C')
    s = s.replace('y', 'i').replace('Y', 'I')
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


# ── SQLite CLI helper ──────────────────────────────────────────────────────

def _sql(sql: str) -> str:
    """Run SQL via sqlite3 CLI (thread-safe)."""
    try:
        result = subprocess.run(
            ["sqlite3", DB, sql],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except Exception:
        return ""


# ── Lemmatizer ─────────────────────────────────────────────────────────────

class Lemmatizer:
    def __init__(self):
        self._all_forms: Optional[List[str]] = None
        self._all_forms_phon: Optional[List[str]] = None

    def _load_forms(self):
        """Load all forms into memory for fuzzy search."""
        if self._all_forms is not None:
            return
        out = _sql("SELECT DISTINCT form FROM forms;")
        self._all_forms = [line for line in out.splitlines() if line.strip()]
        self._all_forms_phon = [_phonetic_norm(f) for f in self._all_forms]

    def lemmatize(self, word: str) -> List[dict]:
        """Exact match: return list of {lemma, lemma_form, part_of_speech, meaning, translation, morphology}."""
        w = norm(word.lower().strip())
        safe = w.replace("'", "''")
        out = _sql(f"""
            SELECT l.lemma, l.pos, l.meaning, f.morphology
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form = '{safe}'
            LIMIT 20;
        """)
        seen = set()
        results = []
        for line in out.splitlines():
            parts = line.split("|")
            if len(parts) < 4:
                continue
            lemma = parts[0]
            if lemma in seen:
                continue
            seen.add(lemma)
            results.append({
                "lemma": lemma,
                "lemma_form": lemma,
                "part_of_speech": parts[1],
                "meaning": parts[2] or "",
                "translation": parts[2] or "",
                "morphology": parts[3] or "",
            })
        return results

    def fuzzy_search(self, word: str, max_distance: int = 2, max_results: int = 10) -> List[dict]:
        """Fuzzy search: find forms within Levenshtein distance, using phonetic normalization."""
        self._load_forms()
        w = norm(word.lower().strip())
        w_phon = _phonetic_norm(w)

        candidates = []
        for i, f in enumerate(self._all_forms):
            d = _levenshtein(w_phon, self._all_forms_phon[i])
            if d <= max_distance:
                candidates.append((d, f))

        candidates.sort(key=lambda x: (x[0], x[1]))
        candidates = candidates[:max_results]

        if not candidates:
            return []

        out = []
        seen_lemmas = set()
        for dist, form in candidates:
            safe = form.replace("'", "''")
            rows = _sql(f"""
                SELECT l.lemma, l.pos, l.meaning
                FROM forms f
                JOIN lemmas l ON f.lemma_id = l.id
                WHERE f.form = '{safe}'
                LIMIT 5;
            """)
            for line in rows.splitlines():
                parts = line.split("|")
                if len(parts) < 3:
                    continue
                lemma = parts[0]
                if lemma in seen_lemmas:
                    continue
                seen_lemmas.add(lemma)
                out.append({
                    "form": form,
                    "lemma": lemma,
                    "part_of_speech": parts[1],
                    "meaning": parts[2] or "",
                    "distance": dist,
                })
                if len(out) >= max_results:
                    break
            if len(out) >= max_results:
                break
        return out

    def prefix_search(self, word: str, max_results: int = 10) -> List[dict]:
        """Prefix match: find forms starting with the given word."""
        w = norm(word.lower().strip())
        safe = w.replace("'", "''")
        out = _sql(f"""
            SELECT DISTINCT f.form, l.lemma, l.pos, l.meaning
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form LIKE '{safe}%'
            LIMIT {max_results};
        """)
        seen = set()
        results = []
        for line in out.splitlines():
            parts = line.split("|")
            if len(parts) < 4:
                continue
            lemma = parts[1]
            if lemma in seen:
                continue
            seen.add(lemma)
            results.append({
                "form": parts[0],
                "lemma": lemma,
                "part_of_speech": parts[2],
                "meaning": parts[3] or "",
            })
        return results


_default: Optional[Lemmatizer] = None


def get_lemmatizer() -> Lemmatizer:
    global _default
    if _default is None:
        _default = Lemmatizer()
    return _default


def lemmatize(word: str, lang: str = "en") -> List[dict]:
    return get_lemmatizer().lemmatize(word)


def fuzzy_search(word: str, max_distance: int = 2, max_results: int = 10) -> List[dict]:
    return get_lemmatizer().fuzzy_search(word, max_distance, max_results)


def prefix_search(word: str, max_results: int = 10) -> List[dict]:
    return get_lemmatizer().prefix_search(word, max_results)
