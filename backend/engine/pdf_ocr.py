"""
PDF OCR engine for Latin text recognition.

Pipeline:
  1. Upload PDF -> save to pdf_books/<book_title>/uploads/<pdf_id>.pdf
  2. Request page -> render to image via PyMuPDF, OCR via Kraken CLI
  3. Cache results in pdf_books/<book_title>/cache/ocr_cache.db
  4. Frontend polls for OCR text after image returned immediately

Book-level directory layout:
    pdf_books/
      <book_title>/          # sanitized book title
        uploads/<pdf_id>.pdf
        cache/ocr_cache.db
"""
import os
import re
import json
import hashlib
import logging
import subprocess
import tempfile
import threading
import base64
import sqlite3
import time

from typing import Optional

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdf_books")
os.makedirs(BASE_DIR, exist_ok=True)


def _sanitize_title(title: str) -> str:
    """Sanitize book title for use as a directory name."""
    # Remove file-unsafe characters
    safe = re.sub(r'[\\/*?:"<>|]', '_', title)
    # Collapse whitespace
    safe = re.sub(r'\s+', ' ', safe).strip()
    # Limit length
    if len(safe) > 80:
        safe = safe[:80]
    if not safe:
        safe = "untitled"
    return safe


def _book_dir(title: str) -> str:
    """Get the per-book directory path."""
    safe = _sanitize_title(title)
    return os.path.join(BASE_DIR, safe)


def _ensure_book_dirs(title: str) -> tuple[str, str, str]:
    """Ensure per-book upload/cache dirs exist. Returns (book_dir, upload_dir, cache_db)."""
    bdir = _book_dir(title)
    udir = os.path.join(bdir, "uploads")
    cdir = os.path.join(bdir, "cache")
    os.makedirs(udir, exist_ok=True)
    os.makedirs(cdir, exist_ok=True)
    return bdir, udir, os.path.join(cdir, "ocr_cache.db")


