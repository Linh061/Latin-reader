import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { PdfPageResponse, ParseResult, DictEntry, BookshelfBook } from '../types/latin';

const API = '';

// ─── Style ────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    fontFamily: "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif",
    color: '#2c1810',
    backgroundColor: '#3e2c1a',
    display: 'flex',
    flexDirection: 'column',
  },
  nav: {
    padding: '10px 20px',
    backgroundColor: '#2c1810',
    borderBottom: '2px solid #8b4513',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  navTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#d4a76a',
    letterSpacing: '1px',
    fontFamily: 'Georgia, serif',
    cursor: 'pointer',
  },
  navLink: {
    padding: '5px 12px',
    borderRadius: '3px',
    border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: 'Georgia, serif',
  },
  main: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  leftPanel: {
    flex: 1,
    overflowY: 'auto',
    backgroundColor: '#fdf5e6',
    padding: '20px',
    borderRight: '2px solid #5a3d2b',
  },
  rightPanel: {
    flex: 1,
    overflowY: 'auto',
    backgroundColor: '#3e2c1a',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px',
    gap: '16px',
  },
  analysisPanel: {
    width: '100%',
    backgroundColor: '#fdf5e6',
    borderRadius: '6px',
    border: '1px solid #c4a77d',
    padding: '10px 12px',
    textAlign: 'left',
  },
  pageImage: {
    maxWidth: '100%',
    boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
    borderRadius: '4px',
  },
  ocrText: {
    whiteSpace: 'pre-wrap',
    fontSize: '15px',
    lineHeight: '1.7',
    fontFamily: 'Georgia, serif',
    color: '#2c1810',
  },
  ocrLine: {
    cursor: 'pointer',
    borderRadius: '3px',
    padding: '1px 3px',
    transition: 'background 0.1s',
  },
  pageNav: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    padding: '10px',
    backgroundColor: '#2c1810',
    borderTop: '2px solid #8b4513',
  },
  pageBtn: {
    padding: '6px 16px',
    borderRadius: '4px',
    border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontFamily: 'Georgia, serif',
    fontSize: '13px',
  },
  pageBtnDisabled: {
    padding: '6px 16px',
    borderRadius: '4px',
    border: '1px solid #5a3d2b',
    backgroundColor: '#3e2c1a',
    color: '#6b4c2a',
    fontFamily: 'Georgia, serif',
    fontSize: '13px',
    cursor: 'not-allowed',
  },
  pageInfo: {
    color: '#d4a76a',
    fontSize: '14px',
    fontFamily: 'Georgia, serif',
  },
  modelToggle: {
    display: 'flex',
    gap: '4px',
    marginLeft: 'auto',
    alignItems: 'center',
  },
  modelBtn: {
    padding: '4px 10px',
    borderRadius: '3px',
    border: '1px solid #8b4513',
    cursor: 'pointer',
    fontSize: '11px',
    fontFamily: 'Georgia, serif',
  },
  modelBtnActive: {
    padding: '4px 10px',
    borderRadius: '3px',
    border: '1px solid #d4a76a',
    backgroundColor: '#d4a76a',
    color: '#1a0f08',
    cursor: 'pointer',
    fontSize: '11px',
    fontFamily: 'Georgia, serif',
    fontWeight: 'bold',
  },
  loadingOverlay: {
    position: 'absolute' as const,
    inset: 0,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
    color: '#d4a76a',
    fontSize: '16px',
    fontFamily: 'Georgia, serif',
    zIndex: 10,
  },
  wordDropdown: {
    position: 'absolute' as const,
    backgroundColor: '#fdf5e6',
    border: '2px solid #8b4513',
    borderRadius: '6px',
    boxShadow: '2px 4px 12px rgba(0,0,0,0.3)',
    padding: '10px 14px',
    zIndex: 20,
    maxWidth: '400px',
    fontSize: '13px',
    lineHeight: '1.5',
  },
  bookshelfZone: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#3e2c1a',
    padding: '40px 20px',
    gap: '24px',
    color: '#e8d5b0',
  },
  bookshelfTitle: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#d4a76a',
    letterSpacing: '2px',
    fontFamily: 'Georgia, serif',
  },
  bookshelfGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: '24px',
    maxWidth: '1000px',
    width: '100%',
    padding: '0 20px',
  },
  bookCard: {
    cursor: 'pointer',
    textAlign: 'center' as const,
    transition: 'transform 0.15s',
  },
  bookCover: {
    width: '150px',
    height: '210px',
    backgroundColor: '#fdf5e6',
    borderRadius: '4px',
    overflow: 'hidden',
    boxShadow: '2px 3px 10px rgba(0,0,0,0.4)',
    margin: '0 auto 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bookCoverImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
  },
  bookCoverPlaceholder: {
    fontSize: '48px',
    color: '#8b7355',
  },
  bookTitle: {
    fontSize: '13px',
    color: '#e8d5b0',
    fontWeight: 'bold',
    wordBreak: 'break-word',
    lineHeight: '1.3',
  },
  bookPages: {
    fontSize: '11px',
    color: '#8b7355',
    marginTop: '2px',
  },
  uploadBtn: {
    padding: '14px 32px',
    borderRadius: '6px',
    border: '2px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontSize: '16px',
    fontFamily: 'Georgia, serif',
    transition: 'background 0.15s',
  },
  uploadBtnHover: {
    backgroundColor: '#6b4c32',
  },
  loading: { color: '#8b7355', fontSize: '14px', padding: '8px', fontStyle: 'italic' },
  error: { color: '#8b1a1a', fontSize: '13px', padding: '8px', borderLeft: '3px solid #8b1a1a', backgroundColor: '#fce8e6', margin: '8px 0' },
  resultCard: {
    backgroundColor: '#fdf5e6',
    borderRadius: '6px',
    padding: '6px 10px',
    marginBottom: '6px',
    border: '1px solid #c4a77d',
    boxShadow: '1px 1px 4px rgba(44,24,16,0.15)',
  },
  resultLemma: { fontSize: '15px', fontWeight: 'bold', color: '#3e2c1a' },
  resultPos: { fontSize: '11px', color: '#6b4c2a', fontStyle: 'italic' },
  resultTrans: { fontSize: '13px', color: '#386e3a', fontStyle: 'italic' },
  resultMorph: { fontSize: '12px', color: '#7b3f9e' },
};

