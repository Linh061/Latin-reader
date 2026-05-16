#!/usr/bin/env python3
"""Build SQLite from DICTLINE.GEN. Run: python3 scripts/build_db.py"""
import re, sqlite3, os, time
BASE = os.path.join(os.path.dirname(__file__), "..", "..")
DICTLINE = os.path.join(BASE, "whitakers-words", "DICTLINE.GEN")
DB = os.path.join(BASE, "backend", "cache", "words.db")

def sd(s):
    r = {'ā':'a','ă':'a','ǎ':'a','â':'a','à':'a','ē':'e','ĕ':'e','ě':'e','ê':'e','è':'e',
         'ī':'i','ĭ':'i','î':'i','ì':'i','ō':'o','ŏ':'o','ǒ':'o','ô':'o','ò':'o',
         'ū':'u','ŭ':'u','ǔ':'u','û':'u','ù':'u','ȳ':'y','ў':'y',
         'Ā':'A','Ă':'A','Â':'A','À':'A','Ē':'E','Ĕ':'E','Ê':'E','È':'E',
         'Ī':'I','Ĭ':'I','Ì':'I','Ō':'O','Ŏ':'O','Ô':'O','Ò':'O',
         'Ū':'U','Ŭ':'U','Û':'U','Ù':'U'}
    return ''.join(r.get(c,c) for c in s)

