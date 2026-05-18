import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const API = '';

// ─── Styling ───────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    fontFamily: "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif",
    color: '#2c1810',
    backgroundColor: '#3e2c1a',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '40px 20px 30px',
    backgroundColor: '#2c1810',
    borderBottom: '3px solid #8b4513',
    textAlign: 'center',
  },
  title: {
    fontSize: '36px',
    fontWeight: 'bold',
    color: '#d4a76a',
    letterSpacing: '2px',
    fontFamily: 'Georgia, serif',
  },
  subtitle: {
    fontSize: '14px',
    color: '#8b7355',
    fontStyle: 'italic',
    marginTop: '4px',
  },
  nav: {
    display: 'flex',
    justifyContent: 'center',
    gap: '12px',
    padding: '14px',
    backgroundColor: '#3e2c1a',
    borderBottom: '1px solid #5a3d2b',
  },
  navBtn: {
    padding: '8px 18px',
    border: '1px solid #8b4513',
    borderRadius: '4px',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontFamily: 'Georgia, serif',
    fontSize: '14px',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '30px 20px',
    backgroundColor: '#fdf5e6',
  },
  sectionTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#8b4513',
    fontFamily: 'Georgia, serif',
    marginBottom: '20px',
    borderBottom: '2px solid #c4a77d',
    paddingBottom: '6px',
    display: 'inline-block',
  },
  bookGrid: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '20px',
    justifyContent: 'center',
    maxWidth: '800px',
    width: '100%',
    marginBottom: '30px',
  },
  bookCard: {
    backgroundColor: '#faf0dc',
    border: '1px solid #c4a77d',
    borderRadius: '8px',
    padding: '20px',
    width: '300px',
    boxShadow: '2px 3px 10px rgba(44,24,16,0.15)',
    cursor: 'pointer',
  },
  bookTitle: {
    fontSize: '17px',
    fontWeight: 'bold',
    color: '#2c1810',
    fontFamily: 'Georgia, serif',
  },
  bookAuthor: {
    fontSize: '13px',
    color: '#6b4c2a',
    fontStyle: 'italic',
    marginTop: '2px',
  },
  bookDesc: {
    fontSize: '13px',
    color: '#5a3d2b',
    marginTop: '10px',
    lineHeight: '1.4',
  },
  readBtn: {
    display: 'inline-block',
    marginTop: '12px',
    padding: '6px 18px',
    border: '1px solid #8b4513',
    borderRadius: '4px',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontFamily: 'Georgia, serif',
    fontSize: '13px',
  },
  hint: {
    fontSize: '13px',
    color: '#8b7355',
    fontStyle: 'italic',
    textAlign: 'center' as const,
    maxWidth: '500px',
    lineHeight: '1.5',
  },
  footer: {
    padding: '16px',
    textAlign: 'center' as const,
    backgroundColor: '#2c1810',
    borderTop: '1px solid #5a3d2b',
    color: '#6b4c2a',
    fontSize: '12px',
  },
  loading: { color: '#8b7355', fontSize: '14px', padding: '20px', fontStyle: 'italic' },
  searchInput: {
    flex: 1,
    maxWidth: '400px',
    padding: '8px 12px',
    border: '1px solid #c4a77d',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'Georgia, serif',
    backgroundColor: '#faf0dc',
    color: '#2c1810',
    outline: 'none',
  },
};

/** Render text with matched search term highlighted (returns HTML string). */
function highlightText(text: string, query: string): string {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return text.replace(
    new RegExp(`(${escaped})`, 'gi'),
    '<mark style="background-color:#f7d44a;color:#2c1810;padding:0 2px;border-radius:2px">$1</mark>'
  );
}