// ─── Morphology helper ────────────────────────────────────────────────────

const _MORPH_MAP: Record<string, string> = {
  'PRS': 'Present', 'IMF': 'Imperfect', 'FUT': 'Future',
  'PRF': 'Perfect', 'PLP': 'Pluperfect', 'FTP': 'Future Perfect',
  'ACT': 'Active', 'PAS': 'Passive',
  'IND': 'Indicative', 'SBJ': 'Subjunctive', 'IMP': 'Imperative', 'INF': 'Infinitive',
  'PPL': 'Participle', 'GER': 'Gerund', 'SUP': 'Supine',
  '1S': '1st Sg', '2S': '2nd Sg', '3S': '3rd Sg',
  '1P': '1st Pl', '2P': '2nd Pl', '3P': '3rd Pl',
  'NOM': 'Nominative', 'VOC': 'Vocative', 'GEN': 'Genitive',
  'DAT': 'Dative', 'ACC': 'Accusative', 'ABL': 'Ablative',
  'S': 'Singular', 'P': 'Plural',
  'M': 'Masc', 'F': 'Fem', 'N': 'Neuter',
};

function _morphologyLabel(code: string): string {
  if (!code) return '';
  const parts = code.match(/[A-Z][a-z]*|[A-Z]+(?=[A-Z]|\d|$)/g) || [code];
  const labels = parts.map(p => _MORPH_MAP[p] || p);
  return labels.join(' · ');
}