VERBS = {
    "1":[("o","PRSACT1S",1),("as","PRSACT2S",2),("at","PRSACT3S",2),("amus","PRSACT1P",2),("atis","PRSACT2P",2),("ant","PRSACT3P",1),
         ("abam","IMFACT1S",1),("abas","IMFACT2S",1),("abat","IMFACT3S",1),("abamus","IMFACT1P",1),("abatis","IMFACT2P",1),("abant","IMFACT3P",1),
         ("abo","FUTACT1S",1),("abis","FUTACT2S",1),("abit","FUTACT3S",1),("abimus","FUTACT1P",1),("abitis","FUTACT2P",1),("abunt","FUTACT3P",1),
         ("or","PRSPAS1S",1),("aris","PRSPAS2S",2),("atur","PRSPAS3S",2),("amur","PRSPAS1P",2),("amini","PRSPAS2P",2),("antur","PRSPAS3P",1),
         ("abar","IMFPAS1S",1),("abaris","IMFPAS2S",1),("abatur","IMFPAS3S",1),("abamur","IMFPAS1P",1),("abamini","IMFPAS2P",1),("abantur","IMFPAS3P",1),
         ("em","PRSSBJ1S",2),("es","PRSSBJ2S",2),("et","PRSSBJ3S",2),("emus","PRSSBJ1P",2),("etis","PRSSBJ2P",2),("ent","PRSSBJ3P",2),
         ("arem","IMFSBJ1S",1),("ares","IMFSBJ2S",1),("aret","IMFSBJ3S",1),("aremus","IMFSBJ1P",1),("aretis","IMFSBJ2P",1),("arent","IMFSBJ3P",1),
         ("a","IMP2S",2),("ate","IMP2P",2),("are","PRSINF",1),("ari","PRSINFPA",1),
         ("i","PRFACT1S",3),("isti","PRFACT2S",3),("it","PRFACT3S",3),("imus","PRFACT1P",3),("istis","PRFACT2P",3),("erunt","PRFACT3P",3),
         ("eram","PLPACT1S",3),("eras","PLPACT2S",3),("erat","PLPACT3S",3),("eramus","PLPACT1P",3),("eratis","PLPACT2P",3),("erant","PLPACT3P",3),
         ("ero","FTPACT1S",3),("eris","FTPACT2S",3),("erit","FTPACT3S",3),("erimus","FTPACT1P",3),("eritis","FTPACT2P",3),("erint","FTPACT3P",3),
         ("issem","PLPSBJ1S",3),("isses","PLPSBJ2S",3),("isset","PLPSBJ3S",3),("issemus","PLPSBJ1P",3),("issetis","PLPSBJ2P",3),("issent","PLPSBJ3P",3),
         ("isse","PRFINF",3),("us","PPPNOMSGM",4),("a","PPPNOMSF",4),("um","PPPNOMSN",4),("u","SUPABL",4)],
    "2":[("eo","PRSACT1S",1),("es","PRSACT2S",2),("et","PRSACT3S",2),("emus","PRSACT1P",2),("etis","PRSACT2P",2),("ent","PRSACT3P",1),
         ("ebam","IMFACT1S",1),("ebas","IMFACT2S",1),("ebat","IMFACT3S",1),("ebamus","IMFACT1P",1),("ebatis","IMFACT2P",1),("ebant","IMFACT3P",1),
         ("ebo","FUTACT1S",1),("ebis","FUTACT2S",1),("ebit","FUTACT3S",1),("ebimus","FUTACT1P",1),("ebitis","FUTACT2P",1),("ebunt","FUTACT3P",1),
         ("eor","PRSPAS1S",1),("eris","PRSPAS2S",2),("etur","PRSPAS3S",2),("emur","PRSPAS1P",2),("emini","PRSPAS2P",2),("entur","PRSPAS3P",1),
         ("eam","PRSSBJ1S",2),("eas","PRSSBJ2S",2),("eat","PRSSBJ3S",2),("eamus","PRSSBJ1P",2),("eatis","PRSSBJ2P",2),("eant","PRSSBJ3P",2),
         ("erem","IMFSBJ1S",1),("eres","IMFSBJ2S",1),("eret","IMFSBJ3S",1),("eremus","IMFSBJ1P",1),("eretis","IMFSBJ2P",1),("erent","IMFSBJ3P",1),
         ("e","IMP2S",2),("ete","IMP2P",2),("ere","PRSINF",1),("eri","PRSINFPA",1),
         ("i","PRFACT1S",3),("isti","PRFACT2S",3),("it","PRFACT3S",3),("imus","PRFACT1P",3),("istis","PRFACT2P",3),("erunt","PRFACT3P",3),
         ("eram","PLPACT1S",3),("eras","PLPACT2S",3),("erat","PLPACT3S",3),("eramus","PLPACT1P",3),("eratis","PLPACT2P",3),("erant","PLPACT3P",3),
         ("ero","FTPACT1S",3),("eris","FTPACT2S",3),("erit","FTPACT3S",3),("erimus","FTPACT1P",3),("eritis","FTPACT2P",3),("erint","FTPACT3P",3),
         ("issem","PLPSBJ1S",3),("isses","PLPSBJ2S",3),("isset","PLPSBJ3S",3),("issemus","PLPSBJ1P",3),("issetis","PLPSBJ2P",3),("issent","PLPSBJ3P",3),
         ("isse","PRFINF",3),("us","PPPNOMSGM",4),("a","PPPNOMSF",4),("um","PPPNOMSN",4),("u","SUPABL",4)],
    "3":[("o","PRSACT1S",1),("is","PRSACT2S",2),("it","PRSACT3S",2),("imus","PRSACT1P",2),("itis","PRSACT2P",2),("unt","PRSACT3P",1),
         ("ebam","IMFACT1S",1),("ebas","IMFACT2S",1),("ebat","IMFACT3S",1),("ebamus","IMFACT1P",1),("ebatis","IMFACT2P",1),("ebant","IMFACT3P",1),
         ("am","FUTACT1S",1),("es","FUTACT2S",2),("et","FUTACT3S",2),("emus","FUTACT1P",2),("etis","FUTACT2P",2),("ent","FUTACT3P",1),
         ("or","PRSPAS1S",1),("eris","PRSPAS2S",2),("itur","PRSPAS3S",2),("imur","PRSPAS1P",2),("imini","PRSPAS2P",2),("untur","PRSPAS3P",1),
         ("am","PRSSBJ1S",2),("as","PRSSBJ2S",2),("at","PRSSBJ3S",2),("amus","PRSSBJ1P",2),("atis","PRSSBJ2P",2),("ant","PRSSBJ3P",2),
         ("erem","IMFSBJ1S",1),("eres","IMFSBJ2S",1),("eret","IMFSBJ3S",1),("eremus","IMFSBJ1P",1),("eretis","IMFSBJ2P",1),("erent","IMFSBJ3P",1),
         ("e","IMP2S",2),("ite","IMP2P",2),("ere","PRSINF",1),("i","PRSINFPA",1),
         ("i","PRFACT1S",3),("isti","PRFACT2S",3),("it","PRFACT3S",3),("imus","PRFACT1P",3),("istis","PRFACT2P",3),("erunt","PRFACT3P",3),
         ("eram","PLPACT1S",3),("eras","PLPACT2S",3),("erat","PLPACT3S",3),("eramus","PLPACT1P",3),("eratis","PLPACT2P",3),("erant","PLPACT3P",3),
         ("ero","FTPACT1S",3),("eris","FTPACT2S",3),("erit","FTPACT3S",3),("erimus","FTPACT1P",3),("eritis","FTPACT2P",3),("erint","FTPACT3P",3),
         ("issem","PLPSBJ1S",3),("isses","PLPSBJ2S",3),("isset","PLPSBJ3S",3),("issemus","PLPSBJ1P",3),("issetis","PLPSBJ2P",3),("issent","PLPSBJ3P",3),
         ("isse","PRFINF",3),("us","PPPNOMSGM",4),("a","PPPNOMSF",4),("um","PPPNOMSN",4),("u","SUPABL",4)],
    "4":[("io","PRSACT1S",1),("is","PRSACT2S",2),("it","PRSACT3S",2),("imus","PRSACT1P",2),("itis","PRSACT2P",2),("iunt","PRSACT3P",1),
         ("iebam","IMFACT1S",1),("iebas","IMFACT2S",1),("iebat","IMFACT3S",1),("iebamus","IMFACT1P",1),("iebatis","IMFACT2P",1),("iebant","IMFACT3P",1),
         ("iam","FUTACT1S",1),("ies","FUTACT2S",1),("iet","FUTACT3S",1),("iemus","FUTACT1P",1),("ietis","FUTACT2P",1),("ient","FUTACT3P",1),
         ("ior","PRSPAS1S",1),("iris","PRSPAS2S",2),("itur","PRSPAS3S",2),("imur","PRSPAS1P",2),("imini","PRSPAS2P",2),("iuntur","PRSPAS3P",1),
         ("iam","PRSSBJ1S",2),("ias","PRSSBJ2S",2),("iat","PRSSBJ3S",2),("iamus","PRSSBJ1P",2),("iatis","PRSSBJ2P",2),("iant","PRSSBJ3P",2),
         ("irem","IMFSBJ1S",1),("ires","IMFSBJ2S",1),("iret","IMFSBJ3S",1),("iremus","IMFSBJ1P",1),("iretis","IMFSBJ2P",1),("irent","IMFSBJ3P",1),
         ("i","IMP2S",2),("ite","IMP2P",2),("ire","PRSINF",1),("iri","PRSINFPA",1),
         ("i","PRFACT1S",3),("isti","PRFACT2S",3),("it","PRFACT3S",3),("imus","PRFACT1P",3),("istis","PRFACT2P",3),("erunt","PRFACT3P",3),
         ("eram","PLPACT1S",3),("eras","PLPACT2S",3),("erat","PLPACT3S",3),("eramus","PLPACT1P",3),("eratis","PLPACT2P",3),("erant","PLPACT3P",3),
         ("ero","FTPACT1S",3),("eris","FTPACT2S",3),("erit","FTPACT3S",3),("erimus","FTPACT1P",3),("eritis","FTPACT2P",3),("erint","FTPACT3P",3),
         ("issem","PLPSBJ1S",3),("isses","PLPSBJ2S",3),("isset","PLPSBJ3S",3),("issemus","PLPSBJ1P",3),("issetis","PLPSBJ2P",3),("issent","PLPSBJ3P",3),
         ("isse","PRFINF",3),("us","PPPNOMSGM",4),("a","PPPNOMSF",4),("um","PPPNOMSN",4),("u","SUPABL",4)],
}

