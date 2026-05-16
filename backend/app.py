"""
Flask backend for Latin Reader.

Provides API endpoints for:
- /api/parse - Lemmatize a Latin word
- /api/dict  - Look up a word in the dictionary
- /api/inflect - Generate inflection table for a lemma
- /api/health - Health check
"""

import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.lemmatizer import get_lemmatizer, lemmatize
from engine.dictionary import get_dictionary, lookup
from engine.inflection import generate_table
from books import load_book, list_books, search_books

app = Flask(__name__)
CORS(app)


# ── Health ──────────────────────────────────────────────────────────────────


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Latin Reader API is running"})


@app.route("/api/parse", methods=["POST"])
def parse_word():
    """
    Lemmatize a Latin word form.
    
    Request JSON:
        word: str - The Latin word to analyze
        lang: str (optional) - Language for translations (default: "en")
    
    Returns:
        List of possible parses with lemma, morphology, and translations
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    lang = data.get("lang", "en")
    
    try:
        results = lemmatize(word, lang)
        return jsonify({
            "word": word,
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dict", methods=["POST"])
def dict_lookup():
    """
    Look up a word in Whitaker's Words dictionary.
    
    Request JSON:
        key: str - The dictionary key to look up
    
    Returns:
        List of dictionary entries
    """
    data = request.get_json()
    if not data or "key" not in data:
        return jsonify({"error": "Missing 'key' parameter"}), 400

    key = data["key"].strip()
    if not key:
        return jsonify({"error": "Empty key"}), 400

    try:
        results = lookup(key)
        return jsonify({
            "key": key,
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/inflect", methods=["POST"])
def inflect_lemma():
    """
    Generate inflection table for a lemma.
    
    Request JSON:
        lemma: str - The lemma key to generate table for
    
    Returns:
        Inflection table organized by mood/tense/voice or case/number
    """
    data = request.get_json()
    if not data or "lemma" not in data:
        return jsonify({"error": "Missing 'lemma' parameter"}), 400

    lemma_key = data["lemma"].strip()
    if not lemma_key:
        return jsonify({"error": "Empty lemma"}), 400

    try:
        table = generate_table(lemma_key)
        if table is None:
            return jsonify({
                "lemma": lemma_key,
                "error": "Could not generate inflection table",
                "table": None,
            }), 404
        
        return jsonify({
            "lemma": lemma_key,
            "table": table,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze_word():
    """
    Full analysis of a Latin word: parse + dictionary lookup.
    
    Request JSON:
        word: str - The Latin word to analyze
        lang: str (optional) - Language for translations (default: "en")
    
    Returns:
        Combined parse results and dictionary entries
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    lang = data.get("lang", "en")
    
    try:
        # Get parse results
        parse_results = lemmatize(word, lang)
        
        # Get dictionary entries for each unique lemma
        dict_results = {}
        for pr in parse_results:
            lemma_key = pr.get("lemma", "")
            if lemma_key and lemma_key not in dict_results:
                dict_results[lemma_key] = lookup(lemma_key)
        
        return jsonify({
            "word": word,
            "parses": parse_results,
            "dictionary": dict_results,
            "parse_count": len(parse_results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Books ───────────────────────────────────────────────────────────────────


@app.route("/api/books", methods=["GET"])
def books_list():
    """List all available books."""
    try:
        books = list_books()
        return jsonify({"books": books})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/books/<book_id>", methods=["GET"])
def book_content(book_id: str):
    """Get structured content of a book by id, with optional pagination."""
    force = request.args.get("force", "0") == "1"
    try:
        book = load_book(book_id, force_reload=force)
        if book is None:
            return jsonify({"error": "Book not found"}), 404

        result = book.to_dict()

        # Optional pagination by paragraph count
        page = request.args.get("page", type=int, default=1)
        per_page = request.args.get("per_page", type=int, default=0)

        if per_page > 0 and page > 0:
            # Flatten all paragraphs across chapters with chapter context
            all_items: list[dict] = []
            for ch in result["chapters"]:
                for para in ch["paragraphs"]:
                    all_items.append({
                        "chapter_number": ch["number"],
                        "chapter_title": ch["title"],
                        "text": para,
                    })

            total_items = len(all_items)
            total_pages = max(1, (total_items + per_page - 1) // per_page)
            start = (page - 1) * per_page
            end = start + per_page
            page_items = all_items[start:end]

            # Re-group into chapters for the frontend
            re_chapters: dict[int, dict] = {}
            for item in page_items:
                cn = item["chapter_number"]
                if cn not in re_chapters:
                    re_chapters[cn] = {
                        "number": cn,
                        "title": item["chapter_title"],
                        "paragraphs": [],
                    }
                re_chapters[cn]["paragraphs"].append(item["text"])

            result["chapters"] = list(re_chapters.values())
            result["chapters"].sort(key=lambda c: c["number"])
            result["pagination"] = {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Search ──────────────────────────────────────────────────────────────────


@app.route("/api/search", methods=["GET"])
def search():
    """
    Full-text search across books.

    Query params:
        q: str - Search term (required)
        book_id: str (optional) - Limit to one book
        page: int (optional) - Page number, default 1
        per_page: int (optional) - Results per page, default 20

    Returns:
        json with results list and pagination info
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing 'q' parameter"}), 400

    book_id = request.args.get("book_id", None)
    page = request.args.get("page", type=int, default=1)
    per_page = request.args.get("per_page", type=int, default=20)

    try:
        all_results = search_books(query, book_id)

        total = len(all_results)
        total_pages = max(1, (total + per_page - 1) // per_page) if per_page > 0 else 1
        start = (page - 1) * per_page if per_page > 0 else 0
        end = start + per_page if per_page > 0 else total
        page_results = all_results[start:end]

        return jsonify({
            "query": query,
            "book_id": book_id,
            "results": page_results,
            "total_results": total,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Serve frontend (built by Vite) ──────────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', 'frontend', 'dist')


@app.route("/assets/<path:filename>")
def frontend_assets(filename):
    """Serve built frontend assets (JS/CSS)."""
    return send_from_directory(os.path.join(FRONTEND_DIST, 'assets'), filename)


@app.route("/")
def frontend_index():
    """Serve the built frontend SPA."""
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.errorhandler(404)
def catch_all(e):
    """Fallback for SPA: serve index.html for any unrecognized non-API path."""
    if not request.path.startswith('/api/'):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    # Pre-load engines on startup
    print("Loading Latin lemmatizer...")
    get_lemmatizer()
    print("Loading dictionary...")
    get_dictionary()
    print("Ready!")
    
    app.run(host="127.0.0.1", port=5000, debug=True)