// ─── PDF Reader Page ──────────────────────────────────────────────────────

export default function PDFReaderPage() {
  const { pdfId: routePdfId } = useParams<{ pdfId: string }>();
  const navigate = useNavigate();

  const [currentPdfId, setCurrentPdfId] = useState(routePdfId || '');
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageData, setPageData] = useState<PdfPageResponse | null>(null);
  const [modelType, setModelType] = useState<'print' | 'manuscript'>('print');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bookshelf
  const [books, setBooks] = useState<BookshelfBook[]>([]);
  const [showBookshelf, setShowBookshelf] = useState(!routePdfId);
  const [uploading, setUploading] = useState(false);
  const [hoverUpload, setHoverUpload] = useState(false);

  // Edit mode
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);

  const [searchWord, setSearchWord] = useState('');
  const [searchingWord, setSearchingWord] = useState(false);

  const [popup, setPopup] = useState<{
    word: string;
    x: number;
    y: number;
    parses: ParseResult[];
    dict: DictEntry[];
  } | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  // Load bookshelf on mount
  useEffect(() => {
    fetch(`${API}/api/pdf/bookshelf`)
      .then(r => r.json())
      .then(data => setBooks(data.books || []))
      .catch(() => {});
  }, []);

  // Load page on mount or when params change
  useEffect(() => {
    if (routePdfId) {
      setCurrentPdfId(routePdfId);
      setShowBookshelf(false);
      setPageNum(1);
    }
  }, [routePdfId]);

  // Fetch page data
  const fetchPage = useCallback(async (pid: string, pn: number, mt: string) => {
    setLoading(true);
    setError(null);
    setPopup(null);  // close floating popup on page change, but keep wordAnalysis
    try {
      const res = await fetch(`${API}/api/pdf/${pid}/page/${pn}?model_type=${mt}`);
      const data: PdfPageResponse = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setPageData(data);
        setTotalPages(data.total_pages);
      }
    } catch (err: any) {
      setError(`Failed to load page: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll OCR text after page image is shown
  const pollOcr = useCallback(async (pid: string, pn: number, mt: string) => {
    for (let attempt = 0; attempt < 60; attempt++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const res = await fetch(`${API}/api/pdf/${pid}/page/${pn}/ocr?model_type=${mt}`);
        const data = await res.json();
        if (data.ocr_text || data.lines?.length > 0) {
          setPageData(prev => prev ? { ...prev, ocr_text: data.ocr_text, lines: data.lines, ocr_pending: false } : prev);
          return;
        }
      } catch {
        // keep polling
      }
    }
  }, []);

  // Refresh when pageNum or modelType changes
  useEffect(() => {
    if (currentPdfId && pageNum > 0 && (totalPages === 0 || pageNum <= totalPages)) {
      fetchPage(currentPdfId, pageNum, modelType);
    }
  }, [currentPdfId, pageNum, modelType, fetchPage, totalPages]);

  // Start OCR polling when page image is loaded but text is pending
  useEffect(() => {
    if (pageData?.ocr_pending && currentPdfId && pageNum) {
      pollOcr(currentPdfId, pageNum, modelType);
    }
  }, [pageData?.ocr_pending, currentPdfId, pageNum, modelType, pollOcr]);

  // Handle upload
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('model_type', modelType);

      const res = await fetch(`${API}/api/pdf/upload`, { method: 'POST', body: form });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        return;
      }
      setCurrentPdfId(data.pdf_id);
      setTotalPages(data.total_pages);
      setPageNum(1);
      setShowBookshelf(false);
      navigate(`/pdf-reader/${data.pdf_id}`, { replace: true });
    } catch (err: any) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }, [modelType, navigate]);

  // Navigate pages
  const goToPage = useCallback((n: number) => {
    if (n >= 1 && n <= totalPages) setPageNum(n);
  }, [totalPages]);

  // Open book from bookshelf
  const openBook = useCallback((pdfId: string) => {
    setCurrentPdfId(pdfId);
    setPageNum(1);
    setShowBookshelf(false);
    navigate(`/pdf-reader/${pdfId}`, { replace: true });
  }, [navigate]);

  // Delete a PDF book
  const handleDeleteBook = useCallback(async (pdfId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this book and all its OCR cache?')) return;
    try {
      await fetch(`${API}/api/pdf/${pdfId}`, { method: 'DELETE' });
      setBooks(prev => prev.filter(b => b.pdf_id !== pdfId));
    } catch {
      // ignore
    }
  }, []);

  // Search word from nav bar
  const handleSearchWord = useCallback(async () => {
    const word = searchWord.trim();
    if (!word) return;
    setSearchingWord(true);
    setPopup(null);
    try {
      const res = await fetch(`${API}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word }),
      });
      const data = await res.json();
      const allDict: DictEntry[] = [];
      if (data.dictionary) {
        for (const entries of Object.values(data.dictionary) as any) {
          allDict.push(...(entries as DictEntry[]));
        }
      }
      setPopup({
        word,
        x: 60,
        y: 120,
        parses: data.parses || [],
        dict: allDict,
      });
    } catch (err: any) {
      setError(`Search failed: ${err.message}`);
    } finally {
      setSearchingWord(false);
    }
  }, [searchWord]);

  // Click a word -> analyze
  const handleWordClick = useCallback(async (word: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPopup(null);

    // Skip non-Latin words (Greek, numbers, punctuation-only)
    if (!/^[a-zA-Z\u0100-\u024F]+$/.test(word)) {
      setPopup({
        word,
        x: Math.min((e.target as HTMLElement).getBoundingClientRect().left, window.innerWidth - 380),
        y: Math.min((e.target as HTMLElement).getBoundingClientRect().bottom + 4, window.innerHeight - 300),
        parses: [],
        dict: [],
      });
      return;
    }

    try {
      const res = await fetch(`${API}/api/pdf/${currentPdfId}/analyze/${pageNum}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word }),
      });
      const data = await res.json();

      const rect = (e.target as HTMLElement).getBoundingClientRect();
      const allDict: DictEntry[] = [];
      if (data.dictionary) {
        for (const entries of Object.values(data.dictionary) as any) {
          allDict.push(...(entries as DictEntry[]));
        }
      }
      setPopup({
        word,
        x: Math.min(rect.left, window.innerWidth - 380),
        y: Math.min(rect.bottom + 4, window.innerHeight - 300),
        parses: data.parses || [],
        dict: allDict,
      });
    } catch (err: any) {
      setError(`Analysis failed: ${err.message}`);
    }
  }, [currentPdfId, pageNum]);

  // Close popup on background click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setPopup(null);
      }
    };
    if (popup) {
      document.addEventListener('mousedown', handler);
      return () => document.removeEventListener('mousedown', handler);
    }
  }, [popup]);

  // Render OCR text with clickable words
  const renderOcrText = () => {
    if (!pageData?.ocr_text) return <div style={{ color: '#8b7355', fontStyle: 'italic' }}>No text recognized.</div>;

    const words = pageData.ocr_text.split(/(\s+)/);
    return (
      <div style={S.ocrText}>
        {words.map((w, i) => {
          const isWord = /^[a-zA-Z\u0100-\u024F]+$/.test(w);
          if (isWord) {
            return (
              <span
                key={i}
                style={S.ocrLine}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e0b0')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                onClick={(e) => handleWordClick(w, e)}
              >
                {w}
              </span>
            );
          }
          return <span key={i}>{w}</span>;
        })}
      </div>
    );
  };

  // ── Bookshelf screen ──────────────────────────────────────────────

  if (showBookshelf) {
    return (
      <div style={S.bookshelfZone}>
        <div style={S.bookshelfTitle}>
          {'\u2766'} My Latin Books
        </div>
        <div style={{ fontSize: '14px', color: '#a09080', fontStyle: 'italic' }}>
          Select a book to read, or upload a new PDF
        </div>

        {/* Bookshelf grid */}
        {books.length > 0 && (
          <div style={S.bookshelfGrid}>
            {books.map(book => (
              <div
                key={book.pdf_id}
                style={S.bookCard}
                onClick={() => openBook(book.pdf_id)}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                <div style={S.bookCover}>
                  {book.cover_thumb ? (
                    <img
                      src={`data:image/png;base64,${book.cover_thumb}`}
                      alt={book.title}
                      style={S.bookCoverImg}
                    />
                  ) : (
                    <div style={S.bookCoverPlaceholder}>{'\uD83D\uDCD6'}</div>
                  )}
                </div>
                <div style={S.bookTitle}>{book.title}</div>
                <div style={S.bookPages}>{book.total_pages} pages</div>
                <button
                  onClick={(e) => handleDeleteBook(book.pdf_id, e)}
                  style={{
                    marginTop: '6px',
                    padding: '2px 8px',
                    border: '1px solid #8b1a1a',
                    borderRadius: '3px',
                    backgroundColor: '#5a2020',
                    color: '#e0b0b0',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontFamily: 'Georgia, serif',
                  }}
                >
                  {'\uD83D\uDDD1'} Delete
                </button>
              </div>
            ))}
          </div>
        )}

        {!loading && books.length === 0 && (
          <div style={{ color: '#8b7355', fontStyle: 'italic', fontSize: '14px' }}>
            No books yet. Upload your first PDF!
          </div>
        )}

        {/* Upload button */}
        <label
          style={{
            ...S.uploadBtn,
            ...(hoverUpload ? { backgroundColor: '#6b4c32' } : {}),
            opacity: uploading ? 0.6 : 1,
            cursor: uploading ? 'not-allowed' : 'pointer',
          }}
          onMouseEnter={() => setHoverUpload(true)}
          onMouseLeave={() => setHoverUpload(false)}
        >
          {uploading ? 'Uploading\u2026' : '\u2795 Upload New PDF'}
          <input
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            disabled={uploading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleUpload(f);
            }}
          />
        </label>

        {error && <div style={S.error}>{error}</div>}

        <div
          style={{ color: '#8b7355', cursor: 'pointer', fontSize: '14px', marginTop: '8px' }}
          onClick={() => navigate('/')}
        >
          {'\u2190'} Back to Home
        </div>
      </div>
    );
  }

  // ── Reader screen ─────────────────────────────────────────────────

  return (
    <div style={S.container}>
      {/* Nav */}
      <nav style={S.nav}>
        <span style={S.navTitle} onClick={() => navigate('/')}>
          {'\u2766'} {pageData?.title || 'PDF Reader'}
        </span>
        <span style={S.navLink} onClick={() => { setShowBookshelf(true); navigate('/pdf-reader'); }}>
          Bookshelf
        </span>

        {/* Word search bar */}
        <input
          value={searchWord}
          onChange={e => setSearchWord(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSearchWord(); }}
          placeholder="Search any Latin word…"
          style={{
            flex: 1,
            maxWidth: '220px',
            padding: '5px 10px',
            borderRadius: '3px',
            border: '1px solid #8b4513',
            backgroundColor: '#faf0dc',
            color: '#2c1810',
            fontSize: '12px',
            fontFamily: 'Georgia, serif',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSearchWord}
          disabled={searchingWord}
          style={{
            padding: '5px 12px',
            borderRadius: '3px',
            border: '1px solid #8b4513',
            backgroundColor: '#5a3d2b',
            color: '#e8d5b0',
            cursor: 'pointer',
            fontSize: '12px',
            fontFamily: 'Georgia, serif',
          }}
        >
          {searchingWord ? '\u2026' : '\uD83D\uDD0D'}
        </button>

        <div style={S.modelToggle}>
          <button
            style={modelType === 'print' ? S.modelBtnActive : S.modelBtn}
            onClick={() => setModelType('print')}
          >
            Print
          </button>
          <button
            style={modelType === 'manuscript' ? S.modelBtnActive : S.modelBtn}
            onClick={() => setModelType('manuscript')}
          >
            MS
          </button>
        </div>
      </nav>

      {/* Main content */}
      <div style={{ position: 'relative', flex: 1, display: 'flex', overflow: 'hidden' }}>
        {loading && (
          <div style={S.loadingOverlay}>Processing page {pageNum}\u2026</div>
        )}

        {/* Left: OCR text / editable textarea */}
        <div style={S.leftPanel}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid #c4a77d', paddingBottom: '4px' }}>
            <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#8b4513' }}>
              Latin Text {pageData?.user_edited ? '(\u270F Edited)' : ''}
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              {!isEditing ? (
                <button
                  onClick={() => { setEditText(pageData?.ocr_text || ''); setIsEditing(true); }}
                  style={{ padding: '3px 10px', fontSize: '11px', border: '1px solid #8b4513', borderRadius: '3px', backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontFamily: 'Georgia, serif' }}
                >
                  {'\u270E'} Edit
                </button>
              ) : (
                <>
                  <button
                    onClick={async () => {
                      setSaving(true);
                      try {
                        await fetch(`${API}/api/pdf/${currentPdfId}/page/${pageNum}/text`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ text: editText }),
                        });
                        setPageData(prev => prev ? { ...prev, ocr_text: editText, user_edited: true } : prev);
                      } catch {
                        // ignore
                      }
                      setSaving(false);
                      setIsEditing(false);
                    }}
                    style={{ padding: '3px 10px', fontSize: '11px', border: '1px solid #386e3a', borderRadius: '3px', backgroundColor: '#2d5a2e', color: '#ffffff', cursor: 'pointer', fontFamily: 'Georgia, serif' }}
                  >
                    {saving ? 'Saving\u2026' : '\u2713 Done'}
                  </button>
                  <button
                    onClick={() => { setIsEditing(false); }}
                    style={{ padding: '3px 10px', fontSize: '11px', border: '1px solid #8b1a1a', borderRadius: '3px', backgroundColor: '#5a2020', color: '#e0b0b0', cursor: 'pointer', fontFamily: 'Georgia, serif' }}
                  >
                    {'\u2715 Cancel'}
                  </button>
                </>
              )}
            </div>
          </div>
          {error && <div style={S.error}>{error}</div>}
          {isEditing ? (
            <textarea
              value={editText}
              onChange={e => setEditText(e.target.value)}
              style={{
                width: '100%',
                minHeight: '400px',
                padding: '10px',
                fontSize: '15px',
                lineHeight: '1.7',
                fontFamily: 'Georgia, serif',
                backgroundColor: '#fff8ee',
                color: '#2c1810',
                border: '1px solid #c4a77d',
                borderRadius: '4px',
                resize: 'vertical',
                outline: 'none',
              }}
            />
          ) : (
            renderOcrText()
          )}
        </div>

        {/* Right: PDF image */}
        <div style={S.rightPanel}>
          {pageData?.page_img && (
            <img
              src={`data:image/png;base64,${pageData.page_img}`}
              alt={`Page ${pageNum}`}
              style={S.pageImage}
            />
          )}
        </div>
      </div>

      {/* Page navigation */}
      <div style={S.pageNav}>
        <button
          style={pageNum <= 1 ? S.pageBtnDisabled : S.pageBtn}
          disabled={pageNum <= 1}
          onClick={() => goToPage(pageNum - 1)}
        >
          {'\u25C0'} Prev
        </button>
        <span style={S.pageInfo}>
          Page {pageNum} / {totalPages}
        </span>
        <button
          style={pageNum >= totalPages ? S.pageBtnDisabled : S.pageBtn}
          disabled={pageNum >= totalPages}
          onClick={() => goToPage(pageNum + 1)}
        >
          Next {'\u25B6'}
        </button>

        <input
          type="number"
          min={1}
          max={totalPages}
          value={pageNum}
          onChange={(e) => {
            const v = parseInt(e.target.value, 10);
            if (v >= 1 && v <= totalPages) goToPage(v);
          }}
          style={{
            width: '60px',
            padding: '4px 8px',
            borderRadius: '3px',
            border: '1px solid #8b4513',
            backgroundColor: '#faf0dc',
            color: '#2c1810',
            fontSize: '13px',
            fontFamily: 'Georgia, serif',
            textAlign: 'center',
          }}
        />
      </div>

      {/* Word analysis popup */}
      {popup && (
        <div
          ref={popupRef}
          style={{
            ...S.wordDropdown,
            left: popup.x,
            top: popup.y,
          }}
        >
          <div style={{ fontWeight: 'bold', fontSize: '16px', color: '#2c1810', marginBottom: '4px', borderBottom: '1px solid #c4a77d', paddingBottom: '4px' }}>
            {popup.word}
          </div>
          {popup.parses.length > 0 && (
            <div style={{ marginBottom: '6px' }}>
              <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b4513', marginBottom: '4px' }}>
                Analysis
              </div>
              {popup.parses.map((p, i) => (
                <div key={i} style={S.resultCard}>
                  <div style={S.resultLemma}>{p.lemma_form}</div>
                  <div style={S.resultPos}>{p.part_of_speech}</div>
                  {p.morphology && (
                    <div style={S.resultMorph}>{_morphologyLabel(p.morphology)}</div>
                  )}
                  {p.translation && (
                    <div style={S.resultTrans}>{p.translation}</div>
                  )}
                </div>
              ))}
            </div>
          )}
          {popup.dict.length > 0 && (
            <div>
              <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b4513', borderBottom: '1px solid #c4a77d', marginBottom: '4px' }}>
                Dictionary
              </div>
              {popup.dict.map((d, i) => (
                <div key={i} style={S.resultCard}>
                  <div style={S.resultLemma}>{d.key}</div>
                  <div style={S.resultPos}>{d.part_of_speech}</div>
                  <div style={{ fontSize: '12px', color: '#2c1810' }}>{d.meaning}</div>
                </div>
              ))}
            </div>
          )}
          {popup.parses.length === 0 && popup.dict.length === 0 && (
            <div style={{ color: '#8b7355', fontSize: '13px', fontStyle: 'italic' }}>No analysis found.</div>
          )}
          {/* Morphology legend */}
          <details style={{ marginTop: '6px', fontSize: '11px', color: '#8b7355', cursor: 'pointer' }}>
            <summary style={{ fontStyle: 'italic' }}>What do the codes mean?</summary>
            <div style={{ marginTop: '4px', lineHeight: '1.6' }}>
              <b>Tense:</b> PRS=Present, IMF=Imperfect, FUT=Future, PRF=Perfect, PLP=Pluperfect<br/>
              <b>Voice:</b> ACT=Active, PAS=Passive<br/>
              <b>Mood:</b> IND=Indicative, SBJ=Subjunctive, IMP=Imperative, INF=Infinitive<br/>
              <b>Person:</b> 1, 2, 3 &nbsp; <b>Number:</b> S=Singular, P=Plural<br/>
              <b>Case:</b> NOM=Nominative, VOC=Vocative, GEN=Genitive, DAT=Dative,<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ACC=Accusative, ABL=Ablative<br/>
              <b>Gender:</b> M=Masculine, F=Feminine, N=Neuter<br/>
              <b>Participle:</b> PPL=Participle, SUP=Supine, GER=Gerund
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