NOUNS = {
    "1":[("a","NOMS"),("a","VOCS"),("ae","GENS"),("ae","DATS"),("am","ACCS"),("a","ABLS"),("ae","NOMP"),("ae","VOCP"),("as","ACCP"),("arum","GENP"),("is","DATP"),("is","ABLP")],
    "2m":[("us","NOMS"),("e","VOCS"),("i","GENS"),("o","DATS"),("um","ACCS"),("o","ABLS"),("i","NOMP"),("i","VOCP"),("os","ACCP"),("orum","GENP"),("is","DATP"),("is","ABLP")],
    "2n":[("um","NOMS"),("um","VOCS"),("i","GENS"),("o","DATS"),("um","ACCS"),("o","ABLS"),("a","NOMP"),("a","VOCP"),("a","ACCP"),("orum","GENP"),("is","DATP"),("is","ABLP")],
    "3":[("","NOMS"),("","VOCS"),("is","GENS"),("i","DATS"),("em","ACCS"),("e","ABLS"),("es","NOMP"),("es","VOCP"),("es","ACCP"),("um","GENP"),("ibus","DATP"),("ibus","ABLP")],
    "3i":[("is","NOMS"),("is","VOCS"),("is","GENS"),("i","DATS"),("em","ACCS"),("i","ABLS"),("es","NOMP"),("es","VOCP"),("es","ACCP"),("ium","GENP"),("ibus","DATP"),("ibus","ABLP")],
    "3n":[("","NOMS"),("","VOCS"),("is","GENS"),("i","DATS"),("","ACCS"),("e","ABLS"),("a","NOMP"),("a","VOCP"),("a","ACCP"),("um","GENP"),("ibus","DATP"),("ibus","ABLP")],
    "4":[("us","NOMS"),("us","VOCS"),("us","GENS"),("ui","DATS"),("um","ACCS"),("u","ABLS"),("us","NOMP"),("us","VOCP"),("us","ACCP"),("uum","GENP"),("ibus","DATP"),("ibus","ABLP")],
    "4n":[("u","NOMS"),("u","VOCS"),("us","GENS"),("u","DATS"),("u","ACCS"),("u","ABLS"),("ua","NOMP"),("ua","VOCP"),("ua","ACCP"),("uum","GENP"),("ibus","DATP"),("ibus","ABLP")],
    "5":[("es","NOMS"),("es","VOCS"),("ei","GENS"),("ei","DATS"),("em","ACCS"),("e","ABLS"),("es","NOMP"),("es","VOCP"),("es","ACCP"),("erum","GENP"),("ebus","DATP"),("ebus","ABLP")],
}