def _init_cache_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ocr_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_meta (
            pdf_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            total_pages INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS page_text (
            page_key TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


# Model filenames (matching ocr.py)
_PRINT_MODEL_RELPATH = "reichenau_lat_cat_099218.mlmodel"
_MANUSCRIPT_MODEL_RELPATH = "bdd-wormser-scriptorium-expanded-0.1.mlmodel"


def _find_model(relpath: str) -> Optional[str]:
    """Find a Kraken model file by searching known data directories."""
    htrmopo = os.path.expanduser("~/.local/share/htrmopo")
    if os.path.isdir(htrmopo):
        for root, dirs, files in os.walk(htrmopo):
            if relpath in files:
                return os.path.join(root, relpath)
    kraken_dir = os.path.expanduser("~/.config/kraken")
    if os.path.isdir(kraken_dir):
        for root, dirs, files in os.walk(kraken_dir):
            if relpath in files:
                return os.path.join(root, relpath)
    return None


def _compress_to_jpeg(pix: "fitz.Pixmap", quality: int = 85) -> bytes:
    """Convert a fitz Pixmap to JPEG bytes, compatible with all PyMuPDF versions.
    
    PyMuPDF < 1.25.3 does not support the `quality` kwarg in tobytes(),
    so we use PIL as a fallback for JPEG compression.
    """
    try:
        # Try direct JPEG output (PyMuPDF >= 1.25.3)
        return pix.tobytes("jpeg", quality=quality)
    except TypeError:
        # Fallback: PNG → PIL → JPEG
        png_bytes = pix.tobytes("png")
        if _HAS_PIL:
            import io
            from PIL import Image as PILImage
            pil_img = PILImage.open(io.BytesIO(png_bytes))
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
        # No PIL available — return PNG (no compression, but works)
        return png_bytes


def _build_kraken_cmd(image_path: str, output_path: str, model_type: str) -> list[str]:
    """Build Kraken CLI command with model path."""
    if model_type == "manuscript":
        model_path = _find_model(_MANUSCRIPT_MODEL_RELPATH)
        if model_path:
            return ["kraken", "-i", image_path, output_path,
                    "binarize", "segment", "ocr", "-m", model_path]
        logger.warning("Manuscript model not found; falling back to print model")

    model_path = _find_model(_PRINT_MODEL_RELPATH)
    if model_path:
        return ["kraken", "-i", image_path, output_path,
                "binarize", "segment", "ocr", "-m", model_path]

    logger.warning("No Kraken model found; attempting default OCR (may fail)")
    return ["kraken", "-i", image_path, output_path, "binarize", "segment", "ocr"]


class PDFProcessor:
    """Manages PDF upload, page rendering, and lazy OCR."""

    def __init__(self):
        self._in_memory: dict[str, dict] = {}
        self._conn_cache: dict[str, sqlite3.Connection] = {}  # db_path -> conn
        self._pdf_cache: dict[str, tuple] = {}  # pdf_id -> (path, total_pages, title, db_path)

    # ── Connection management ──────────────────────────────────────────

    def _get_conn(self, db_path: str) -> sqlite3.Connection:
        """Get or create a SQLite connection for a book's cache DB."""
        if db_path not in self._conn_cache:
            self._conn_cache[db_path] = _init_cache_db(db_path)
        return self._conn_cache[db_path]

    # ── Upload ─────────────────────────────────────────────────────────

    def upload(self, file_bytes: bytes, filename: str = "") -> dict:
        """Save uploaded PDF, return metadata. Creates per-book directories."""
        pdf_id = hashlib.md5(file_bytes).hexdigest()[:12]

        # Determine title from PDF metadata first
        try:
            import fitz
            tmp_path = os.path.join(tempfile.gettempdir(), f"pdf_tmp_{pdf_id}.pdf")
            with open(tmp_path, "wb") as f:
                f.write(file_bytes)
            doc = fitz.open(tmp_path)
            title = doc.metadata.get("title", "") or filename or f"PDF_{pdf_id}"
            total_pages = len(doc)
            doc.close()
            os.unlink(tmp_path)
        except Exception:
            total_pages = 0
            title = filename or f"PDF_{pdf_id}"

        # Create per-book directories
        bdir, udir, db_path = _ensure_book_dirs(title)
        conn = self._get_conn(db_path)

        # Check if already uploaded
        cur = conn.execute("SELECT total_pages FROM pdf_meta WHERE pdf_id = ?", (pdf_id,))
        row = cur.fetchone()
        if row:
            return {"pdf_id": pdf_id, "total_pages": row[0], "title": title}

        # Save PDF
        save_path = os.path.join(udir, f"{pdf_id}.pdf")
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        conn.execute(
            "INSERT OR REPLACE INTO pdf_meta (pdf_id, path, total_pages, title, created_at) VALUES (?, ?, ?, ?, ?)",
            (pdf_id, save_path, total_pages, title, int(time.time())),
        )
        conn.commit()
        return {"pdf_id": pdf_id, "total_pages": total_pages, "title": title}

    # ── Get Page ───────────────────────────────────────────────────────

    def get_page(self, pdf_id: str, page_num: int, model_type: str = "print") -> dict:
        """Get page: return image immediately, OCR runs in background.

        Frontend should poll /api/pdf/<id>/page/<n>/ocr to get OCR text.
        """
        # Find which book this PDF belongs to by scanning all book dirs
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}

        if page_num < 1 or page_num > total_pages:
            return {"error": f"Page {page_num} out of range (1-{total_pages})"}

        cache_key = f"{pdf_id}_p{page_num:04d}_{model_type}"

        # Check memory cache
        if cache_key in self._in_memory:
            data = dict(self._in_memory[cache_key])
            data.update(cached=True, page_num=page_num, total_pages=total_pages, title=title)
            return data

        # Check SQLite cache (OCR text only — page_img is NOT stored in DB)
        conn = self._get_conn(db_path)
        cur = conn.execute("SELECT data FROM ocr_cache WHERE cache_key = ?", (cache_key,))
        cached = cur.fetchone()
        if cached:
            data = json.loads(cached[0])
            # Re-render page image (fast, ~0.1s) since we don't cache images in DB
            try:
                import fitz
                doc = fitz.open(pdf_path)
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(dpi=200)
                img_bytes = _compress_to_jpeg(pix)
                data["page_img"] = base64.b64encode(img_bytes).decode("ascii")
                doc.close()
            except Exception:
                pass
            data.update(cached=True, page_num=page_num, total_pages=total_pages, title=title)
            self._in_memory[cache_key] = data
            return data

        # Render page image (fast, ~0.1s) — use JPEG at 85% quality to save space
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)
            pix = page.get_pixmap(dpi=200)
            img_bytes = _compress_to_jpeg(pix)
            page_b64 = base64.b64encode(img_bytes).decode("ascii")
            doc.close()
        except Exception as e:
            return {"error": f"Failed to render page: {e}"}

        # Return image immediately; no OCR text yet
        # NOTE: page_img is NOT cached in SQLite — only kept in memory.
        # Rendering is fast (~0.1s) so we re-render on each request.
        # This keeps the cache DB small (OCR text only, not images).
        data = {
            "page_img": page_b64,
            "ocr_text": "",
            "lines": [],
            "page_num": page_num,
            "total_pages": total_pages,
            "title": title,
            "db_path": db_path,
            "cached": False,
            "ocr_pending": True,
        }

        # Kick off OCR in background
        threading.Thread(
            target=self._do_ocr_and_cache,
            args=(pdf_id, pdf_path, page_num, model_type, db_path, title),
            daemon=True,
        ).start()

        return data

    # ── Get OCR (poll) ─────────────────────────────────────────────────

    def get_ocr(self, pdf_id: str, page_num: int, model_type: str = "print") -> dict:
        """Get OCR text for a page (poll this after get_page)."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}

        cache_key = f"{pdf_id}_p{page_num:04d}_{model_type}"

        # Check memory
        if cache_key in self._in_memory:
            data = dict(self._in_memory[cache_key])
            data.update(cached=True, page_num=page_num, total_pages=total_pages, title=title)
            return data

        # Check SQLite
        conn = self._get_conn(db_path)
        cur = conn.execute("SELECT data FROM ocr_cache WHERE cache_key = ?", (cache_key,))
        cached = cur.fetchone()
        if cached:
            data = json.loads(cached[0])
            if data.get("ocr_text") or data.get("lines"):
                data.update(cached=True, page_num=page_num, total_pages=total_pages, title=title)
                self._in_memory[cache_key] = data
                return data

        return {"ocr_text": "", "lines": [], "ocr_pending": True, "page_num": page_num, "total_pages": total_pages, "title": title}

    # ── List & Status ──────────────────────────────────────────────────

    def list_pdfs(self) -> list[dict]:
        """List all PDFs across all book directories."""
        results = []
        if not os.path.isdir(BASE_DIR):
            return results
        for entry in os.listdir(BASE_DIR):
            book_dir = os.path.join(BASE_DIR, entry.rstrip())
            db_path = os.path.join(book_dir, "cache", "ocr_cache.db")
            if not os.path.isfile(db_path):
                continue
            try:
                conn = self._get_conn(db_path)
                cur = conn.execute("SELECT pdf_id, title, total_pages FROM pdf_meta ORDER BY created_at DESC")
                for r in cur.fetchall():
                    results.append({"pdf_id": r[0], "title": r[1], "total_pages": r[2]})
            except Exception:
                pass
        return results

    def delete_pdf(self, pdf_id: str) -> dict:
        """Delete a PDF and its cache. Returns success/error."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}
        try:
            # Remove PDF file
            if pdf_path and os.path.isfile(pdf_path):
                os.unlink(pdf_path)
            # Remove cache DB
            if db_path and os.path.isfile(db_path):
                os.unlink(db_path)
            # Remove from caches
            self._pdf_cache.pop(pdf_id, None)
            self._in_memory = {k: v for k, v in self._in_memory.items() if not k.startswith(pdf_id)}
            # Remove empty book dir if no PDFs left
            book_dir = os.path.dirname(os.path.dirname(pdf_path)) if pdf_path else None
            if book_dir and os.path.isdir(book_dir):
                upload_dir = os.path.join(book_dir, "uploads")
                cache_dir = os.path.join(book_dir, "cache")
                if os.path.isdir(upload_dir) and not os.listdir(upload_dir):
                    os.rmdir(upload_dir)
                if os.path.isdir(cache_dir) and not os.listdir(cache_dir):
                    os.rmdir(cache_dir)
                if not os.listdir(book_dir):
                    os.rmdir(book_dir)
            return {"success": True, "pdf_id": pdf_id}
        except Exception as e:
            return {"error": str(e)}

    def get_status(self, pdf_id: str) -> dict:
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}
        conn = self._get_conn(db_path)
        cached = 0
        for n in range(1, total_pages + 1):
            for m in ("print", "manuscript"):
                ck = f"{pdf_id}_p{n:04d}_{m}"
                cur = conn.execute("SELECT 1 FROM ocr_cache WHERE cache_key = ?", (ck,))
                if cur.fetchone():
                    cached += 1
                    break
        return {"pdf_id": pdf_id, "title": title, "total_pages": total_pages, "cached_pages": cached}

    # ── Bookshelf cover thumbnails ────────────────────────────────────

    def get_cover_thumbnail(self, pdf_id: str) -> Optional[str]:
        """Return base64-encoded PNG thumbnail of the first page (150px wide).
        Cache in SQLite after first render.
        """
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return None

        thumb_key = f"{pdf_id}_cover"
        if db_path:
            conn = self._get_conn(db_path)
            cur = conn.execute("SELECT data FROM ocr_cache WHERE cache_key = ?", (thumb_key,))
            cached = cur.fetchone()
            if cached:
                try:
                    return json.loads(cached[0]).get("thumb")
                except Exception:
                    pass

        # Render first page → small thumbnail
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            # Pixmap at ~150px width (maintain aspect ratio)
            rect = page.rect
            target_w = 150
            zoom = target_w / rect.width
            pix = page.get_pixmap(dpi=72, matrix=fitz.Matrix(zoom, zoom))
            img_bytes = pix.tobytes("png")
            thumb_b64 = base64.b64encode(img_bytes).decode("ascii")
            doc.close()

            # Cache
            if db_path:
                own = sqlite3.connect(db_path)
                own.execute(
                    "INSERT OR REPLACE INTO ocr_cache (cache_key, data, created_at) VALUES (?, ?, ?)",
                    (thumb_key, json.dumps({"thumb": thumb_b64}, ensure_ascii=False), int(time.time())),
                )
                own.commit()
                own.close()

            return thumb_b64
        except Exception:
            return None

    # ── Re-OCR (force re-run) ────────────────────────────────────────

    def re_ocr_page(self, pdf_id: str, page_num: int, model_type: str = "print") -> dict:
        """Delete cached OCR for a page and re-run OCR immediately.
        Returns the new page data (image + OCR text).
        """
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}

        cache_key = f"{pdf_id}_p{page_num:04d}_{model_type}"

        # Remove from memory cache
        self._in_memory.pop(cache_key, None)

        # Remove from SQLite cache
        if db_path:
            conn = self._get_conn(db_path)
            conn.execute("DELETE FROM ocr_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()

        # Re-run OCR synchronously — use JPEG at 85% quality to save space
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)
            dpi = 600
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = _compress_to_jpeg(pix)
            page_b64 = base64.b64encode(img_bytes).decode("ascii")
            doc.close()

            ocr_result = self._ocr_bytes(img_bytes, model_type)

            # Only cache OCR text + lines — NOT page_img
            cache_data = {
                "ocr_text": ocr_result.get("full_text", ""),
                "lines": ocr_result.get("lines", []),
            }

            if db_path:
                own_conn = sqlite3.connect(db_path)
                own_conn.execute(
                    "INSERT OR REPLACE INTO ocr_cache (cache_key, data, created_at) VALUES (?, ?, ?)",
                    (cache_key, json.dumps(cache_data, ensure_ascii=False), int(time.time())),
                )
                own_conn.commit()
                own_conn.close()

            # Check for user-edited text
            user_edited = False
            if db_path:
                page_key = f"{pdf_id}_p{page_num:04d}_edited"
                conn = self._get_conn(db_path)
                cur = conn.execute("SELECT text FROM page_text WHERE page_key = ?", (page_key,))
                row = cur.fetchone()
                if row:
                    cache_data["ocr_text"] = row[0]
                    user_edited = True

            # Include page_img in the response (not cached, re-rendered)
            cache_data["page_img"] = page_b64
            cache_data.update({
                "cached": True,
                "page_num": page_num,
                "total_pages": total_pages,
                "title": title,
                "ocr_pending": False,
                "user_edited": user_edited,
            })
            self._in_memory[cache_key] = cache_data
            return cache_data

        except Exception as e:
            return {"error": f"Re-OCR failed: {e}"}

    # ── User-edited text (permanent save) ─────────────────────────────

    def save_page_text(self, pdf_id: str, page_num: int, text: str) -> dict:
        """Save user-edited text for a page. Returns success/error."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}
        if db_path is None:
            return {"error": "No cache database found"}

        page_key = f"{pdf_id}_p{page_num:04d}_edited"
        conn = self._get_conn(db_path)
        conn.execute(
            "INSERT OR REPLACE INTO page_text (page_key, text, updated_at) VALUES (?, ?, ?)",
            (page_key, text, int(time.time())),
        )
        conn.commit()
        return {"success": True, "saved_at": int(time.time())}

    def get_page_display(self, pdf_id: str, page_num: int, model_type: str = "print") -> dict:
        """Get page display text: user-edited text if available, else OCR text."""
        result = self.get_page(pdf_id, page_num, model_type)
        if not isinstance(result, dict) or "error" in result:
            return result

        result["user_edited"] = False

        # Override ocr_text with user-edited text if available.
        # Use db_path from get_page result to avoid scanning directories again.
        db_path = result.get("db_path")
        if db_path:
            page_key = f"{pdf_id}_p{page_num:04d}_edited"
            conn = self._get_conn(db_path)
            cur = conn.execute("SELECT text FROM page_text WHERE page_key = ?", (page_key,))
            row = cur.fetchone()
            if row:
                result["ocr_text"] = row[0]
                result["user_edited"] = True
                result["ocr_pending"] = False

        return result

    # ── Helpers ────────────────────────────────────────────────────────

    def _find_pdf(self, pdf_id: str) -> tuple[Optional[str], int, str, Optional[str]]:
        """Find a PDF across all book directories.
        Returns (path, total_pages, title, db_path) or (None, 0, '', None).
        Uses in-memory cache to avoid repeated directory scans.
        """
        cached = self._pdf_cache.get(pdf_id)
        if cached is not None:
            return cached
        if not os.path.isdir(BASE_DIR):
            return None, 0, "", None
        for entry in os.listdir(BASE_DIR):
            book_dir = os.path.join(BASE_DIR, entry.rstrip())
            db_path = os.path.join(book_dir, "cache", "ocr_cache.db")
            if not os.path.isfile(db_path):
                continue
            try:
                conn = self._get_conn(db_path)
                cur = conn.execute(
                    "SELECT path, total_pages, title FROM pdf_meta WHERE pdf_id = ?",
                    (pdf_id,),
                )
                row = cur.fetchone()
                if row:
                    result = (row[0], row[1], row[2], db_path)
                    self._pdf_cache[pdf_id] = result
                    return result
            except Exception:
                pass
        return None, 0, "", None

    @staticmethod
    def _postprocess_ocr_text(text: str) -> str:
        """Post-process OCR output: normalize typographic variants."""
        # Ligature expansions (early printed books)
        replacements = {
            'ſ': 's',       # long s → s
            'æ': 'ae',      # ash ligature
            'œ': 'oe',      # ethel ligature
            'Æ': 'Ae',
            'Œ': 'Oe',
            'ﬃ': 'ffi',     # typographic ligatures
            'ﬄ': 'ffl',
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            '℔': 'lb',
            '¬': '-',       # OCR misrecognized hyphen as not-sign
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _ocr_bytes(self, img_bytes: bytes, model_type: str) -> dict:
        """Run Kraken CLI on raw PNG bytes."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                img_path = tmp.name
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as out:
                out_path = out.name

            cmd = _build_kraken_cmd(img_path, out_path, model_type)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            os.unlink(img_path)

            if result.returncode != 0:
                os.unlink(out_path)
                return {"full_text": "", "lines": [], "error": result.stderr.strip()}

            raw_text = ""
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                os.unlink(out_path)

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            full_text = self._postprocess_ocr_text("\n".join(lines))
            lines = [{"text": self._postprocess_ocr_text(l), "bbox": None} for l in lines]
            return {"full_text": full_text, "lines": lines}

        except subprocess.TimeoutExpired:
            return {"full_text": "", "lines": [], "error": "OCR timed out"}
        except FileNotFoundError:
            return {"full_text": "", "lines": [], "error": "kraken CLI not found"}
        except Exception as e:
            logger.exception("OCR failed for page")
            return {"full_text": "", "lines": [], "error": str(e)}

    # ── Bookmarks ──────────────────────────────────────────────────────

    def get_bookmarks(self, pdf_id: str) -> list:
        """Get all bookmarks for a PDF. Returns list of {page, label}, sorted by page."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None or db_path is None:
            return []
        try:
            conn = self._get_conn(db_path)
            cur = conn.execute("SELECT data FROM ocr_cache WHERE cache_key = ?", (f"{pdf_id}_bookmarks",))
            row = cur.fetchone()
            if row:
                bookmarks = json.loads(row[0])
                # Sort by page number ascending
                bookmarks.sort(key=lambda b: b.get("page", 0))
                return bookmarks
        except Exception:
            pass
        return []

    def add_bookmark(self, pdf_id: str, page: int, label: str = "") -> dict:
        """Add a bookmark for a PDF page. Returns updated bookmark list."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}
        if db_path is None:
            return {"error": "No cache database found"}
        bookmarks = self.get_bookmarks(pdf_id)
        # Avoid duplicates
        bookmarks = [b for b in bookmarks if b.get("page") != page]
        bookmarks.append({"page": page, "label": label or f"Page {page}"})
        conn = self._get_conn(db_path)
        conn.execute(
            "INSERT OR REPLACE INTO ocr_cache (cache_key, data, created_at) VALUES (?, ?, ?)",
            (f"{pdf_id}_bookmarks", json.dumps(bookmarks), int(time.time())),
        )
        conn.commit()
        return {"success": True, "bookmarks": bookmarks}

    def remove_bookmark(self, pdf_id: str, page: int) -> dict:
        """Remove a bookmark for a PDF page. Returns updated bookmark list."""
        pdf_path, total_pages, title, db_path = self._find_pdf(pdf_id)
        if pdf_path is None:
            return {"error": "PDF not found"}
        if db_path is None:
            return {"error": "No cache database found"}
        bookmarks = self.get_bookmarks(pdf_id)
        bookmarks = [b for b in bookmarks if b.get("page") != page]
        conn = self._get_conn(db_path)
        conn.execute(
            "INSERT OR REPLACE INTO ocr_cache (cache_key, data, created_at) VALUES (?, ?, ?)",
            (f"{pdf_id}_bookmarks", json.dumps(bookmarks), int(time.time())),
        )
        conn.commit()
        return {"success": True, "bookmarks": bookmarks}

    def _do_ocr_and_cache(self, pdf_id: str, pdf_path: str, page_num: int, model_type: str, db_path: str, title: str):
        """Run OCR on a page and cache result. Runs in background thread."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)
            dpi = 600
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = _compress_to_jpeg(pix)
            doc.close()

            ocr_result = self._ocr_bytes(img_bytes, model_type)

            # Only cache OCR text + lines — NOT page_img.
            # page_img is re-rendered on each request (~0.1s per page).
            # This keeps the cache DB small (text only, not images).
            cache_data = {
                "ocr_text": ocr_result.get("full_text", ""),
                "lines": ocr_result.get("lines", []),
            }

            # Use own SQLite connection (thread-safe)
            own_conn = sqlite3.connect(db_path)
            cache_key = f"{pdf_id}_p{page_num:04d}_{model_type}"
            own_conn.execute(
                "INSERT OR REPLACE INTO ocr_cache (cache_key, data, created_at) VALUES (?, ?, ?)",
                (cache_key, json.dumps(cache_data, ensure_ascii=False), int(time.time())),
            )
            own_conn.commit()
            own_conn.close()
        except Exception as e:
            logger.debug("Background OCR failed for page %d: %s", page_num, e)


_default: Optional[PDFProcessor] = None


def get_pdf_processor() -> PDFProcessor:
    global _default
    if _default is None:
        _default = PDFProcessor()
    return _default