interface BookMeta {
  id: string;
  title: string;
  author: string;
  book_count: number;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [books, setBooks] = useState<BookMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQ, setSearchQ] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deleteMode, setDeleteMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const loadBooks = useCallback(() => {
    setLoading(true);
    fetch(`${API}/api/books`)
      .then(r => r.json())
      .then(data => setBooks(data.books || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadBooks();
  }, [loadBooks]);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API}/api/books/upload`, {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      if (data.error) {
        setUploadError(data.error);
      } else {
        // Reload book list
        loadBooks();
      }
    } catch (err: any) {
      setUploadError(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }, [loadBooks]);

  const toggleSelect = useCallback((bookId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(bookId)) {
        next.delete(bookId);
      } else {
        next.add(bookId);
      }
      return next;
    });
  }, []);

  const handleBatchDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Delete ${selectedIds.size} selected book(s)? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await Promise.all(
        Array.from(selectedIds).map(id =>
          fetch(`${API}/api/books/${id}`, { method: 'DELETE' })
        )
      );
      setSelectedIds(new Set());
      setDeleteMode(false);
      loadBooks();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  }, [selectedIds, loadBooks]);

  const cancelDeleteMode = useCallback(() => {
    setDeleteMode(false);
    setSelectedIds(new Set());
  }, []);

  // Filter books by title/author (client-side)
  const filteredBooks = searchQ.trim()
    ? books.filter(b => {
        const q = searchQ.toLowerCase();
        return b.title.toLowerCase().includes(q) || b.author.toLowerCase().includes(q);
      })
    : books;

  return (
    <div style={S.container}>
      {/* Header */}
      <header style={S.header}>
        <div style={S.title}>{'\u2766'} Latin Reader</div>
        <div style={S.subtitle}>
          A digital reading tool for ancient Latin texts
        </div>
      </header>

      {/* Nav with search */}
      <nav style={S.nav}>
        <input
          style={S.searchInput}
          placeholder="Search books by title or author…"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
        />
        <button style={S.navBtn} onClick={() => navigate('/ocr')}>
          Image OCR
        </button>
        <button style={S.navBtn} onClick={() => navigate('/pdf-reader')}>
          PDF Reader
        </button>
        {/* Upload book button */}
        <label
          style={{
            ...S.navBtn,
            opacity: uploading ? 0.6 : 1,
            cursor: uploading ? 'not-allowed' : 'pointer',
          }}
        >
          {uploading ? '\u23F3 Uploading\u2026' : '\u2795 Upload Book'}
          <input
            type="file"
            accept=".html,.htm,.txt"
            style={{ display: 'none' }}
            disabled={uploading}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleUpload(f);
              // Reset so the same file can be re-selected
              e.target.value = '';
            }}
          />
        </label>
        <div style={{ fontSize: '11px', color: '#8b7355', fontStyle: 'italic', marginTop: '4px', textAlign: 'center' }}>
          Supports .html, .htm, .txt files only
        </div>
      </nav>

      {/* Main */}
      <div style={S.main}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '20px' }}>
          <div style={S.sectionTitle}>{'\uD83D\uDCD6'} Books</div>
          {!deleteMode ? (
            <button
              onClick={() => setDeleteMode(true)}
              style={{
                padding: '4px 14px',
                fontSize: '12px',
                border: '1px solid #c0392b',
                borderRadius: '4px',
                backgroundColor: '#faf0dc',
                color: '#c0392b',
                cursor: 'pointer',
                fontFamily: 'Georgia, serif',
                marginTop: '6px',
              }}
            >
              {'\u2716'} Delete
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              <button
                onClick={handleBatchDelete}
                disabled={deleting || selectedIds.size === 0}
                style={{
                  padding: '4px 14px',
                  fontSize: '12px',
                  border: '1px solid #c0392b',
                  borderRadius: '4px',
                  backgroundColor: selectedIds.size > 0 ? '#c0392b' : '#faf0dc',
                  color: selectedIds.size > 0 ? '#fff' : '#c0392b',
                  cursor: selectedIds.size > 0 ? 'pointer' : 'default',
                  fontFamily: 'Georgia, serif',
                }}
              >
                {deleting ? '\u2026' : `\u2714 Delete (${selectedIds.size})`}
              </button>
              <button
                onClick={cancelDeleteMode}
                style={{
                  padding: '4px 14px',
                  fontSize: '12px',
                  border: '1px solid #8b7355',
                  borderRadius: '4px',
                  backgroundColor: '#faf0dc',
                  color: '#8b7355',
                  cursor: 'pointer',
                  fontFamily: 'Georgia, serif',
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {loading && <div style={S.loading}>Loading books...</div>}

        {uploadError && (
          <div style={{ color: '#c0392b', fontSize: '13px', padding: '8px 16px', marginBottom: '12px', backgroundColor: '#fce4e4', borderRadius: '4px', maxWidth: '500px' }}>
            {'\u26A0'} {uploadError}
          </div>
        )}

        {searchQ.trim() && filteredBooks.length === 0 && !loading && (
          <div style={{ color: '#8b7355', fontStyle: 'italic', padding: '10px', marginBottom: '16px' }}>
            No books match "{searchQ}".
          </div>
        )}

        <div style={S.bookGrid}>
          {filteredBooks.map(book => (
            <div
              key={book.id}
              style={S.bookCard}
              onClick={() => { if (!deleteMode) navigate(`/reader/${book.id}`); }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                {deleteMode && (
                  <input
                    type="checkbox"
                    checked={selectedIds.has(book.id)}
                    onChange={() => toggleSelect(book.id)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ marginTop: '3px', cursor: 'pointer', accentColor: '#c0392b' }}
                  />
                )}
                <div style={{ flex: 1 }}>
                  <div style={S.bookTitle} dangerouslySetInnerHTML={{ __html: highlightText(book.title, searchQ) }} />
                  <div style={S.bookAuthor} dangerouslySetInnerHTML={{ __html: highlightText(book.author, searchQ) }} />
                  <div style={S.bookDesc}>
                    {book.book_count} books &middot; Click any word to analyze
                  </div>
                  <div style={S.readBtn}>Read</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {!loading && books.length === 0 && (
          <div style={{ color: '#8b7355', fontStyle: 'italic', padding: '20px' }}>
            No books available.
          </div>
        )}

        <div style={S.hint}>
          Click any Latin word in a book to see its grammar and dictionary entry.
        </div>
      </div>

      {/* Footer */}
      <div style={S.footer}>
        {'\u2766'} Latin Reader
      </div>
    </div>
  );
}
