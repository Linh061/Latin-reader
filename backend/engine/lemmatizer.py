"""
Fast Latin lemmatizer using Python sqlite3 binding (thread-safe with lock).

Supports exact match + fuzzy search (prefix + LIKE + Levenshtein distance).
Uses a threading.Lock to ensure thread safety with Flask debug mode.
"""
import os
import re
import sqlite3
import threading
from typing import Optional, List, Dict



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
    'æ': 'e', 'œ': 'e', 'Æ': 'E', 'Œ': 'E',
})


def _phonetic_norm(s: str) -> str:
    """Normalize Latin spelling variants for fuzzy matching."""
    s = s.translate(_PHONETIC_MAP)
    s = s.replace('ph', 'f').replace('Ph', 'F').replace('PH', 'F')
    s = s.replace('th', 't').replace('Th', 'T').replace('TH', 'T')
    s = s.replace('ch', 'c').replace('Ch', 'C').replace('CH', 'C')
    s = s.replace('y', 'i').replace('Y', 'I')
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


# ── Thread-safe SQLite connection ──────────────────────────────────────────

_db_lock = threading.Lock()
_db_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        if not os.path.exists(DB):
            raise FileNotFoundError(f"Database not found: {DB}")
        _db_conn = sqlite3.connect(DB, check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def _query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Thread-safe query execution."""
    with _db_lock:
        c = _get_conn().cursor()
        c.execute(sql, params)
        return c.fetchall()


# ── Morphology parser (inlined to avoid circular import) ────────────────────

VERB_LABELS = {
    "PRS": "Present",  "IMF": "Imperfect",  "FUT": "Future",
    "PRF": "Perfect",  "PLP": "Pluperfect", "FTP": "Future Perfect",
}
ACT_LABELS = {
    "ACT": "Active",  "PAS": "Passive",
    "INF": "Infinitive", "IMP": "Imperative",
    "SBJ": "Subjunctive",
}
PERSON_LABELS = {
    "1S": "1st Sing",   "2S": "2nd Sing",   "3S": "3rd Sing",
    "1P": "1st Plur",   "2P": "2nd Plur",   "3P": "3rd Plur",
}
CASE_LABELS = {
    "NOM": "Nominative", "GEN": "Genitive",  "DAT": "Dative",
    "ACC": "Accusative", "ABL": "Ablative",  "VOC": "Vocative",
}
GENDER_LABELS = {"M": "Masculine", "F": "Feminine", "N": "Neuter"}


def parse_morph(m: str) -> dict:
    """Parse morphology string into human-readable components."""
    info: Dict[str, str] = {}
    # Verb patterns
    if any(t in m for t in ["PRS","IMF","FUT","PRF","PLP","FTP"]):
        for k in ["PRS","IMF","FUT","PRF","PLP","FTP"]:
            if k in m:
                info["tense"] = VERB_LABELS[k]
                break
        for k in ["ACT","PAS","INF","IMP","SBJ"]:
            if k in m:
                info["voice"] = ACT_LABELS[k]
                break
        for k in ["1S","2S","3S","1P","2P","3P"]:
            if k in m:
                info["person"] = PERSON_LABELS[k]
                break
        if "PPP" in m or "PPA" in m:
            info["form"] = "Participle"
            for g in ["M","F","N"]:
                if g in m:
                    info["gender"] = GENDER_LABELS[g]
                    break
    # Noun/Adjective patterns
    elif any(c in m for c in ["NOM","GEN","DAT","ACC","ABL","VOC"]):
        for c in ["NOM","GEN","DAT","ACC","ABL","VOC"]:
            if c in m:
                info["case"] = CASE_LABELS[c]
                break
        if "P" in m:
            info["number"] = "Plural"
        elif "S" in m:
            info["number"] = "Singular"
        # Gender: match M/F/N only when they appear as standalone gender markers
        # after the case+number part. The morphology codes follow this pattern:
        #   CASE + NUMBER + GENDER  (e.g. NOMSM, NOMPF, GENSN)
        #   CASE + NUMBER          (e.g. NOMS, NOMP, GENS)
        # So gender is present when the code has more than 4 chars (case=3 + number=1 + gender=1)
        # OR when the code explicitly has M/F/N after the case part.
        # Use regex: match M/F/N that appears after the case code (not as part of S/P)
        gender_match = re.search(r'(?:NOM|GEN|DAT|ACC|ABL|VOC)[SP]([MFN])', m)
        if gender_match:
            g = gender_match.group(1)
            info["gender"] = GENDER_LABELS.get(g, g)
    else:
        info["raw"] = m
    return info


# ── Lemmatizer ─────────────────────────────────────────────────────────────

class Lemmatizer:

    def __init__(self):
        self._all_forms: Optional[list[tuple[str, str]]] = None  # (form, phon_norm)

    def _load_forms(self):
        """Load all forms into memory for fuzzy search."""
        if self._all_forms is not None:
            return
        rows = _query("SELECT DISTINCT form FROM forms;")
        self._all_forms = [(r["form"], _phonetic_norm(r["form"])) for r in rows]

    def lemmatize(self, word: str) -> List[dict]:
        """Exact match: return list of {lemma, lemma_form, part_of_speech, meaning, translation, morphology}.

        First tries forms table (inflected forms). If no match found,
        falls back to lemmas table to handle indeclinable words
        (e.g. et, atque, in, ad) that have no inflection rules.
        """
        w = norm(word.lower().strip())
        rows = _query("""
            SELECT l.lemma, l.pos, l.meaning, f.morphology
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form = ?
            LIMIT 20;
        """, (w,))

        # Fallback: indeclinable words not in forms table → look up lemmas directly
        if not rows:
            rows = _query("""
                SELECT lemma, pos, meaning, '' as morphology
                FROM lemmas
                WHERE lemma = ?
                LIMIT 5;
            """, (w,))

        seen = set()
        results = []
        for r in rows:
            lemma = r["lemma"]
            if lemma in seen:
                continue
            seen.add(lemma)
            # Convert morphology code (e.g. "IMF3P") to human-readable text
            morph_raw = r["morphology"] or ""
            morph_info = parse_morph(morph_raw)
            morph_readable = ", ".join(v for v in morph_info.values() if v)
            results.append({
                "lemma": lemma,
                "lemma_form": lemma,
                "part_of_speech": r["pos"],
                "meaning": r["meaning"] or "",
                "translation": r["meaning"] or "",
                "morphology": morph_readable or morph_raw,
            })
        return results


    def fuzzy_search(self, word: str, max_distance: int = 2, max_results: int = 10) -> List[dict]:
        """Fuzzy search: try prefix match first, then LIKE, then Levenshtein."""
        w = norm(word.lower().strip())
        w_phon = _phonetic_norm(w)

        # 1. Prefix match (fastest)
        prefix_rows = _query("""
            SELECT DISTINCT f.form, l.lemma, l.pos, l.meaning
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form LIKE ? || '%'
            LIMIT ?;
        """, (w, max_results))

        if prefix_rows:
            seen = set()
            results = []
            for r in prefix_rows:
                lemma = r["lemma"]
                if lemma in seen:
                    continue
                seen.add(lemma)
                results.append({
                    "form": r["form"],
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "distance": 0,
                    "highlight": _highlight_ranges(r["form"], w),
                })
                if len(results) >= max_results:
                    break
            return results

        # 2. LIKE match (contains)
        like_rows = _query("""
            SELECT DISTINCT f.form, l.lemma, l.pos, l.meaning
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form LIKE '%' || ? || '%'
            LIMIT ?;
        """, (w, max_results))

        if like_rows:
            seen = set()
            results = []
            for r in like_rows:
                lemma = r["lemma"]
                if lemma in seen:
                    continue
                seen.add(lemma)
                results.append({
                    "form": r["form"],
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "distance": 1,
                    "highlight": _highlight_ranges(r["form"], w),
                })
                if len(results) >= max_results:
                    break
            return results

        # 3. Fallback: try lemmas table (for indeclinable words not in forms)
        lemma_rows = _query("""
            SELECT lemma, pos, meaning FROM lemmas
            WHERE lemma LIKE ? || '%'
            LIMIT ?;
        """, (w, max_results))
        if lemma_rows:
            seen = set()
            results = []
            for r in lemma_rows:
                lemma = r["lemma"]
                if lemma in seen:
                    continue
                seen.add(lemma)
                results.append({
                    "form": r["lemma"],
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "distance": 0,
                    "highlight": _highlight_ranges(r["lemma"], w),
                })
                if len(results) >= max_results:
                    break
            return results

        # 4. Levenshtein (slowest, only as last resort)
        self._load_forms()

        candidates = []
        for form, phon in self._all_forms:
            d = _levenshtein(w_phon, phon)
            if d <= max_distance:
                candidates.append((d, form))

        candidates.sort(key=lambda x: (x[0], x[1]))
        candidates = candidates[:max_results]

        if not candidates:
            return []

        seen = set()
        results = []
        for dist, form in candidates:
            rows = _query("""
                SELECT l.lemma, l.pos, l.meaning
                FROM forms f
                JOIN lemmas l ON f.lemma_id = l.id
                WHERE f.form = ?
                LIMIT 5;
            """, (form,))
            for r in rows:
                lemma = r["lemma"]
                if lemma in seen:
                    continue
                seen.add(lemma)
                results.append({
                    "form": form,
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "distance": dist,
                    "highlight": _highlight_ranges(form, w),
                })
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        return results

    def prefix_search(self, word: str, max_results: int = 10) -> List[dict]:
        """Prefix match: find forms starting with the given word."""
        w = norm(word.lower().strip())
        rows = _query("""
            SELECT DISTINCT f.form, l.lemma, l.pos, l.meaning
            FROM forms f
            JOIN lemmas l ON f.lemma_id = l.id
            WHERE f.form LIKE ? || '%'
            LIMIT ?;
        """, (w, max_results))
        seen = set()
        results = []
        for r in rows:
            lemma = r["lemma"]
            if lemma in seen:
                continue
            seen.add(lemma)
            results.append({
                "form": r["form"],
                "lemma": lemma,
                "part_of_speech": r["pos"],
                "meaning": r["meaning"] or "",
                "highlight": _highlight_ranges(r["form"], w),
            })

        # Fallback: try lemmas table (for indeclinable words not in forms)
        if not results:
            lemma_rows = _query("""
                SELECT lemma, pos, meaning FROM lemmas
                WHERE lemma LIKE ? || '%'
                LIMIT ?;
            """, (w, max_results))
            for r in lemma_rows:
                lemma = r["lemma"]
                if lemma in seen:
                    continue
                seen.add(lemma)
                results.append({
                    "form": r["lemma"],
                    "lemma": lemma,
                    "part_of_speech": r["pos"],
                    "meaning": r["meaning"] or "",
                    "highlight": _highlight_ranges(r["lemma"], w),
                })

        return results



def _highlight_ranges(form: str, query: str) -> list[dict]:
    """Return highlight ranges for matching characters in form vs query.
    
    Returns list of {start, end} (0-based, end-exclusive) for characters
    in `form` that match the query (case-insensitive prefix match).
    """
    fl = form.lower()
    ql = query.lower()
    ranges = []
    i = 0
    while i < len(fl):
        # Find the start of a match
        if fl[i] == ql[0]:
            j = 0
            while i + j < len(fl) and j < len(ql) and fl[i + j] == ql[j]:
                j += 1
            if j > 0:
                ranges.append({"start": i, "end": i + j})
                i += j
                continue
        i += 1
    return ranges


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