ADJMF = [("us","NOMSM"),("a","NOMSF"),("um","NOMSN"),("i","GENS"),("o","DATS"),("um","ACCSM"),("am","ACCSF"),("um","ACCSN"),("o","ABLS"),
         ("i","NOMPM"),("ae","NOMPF"),("a","NOMPN"),("orum","GENPM"),("arum","GENPF"),("orum","GENPN"),("is","DATP"),("is","ABLP")]
ADJ3 = [("is","NOMSMF"),("e","NOMSN"),("is","GENS"),("i","DATS"),("em","ACCSMF"),("e","ACCSN"),("i","ABLS"),
        ("es","NOMPMF"),("ia","NOMPN"),("ium","GENP"),("ibus","DATP"),("ibus","ABLP")]

POS_MAP = {"N":"Noun","V":"Verb","ADJ":"Adjective","ADV":"Adverb",
           "PREP":"Preposition","CONJ":"Conjunction","PRON":"Pronoun",
           "INTERJ":"Interjection","NUM":"Numeral","PACK":"Pack"}

t0 = time.time()
os.makedirs(os.path.dirname(DB), exist_ok=True)
conn = sqlite3.connect(DB)
c = conn.cursor()
c.executescript("""CREATE TABLE IF NOT EXISTS lemmas(id INTEGER PRIMARY KEY, lemma TEXT NOT NULL, pos TEXT, meaning TEXT);
CREATE TABLE IF NOT EXISTS forms(form TEXT NOT NULL, lemma_id INTEGER NOT NULL, morphology TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_f ON forms(form); CREATE INDEX IF NOT EXISTS idx_l ON lemmas(lemma);""")

