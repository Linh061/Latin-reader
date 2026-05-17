"""
Import Collatinus dictionary data into words.db using sqlite3 CLI.

Collatinus provides:
  - lemmes.en:  lemma:english_meaning  (16,557 entries)
  - lemmes.la:  lemma|model|||pos,freq  (24,176 entries, with macrons)
  - lem_ext.la: extended lexicon (same format)

This script merges Collatinus data into words.db:
  - For existing lemmas: replaces meaning with Collatinus's (cleaner, no annotation codes)
  - For new lemmas: inserts them with Collatinus's meaning and POS
  - Preserves Whitaker's-only lemmas untouched

After import, rebuild text indexes:
    python -m engine.build_dict

Usage:
    python -m engine.import_collatinus
"""
import os
import re
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(__file__))
COLLATINUS_DIR = os.path.join(os.path.dirname(BASE), "collatinus", "bin", "data")
DB_PATH = os.path.join(BASE, "cache", "words.db")

# Latin diacritic stripping
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
    """Strip Latin diacritics and lowercase."""
    return ''.join(LATIN_MAP.get(c, c) for c in s).strip().lower()


def sql(sql: str):
    """Run SQL via sqlite3 CLI."""
    result = subprocess.run(
        ["sqlite3", DB_PATH, sql],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        logger.error("sqlite3 error: %s", result.stderr)
    return result.stdout


def parse_lemmes_en(path: str) -> dict[str, str]:
    """Parse lemmes.en → {normalized_lemma: meaning_text}"""
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            colon_pos = line.find(":")
            if colon_pos < 0:
                continue
            lemma_raw = line[:colon_pos].strip()
            meaning = line[colon_pos + 1:].strip()
            if not lemma_raw or not meaning:
                continue
            key = norm(lemma_raw)
            if key:
                result[key] = meaning
    return result


def parse_lemmes_la(path: str) -> dict[str, str]:
    """Parse lemmes.la → {normalized_lemma: pos_string}"""
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            lemma_raw = parts[0].strip()
            lemma_clean = lemma_raw.split("=")[0].strip()
            pos_field = parts[4].strip() if len(parts) > 4 else ""
            key = norm(lemma_clean)
            if key:
                result[key] = pos_field
    return result


def pos_from_collatinus(pos_field: str) -> str:
    """Convert Collatinus POS field to a simple POS string."""
    pf = pos_field.lower().strip()
    if not pf:
        return ""
    if any(kw in pf for kw in ("prép", "prep")):
        return "Preposition"
    if "interj" in pf:
        return "Interjection"
    if "conj" in pf:
        return "Conjunction"
    if "adv" in pf:
        return "Adverb"
    if "numér" in pf or "num" in pf:
        return "Numeral"
    if "pron" in pf or "pronom" in pf:
        return "Pronoun"
    if re.search(r'\b(are|ere|ire)\b', pf):
        return "Verb"
    if re.search(r',\s*(ere|ire|are)\s*,', pf):
        return "Verb"
    if re.search(r'\ba,\s*um\b', pf) or re.search(r'\bus,\s*a,\s*um\b', pf) or re.search(r'\bis,\s*e\b', pf):
        return "Adjective"
    if re.search(r'\b(m\.|f\.|n\.)\b', pf):
        return "Noun"
    if re.search(r'\b(i|ae|is|us|ei|er|o|onis|inis|ud)\b', pf):
        return "Noun"
    return ""


def main():
    # ── Parse Collatinus data ──────────────────────────────────────
    en_path = os.path.join(COLLATINUS_DIR, "lemmes.en")
    la_path = os.path.join(COLLATINUS_DIR, "lemmes.la")
    ext_path = os.path.join(COLLATINUS_DIR, "lem_ext.la")

    logger.info("Parsing lemmes.en ...")
    en_data = parse_lemmes_en(en_path)
    logger.info("  → %d entries", len(en_data))

    logger.info("Parsing lemmes.la ...")
    la_data = parse_lemmes_la(la_path)
    logger.info("  → %d entries", len(la_data))

    logger.info("Parsing lem_ext.la ...")
    ext_data = parse_lemmes_la(ext_path)
    logger.info("  → %d entries", len(ext_data))

    pos_data = {**la_data, **ext_data}

    # ── Get existing lemmas from DB ────────────────────────────────
    logger.info("Reading existing lemmas from words.db...")
    out = sql("SELECT lemma FROM lemmas;")
    existing = set(out.strip().splitlines()) if out.strip() else set()
    logger.info("Existing lemmas: %d", len(existing))

    # ── Build SQL statements ───────────────────────────────────────
    updates = []
    inserts = []

    for key, meaning in en_data.items():
        # Escape single quotes for SQL
        meaning_safe = meaning.replace("'", "''")
        pos = pos_from_collatinus(pos_data.get(key, ""))

        if key in existing:
            if pos:
                updates.append(
                    f"UPDATE lemmas SET meaning = '{meaning_safe}', pos = '{pos}' WHERE lemma = '{key}';"
                )
            else:
                updates.append(
                    f"UPDATE lemmas SET meaning = '{meaning_safe}' WHERE lemma = '{key}';"
                )
        else:
            pos_safe = pos.replace("'", "''")
            inserts.append(
                f"INSERT INTO lemmas (lemma, pos, meaning) VALUES ('{key}', '{pos_safe}', '{meaning_safe}');"
            )

    # ── Execute ────────────────────────────────────────────────────
    logger.info("Updates: %d, Inserts: %d", len(updates), len(inserts))

    if updates:
        logger.info("Applying updates...")
        # Batch updates in groups of 100
        for i in range(0, len(updates), 100):
            batch = updates[i:i + 100]
            sql("BEGIN TRANSACTION; " + " ".join(batch) + " COMMIT;")
        logger.info("Updates done.")

    if inserts:
        logger.info("Inserting new lemmas...")
        for i in range(0, len(inserts), 100):
            batch = inserts[i:i + 100]
            sql("BEGIN TRANSACTION; " + " ".join(batch) + " COMMIT;")
        logger.info("Inserts done.")

    # ── Report ─────────────────────────────────────────────────────
    out = sql("SELECT COUNT(*) FROM lemmas;")
    total = out.strip()
    logger.info("Done! Total lemmas now: %s (was %d)", total, len(existing))
    logger.info("")
    logger.info("NEXT STEP: Rebuild text indexes:")
    logger.info("  python -m engine.build_dict")


if __name__ == "__main__":
    main()
