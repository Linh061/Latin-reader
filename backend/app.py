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
from engine.ocr import ocr_image, ocr_image_with_analysis
from engine.pdf_ocr import get_pdf_processor
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


@app.route("/api/pdf/<pdf_id>/status", methods=["GET"])
def pdf_status(pdf_id: str):
    """Get OCR processing status for a PDF."""
    try:
        proc = get_pdf_processor()
        return jsonify(proc.get_status(pdf_id))
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
