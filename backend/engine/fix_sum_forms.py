"""
Fix: Insert correct inflection forms for verb "sum" (to be).

The database has lemma 'sum' (to be) with id 29724, but its forms table
contains only 'sumo' (take up) forms. This script:
1. Creates a new lemma 'sumo' (take up) 
2. Moves sumo-related forms to the new lemma
3. Inserts correct sum (to be) forms based on Whitaker's Words INFLECTS.LAT rules (V 5 1)
"""
import os
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "words.db")

SUM_LEMMA_ID = 29724  # sum (to be)

# Correct sum (to be) forms based on INFLECTS.LAT V 5 1 rules
# Stem: s- (present), er- (imperfect/future), fu- (perfect), fut- (future participle)
SUM_FORMS = [
    # Present Indicative Active
    ("sum", "PRSACT1S"),
    ("es", "PRSACT2S"),
    ("est", "PRSACT3S"),
    ("sumus", "PRSACT1P"),
    ("estis", "PRSACT2P"),
    ("sunt", "PRSACT3P"),
    
    # Imperfect Indicative Active
    ("eram", "IMFACT1S"),
    ("eras", "IMFACT2S"),
    ("erat", "IMFACT3S"),
    ("eramus", "IMFACT1P"),
    ("eratis", "IMFACT2P"),
    ("erant", "IMFACT3P"),
    
    # Future Indicative Active
    ("ero", "FUTACT1S"),
    ("eris", "FUTACT2S"),
    ("erit", "FUTACT3S"),
    ("erimus", "FUTACT1P"),
    ("eritis", "FUTACT2P"),
    ("erunt", "FUTACT3P"),
    
    # Present Subjunctive Active
    ("sim", "PRSSBJ1S"),
    ("sis", "PRSSBJ2S"),
    ("sit", "PRSSBJ3S"),
    ("simus", "PRSSBJ1P"),
    ("sitis", "PRSSBJ2P"),
    ("sint", "PRSSBJ3P"),
    
    # Imperfect Subjunctive Active
    ("essem", "IMFSBJ1S"),
    ("esses", "IMFSBJ2S"),
    ("esset", "IMFSBJ3S"),
    ("essemus", "IMFSBJ1P"),
    ("essetis", "IMFSBJ2P"),
    ("essent", "IMFSBJ3P"),
    
    # Imperfect Subjunctive Active (alternative)
    ("forem", "IMFSBJ1S"),
    ("fores", "IMFSBJ2S"),
    ("foret", "IMFSBJ3S"),
    ("foremus", "IMFSBJ1P"),
    ("foretis", "IMFSBJ2P"),
    ("forent", "IMFSBJ3P"),
    
    # Imperative Present Active
    ("es", "PRSIMP2S"),
    ("este", "PRSIMP2P"),
    
    # Imperative Future Active
    ("esto", "FUTIMP2S"),
    ("esto", "FUTIMP3S"),
    ("estote", "FUTIMP2P"),
    ("sunto", "FUTIMP3P"),
    
    # Infinitive Present Active
    ("esse", "PRSINF"),
    
    # Perfect forms (stem: fu-)
    ("fui", "PRFACT1S"),
    ("fuisti", "PRFACT2S"),
    ("fuit", "PRFACT3S"),
    ("fuimus", "PRFACT1P"),
    ("fuistis", "PRFACT2P"),
    ("fuerunt", "PRFACT3P"),
    ("fuere", "PRFACT3P"),
    
    # Pluperfect Indicative (stem: fuer-)
    ("fueram", "PLPACT1S"),
    ("fueras", "PLPACT2S"),
    ("fuerat", "PLPACT3S"),
    ("fueramus", "PLPACT1P"),
    ("fueratis", "PLPACT2P"),
    ("fuerant", "PLPACT3P"),
    
    # Future Perfect Indicative (stem: fuer-)
    ("fuero", "FTPACT1S"),
    ("fueris", "FTPACT2S"),
    ("fuerit", "FTPACT3S"),
    ("fuerimus", "FTPACT1P"),
    ("fueritis", "FTPACT2P"),
    ("fuerint", "FTPACT3P"),
    
    # Perfect Subjunctive (stem: fuer-)
    ("fuerim", "PRFSBJ1S"),
    ("fueris", "PRFSBJ2S"),
    ("fuerit", "PRFSBJ3S"),
    ("fuerimus", "PRFSBJ1P"),
    ("fueritis", "PRFSBJ2P"),
    ("fuerint", "PRFSBJ3P"),
    
    # Pluperfect Subjunctive (stem: fuiss-)
    ("fuissem", "PLPSBJ1S"),
    ("fuisses", "PLPSBJ2S"),
    ("fuisset", "PLPSBJ3S"),
    ("fuissemus", "PLPSBJ1P"),
    ("fuissetis", "PLPSBJ2P"),
    ("fuissent", "PLPSBJ3P"),
    
    # Perfect Infinitive
    ("fuisse", "PRFINF"),
    
    # Future Infinitive
    ("fore", "FUTINF"),
    ("futurus esse", "FUTINF"),
    ("futuram esse", "FUTINF"),
    ("futurum esse", "FUTINF"),
    
    # Future Participle
    ("futurus", "FUTNOMSM"),
    ("futura", "FUTNOMSF"),
    ("futurum", "FUTNOMSN"),
]

def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Step 1: Check if sumo already exists as a separate lemma
    c.execute("SELECT id FROM lemmas WHERE lemma = 'sumo' AND pos = 'Verb'")
    row = c.fetchone()
    
    if row:
        sumo_id = row[0]
        print(f"sumo lemma already exists with id {sumo_id}")
    else:
        # Create sumo lemma
        c.execute("""
            INSERT INTO lemmas (lemma, pos, meaning) 
            VALUES ('sumo', 'Verb', 'take up; begin; suppose, assume; select; purchase; exact (punishment); obtain;')
        """)
        sumo_id = c.lastrowid
        print(f"Created sumo lemma with id {sumo_id}")
    
    # Step 2: Move sumo forms from sum lemma to sumo lemma
    # sumo forms start with "sum" and are NOT in our SUM_FORMS list
    sum_form_set = {f[0] for f in SUM_FORMS}
    
    c.execute("SELECT form, morphology FROM forms WHERE lemma_id = ?", (SUM_LEMMA_ID,))
    existing = c.fetchall()
    
    moved = 0
    for form, morph in existing:
        if form not in sum_form_set:
            # This is a sumo form, move it
            c.execute("INSERT INTO forms (form, lemma_id, morphology) VALUES (?, ?, ?)",
                      (form, sumo_id, morph))
            c.execute("DELETE FROM forms WHERE form = ? AND lemma_id = ? AND morphology = ?",
                      (form, SUM_LEMMA_ID, morph))
            moved += 1
    
    print(f"Moved {moved} sumo forms to lemma sumo (id={sumo_id})")
    
    # Step 3: Insert correct sum (to be) forms
    inserted = 0
    for form, morph in SUM_FORMS:
        # Check if already exists
        c.execute("SELECT COUNT(*) FROM forms WHERE form = ? AND lemma_id = ? AND morphology = ?",
                  (form, SUM_LEMMA_ID, morph))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO forms (form, lemma_id, morphology) VALUES (?, ?, ?)",
                      (form, SUM_LEMMA_ID, morph))
            inserted += 1
    
    print(f"Inserted {inserted} sum (to be) forms")
    
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
