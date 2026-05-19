"""
Inflection table generator using sqlite3 CLI subprocess (thread-safe).

Groups forms by morphology codes to build declension/conjugation tables.
"""
import os
import re
import subprocess
from typing import Optional, List, Dict

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "words.db")

# ── Morphology code labels ──────────────────────────────────────────────────

VERB_LABELS: Dict[str, str] = {
    "PRS": "Present",  "IMF": "Imperfect",  "FUT": "Future",
    "PRF": "Perfect",  "PLP": "Pluperfect", "FTP": "Future Perfect",
}
ACT_LABELS: Dict[str, str] = {
    "ACT": "Active",  "PAS": "Passive",
    "INF": "Infinitive", "IMP": "Imperative",
    "SBJ": "Subjunctive",
}
PERSON_LABELS: Dict[str, str] = {
    "1S": "1st Sing",   "2S": "2nd Sing",   "3S": "3rd Sing",
    "1P": "1st Plur",   "2P": "2nd Plur",   "3P": "3rd Plur",
}

CASE_LABELS: Dict[str, str] = {
    "NOM": "Nominative", "GEN": "Genitive",  "DAT": "Dative",
    "ACC": "Accusative", "ABL": "Ablative",  "VOC": "Vocative",
}
NUM_LABELS: Dict[str, str] = {"S": "Singular", "P": "Plural"}
GENDER_LABELS: Dict[str, str] = {"M": "Masculine", "F": "Feminine", "N": "Neuter"}

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


# ── Parser ──────────────────────────────────────────────────────────────────

def parse_morph(m: str) -> dict:
    """Parse morphology string into components.
    Verb: PRSACT1S, IMFACT2P, PRSPAS1S, PPPNOMSGM, etc.
    Noun: NOMS, GENS, DATS, etc.
    """
    info: Dict[str, str] = {}
    # Verb patterns
    if "PRS" in m or "IMF" in m or "FUT" in m or "PRF" in m or "PLP" in m or "FTP" in m:
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
        # Participle (PPP, PPA, etc.)
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
        # after the case+number part (e.g. NOMSM, NOMPF), not as part of S/P.
        gender_match = re.search(r'(?:NOM|GEN|DAT|ACC|ABL|VOC)[SP]([MFN])', m)
        if gender_match:
            g = gender_match.group(1)
            info["gender"] = GENDER_LABELS.get(g, g)
    else:
        info["raw"] = m
    return info


def form_sort_key(info: dict) -> tuple:
    """Sort order for inflection table rows."""
    order = {"Singular": 0, "Plural": 1}
    case_order = {"Nominative": 0, "Genitive": 1, "Dative": 2,
                  "Accusative": 3, "Vocative": 4, "Ablative": 5}
    person_order = {"1st Sing": 0, "2nd Sing": 1, "3rd Sing": 2,
                    "1st Plur": 3, "2nd Plur": 4, "3rd Plur": 5}
    tense_order = {"Present": 0, "Imperfect": 1, "Future": 2,
                   "Perfect": 3, "Pluperfect": 4, "Future Perfect": 5}
    voice_order = {"Active": 0, "Passive": 1}
    return (
        order.get(info.get("number", ""), 9),
        case_order.get(info.get("case", ""), 9),
        tense_order.get(info.get("tense", ""), 9),
        voice_order.get(info.get("voice", ""), 9),
        person_order.get(info.get("person", ""), 9),
    )


# ── Generator ───────────────────────────────────────────────────────────────

