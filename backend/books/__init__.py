"""
Book importer for Project Gutenberg Latin texts.

Parses PG HTML files and makes them available as structured JSON.
"""
import os
import json
import html
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

# ── Book metadata ───────────────────────────────────────────────────────────

BOOKS_CONFIG: List[Dict] = [
    {
        "id": "bgallico-1-4",
        "title": "C. Iuli Caesaris De Bello Gallico I-IV",
        "author": "Julius Caesar",
        "file": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "pg218-images.html"),
        "book_count": 4,
    },
    {
        "id": "bgallico-5-8",
        "title": "C. Iuli Caesaris De Bello Gallico V-VIII",
        "author": "Julius Caesar",
        "file": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "pg18837-images.html"),
        "book_count": 4,
    },
]

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class Paragraph:
    text: str

@dataclass
class Chapter:
    number: int
    title: str
    paragraphs: List[Paragraph] = field(default_factory=list)

@dataclass
class Book:
    id: str
    title: str
    author: str
    chapters: List[Chapter] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "paragraphs": [p.text for p in c.paragraphs],
                }
                for c in self.chapters
            ],
        }


# ── Parser ──────────────────────────────────────────────────────────────────

# Latin book ordinal regex
BOOK_ORDINAL = re.compile(
    r'(PRIMUS|SECUNDUS|TERTIUS|QUARTUS|QUINTUS|SEXTUS|SEPTIMUS|OCTAVUS|NONUS|DECIMUS)'
)
BOOK_ORDINAL_NUM = {
    'PRIMUS': 1, 'SECUNDUS': 2, 'TERTIUS': 3, 'QUARTUS': 4,
    'QUINTUS': 5, 'SEXTUS': 6, 'SEPTIMUS': 7, 'OCTAVUS': 8,
    'NONUS': 9, 'DECIMUS': 10,
}

CHAPTER_PATTERN = re.compile(
    r'(?:CAPUT|caput)\s+([A-Z]+)',
)
# Also matches: bracketed number like [1], [2] etc — some PG versions use inline numbering
BRACKET_CHAPTER = re.compile(r'\<a\s+[^>]*name="[^"]*"[^>]*\>.*?\</a\>\s*\[(\d+)\]')


