import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type {
  BookData,
  ChapterData,
  ParseResult,
  DictEntry,
  AnalyzeResponse,
} from '../types/latin';

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
    padding: '20px',
    backgroundColor: '#2c1810',
    borderBottom: '3px solid #8b4513',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#d4a76a',
    fontFamily: 'Georgia, serif',
    cursor: 'pointer',
  },
  main: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
  },
  leftPanel: {
    flex: 1,
    overflowY: 'auto',
    backgroundColor: '#fdf5e6',
    padding: '20px',
  },
  rightPanel: {
    width: '360px',
    minWidth: '280px',
    overflowY: 'auto',
    backgroundColor: '#3e2c1a',
    padding: '16px',
    borderLeft: '2px solid #5a3d2b',
  },
  panelHeader: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#d4a76a',
    borderBottom: '1px solid #8b4513',
    paddingBottom: '6px',
    marginBottom: '12px',
    fontFamily: 'Georgia, serif',
  },
  chapter: {
    marginBottom: '24px',
  },
  chapterTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#8b4513',
    marginBottom: '12px',
    borderBottom: '1px solid #c4a77d',
    paddingBottom: '4px',
  },
  paragraph: {
    marginBottom: '16px',
    lineHeight: '1.8',
    fontSize: '16px',
  },
  word: {
    color: '#2c1810',
    cursor: 'pointer',
    padding: '1px 2px',
    borderRadius: '2px',
    transition: 'background 0.1s',
  },
  // Result cards
  resultCard: {
    borderBottom: '1px solid #5a3d2b',
    padding: '8px 0',
  },
  lemma: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#e8d5b0',
  },
  pos: {
    fontSize: '11px',
    color: '#8b7355',
    fontStyle: 'italic',
  },
  translation: {
    fontSize: '13px',
    color: '#c4a77d',
    fontStyle: 'italic',
    marginTop: '2px',
  },
  morphology: {
    fontSize: '12px',
    color: '#7b3f9e',
    marginTop: '2px',
  },
  // Dict entry
  dictEntry: {
    borderBottom: '1px solid #5a3d2b',
    padding: '8px 0',
  },
  dictMeaning: {
    fontSize: '13px',
    color: '#c4a77d',
    fontStyle: 'italic',
  },
  // Pagination
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
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
  loading: { color: '#8b7355', fontSize: '14px', padding: '8px', fontStyle: 'italic' },
  error: { color: '#8b1a1a', fontSize: '13px', padding: '8px', borderLeft: '3px solid #8b1a1a', backgroundColor: '#fce8e6', margin: '8px 0' },
};

// ─── Helper: split text into clickable words ──────────────────────────────