def genv(stems, conj):
    for end, morph, sn in VERBS.get(conj, []):
        s = stems.get(sn)
        if s: yield s + end, morph

def genn(stem, typ):
    for end, morph in NOUNS.get(typ, []):
        yield stem + end, morph

def gena(stem, decl):
    rules = ADJ3 if decl and decl[0] in ("2","3") else ADJMF
    for end, morph in rules:
        yield stem + end, morph

seen_lemma = {}
batch = []

for line in open(DICTLINE, encoding="latin-1"):
    line = line.rstrip('\n\r')
    if not line: continue
    f = re.split(r'  +', line)
    if len(f) < 4: continue
    stem = f[0].strip()
    if not stem: continue
    # POS at f[2] (noun/adj/adv/etc) or f[4] (verb)
    if len(f) > 4 and f[4].strip() in POS_MAP:
        pc = f[4].strip(); pi = 4
    elif f[2].strip() in POS_MAP:
        pc = f[2].strip(); pi = 2
    else:
        continue
    st = sd(stem)
    pos = POS_MAP[pc]
    meaning = f[-1].strip() if len(f) > pi else ""
    sp = f[pi+1].split() if len(f) > pi+1 else []
    forms = []
    if pc == "V":
        conj = sp[0] if sp else "1"
        forms = list(genv({1:sd(f[1]) if len(f)>1 and f[1] else st,
                           2:sd(f[1]) if len(f)>1 and f[1] else st,
                           3:sd(f[2]) if len(f)>2 and f[2] else "",
                           4:sd(f[3]) if len(f)>3 and f[3] else ""}, conj))
    elif pc == "N":
        # noun stem is at f[1] if present, else f[0]
        ns = sd(f[1]) if len(f) > 1 and f[1] else st
        decl = sp[0] if sp else "1"
        g = sp[2] if len(sp) > 2 else "X"
        if decl == "1": dt = "1"
        elif decl == "2": dt = "2n" if g == "N" else "2m"
        elif decl == "3": dt = "3n" if g == "N" else ("3i" if len(sp)>1 and sp[1] in ("2","5","6","7","8") else "3")
        elif decl == "4": dt = "4n" if g == "N" else "4"
        elif decl == "5": dt = "5"
        else: dt = None
        if dt: forms = list(genn(ns, dt))
    elif pc == "ADJ":
        forms = list(gena(st, sp))
    else:
        forms = [(st, "")]
    if not forms: continue
    lkey = st + "\0" + pos
    if lkey in seen_lemma:
        lid = seen_lemma[lkey]
    else:
        c.execute("INSERT INTO lemmas(lemma,pos,meaning) VALUES(?,?,?)", (st, pos, meaning))
        lid = c.lastrowid
        seen_lemma[lkey] = lid
    for form, morph in forms:
        batch.append((form, lid, morph))
    if len(batch) >= 50000:
        c.executemany("INSERT INTO forms VALUES(?,?,?)", batch)
        conn.commit(); batch.clear()

if batch:
    c.executemany("INSERT INTO forms VALUES(?,?,?)", batch)
    conn.commit()
lc = c.execute("SELECT COUNT(DISTINCT lemma) FROM lemmas").fetchone()[0]
fc = c.execute("SELECT COUNT(*) FROM forms").fetchone()[0]
uc = c.execute("SELECT COUNT(DISTINCT form) FROM forms").fetchone()[0]
conn.close()
elapsed = time.time() - t0
print(f"{lc} lemmas, {fc} forms ({uc} unique), {os.path.getsize(DB)/1024/1024:.1f}MB, {elapsed:.2f}s")
