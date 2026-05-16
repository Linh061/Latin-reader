"""
Inflection table generator using SQLite database (words.db).

Groups forms by morphology codes to build declension/conjugation tables.
"""
import os, sqlite3
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
        for g in ["M","F","N"]:
            if g in m:
                info["gender"] = GENDER_LABELS[g]
                break
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
        self.conn: Optional[sqlite3.Connection] = None

    def _ready(self):
        if self.conn is not None:
            return
        if not os.path.exists(self.db):
            raise FileNotFoundError(f"DB missing: {self.db}")
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row

    def generate(self, lemma: str) -> Optional[Dict[str, list]]:
        """Generate inflection table for a lemma."""
        self._ready()
        c = self.conn.cursor()
        c.execute("SELECT id, pos FROM lemmas WHERE lemma = ?", (lemma,))
        row = c.fetchone()
        if not row:
            return None
        lid = row["id"]
        pos = row["pos"]

        c.execute("SELECT form, morphology FROM forms WHERE lemma_id = ?", (lid,))
        rows = c.fetchall()
        if not rows:
            return None

        entries = []
        for r in rows:
            morph = r["morphology"] or ""
            info = parse_morph(morph)
            entries.append({
                "form": r["form"],
                "morphology": morph,
                "info": info,
            })

        # Group by tense+voice or case+number
        groups: Dict[str, list] = {}
        for e in entries:
            info = e["info"]
            if "tense" in info and "voice" in info:
                group = f"{info.get('tense','?')} {info.get('voice','?')}"
            elif "case" in info and "number" in info:
                group = f"{info.get('number','?')}"
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