class Inflector:
    def __init__(self, db: str = DB):
        self.db = db

    def generate(self, lemma: str) -> Optional[Dict[str, list]]:
        """Generate inflection table for a lemma."""
        if not os.path.exists(self.db):
            return None

        # Get all matching lemma ids
        safe = lemma.replace("'", "''")
        out = _sql(f"SELECT id, pos FROM lemmas WHERE lemma = '{safe}';")
        lines = [l for l in out.splitlines() if l.strip()]
        if not lines:
            return None

        # Parts of speech that don't have inflections (conjunctions, prepositions,
        # adverbs, interjections, etc.) — return None immediately.
        NON_INFLECTABLE = {'Conjunction', 'Preposition', 'Adverb', 'Interjection',
                           'Prefix', 'Suffix', 'Punctuation', 'Numeral'}
        for line in lines:
            parts = line.split("|")
            if len(parts) >= 2:
                pos = parts[1].strip()
                if pos in NON_INFLECTABLE:
                    return None

        # Try each lemma_id, pick the one with the most forms
        best_lid = None
        best_rows: list[str] = []
        for line in lines:
            parts = line.split("|")
            if len(parts) < 1:
                continue
            lid = parts[0].strip()
            out2 = _sql(f"SELECT form, morphology FROM forms WHERE lemma_id = {lid};")
            rows2 = [l for l in out2.splitlines() if l.strip()]
            if len(rows2) > len(best_rows):
                best_lid = lid
                best_rows = rows2

        # If no forms found, try stripping verb endings: differo -> differ
        # Only do this if the lemma is long enough (>3 chars) to avoid
        # matching short words like "ut" (conjunction) as verb stems.
        if not best_rows and len(lemma) > 3:
            for suffix in ['o', 're', 'is', 'it', 'mus', 'tis', 'nt', 'ri', 'ror']:
                if lemma.endswith(suffix) and len(lemma) > len(suffix) + 1:
                    stem = lemma[:-len(suffix)]
                    out2 = _sql(f"SELECT id FROM lemmas WHERE lemma = '{stem.replace(chr(39), chr(39)+chr(39))}';")
                    stem_lines = [l for l in out2.splitlines() if l.strip()]
                    for sl in stem_lines:
                        sid = sl.strip()
                        out3 = _sql(f"SELECT form, morphology FROM forms WHERE lemma_id = {sid};")
                        rows3 = [l for l in out3.splitlines() if l.strip()]
                        if len(rows3) > len(best_rows):
                            best_lid = sid
                            best_rows = rows3
                    if best_rows:
                        break

        if not best_rows:
            return None

        # Deduplicate by (form, morphology)
        seen: set[tuple[str, str]] = set()
        entries = []
        for line in best_rows:
            fp = line.split("|", 1)
            form = fp[0]
            morph = fp[1] if len(fp) > 1 else ""
            key = (form, morph)
            if key in seen:
                continue
            seen.add(key)
            # Skip entries with empty morphology (like the base form "un" itself)
            if not morph:
                continue
            # Skip placeholder forms (Collatinus uses "zzz" prefix for unknown forms)
            if form.startswith('zzz'):
                continue
            info = parse_morph(morph)
            entries.append({
                "form": form,
                "morphology": morph,
                "info": info,
            })

        # Group by tense+voice or case+number+gender
        groups: Dict[str, list] = {}
        for e in entries:
            info = e["info"]
            if "tense" in info and "voice" in info:
                group = f"{info.get('tense','?')} {info.get('voice','?')}"
            elif "case" in info and "number" in info:
                # Include gender in group name to separate M/F/N
                gender = info.get("gender", "")
                group = f"{info.get('number','?')}{' ' + gender if gender else ''}"
            elif "case" in info:
                group = "Cases"
            elif "form" in info:
                group = info["form"]
            else:
                group = "Other"
            groups.setdefault(group, []).append(e)

        # Sort within each group
        table: Dict[str, list] = {}
        for g, items in groups.items():
            items.sort(key=lambda x: form_sort_key(x["info"]))
            table[g] = []
            for it in items:
                i = it["info"]
                row_entry: Dict[str, str] = {"form": it["form"], "ending": it["morphology"]}
                if "case" in i:
                    row_entry["case"] = i["case"]
                if "person" in i:
                    row_entry["person"] = i["person"]
                if "number" in i:
                    row_entry["number"] = i["number"]
                if "gender" in i:
                    row_entry["gender"] = i["gender"]
                table[g].append(row_entry)

        return table if table else None


_default: Optional[Inflector] = None


def get_inflector() -> Inflector:
    global _default
    if _default is None:
        _default = Inflector()
    return _default


def generate_table(lemma: str) -> Optional[Dict[str, list]]:
    return get_inflector().generate(lemma)
