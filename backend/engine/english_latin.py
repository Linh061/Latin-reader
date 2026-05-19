"""
English → Latin dictionary lookup using Smith & Hall (1871) XDXF file.

Parses the XDXF XML and builds a fast lookup index (JSON).
Supports prefix search for autocomplete-style English→Latin queries.
"""
import os
import re
import json
import logging
import unicodedata
import xml.etree.ElementTree as ET
from typing import List, Dict

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XDXF_PATH = os.path.join(BASE, "latin-dictionary", "SmithHall1871", "dict.xdxf")
INDEX_PATH = os.path.join(BASE, "cache", "english_latin_index.json")


def _parse_xdxf() -> Dict[str, str]:
    """Parse the XDXF file and return {english_headword: latin_definition}."""
    if not os.path.exists(XDXF_PATH):
        logger.error("XDXF file not found: %s", XDXF_PATH)
        return {}

    logger.info("Parsing XDXF: %s", XDXF_PATH)
    entries = {}

    try:
        tree = ET.parse(XDXF_PATH)
        root = tree.getroot()
        # XDXF namespace
        ns = {"x": "https://raw.github.com/soshial/xdxf_makedict/master/format_standard/xdxf_strict.dtd"}

        for ar in root.findall(".//ar"):
            k_elem = ar.find("k")
            if k_elem is None or not k_elem.text:
                continue

            # Get headword (English word)
            headword = k_elem.text.strip().lower()

            # Get definition text
            def_elem = ar.find("def")
            if def_elem is None:
                continue

            # Extract all text from definition, stripping XML tags
            def_text = "".join(def_elem.itertext()).strip()
            # Clean up whitespace
            def_text = re.sub(r'\s+', ' ', def_text)

            if headword and def_text:
                entries[headword] = def_text

    except ET.ParseError as e:
        logger.error("XML parse error: %s", e)
        # Fallback: try regex parsing
        return _parse_xdxf_regex()

    logger.info("Parsed %d entries from XDXF", len(entries))
    return entries


def _parse_xdxf_regex() -> Dict[str, str]:
    """Fallback: parse XDXF using regex if XML parser fails."""
    entries = {}
    with open(XDXF_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Match <ar><k>word</k>...<def>...</def></ar>
    pattern = re.compile(r'<ar>.*?<k>(.*?)</k>.*?<def>(.*?)</def>.*?</ar>', re.DOTALL)
    for match in pattern.finditer(content):
        headword = match.group(1).strip().lower()
        def_text = re.sub(r'<[^>]+>', '', match.group(2))
        def_text = re.sub(r'\s+', ' ', def_text).strip()
        if headword and def_text:
            entries[headword] = def_text

    logger.info("Regex fallback parsed %d entries", len(entries))
    return entries


def _build_index(entries: Dict[str, str]):
    """Build and save the JSON index."""
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    logger.info("Index saved to %s (%d entries)", INDEX_PATH, len(entries))


def _load_index() -> Dict[str, str]:
    """Load the JSON index, rebuild if missing."""
    if not os.path.exists(INDEX_PATH):
        logger.info("Index not found, rebuilding from XDXF...")
        entries = _parse_xdxf()
        if entries:
            _build_index(entries)
        return entries

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(s: str) -> str:
    """
    Normalize a string by:
    1. Decomposing Unicode (NFD) to separate base chars from combining marks
    2. Removing combining diacritical marks (accents, umlauts, etc.)
    3. Lowercasing
    This makes "cafe" match "café", "naive" match "naïve", etc.
    """
    nfkd = unicodedata.normalize('NFKD', s)
    # Remove combining diacritical marks (category Mn = Mark, Nonspacing)
    no_accents = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    return no_accents.lower()


def lookup(english_word: str, max_results: int = 30) -> List[Dict]:
    """
    Look up an English word in the Smith & Hall dictionary.

    Returns [{english, latin_definition}, ...] matching the query.
    Supports prefix matching (e.g. "aband" → "abandon", "abandoned", etc.)
    Handles Unicode normalization so "cafe" matches "café", etc.
    """
    word = _normalize(english_word)
    if not word:
        return []

    index = _load_index()
    results = []

    # Build a normalized lookup map: {normalized_key: original_key}
    # Only compute for keys that actually have diacritics (lazy)
    norm_map: Dict[str, str] = {}

    def _get_norm(orig: str) -> str:
        n = _normalize(orig)
        if n != orig:
            norm_map[n] = orig
        return n

    # 1. Exact match first (try original, then normalized)
    if word in index:
        results.append({
            "english": word,
            "latin_definition": index[word],
        })
    elif word in norm_map or True:
        # Check if any key normalizes to the query
        for eng in index:
            if _get_norm(eng) == word:
                results.append({
                    "english": eng,
                    "latin_definition": index[eng],
                })
                break

    # 2. Prefix match (for autocomplete / partial search)
    for eng, lat in index.items():
        if len(results) >= max_results:
            break
        norm_eng = _get_norm(eng)
        if norm_eng.startswith(word) and norm_eng != word:
            results.append({
                "english": eng,
                "latin_definition": lat,
            })

    return results


def rebuild_index():
    """Force rebuild the index from XDXF."""
    entries = _parse_xdxf()
    if entries:
        _build_index(entries)
    return len(entries)
