# Latin Reader

A web-based Latin reading tool powered by [Whitaker's Words](https://github.com/mk270/whitakers-words). Read Project Gutenberg Latin texts or upload PDFs, click any word to see its grammatical analysis and dictionary definition.

## Features

- **Interactive Reader** — Project Gutenberg Latin books in a parchment-style interface. Click any word to analyze.
- **PDF Reader** — Upload PDFs of Latin texts; Kraken OCR with automatic word analysis. Page-by-page image + text view.
- **Grammatical Analysis** — Part-of-speech, lemma, morphology, and translation for every word form.
- **Dictionary Lookup** — Full Whitaker's Words dictionary entries for every lemma.
- **Inflection Tables** — Complete declension / conjugation tables for any identified lemma.
- **Full-Text Search** — Search across all books; results with context snippets and highlighted matches.
- **Dark Academia UI** — Parchment-toned background, serif typography, ornamental details.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Frontend | React, TypeScript, Vite |
| Latin Engine | [Whitaker's Words](https://github.com/mk270/whitakers-words) (Ada, compiled to SQLite) |
| OCR | Kraken (CLI) |
| Book Source | [Project Gutenberg](https://www.gutenberg.org/) |

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm 9+
- [Kraken](https://github.com/mittagessen/kraken) CLI installed (`pip install kraken`)

### 1. Set up the backend

```bash
cd backend
pip install -r requirements.txt
python3 app.py
```

The server starts at `http://127.0.0.1:5000`. It pre-loads the Latin lemmatizer and dictionary on startup.

### 2. (Optional) Rebuild the frontend

```bash
cd frontend
npm install
npx vite build
```

Then restart the Flask server.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/books` | GET | List available books |
| `/api/books/<id>?page=&per_page=` | GET | Book content with optional pagination |
| `/api/analyze` | POST | Full analysis: parse + dictionary lookup |
| `/api/parse` | POST | Lemmatize a word form |
| `/api/dict` | POST | Look up a dictionary entry |
| `/api/inflect` | POST | Generate inflection table for a lemma |
| `/api/search?q=` | GET | Full-text search across books |
| `/api/ocr` | POST | Recognize Latin text from an uploaded image |
| `/api/ocr/analyze` | POST | Recognize + word-by-word analysis |
| `/api/pdf/upload` | POST | Upload a PDF for OCR reading |
| `/api/pdf/bookshelf` | GET | List uploaded PDFs with cover thumbnails |
| `/api/pdf/<id>/page/<n>` | GET | Get rendered page image + text |
| `/api/pdf/<id>/page/<n>/ocr` | GET | Poll OCR text for a page |
| `/api/pdf/<id>/page/<n>/text` | PUT | Save user-edited text |
| `/api/pdf/<id>/analyze/<n>` | POST | Analyze a word on a PDF page |
| `/api/pdf/<id>` | DELETE | Delete a PDF and its cache |

## Project Structure

```
Latin-reader/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt
│   ├── books/
│   │   ├── __init__.py        # PG HTML parser, book cache, search
│   │   └── data/              # PG HTML source files
│   ├── cache/                 # Cached book JSON + Whitaker's Words DB
│   ├── data/                  # Whitaker's Words dictionary data
│   ├── engine/
│   │   ├── lemmatizer.py      # Latin lemmatization
│   │   ├── dictionary.py      # Dictionary lookup
│   │   ├── inflection.py      # Inflection table generation
│   │   ├── ocr.py             # Kraken OCR text recognition
│   │   └── pdf_ocr.py         # PDF upload, rendering, OCR pipeline
│   └── pdf_books/             # Uploaded PDFs + OCR cache (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Root component (route-based)
│   │   ├── main.tsx           # Entry point
│   │   ├── pages/             # Route pages (Home, Reader, OCR, PDFReader)
│   │   └── types/latin.ts     # TypeScript type definitions
│   └── dist/                  # Built static files (served by Flask)
└── .gitignore
```

## How It Works

1. **Book import:** `books/__init__.py` parses Project Gutenberg HTML files into chapters and paragraphs. Cached as JSON.
2. **Analysis:** Click a word → `/api/analyze` → lemmatize → dictionary lookup.
3. **Inflection:** Click "Declina …" → `/api/inflect` → full declension/conjugation table.
4. **PDF OCR:** Upload PDF → render page image → Kraken OCR in background → poll for text → click any word to analyze.
5. **Search:** `/api/search` does case-insensitive substring match across all cached book paragraphs.

## Adding Books

1. Download a Latin text from Project Gutenberg in "HTML" format.
2. Place the `.html` file in `backend/books/data/`.
3. Add a new entry to `BOOKS_CONFIG` in `backend/books/__init__.py`.
4. Restart the server.

## Credits

- [Whitaker's Words](https://github.com/mk270/whitakers-words) — the engine behind all Latin analysis, ported from the original Ada code by William Whitaker.
- [Project Gutenberg](https://www.gutenberg.org/) — source of the Latin texts.
- [Kraken](https://github.com/mittagessen/kraken) — OCR engine for Latin text recognition.
