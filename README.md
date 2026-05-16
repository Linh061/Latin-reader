# Latin Reader

A web-based Latin reading tool powered by [Whitaker's Words](https://github.com/mk270/whitakers-words). Load Project Gutenberg Latin texts, click any word to see its grammatical analysis, dictionary definition, and full inflection table.

## Features

- **Interactive Reader** — Project Gutenberg Latin books rendered in a medieval-parchment style interface. Click any word to analyze it.
- **Grammatical Analysis** — Part-of-speech, lemma, morphology, and translation for every word form.
- **Dictionary Lookup** — Full Whitaker's Words dictionary entries for every lemma.
- **Inflection Tables** — Complete declension / conjugation tables for any identified lemma.
- **Full-Text Search** — Search across all books for a word or phrase; results with context snippets and highlighted matches.
- **Pagination** — Large books split into pages of 30 paragraphs each.
- **Dark Academia UI** — Parchment-toned background, drop caps, ornamental dividers, serif typography.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Frontend | React, TypeScript, Vite |
| Latin Engine | [Whitaker's Words](https://github.com/mk270/whitakers-words) (Ada, compiled to SQLite) |
| Book Source | [Project Gutenberg](https://www.gutenberg.org/) |

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm 9+

### 1. Set up the backend

```bash
cd backend
pip install -r requirements.txt
python3 app.py
```

The server starts at `http://127.0.0.1:5000`. It pre-loads the Latin lemmatizer and dictionary on startup (takes a few seconds).

### 2. (Optional) Rebuild the frontend

If you modify any TypeScript code, rebuild the static files:

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
| `/api/search?q=&page=&per_page=` | GET | Full-text search across books |

## Project Structure

```
Latin-reader/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt
│   ├── books/
│   │   ├── __init__.py        # PG HTML parser, book cache, search
│   │   └── data/              # PG HTML source files
│   │       ├── pg218-images.html      # Caesar, Gallic War I-IV
│   │       └── pg18837-images.html    # Caesar, Gallic War V-VIII
│   ├── cache/                 # Cached book JSON files
│   ├── data/                  # Whitaker's Words dictionary data
│   └── engine/
│       ├── lemmatizer.py      # Latin lemmatization
│       ├── dictionary.py      # Dictionary lookup
│       └── inflection.py      # Inflection table generation
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main React application
│   │   ├── main.tsx           # Entry point
│   │   ├── hooks/useApi.ts    # API helper
│   │   └── types/latin.ts     # TypeScript type definitions
│   └── dist/                  # Built static files (served by Flask)
├── whitakers-words/           # Whitaker's Words source (Ada)
└── electron/                  # Optional Electron shell
```

## How It Works

1. **Book import:** `books/__init__.py` parses each Project Gutenberg HTML file into chapters and paragraphs. The result is cached as JSON in `backend/cache/`.
2. **Analysis:** When you click a word, the frontend sends it to `/api/analyze`. The backend calls the Whitaker's Words engine to lemmatize the form, then looks up the lemma in the dictionary.
3. **Inflection:** Clicking "Declina …" sends the lemma back to `/api/inflect`, which generates a complete declension or conjugation table.
4. **Search:** `/api/search` does a case-insensitive substring match across all cached book paragraphs.

## Adding Your Own Books

1. Download a Latin text from Project Gutenberg in "HTML" format.
2. Place the `.html` file in `backend/books/data/`.
3. Add a new entry to `BOOKS_CONFIG` in `backend/books/__init__.py`.
4. Restart the server.

The parser recognizes `<h2>` chapter headings (e.g., `COMMENTARIUS PRIMUS`) and `<p>Liber V</p>` markers.

## Credits

- [Whitaker's Words](https://github.com/mk270/whitakers-words) — the engine behind all Latin analysis, ported from the original Ada code by William Whitaker.
- [Project Gutenberg](https://www.gutenberg.org/) — source of the Latin texts.