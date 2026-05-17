"""
Kraken OCR engine for Latin text recognition.

Supports two model types:
  - "print":     Latin incunabula / early prints model
  - "manuscript": Specialized model for medieval manuscripts

Uses Kraken CLI via subprocess (avoids Python-side TensorFlow loading).

Usage:
    from engine.ocr import ocr_image, ocr_image_with_analysis
"""
import os
import re
import logging
import subprocess
import tempfile

from typing import Optional

logger = logging.getLogger(__name__)

# Model filenames (Kraken stores models in ~/.local/share/htrmopo/<uuid>/)
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


def _build_cmd(image_path: str, output_path: str, model_type: str) -> list[str]:
    """Build Kraken CLI command based on model type.

    Kraken >= 6.0 requires -m flag for ocr subcommand.
    """
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


def ocr_image(image_source: str, model_type: str = "print") -> dict:
    """Recognize Latin text in an image using Kraken CLI."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            out_path = tmp.name

        cmd = _build_cmd(image_source, out_path, model_type)
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            return {
                "full_text": "",
                "lines": [],
                "error": f"Kraken failed: {result.stderr.strip()}",
            }

        raw_text = ""
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            os.unlink(out_path)
        else:
            raw_text = result.stdout

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return {"full_text": "\n".join(lines), "lines": [{"text": l, "bbox": None} for l in lines]}

    except subprocess.TimeoutExpired:
        return {"full_text": "", "lines": [], "error": "Kraken timed out"}
    except FileNotFoundError:
        return {"full_text": "", "lines": [], "error": "kraken CLI not found. Install: pip install kraken"}
    except Exception as e:
        logger.exception("OCR failed")
        return {"full_text": "", "lines": [], "error": str(e)}


def ocr_image_with_analysis(image_source: str, lang: str = "en", model_type: str = "print") -> dict:
    """Recognize and analyze each word."""
    ocr_result = ocr_image(image_source, model_type)
    if "error" in ocr_result and ocr_result["error"]:
        return ocr_result

    from engine.lemmatizer import lemmatize

    word_analyses = []
    seen_words = {}

    for line in ocr_result.get("lines", []):
        for token in re.findall(r"[a-zA-Z\u0100-\u024F]+", line.get("text", "")):
            lower = token.lower()
            if lower not in seen_words:
                seen_words[lower] = lemmatize(token, lang)
            word_analyses.append({"word": token, "analyses": seen_words[lower]})

    return {"full_text": ocr_result["full_text"], "lines": ocr_result["lines"], "words": word_analyses}
