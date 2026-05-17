import { useEffect, useState } from 'react';
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
  searchBtn: {
    padding: '8px 16px',
    border: '1px solid #8b4513',
    borderRadius: '4px',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontFamily: 'Georgia, serif',
    fontSize: '13px',
  },
  searchResults: {
    width: '100%',
    maxWidth: '800px',
    marginTop: '16px',
    marginBottom: '20px',
  },
  searchResultItem: {
    padding: '10px 14px',
    marginBottom: '6px',
    backgroundColor: '#faf0dc',
    border: '1px solid #c4a77d',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  searchResultMeta: {
    fontSize: '12px',
    color: '#6b4c2a',
    fontStyle: 'italic',
    marginBottom: '2px',
  },
  searchResultText: {
    fontSize: '14px',
    color: '#2c1810',
    lineHeight: '1.5',
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

interface SearchResult {
  book_id: string;
  book_title: string;
  chapter_number: number;
  chapter_title: string;
  text: string;
  match_index: number;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [books, setBooks] = useState<BookMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/books`)
      .then(r => r.json())
      .then(data => setBooks(data.books || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const doSearch = async () => {
    const q = searchQ.trim();
    if (!q) return;
    setSearching(true);
    setSearchResults(null);
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

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
          placeholder="Search Latin text…"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
        />
        <button style={S.searchBtn} onClick={doSearch} disabled={searching}>
          {searching ? '…' : 'Search'}
        </button>
        <button style={S.navBtn} onClick={() => navigate('/ocr')}>
          Image OCR
        </button>
        <button style={S.navBtn} onClick={() => navigate('/pdf-reader')}>
          PDF Reader
        </button>
      </nav>

      {/* Main */}
      <div style={S.main}>
        {/* Search results */}
        {searchResults !== null && (
          <div style={S.searchResults}>
            <div style={{ fontSize: '14px', color: '#6b4c2a', marginBottom: '8px' }}>
              {searchResults.length === 0
                ? 'No results found.'
                : `${searchResults.length} result(s) found.`}
            </div>
            {searchResults.slice(0, 20).map((r, i) => (
              <div
                key={i}
                style={S.searchResultItem}
                onClick={() => navigate(`/reader/${r.book_id}`)}
              >
                <div style={S.searchResultMeta}>
                  {r.book_title} &middot; {r.chapter_title || `Chapter ${r.chapter_number}`}
                </div>
                <div style={S.searchResultText} dangerouslySetInnerHTML={{ __html: highlightText(r.text.substring(0, 200), searchQ) }} />
              </div>
            ))}
          </div>
        )}

        {/* Search hint / books when no search */}
        {searchResults === null && (
          <>
            <div style={S.sectionTitle}>{'\uD83D\uDCD6'} Books</div>

            {loading && <div style={S.loading}>Loading books...</div>}

            <div style={S.bookGrid}>
              {books.map(book => (
                <div
                  key={book.id}
                  style={S.bookCard}
                  onClick={() => navigate(`/reader/${book.id}`)}
                >
                  <div style={S.bookTitle}>{book.title}</div>
                  <div style={S.bookAuthor}>{book.author}</div>
                  <div style={S.bookDesc}>
                    {book.book_count} books &middot; Click any word to analyze
                  </div>
                  <div style={S.readBtn}>Read</div>
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
          </>
        )}
      </div>

      {/* Footer */}
      <div style={S.footer}>
        {'\u2766'} Latin Reader
      </div>
    </div>
  );
}