function renderText(text: string, onClick: (word: string, e: React.MouseEvent) => void) {
  const tokens = text.split(/(\s+|[.,;:!?()\[\]{}"\-])/);
  return tokens.map((token, i) => {
    const isWord = /^[a-zA-Z\u0100-\u024F]+$/.test(token);
    if (isWord) {
      return (
        <span
          key={i}
          style={S.word}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e0b0')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          onClick={(e) => onClick(token.toLowerCase(), e)}
        >
          {token}
        </span>
      );
    }
    return <span key={i}>{token}</span>;
  });
}

// ─── Helper Components ─────────────────────────────────────────────────────

function ParseResultCard({ result }: { result: ParseResult }) {
  return (
    <div style={S.resultCard}>
      <div style={S.lemma}>{result.lemma_form}</div>
      <div style={S.pos}>{result.part_of_speech}</div>
      {result.morphology && <div style={S.morphology}>{result.morphology}</div>}
      {result.translation && <div style={S.translation}>{result.translation}</div>}
    </div>
  );
}

function DictEntryCard({ entry }: { entry: DictEntry }) {
  return (
    <div style={S.dictEntry}>
      <div style={{ fontWeight: 'bold', fontSize: '15px', color: '#e8d5b0' }}>{entry.key}</div>
      <div style={S.pos}>{entry.part_of_speech}</div>
      <div style={S.dictMeaning}>{entry.meaning}</div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────

export default function ReaderPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();

  const [book, setBook] = useState<BookData | null>(null);
  const [popup, setPopup] = useState<{
    word: string;
    x: number;
    y: number;
    parses: ParseResult[];
    dict: DictEntry[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<{
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  } | null>(null);
  const PER_PAGE = 30;

  // Load book
  const loadBook = useCallback(async (id: string, p: number) => {
    setLoading(true);
    setError(null);
    setPopup(null);
    setPagination(null);
    try {
      const res = await fetch(`${API}/api/books/${id}?page=${p}&per_page=${PER_PAGE}&force=0`);
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setBook(null);
      } else {
        setBook(data as BookData);
        setPagination(data.pagination || null);
      }
    } catch (err: any) {
      setError(`Failed to load book: ${err.message}`);
      setBook(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load book on mount / bookId change
  useEffect(() => {
    if (bookId) loadBook(bookId, page);
  }, [bookId, page, loadBook]);

  // Click word -> analyze
  const handleWordClick = useCallback(async (word: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPopup(null);

    try {
      const res = await fetch(`${API}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word }),
      });
      const data: AnalyzeResponse = await res.json();

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
  }, []);

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

  return (
    <div style={S.container}>
      {/* Header */}
      <header style={S.header}>
        <span style={S.title} onClick={() => navigate('/')}>
          {'\u2766'} {book?.title || 'Reader'}
        </span>
      </header>

      {/* Main */}
      <div style={S.main}>
        {/* Left: book text */}
        <div style={S.leftPanel}>
          {error && <div style={S.error}>{error}</div>}
          {loading && <div style={S.loading}>Loading book...</div>}

          {book?.chapters?.map((ch: ChapterData, ci: number) => (
            <div key={ci} style={S.chapter}>
              <div style={S.chapterTitle}>
                {ch.title || `Chapter ${ch.number}`}
              </div>
              {ch.paragraphs.map((para: string, pi: number) => (
                <div key={pi} style={S.paragraph}>
                  {renderText(para, handleWordClick)}
                </div>
              ))}
            </div>
          ))}

          {!loading && !error && !book && (
            <div style={{ color: '#8b7355', fontStyle: 'italic', padding: '20px' }}>
              Book not found.
            </div>
          )}
        </div>

        {/* Right: analysis */}
        <div style={S.rightPanel}>
          <div style={S.panelHeader}>Word Analysis</div>
          {popup && (
            <div ref={popupRef}>
              <div style={{ fontWeight: 'bold', fontSize: '18px', color: '#d4a76a', marginBottom: '8px' }}>
                {popup.word}
              </div>
              {popup.parses.length > 0 && (
                <>
                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b7355', marginBottom: '4px' }}>
                    Analysis
                  </div>
                  {popup.parses.map((p, i) => (
                    <ParseResultCard key={i} result={p} />
                  ))}
                </>
              )}
              {popup.dict.length > 0 && (
                <>
                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b7355', marginTop: '8px', marginBottom: '4px' }}>
                    Dictionary
                  </div>
                  {popup.dict.map((d, i) => (
                    <DictEntryCard key={i} entry={d} />
                  ))}
                </>
              )}
              {popup.parses.length === 0 && popup.dict.length === 0 && (
                <div style={{ color: '#8b7355', fontStyle: 'italic', fontSize: '13px' }}>
                  No analysis found.
                </div>
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
          {!popup && !loading && (
            <div style={{ color: '#6b4c2a', fontStyle: 'italic', fontSize: '13px' }}>
              Click any Latin word to analyze.
            </div>
          )}
        </div>
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div style={S.pagination}>
          <button
            style={pagination.has_prev ? S.pageBtn : S.pageBtnDisabled}
            disabled={!pagination.has_prev}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            {'\u25C0'} Prev
          </button>
          <span style={S.pageInfo}>
            Page {pagination.page} of {pagination.total_pages}
          </span>
          <button
            style={pagination.has_next ? S.pageBtn : S.pageBtnDisabled}
            disabled={!pagination.has_next}
            onClick={() => setPage(p => p + 1)}
          >
            Next {'\u25B6'}
          </button>
        </div>
      )}
    </div>
  );
}
