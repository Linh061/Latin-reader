"""
Book importer for Project Gutenberg Latin texts.

Parses PG HTML files and makes them available as structured JSON.
Supports auto-scanning of a books data directory.
"""
import os
import json
import html
import re
from html.parser import HTMLParser
import shutil
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

# ── Paths ───────────────────────────────────────────────────────────────────

BOOKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")

os.makedirs(BOOKS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


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
BRACKET_CHAPTER = re.compile(r'\<a\s+[^>]*name="[^"]*"[^>]*\>.*?\</a\>\s*\[(\d+)\]')


def _strip_html(html_text: str) -> str:
    """Strip HTML tags, decode entities, normalize whitespace."""
    text = re.sub(r'<[^>]+>', '', html_text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _clean_html_for_display(html_text: str) -> str:
    """
    Clean HTML for display: keep safe inline tags (b, i, u, a, em, strong),
    strip everything else, decode entities, normalize whitespace.
    """
    # First, strip all tags except whitelisted inline ones
    # Use a callback to decide per tag
    def _replace_tag(m):
        tag = m.group(0)
        # Keep whitelisted tags
        if re.match(r'</?(b|i|u|a|em|strong|span|br)(\s[^>]*)?>', tag, re.IGNORECASE):
            return tag
        # Strip everything else
        return ''
    text = re.sub(r'<[^>]+>', _replace_tag, html_text)
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


def _book_id_from_filename(filepath: str) -> str:
    """Generate a book ID from the filename (without extension)."""
    base = os.path.splitext(os.path.basename(filepath))[0]
    # Sanitize: lowercase, replace non-alphanumeric with hyphens
    safe = re.sub(r'[^a-zA-Z0-9]+', '-', base).strip('-').lower()
    return safe or "unknown"


def process_book_file(filepath: str) -> Book:
    """Parse a PG HTML file and return a structured Book object."""
    book_id = _book_id_from_filename(filepath)
    title = _find_book_title_in_html(filepath)
    author = _find_book_author_in_html(filepath)
    sections = parse_pg_html(filepath)

    book = Book(
        id=book_id,
        title=title,
        author=author,
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


# ── Auto-scan books directory ──────────────────────────────────────────────

def _find_book_title_in_txt(filepath: str) -> str:
    """Extract a title from a text file (first meaningful line)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    return _guess_title_from_txt(lines)


def _find_book_author_in_txt(filepath: str) -> str:
    """Extract author from a text file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    return _guess_author_from_txt(lines)


def _scan_cache_dir() -> List[Dict]:
    """
    Scan CACHE_DIR for book_*.json files and return metadata for each.
    These are books that were previously imported but whose source files
    may have been removed.
    """
    found = []
    if not os.path.exists(CACHE_DIR):
        return found

    for fname in sorted(os.listdir(CACHE_DIR)):
        if not fname.startswith('book_') or not fname.endswith('.json'):
            continue
        filepath = os.path.join(CACHE_DIR, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            found.append({
                "id": data.get("id", ""),
                "title": data.get("title", fname),
                "author": data.get("author", "Unknown"),
                "file": filepath,
                "_source": "cache",
            })
        except Exception:
            continue
    return found


def scan_books_dir() -> List[Dict]:
    """
    Scan BOOKS_DIR for HTML/TXT files AND CACHE_DIR for cached book JSONs,
    returning metadata for each unique book.
    """
    seen_ids: set = set()
    found: List[Dict] = []

    # 1. Scan source files in BOOKS_DIR
    if os.path.exists(BOOKS_DIR):
        for fname in sorted(os.listdir(BOOKS_DIR)):
            ext = fname.lower()
            if not (ext.endswith('.html') or ext.endswith('.htm') or ext.endswith('.txt')):
                continue
            filepath = os.path.join(BOOKS_DIR, fname)
            book_id = _book_id_from_filename(filepath)

            if ext.endswith('.txt'):
                title = _find_book_title_in_txt(filepath)
                author = _find_book_author_in_txt(filepath)
            else:
                title = _find_book_title_in_html(filepath)
                author = _find_book_author_in_html(filepath)

            seen_ids.add(book_id)
            found.append({
                "id": book_id,
                "title": title,
                "author": author,
                "file": filepath,
            })

    # 2. Also scan cache for books not already found
    for cached in _scan_cache_dir():
        if cached["id"] not in seen_ids:
            seen_ids.add(cached["id"])
            found.append(cached)

    return found


# ── Cache ───────────────────────────────────────────────────────────────────

def _cache_path(book_id: str) -> str:
    return os.path.join(CACHE_DIR, f"book_{book_id}.json")


def _bookmark_path(book_id: str) -> str:
    return _cache_path(book_id) + ".bookmark"


def get_bookmarks(book_id: str) -> list:
    """Get all bookmarks for a book. Returns list of {chapter, label}."""
    bpath = _bookmark_path(book_id)
    if os.path.exists(bpath):
        try:
            with open(bpath, 'r') as f:
                data = json.load(f)
            # Support both old format (int) and new format (list)
            if isinstance(data, dict) and "bookmarks" in data:
                return data["bookmarks"]
            if isinstance(data, dict) and "chapter" in data:
                return [{"chapter": data["chapter"], "label": f"Chapter {data['chapter']}"}]
        except Exception:
            pass
    return []


def add_bookmark(book_id: str, chapter: int, label: str = "") -> list:
    """Add a bookmark for a book chapter. Returns updated bookmark list."""
    bookmarks = get_bookmarks(book_id)
    # Avoid duplicates
    bookmarks = [b for b in bookmarks if b.get("chapter") != chapter]
    bookmarks.append({"chapter": chapter, "label": label or f"Chapter {chapter}"})
    bpath = _bookmark_path(book_id)
    with open(bpath, 'w') as f:
        json.dump({"bookmarks": bookmarks}, f)
    return bookmarks


def remove_bookmark(book_id: str, chapter: int) -> list:
    """Remove a bookmark for a book chapter. Returns updated bookmark list."""
    bookmarks = get_bookmarks(book_id)
    bookmarks = [b for b in bookmarks if b.get("chapter") != chapter]
    bpath = _bookmark_path(book_id)
    with open(bpath, 'w') as f:
        json.dump({"bookmarks": bookmarks}, f)
    return bookmarks


def load_book(book_id: str, force_reload: bool = False) -> Optional[Book]:
    """Load a book, using cache if available."""
    cache_path = _cache_path(book_id)

    if not force_reload and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # If cache has no chapters, it's stale — delete and re-parse
        if not data.get("chapters"):
            os.remove(cache_path)
            return load_book(book_id, force_reload=True)
        book = Book(id=data["id"], title=data["title"], author=data["author"])
        for ch in data.get("chapters", []):
            chapter = Chapter(number=ch["number"], title=ch["title"])
            for p in ch.get("paragraphs", []):
                chapter.paragraphs.append(Paragraph(text=p))
            book.chapters.append(chapter)
        return book

    # Find the file in BOOKS_DIR
    filepath = None
    for fname in os.listdir(BOOKS_DIR):
        if _book_id_from_filename(os.path.join(BOOKS_DIR, fname)) == book_id:
            filepath = os.path.join(BOOKS_DIR, fname)
            break

    if not filepath:
        return None

    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.txt':
            book = process_txt_file(filepath)
        else:
            try:
                book = process_book_file(filepath)
                # If PG parser returned 0 chapters, it's not a PG-style file
                if not book.chapters:
                    book = process_html_file(filepath)
            except (ValueError, Exception):
                book = process_html_file(filepath)
        # Cache it
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(book.to_dict(), f, ensure_ascii=False, indent=2)
        return book
    except Exception as e:
        raise RuntimeError(f"Failed to load book {book_id}: {e}")


def delete_book(book_id: str) -> bool:
    """
    Delete a book by removing its cache JSON and source file.
    Returns True if anything was deleted, False if the book didn't exist.
    """
    deleted = False

    # Remove cache file
    cache_path = _cache_path(book_id)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        deleted = True

    # Remove source file from BOOKS_DIR
    if os.path.exists(BOOKS_DIR):
        for fname in os.listdir(BOOKS_DIR):
            if _book_id_from_filename(os.path.join(BOOKS_DIR, fname)) == book_id:
                os.remove(os.path.join(BOOKS_DIR, fname))
                deleted = True
                break

    return deleted


def save_book_text(book_id: str, chapter_number: int, paragraph_index: int, new_text: str) -> bool:
    """
    Save edited text for a specific paragraph in a book.
    Updates both the cache file and returns success.
    Uses atomic write (temp file + rename) to prevent corruption on crash.
    """
    cache_path = _cache_path(book_id)
    if not os.path.exists(cache_path):
        return False

    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for ch in data.get("chapters", []):
        if ch["number"] == chapter_number:
            if 0 <= paragraph_index < len(ch["paragraphs"]):
                ch["paragraphs"][paragraph_index] = new_text
                # Atomic write: write to temp file, then rename
                tmp_path = cache_path + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, cache_path)
                return True
    return False



def list_books() -> List[Dict]:
    """
    Return metadata for all available books.

    Reads from:
      1. CACHE_DIR/book_*.json (previously imported/cached books)
      2. BOOKS_DIR/*.html/.htm/.txt (source files not yet cached)
    """
    seen_ids: set = set()
    result: List[Dict] = []

    # 1. Read cached books (fast: just read JSON metadata)
    if os.path.exists(CACHE_DIR):
        for fname in sorted(os.listdir(CACHE_DIR)):
            if not fname.startswith('book_') or not fname.endswith('.json'):
                continue
            fpath = os.path.join(CACHE_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                bid = data.get("id", "")
                if bid and bid not in seen_ids:
                    seen_ids.add(bid)
                    result.append({
                        "id": bid,
                        "title": data.get("title", fname),
                        "author": data.get("author", "Unknown"),
                        "book_count": 1,
                    })
            except Exception:
                continue

    # 2. Scan source files in BOOKS_DIR (for books not yet cached)
    if os.path.exists(BOOKS_DIR):
        for fname in sorted(os.listdir(BOOKS_DIR)):
            ext = fname.lower()
            if not (ext.endswith('.html') or ext.endswith('.htm') or ext.endswith('.txt')):
                continue
            filepath = os.path.join(BOOKS_DIR, fname)
            book_id = _book_id_from_filename(filepath)
            if book_id in seen_ids:
                continue
            seen_ids.add(book_id)
            if ext.endswith('.txt'):
                title = _find_book_title_in_txt(filepath)
                author = _find_book_author_in_txt(filepath)
            else:
                title = _find_book_title_in_html(filepath)
                author = _find_book_author_in_html(filepath)
            result.append({
                "id": book_id,
                "title": title,
                "author": author,
                "book_count": 1,
            })

    return result


# ── TXT file parser ─────────────────────────────────────────────────────────

def _guess_title_from_txt(lines: List[str]) -> str:
    """Guess a book title from the first few non-empty lines of a text file."""
    for line in lines[:20]:
        line = line.strip()
        if line and len(line) > 3 and len(line) < 100:
            return line
    return "Untitled Latin Text"


def _guess_author_from_txt(lines: List[str]) -> str:
    """Guess author from text — look for common patterns."""
    for line in lines[:30]:
        low = line.strip().lower()
        if 'by ' in low or 'author' in low:
            return line.strip()
    return "Unknown"


# Latin chapter heading patterns for .txt files
_TXT_CHAPTER_PATTERNS = [
    re.compile(r'^(LIBER|CAPUT|LECTIO|PARS)\s+[IVXLCDM]+\b', re.IGNORECASE),
    re.compile(r'^(BOOK|CHAPTER|SECTION|PART)\s+\d+\b', re.IGNORECASE),
    re.compile(r'^[IVXLCDM]+\.\s+', re.IGNORECASE),  # "I. De bello gallico"
]


def _is_txt_chapter_heading(line: str) -> bool:
    """Check if a line looks like a chapter heading in a Latin text."""
    stripped = line.strip()
    if not stripped:
        return False
    for pat in _TXT_CHAPTER_PATTERNS:
        if pat.match(stripped):
            return True
    # All-caps short lines (e.g. "COMMENTARIUS PRIMUS")
    if stripped.isupper() and len(stripped) > 5 and len(stripped) < 50:
        return True
    return False


def process_txt_file(filepath: str) -> Book:
    """
    Parse a plain-text Latin file into a structured Book object.

    Chapter detection:
      - Lines matching LIBER/CAPUT/LECTIO/PARS + Roman numeral
      - Lines matching BOOK/CHAPTER/SECTION/PART + number
      - All-caps short lines
    If no chapters found, the whole text becomes one chapter.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    lines = raw.split('\n')
    title = _guess_title_from_txt(lines)
    author = _guess_author_from_txt(lines)
    book_id = _book_id_from_filename(filepath)

    # Split into paragraphs by blank lines
    paragraphs = []
    current_para: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
        else:
            current_para.append(stripped)
    if current_para:
        paragraphs.append(' '.join(current_para))

    # Detect chapters
    chapters: List[Chapter] = []
    current_chapter: Optional[Chapter] = None

    for para in paragraphs:
        if _is_txt_chapter_heading(para):
            # Start a new chapter
            current_chapter = Chapter(
                number=len(chapters) + 1,
                title=para.strip(),
            )
            chapters.append(current_chapter)
        else:
            if current_chapter is None:
                # Before first chapter heading — create a preamble chapter
                current_chapter = Chapter(number=1, title="Text")
                chapters.append(current_chapter)
            current_chapter.paragraphs.append(Paragraph(text=para))

    if not chapters:
        # No chapter headings found — whole text as one chapter
        chapters.append(Chapter(number=1, title="Text"))
        for para in paragraphs:
            chapters[0].paragraphs.append(Paragraph(text=para))

    return Book(id=book_id, title=title, author=author, chapters=chapters)


# ── Generic HTML parser (non-PG) using html.parser ─────────────────────────

class _HtmlBookParser(HTMLParser):
    """
    HTMLParser subclass that extracts chapters and paragraphs from a generic HTML file.

    State machine:
      - in_body: are we inside <body>?
      - in_heading: are we inside <h1>-<h6>?
      - in_para: are we inside <p>?
      - in_td: are we inside <td>?
      - skip_tag: depth counter for <script>/<style> to skip their content
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chapters: List[Chapter] = []
        self._chapter_counter = 0
        self._current_chapter: Optional[Chapter] = None

        self._in_body = False
        self._in_heading = False
        self._heading_level = 0
        self._heading_text = ''
        self._in_para = False
        self._para_text = ''
        self._in_td = False
        self._td_text = ''
        self._skip_tag = 0  # depth for <script>/<style>

        # Collect <td> content for sections without <p> tags
        self._td_paras: List[str] = []
        self._has_p_tag = False

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if self._skip_tag > 0:
            self._skip_tag += 1
            return
        if tag_lower in ('script', 'style'):
            self._skip_tag = 1
            return
        if tag_lower == 'body':
            self._in_body = True
            return
        if not self._in_body:
            return

        if tag_lower in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._in_heading = True
            self._heading_level = int(tag_lower[1])
            self._heading_text = ''
            return
        if tag_lower == 'p':
            self._in_para = True
            self._para_text = ''
            self._has_p_tag = True
            return
        if tag_lower == 'td':
            self._in_td = True
            self._td_text = ''
            return

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if self._skip_tag > 0:
            self._skip_tag -= 1
            return
        if tag_lower == 'body':
            self._in_body = False
            return
        if not self._in_body:
            return

        if tag_lower in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if self._in_heading:
                self._in_heading = False
                title_text = self._heading_text.strip()
                # Skip PG boilerplate headings
                if 'PROJECT GUTENBERG' in title_text.upper():
                    return
                # Skip h5/h6 short/decorative headings (PG sub-titles like "AND", "VOL. II.", "Part I.")
                # But keep legitimate chapter titles like "TARTARY.", "LIBRI XXXII."
                if self._heading_level >= 5:
                    # Very short (≤3 chars) is always decorative
                    if len(title_text) <= 3:
                        return
                    # Single word, all-caps, ≤5 chars is decorative (e.g. "AND")
                    if len(title_text) <= 5 and title_text.isupper() and ' ' not in title_text:
                        return
                    # "Part I.", "Part II.", "VOL. II.", "VOLUME 2" etc. are decorative sub-headings
                    if re.match(r'^(Part|VOL\.?|VOLUME|BOOK|CHAPTER|SECTION)\s+[IVXLCDM\d]+\.?$', title_text, re.IGNORECASE):
                        return
                self._chapter_counter += 1
                self._current_chapter = Chapter(
                    number=self._chapter_counter,
                    title=title_text or f"Chapter {self._chapter_counter}"
                )
                self.chapters.append(self._current_chapter)
                # Reset paragraph tracking for new chapter
                self._td_paras = []
                self._has_p_tag = False
            return
        if tag_lower == 'p':
            if self._in_para:
                self._in_para = False
                text = self._para_text.strip()
                if text and len(text) > 3:
                    self._add_paragraph(text)
            return
        if tag_lower == 'td':
            if self._in_td:
                self._in_td = False
                text = self._td_text.strip()
                if text and len(text) > 3:
                    self._td_paras.append(text)
            return

    def handle_data(self, data):
        if self._skip_tag > 0:
            return
        if not self._in_body:
            return
        if self._in_heading:
            self._heading_text += data
        elif self._in_para:
            self._para_text += data
        elif self._in_td:
            self._td_text += data

    def _add_paragraph(self, text: str):
        """Add a paragraph to the current chapter, creating one if needed."""
        if self._current_chapter is None:
            self._chapter_counter += 1
            self._current_chapter = Chapter(number=self._chapter_counter, title="Text")
            self.chapters.append(self._current_chapter)
        self._current_chapter.paragraphs.append(Paragraph(text=text))

    def finalize(self):
        """
        After parsing, if we have <td> content but no <p> tags were found,
        use <td> content as paragraphs.
        """
        if not self._has_p_tag and self._td_paras:
            for text in self._td_paras:
                self._add_paragraph(text)


def process_html_file(filepath: str) -> Book:
    """
    Parse a generic HTML Latin file into a structured Book object.

    Uses HTMLParser for fast, reliable parsing (no regex backtracking).
    Extracts text from <body>, splits chapters by <h1>-<h6>,
    paragraphs by <p> tags (or <td> if no <p> found).
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    title = _find_book_title_in_html(filepath)
    author = _find_book_author_in_html(filepath)
    book_id = _book_id_from_filename(filepath)

    # Fallback: use filename as title
    if not title or title == os.path.basename(filepath):
        title = _guess_title_from_txt(content.split('\n'))

    parser = _HtmlBookParser()
    try:
        parser.feed(content)
    except Exception:
        pass
    parser.finalize()

    chapters = parser.chapters

    if not chapters:
        # No headings found — whole text as one chapter
        # Extract text from body using a simple approach
        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
        body = body_match.group(1) if body_match else content
        text = _strip_html(body)
        if text:
            chapters.append(Chapter(number=1, title="Text"))
            for para in re.split(r'\n\s*\n|<br\s*/?>', text):
                para = para.strip()
                if para and len(para) > 3:
                    chapters[0].paragraphs.append(Paragraph(text=para))

    return Book(id=book_id, title=title, author=author, chapters=chapters)


# ── Unified import ──────────────────────────────────────────────────────────

def import_book_file(filepath: str) -> Book:
    """
    Import a book file (HTML or TXT) into the books data directory.

    Copies the file to BOOKS_DIR, parses it, caches the result, and returns the Book.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    # Determine parser
    if ext in ('.html', '.htm'):
        # Try PG parser first, fall back to generic HTML parser
        try:
            book = process_book_file(filepath)
            # If PG parser returned 0 chapters, it's not a PG-style file
            if not book.chapters:
                book = process_html_file(filepath)
        except (ValueError, Exception):
            book = process_html_file(filepath)
    elif ext == '.txt':
        book = process_txt_file(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext} (supported: .html, .htm, .txt)")

    # Copy file to BOOKS_DIR if not already there
    dest = os.path.join(BOOKS_DIR, os.path.basename(filepath))
    if os.path.abspath(filepath) != os.path.abspath(dest):
        shutil.copy2(filepath, dest)

    # Cache the parsed book
    cache_path = _cache_path(book.id)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(book.to_dict(), f, ensure_ascii=False, indent=2)

    return book


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

    scanned = scan_books_dir()
    books_to_search = (
        [b for b in scanned if b["id"] == book_id]
        if book_id
        else scanned
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
            for para_idx, para in enumerate(ch.paragraphs):
                text_lower = para.text.lower()
                idx = text_lower.find(query_lower)
                if idx != -1:
                    results.append({
                        "book_id": book.id,
                        "book_title": book.title,
                        "chapter_number": ch.number,
                        "chapter_title": ch.title,
                        "paragraph_index": para_idx,
                        "text": para.text,
                        "match_index": idx,
                    })

    return results