def _strip_html(html_text: str) -> str:
    """Strip HTML tags, decode entities, normalize whitespace."""
    text = re.sub(r'<[^>]+>', '', html_text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _is_in_prologue_or_epilogue(text: str) -> bool:
    """Check if a line is part of PG header/footer."""
    low = text.lower()
    if '*** start of the project gutenberg' in low:
        return True
    if '*** end of the project gutenberg' in low:
        return True
    if 'project gutenberg' in low and ('ebook' in low or 'license' in low):
        return True
    return False


def parse_pg_html(filepath: str) -> Dict[str, List[str]]:
    """
    Parse PG Latin HTML into a dict: {"COMMENTARIUS PRIMUS": ["paragraphs..."], ...}

    Returns {chapter_title: [paragraphs]}
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract body content (skip header/footer PG boilerplate)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if not body_match:
        raise ValueError("No <body> found")

    body = body_match.group(1)

    # Remove PG header section
    body = re.sub(
        r'<section class="pg-boilerplate pgheader".*?</section>',
        '',
        body,
        flags=re.DOTALL,
    )
    # Remove PG footer section
    body = re.sub(
        r'<div id="pg-footer".*?</div>',
        '',
        body,
        flags=re.DOTALL,
    )
    # Remove license section
    body = re.sub(
        r'<div id="project-gutenberg-license".*?</div>',
        '',
        body,
        flags=re.DOTALL,
    )
    # Remove remaining full license text
    body = re.sub(
        r'<h2[^>]*>THE FULL PROJECT GUTENBERG.*?</h2>.*?(?=<h2|<div|<section|$)',
        '',
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r'<div id="pg-footer".*',
        '',
        body,
        flags=re.DOTALL,
    )

    # Normalize pg18837-style chapter markers:
    #   <p id="id00000">Liber V</p>  →  <h2>COMMENTARIUS LIBER V</h2>
    def _replace_liber_marker(m):
        num = m.group(1)
        roman_to_latin = {'V': 'QUINTUS', 'VI': 'SEXTUS', 'VII': 'SEPTIMUS', 'VIII': 'OCTAVUS'}
        latin = roman_to_latin.get(num.upper(), num)
        return f'<h2>COMMENTARIUS {latin}</h2>'
    body = re.sub(
        r'<p[^>]*>Liber\s+([IVXL]+)\s*</p>',
        _replace_liber_marker,
        body,
        flags=re.IGNORECASE,
    )

    # Extract h2 sections which are book/chapter titles
    # Pattern: <h2>...</h2> then paragraphs
    sections: Dict[str, List[str]] = {}
    current_section = "Preamble"
    sections[current_section] = []

    # Find all h2 tags and content between them
    parts = re.split(r'(<h2[^>]*>.*?</h2>)', body, flags=re.DOTALL)

    for i, part in enumerate(parts):
        h2_match = re.match(r'<h2[^>]*>(.*?)</h2>', part, re.DOTALL)
        if h2_match:
            title = _strip_html(h2_match.group(1)).strip()
            # Skip boilerplate headings
            if 'Contents' in title or 'PROJECT GUTENBERG' in title.upper() or not title:
                continue
            # Found a new section
            if 'COMMENTARIUS' in title.upper():
                current_section = title
                if current_section not in sections:
                    sections[current_section] = []
        else:
            # This part contains paragraphs
            # Extract all <p> tags
            paras = re.findall(r'<p[^>]*>(.*?)</p>', part, re.DOTALL)
            for para in paras:
                text = _strip_html(para)
                if not text:
                    continue
                if _is_in_prologue_or_epilogue(text):
                    continue
                # Skip single non-Latin lines (table of contents entries, etc.)
                if len(text) < 5:
                    continue
                sections.setdefault(current_section, []).append(text)

    # Remove empty sections and preamble
    result = {k: v for k, v in sections.items() if v and k != "Preamble"}
    return result


def _find_book_title_in_html(filepath: str) -> str:
    """Extract dc.title from HTML meta."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'<meta name="dc\.title"\s+content="([^"]+)"', content)
    return m.group(1) if m else os.path.basename(filepath)


def _find_book_author_in_html(filepath: str) -> str:
    """Extract author from HTML meta."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'<meta name="dc\.creator"\s+content="([^"]+)"', content)
    return m.group(1) if m else "Unknown"


def process_book(book_id: str) -> Book:
    """Parse a PG HTML file and return a structured Book object."""
    config = next((b for b in BOOKS_CONFIG if b["id"] == book_id), None)
    if not config:
        raise ValueError(f"Unknown book id: {book_id}")

    filepath = config["file"]
    sections = parse_pg_html(filepath)

    book = Book(
        id=book_id,
        title=config["title"],
        author=config["author"],
    )

    for i, (section_title, paragraphs) in enumerate(sections.items(), 1):
        # Extract book number from Latin ordinal in title
        ordinal_match = BOOK_ORDINAL.search(section_title.upper())
        book_num = BOOK_ORDINAL_NUM.get(ordinal_match.group(1), i) if ordinal_match else i
        chapter = Chapter(number=book_num, title=section_title)
        for p in paragraphs:
            chapter.paragraphs.append(Paragraph(text=p))
        book.chapters.append(chapter)

    # Sort chapters by number
    book.chapters.sort(key=lambda c: c.number)
    return book


# ── Cache ───────────────────────────────────────────────────────────────────

def _cache_path(book_id: str) -> str:
    return os.path.join(CACHE_DIR, f"book_{book_id}.json")


def load_book(book_id: str, force_reload: bool = False) -> Optional[Book]:
    """Load a book, using cache if available."""
    cache_path = _cache_path(book_id)

    if not force_reload and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        book = Book(id=data["id"], title=data["title"], author=data["author"])
        for ch in data.get("chapters", []):
            chapter = Chapter(number=ch["number"], title=ch["title"])
            for p in ch.get("paragraphs", []):
                chapter.paragraphs.append(Paragraph(text=p))
            book.chapters.append(chapter)
        return book

    try:
        book = process_book(book_id)
        # Cache it
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(book.to_dict(), f, ensure_ascii=False, indent=2)
        return book
    except Exception as e:
        raise RuntimeError(f"Failed to load book {book_id}: {e}")


def list_books() -> List[Dict]:
    """Return metadata for all available books."""
    return [
        {
            "id": b["id"],
            "title": b["title"],
            "author": b["author"],
            "book_count": b["book_count"],
        }
        for b in BOOKS_CONFIG
    ]


def search_books(query: str, book_id: Optional[str] = None) -> List[Dict]:
    """
    Full-text search across book paragraphs (case-insensitive).

    Args:
        query: Search term (plain text, not regex).
        book_id: If given, search only that book; otherwise search all.

    Returns:
        List of result dicts, each with:
          book_id, book_title, chapter_number, chapter_title,
          text (full paragraph), match_index (position in paragraph).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    books_to_search = (
        [b for b in BOOKS_CONFIG if b["id"] == book_id]
        if book_id
        else BOOKS_CONFIG
    )

    results: List[Dict] = []
    for config in books_to_search:
        try:
            book = load_book(config["id"])
        except Exception:
            continue
        if not book:
            continue
        for ch in book.chapters:
            for para in ch.paragraphs:
                text_lower = para.text.lower()
                idx = text_lower.find(query_lower)
                if idx != -1:
                    results.append({
                        "book_id": book.id,
                        "book_title": book.title,
                        "chapter_number": ch.number,
                        "chapter_title": ch.title,
                        "text": para.text,
                        "match_index": idx,
                    })

    return results
