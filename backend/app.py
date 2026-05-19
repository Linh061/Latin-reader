"""
Flask backend for Latin Reader.

Provides API endpoints for:
- /api/parse - Lemmatize a Latin word
- /api/dict  - Look up a word in the dictionary
- /api/inflect - Generate inflection table for a lemma
- /api/health - Health check
"""

import os
import re
import sys
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.lemmatizer import get_lemmatizer, lemmatize, fuzzy_search, prefix_search
from engine.dictionary import get_dictionary, lookup, reverse_lookup
from engine.inflection import generate_table
from engine.english_latin import lookup as english_latin_lookup
from engine.ocr import ocr_image, ocr_image_with_analysis
from engine.pdf_ocr import get_pdf_processor
from books import load_book, list_books, search_books, save_book_text, import_book_file, delete_book


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


@app.route("/api/fuzzy", methods=["POST"])
def fuzzy():
    """
    Fuzzy search for a Latin word form.

    Tries exact match first, then phonetic Levenshtein (distance ≤ 2),
    then prefix match.

    Request JSON:
        word: str - The Latin word to search for
        max_distance: int (optional) - Levenshtein distance threshold (default 2)
        max_results: int (optional) - Max results (default 10)

    Returns:
        query: the original query
        exact: list of exact parse results (same as /api/analyze)
        fuzzy: list of fuzzy match candidates {form, lemma, part_of_speech, meaning, distance}
        prefix: list of prefix match candidates {form, lemma, part_of_speech, meaning}
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    max_distance = data.get("max_distance", 2)
    max_results = data.get("max_results", 10)

    try:
        # 1. Exact match
        exact = lemmatize(word)

        # 2. Fuzzy (phonetic Levenshtein)
        fuzzy = fuzzy_search(word, max_distance, max_results) if not exact else []

        # 3. Prefix match
        prefix = prefix_search(word, max_results) if not exact and not fuzzy else []

        return jsonify({
            "query": word,
            "exact": exact,
            "fuzzy": fuzzy,
            "prefix": prefix,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reverse", methods=["POST"])
def reverse_dict():
    """
    English → Latin reverse lookup.

    Searches lemmas by English meaning (LIKE match).

    Request JSON:
        word: str - The English word to search for
        max_results: int (optional) - Max results (default 30)

    Returns:
        query: the original English query
        results: list of {key, part_of_speech, meaning}
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    max_results = data.get("max_results", 30)

    try:
        results = reverse_lookup(word, max_results)
        return jsonify({
            "query": word,
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/english-latin", methods=["POST"])
def english_latin():
    """
    English → Latin dictionary lookup.

    Combines results from:
    1. Smith & Hall (1871) — dedicated English→Latin dictionary
    2. Whitaker's Words — reverse lookup via English meaning LIKE match

    Request JSON:
        word: str - The English word to search for
        max_results: int (optional) - Max results (default 30)

    Returns:
        query: the original English query
        results: list of {english, latin_definition, source}
        count: number of results
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    max_results = data.get("max_results", 30)

    try:
        # 1. Smith & Hall results
        sh_results = english_latin_lookup(word, max_results)

        # 2. Whitaker reverse lookup results
        wh_results = reverse_lookup(word, max_results)

        # Merge: Smith & Hall first, then Whitaker (deduplicated by latin key)
        seen_keys: set[str] = set()
        merged = []
        for r in sh_results:
            key = r.get("english", "").lower()
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append({**r, "source": "Smith & Hall 1871"})

        for r in wh_results:
            key = r.get("key", "").lower()
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append({
                    "english": r.get("key", ""),
                    "latin_definition": r.get("meaning", ""),
                    "source": "Whitaker's Words",
                })

        return jsonify({
            "query": word,
            "results": merged[:max_results],
            "count": min(len(merged), max_results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── OCR ─────────────────────────────────────────────────────────────────────

import base64
import tempfile
import uuid


@app.route("/api/ocr", methods=["POST"])
def ocr_recognize():
    """
    Recognize Latin text in an image using Kraken OCR.

    Accepts either:
        - JSON: { "image": "base64-encoded-image-data", "model_type": "print|manuscript" }
        - multipart/form-data with file field "image"

    Returns:
        full_text: Recognized text.
        lines: List of {text, bbox}.
        error: Optional error message.
    """
    image_data = None
    model_type = "print"

    # Try multipart file upload first
    if "image" in request.files:
        file = request.files["image"]
        image_data = file.read()
        model_type = request.form.get("model_type", "print")
    # Then try base64 JSON
    elif request.is_json:
        data = request.get_json()
        if data and "image" in data:
            raw = data["image"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            try:
                image_data = base64.b64decode(raw)
            except Exception:
                return jsonify({"error": "Invalid base64 image data"}), 400
            model_type = data.get("model_type", "print")

    if not image_data:
        return jsonify({"error": "Missing 'image' (file or base64)"}), 400

    tmp_path = os.path.join(tempfile.gettempdir(), f"latin_ocr_{uuid.uuid4().hex}.png")
    try:
        with open(tmp_path, "wb") as f:
            f.write(image_data)

        result = ocr_image(tmp_path, model_type)
        if "error" in result and result["error"] and not result.get("full_text"):
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/api/ocr/analyze", methods=["POST"])
def ocr_analyze():
    """
    Recognize Latin text in an image AND analyze each word.

    Accepts same input as /api/ocr.

    Returns:
        full_text: Recognized text.
        lines: List of {text, bbox}.
        words: List of {word, analyses} from lemmatizer.
        error: Optional error message.
    """
    image_data = None
    model_type = "print"

    if "image" in request.files:
        file = request.files["image"]
        image_data = file.read()
        model_type = request.form.get("model_type", "print")
    elif request.is_json:
        data = request.get_json()
        if data and "image" in data:
            raw = data["image"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            try:
                image_data = base64.b64decode(raw)
            except Exception:
                return jsonify({"error": "Invalid base64 image data"}), 400
            model_type = data.get("model_type", "print")

    if not image_data:
        return jsonify({"error": "Missing 'image' (file or base64)"}), 400

    lang = request.form.get("lang", "en") if not request.is_json else request.get_json().get("lang", "en")

    tmp_path = os.path.join(tempfile.gettempdir(), f"latin_ocr_{uuid.uuid4().hex}.png")
    try:
        with open(tmp_path, "wb") as f:
            f.write(image_data)

        result = ocr_image_with_analysis(tmp_path, lang, model_type)
        if "error" in result and result["error"] and not result.get("full_text"):
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Books ───────────────────────────────────────────────────────────────────


@app.route("/api/books", methods=["GET"])
def books_list():
    """List all available books."""
    try:
        books = list_books()
        return jsonify({"books": books})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/books/upload", methods=["POST"])
def books_upload():
    """
    Upload a Latin book file (HTML or TXT).

    multipart/form-data:
        file: the book file (.html, .htm, or .txt)

    Returns:
        book_id, title, author, chapters count
    """
    if "file" not in request.files:
        return jsonify({"error": "Missing 'file'"}), 400

    file = request.files["file"]
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ('.html', '.htm', '.txt'):
        return jsonify({
            "error": f"Unsupported file type: '{ext}'. Supported: .html, .htm, .txt"
        }), 400

    # Save to a temp location, then import
    import tempfile
    import uuid
    tmp_path = os.path.join(tempfile.gettempdir(), f"book_upload_{uuid.uuid4().hex}{ext}")
    try:
        file.save(tmp_path)
        book = import_book_file(tmp_path)
        return jsonify({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "chapters": len(book.chapters),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to import book: {str(e)}"}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/api/books/<book_id>", methods=["DELETE"])
def book_delete(book_id: str):
    """Delete a book by id (removes cache JSON and source file)."""
    try:
        ok = delete_book(book_id)
        if not ok:
            return jsonify({"error": "Book not found"}), 404
        return jsonify({"success": True, "message": f"Book '{book_id}' deleted"})
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
            # Split paragraphs into smaller lines (sentences/clauses)
            # so each page fits within one screen.
            all_items: list[dict] = []
            for ch in result["chapters"]:
                for para in ch["paragraphs"]:
                    # Split on sentence-ending punctuation, keep delimiter
                    lines = re.split(r'(?<=[.;!?])\s+', para)
                    for line in lines:
                        line = line.strip()
                        if line:
                            all_items.append({
                                "chapter_number": ch["number"],
                                "chapter_title": ch["title"],
                                "text": line,
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


@app.route("/api/books/<book_id>/bookmark", methods=["GET"])
def book_get_bookmarks(book_id: str):
    """Get all bookmarks for a book."""
    try:
        from books import get_bookmarks
        bookmarks = get_bookmarks(book_id)
        return jsonify({"bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/books/<book_id>/bookmark", methods=["PUT"])
def book_add_bookmark(book_id: str):
    """Add a bookmark for a book chapter."""
    data = request.get_json()
    if not data or "chapter" not in data:
        return jsonify({"error": "Missing 'chapter'"}), 400
    try:
        from books import add_bookmark
        label = data.get("label", "")
        bookmarks = add_bookmark(book_id, int(data["chapter"]), label)
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/books/<book_id>/bookmark", methods=["DELETE"])
def book_remove_bookmark(book_id: str):
    """Remove a bookmark for a book chapter."""
    data = request.get_json()
    if not data or "chapter" not in data:
        return jsonify({"error": "Missing 'chapter'"}), 400
    try:
        from books import remove_bookmark
        bookmarks = remove_bookmark(book_id, int(data["chapter"]))
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/books/<book_id>/text", methods=["PUT"])
def book_save_text(book_id: str):
    """
    Save edited text for a specific paragraph in an HTML book.

    Request JSON:
        chapter_number: int - The chapter number
        paragraph_index: int - The paragraph index within the chapter
        text: str - The new text

    Returns:
        success: bool
    """
    data = request.get_json()
    if not data or "text" not in data or "chapter_number" not in data or "paragraph_index" not in data:
        return jsonify({"error": "Missing 'text', 'chapter_number', or 'paragraph_index'"}), 400

    try:
        ok = save_book_text(
            book_id,
            int(data["chapter_number"]),
            int(data["paragraph_index"]),
            data["text"],
        )
        if not ok:
            return jsonify({"error": "Could not save text (book or paragraph not found)"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── PDF OCR ─────────────────────────────────────────────────────────────────


@app.route("/api/pdf/upload", methods=["POST"])
def pdf_upload():
    """
    Upload a PDF for OCR reading.

    multipart/form-data:
        file: the PDF file
        model_type: "print" or "manuscript" (default "print")

    Returns:
        pdf_id, total_pages, title
    """
    if "file" not in request.files:
        return jsonify({"error": "Missing 'file'"}), 400

    file = request.files["file"]
    pdf_bytes = file.read()
    if not pdf_bytes:
        return jsonify({"error": "Empty file"}), 400

    try:
        proc = get_pdf_processor()
        result = proc.upload(pdf_bytes, file.filename or "")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/bookshelf", methods=["GET"])
def pdf_bookshelf():
    """List all uploaded PDFs with cover thumbnails (for bookshelf display)."""
    try:
        proc = get_pdf_processor()
        pdfs = proc.list_pdfs()
        bookshelf = []
        for p in pdfs:
            cover = proc.get_cover_thumbnail(p["pdf_id"])
            bookshelf.append({
                "pdf_id": p["pdf_id"],
                "title": p["title"],
                "total_pages": p["total_pages"],
                "cover_thumb": cover,
            })
        return jsonify({"books": bookshelf})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/list", methods=["GET"])
def pdf_list():
    """List all uploaded PDFs."""
    try:
        proc = get_pdf_processor()
        return jsonify({"pdfs": proc.list_pdfs()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/page/<int:page_num>/ocr", methods=["GET"])
def pdf_page_ocr(pdf_id: str, page_num: int):
    """Poll OCR text for a page (async after get_page returns image)."""
    model_type = request.args.get("model_type", "print")
    try:
        proc = get_pdf_processor()
        result = proc.get_ocr(pdf_id, page_num, model_type)
        if "error" in result:
            return jsonify(result), 404 if "not found" in result.get("error", "") else 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/page/<int:page_num>", methods=["GET"])
def pdf_page(pdf_id: str, page_num: int):
    """
    Get a page from a PDF: rendered image (base64) + display text.

    Display text is user-edited text if saved, or OCR text as fallback.
    OCR runs in background for uncached pages (poll /api/pdf/<id>/page/<n>/ocr).

    Query params:
        model_type: "print" or "manuscript" (default "print")

    Returns:
        page_img (base64), ocr_text, lines, page_num, total_pages, title, cached, user_edited
    """
    model_type = request.args.get("model_type", "print")
    try:
        proc = get_pdf_processor()
        result = proc.get_page_display(pdf_id, page_num, model_type)
        if "error" in result:
            return jsonify(result), 404 if "not found" in result.get("error", "") else 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/page/<int:page_num>/re-ocr", methods=["POST"])
def pdf_page_re_ocr(pdf_id: str, page_num: int):
    """
    Re-run OCR on a page (delete cache + re-OCR synchronously).

    Query params:
        model_type: "print" or "manuscript" (default "print")

    Returns:
        Same as GET /api/pdf/<id>/page/<n>
    """
    model_type = request.args.get("model_type", "print")
    try:
        proc = get_pdf_processor()
        result = proc.re_ocr_page(pdf_id, page_num, model_type)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/page/<int:page_num>/text", methods=["PUT"])
def pdf_page_save_text(pdf_id: str, page_num: int):
    """
    Save user-edited text for a page. Permanent storage.

    Request JSON:
        text: str - The edited Latin text

    Returns:
        success: bool, saved_at: int (unix timestamp)
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in request body"}), 400
    try:
        proc = get_pdf_processor()
        result = proc.save_page_text(pdf_id, page_num, data["text"])
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/analyze/<int:page_num>", methods=["POST"])
def pdf_analyze_word(pdf_id: str, page_num: int):
    """
    Analyze a specific word on a PDF page.

    Request JSON:
        word: str - The Latin word to analyze

    Returns:
        Same as /api/analyze
    """
    data = request.get_json()
    if not data or "word" not in data:
        return jsonify({"error": "Missing 'word'"}), 400

    word = data["word"].strip()
    if not word:
        return jsonify({"error": "Empty word"}), 400

    try:
        from engine.lemmatizer import lemmatize
        from engine.dictionary import lookup

        parse_results = lemmatize(word)
        dict_results = {}
        for pr in parse_results:
            lk = pr.get("lemma", "")
            if lk and lk not in dict_results:
                dict_results[lk] = lookup(lk)

        return jsonify({"word": word, "parses": parse_results, "dictionary": dict_results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>", methods=["DELETE"])
def pdf_delete(pdf_id: str):
    """Delete a PDF and its cache."""
    try:
        proc = get_pdf_processor()
        result = proc.delete_pdf(pdf_id)
        if "error" in result:
            return jsonify(result), 404 if "not found" in result.get("error", "") else 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/bookmark", methods=["GET"])
def pdf_get_bookmarks(pdf_id: str):
    """Get all bookmarks for a PDF."""
    try:
        proc = get_pdf_processor()
        bookmarks = proc.get_bookmarks(pdf_id)
        return jsonify({"bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/bookmark", methods=["PUT"])
def pdf_add_bookmark(pdf_id: str):
    """Add a bookmark for a PDF page."""
    data = request.get_json()
    if not data or "page" not in data:
        return jsonify({"error": "Missing 'page'"}), 400
    try:
        proc = get_pdf_processor()
        label = data.get("label", "")
        result = proc.add_bookmark(pdf_id, int(data["page"]), label)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/bookmark", methods=["DELETE"])
def pdf_remove_bookmark(pdf_id: str):
    """Remove a bookmark for a PDF page."""
    data = request.get_json()
    if not data or "page" not in data:
        return jsonify({"error": "Missing 'page'"}), 400
    try:
        proc = get_pdf_processor()
        result = proc.remove_bookmark(pdf_id, int(data["page"]))
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<pdf_id>/status", methods=["GET"])
def pdf_status(pdf_id: str):
    """Get OCR processing status for a PDF."""
    try:
        proc = get_pdf_processor()
        return jsonify(proc.get_status(pdf_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Vocabulary (生词本) ─────────────────────────────────────────────────────

VOCAB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'cache', 'vocab.json')


def _load_vocab() -> list:
    """Load vocabulary list from JSON file."""
    if not os.path.exists(VOCAB_FILE):
        return []
    try:
        with open(VOCAB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_vocab(vocab: list):
    """Save vocabulary list to JSON file."""
    os.makedirs(os.path.dirname(VOCAB_FILE), exist_ok=True)
    with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)


@app.route("/api/vocab", methods=["GET"])
def vocab_list():
    """Get all saved vocabulary entries, sorted by added_at descending."""
    try:
        vocab = _load_vocab()
        # Sort by added_at descending (newest first)
        vocab.sort(key=lambda v: v.get("added_at", ""), reverse=True)
        return jsonify({"vocab": vocab, "count": len(vocab)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vocab", methods=["POST"])
def vocab_add():
    """Add a word to vocabulary.

    Request JSON:
        lemma: str - The dictionary lemma (stem)
        lemma_form: str - The original word form as clicked by user
        pos: str - Part of speech
        meaning: str - Translation/meaning
    """
    data = request.get_json()
    if not data or "lemma" not in data:
        return jsonify({"error": "Missing 'lemma' parameter"}), 400

    lemma = data["lemma"].strip()
    if not lemma:
        return jsonify({"error": "Empty lemma"}), 400

    try:
        vocab = _load_vocab()
        # Check if already exists
        for entry in vocab:
            if entry["lemma"] == lemma:
                return jsonify({"message": "Already in vocabulary", "vocab": vocab, "count": len(vocab)})

        from datetime import datetime, timezone
        vocab.append({
            "lemma": lemma,
            "lemma_form": data.get("lemma_form", lemma),
            "pos": data.get("pos", ""),
            "meaning": data.get("meaning", ""),
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        _save_vocab(vocab)
        return jsonify({"message": "Added", "vocab": vocab, "count": len(vocab)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vocab/<lemma>", methods=["DELETE"])
def vocab_remove(lemma: str):
    """Remove a word from vocabulary."""
    try:
        vocab = _load_vocab()
        vocab = [e for e in vocab if e["lemma"] != lemma]
        _save_vocab(vocab)
        return jsonify({"message": "Removed", "vocab": vocab, "count": len(vocab)})
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
    
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
