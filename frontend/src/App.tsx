import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { ParseResult, DictEntry, InflectionTable } from './types/latin';

// ─── Types ──────────────────────────────────────────────────────────────────

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

interface SearchResponse {
  query: string;
  book_id: string | null;
  results: SearchResult[];
  total_results: number;
  pagination: {
    page: number;
    per_page: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface BookContent {
  id: string;
  title: string;
  author: string;
  chapters: {
    number: number;
    title: string;
    paragraphs: string[];
  }[];
  pagination?: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface WordToken {
  text: string;
  isWord: boolean;
}

const PER_PAGE = 30;
const PANEL_HEIGHT = 260;
const SIDEBAR_WIDTH = 380;

// ─── Medieval Parchment Styles ──────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    height: '100vh',
    fontFamily: "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, 'Times New Roman', serif",
    color: '#2c1810',
    backgroundColor: '#3e2c1a',
    overflow: 'hidden',
  },
  // Left side: reader (tall) + optional bottom panel
  leftColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
    position: 'relative' as const,
  },
  readerPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    transition: 'margin-bottom 0.25s ease',
  },
  // Bottom analysis panel — animated
  bottomPanel: {
    position: 'absolute' as const,
    bottom: 0,
    left: 0,
    right: 0,
    height: PANEL_HEIGHT,
    borderTop: '2px solid #5a3d2b',
    backgroundColor: '#ede0c8',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    zIndex: 10,
    transition: 'transform 0.25s ease, opacity 0.2s ease',
  },
  bottomPanelInner: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 16px',
  },
  // Sidebar — animated width
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    backgroundColor: '#f5e6c8',
    borderLeft: '3px solid #5a3d2b',
    transition: 'width 0.25s ease, opacity 0.2s ease',
  },
  sidebarInner: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px',
  },
  toolbar: {
    padding: '10px 16px',
    backgroundColor: '#2c1810',
    color: '#e8d5b0',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap' as const,
    borderBottom: '2px solid #8b4513',
    fontFamily: "'Palatino Linotype', Georgia, serif",
    flexShrink: 0,
  },
  title: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#d4a76a',
    letterSpacing: '1px',
  },
  bookSelect: {
    padding: '6px 10px',
    fontSize: '13px',
    maxWidth: '300px',
    backgroundColor: '#4a3520',
    color: '#e8d5b0',
    border: '1px solid #8b4513',
    borderRadius: '3px',
    fontFamily: 'Georgia, serif',
  },
  textArea: {
    flex: 1,
    padding: '24px 40px',
    fontSize: '17px',
    lineHeight: '2',
    border: 'none',
    outline: 'none',
    overflowY: 'auto',
    fontFamily: "'Palatino Linotype', 'Times New Roman', serif",
    backgroundColor: '#faf0dc',
    color: '#2c1810',
    backgroundImage:
      'radial-gradient(ellipse at 20% 50%, rgba(139,69,19,0.03) 0%, transparent 70%)',
  },
  wordToken: {
    cursor: 'pointer',
    padding: '0 1px',
    borderRadius: '2px',
    whiteSpace: 'pre-wrap' as const,
  },
  manualInput: {
    padding: '6px 10px',
    borderRadius: '3px',
    border: '1px solid #8b4513',
    fontSize: '13px',
    width: '140px',
    backgroundColor: '#4a3520',
    color: '#e8d5b0',
    fontFamily: 'Georgia, serif',
  },
  button: {
    padding: '6px 14px',
    borderRadius: '3px',
    border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: 'Georgia, serif',
  },
  resultCard: {
    backgroundColor: '#fdf5e6',
    borderRadius: '6px',
    padding: '8px 12px',
    marginBottom: '8px',
    border: '1px solid #c4a77d',
    boxShadow: '1px 1px 4px rgba(44,24,16,0.15)',
  },
  lemma: { fontSize: '18px', fontWeight: 'bold', color: '#3e2c1a' },
  pos: { fontSize: '12px', color: '#6b4c2a', marginTop: '1px', fontStyle: 'italic' },
  translation: { fontSize: '14px', color: '#386e3a', marginTop: '4px', fontStyle: 'italic' },
  morphology: { fontSize: '13px', color: '#7b3f9e', marginTop: '2px' },
  dictEntry: {
    backgroundColor: '#fdf5e6',
    borderRadius: '6px',
    padding: '8px 12px',
    marginBottom: '6px',
    border: '1px solid #c4a77d',
  },
  dictMeaning: { fontSize: '13px', color: '#2c1810', marginTop: '3px' },
  dictMeta: { fontSize: '11px', color: '#8b7355', marginTop: '1px' },
  loading: { color: '#8b7355', fontSize: '14px', padding: '8px', fontStyle: 'italic' },
  error: { color: '#8b1a1a', fontSize: '14px', padding: '8px', borderLeft: '3px solid #8b1a1a', backgroundColor: '#fce8e6', margin: '8px 0' },
  tabBar: {
    display: 'flex',
    borderBottom: '2px solid #c4a77d',
    backgroundColor: '#ede0c8',
    flexShrink: 0,
  },
  tab: { padding: '6px 16px', cursor: 'pointer', borderBottom: '2px solid transparent', fontSize: '13px', color: '#8b7355', marginBottom: '-2px' },
  activeTab: { padding: '6px 16px', cursor: 'pointer', borderBottom: '2px solid #3e2c1a', fontSize: '13px', color: '#2c1810', fontWeight: 'bold', marginBottom: '-2px' },
  tableSection: { marginBottom: '12px' },
  tableTitle: { fontSize: '13px', fontWeight: 'bold', color: '#2c1810', marginBottom: '4px', borderBottom: '1px solid #c4a77d', paddingBottom: '3px' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: { border: '1px solid #c4a77d', padding: '3px 6px', backgroundColor: '#ede0c8', color: '#2c1810', textAlign: 'left' },
  td: { border: '1px solid #c4a77d', padding: '3px 6px' },
  chapterTitle: {
    fontSize: '22px', fontWeight: 'bold', color: '#6b2300', marginTop: '32px', marginBottom: '20px',
    textAlign: 'center' as const, letterSpacing: '1px', borderBottom: '1px solid #c4a77d', paddingBottom: '8px',
  },
  paragraph: { marginBottom: '14px', textIndent: '2em', lineHeight: '1.9' },
  dropCap: { marginBottom: '14px', textIndent: '2em', lineHeight: '1.9' },
  paginationBar: {
    display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px',
    padding: '8px 16px', borderTop: '1px solid #c4a77d', backgroundColor: '#ede0c8',
    flexWrap: 'wrap' as const, flexShrink: 0,
  },
  pageBtn: {
    padding: '4px 10px', borderRadius: '3px', border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer',
    fontSize: '12px', fontFamily: 'Georgia, serif',
  },
  pageBtnDisabled: {
    padding: '4px 10px', borderRadius: '3px', border: '1px solid #6b5a4a',
    backgroundColor: '#6b5a4a', color: '#a09080', fontSize: '12px', fontFamily: 'Georgia, serif', opacity: 0.5,
  },
  pageInfo: { fontSize: '13px', color: '#2c1810', fontFamily: 'Georgia, serif' },
  searchResultCard: {
    backgroundColor: '#fdf5e6', borderRadius: '4px', padding: '8px 10px', marginBottom: '8px',
    border: '1px solid #c4a77d', cursor: 'pointer', transition: 'background 0.15s',
  },
  searchResultText: { fontSize: '13px', color: '#2c1810', lineHeight: '1.5', marginTop: '3px' },
  searchResultMeta: { fontSize: '10px', color: '#8b7355', marginBottom: '1px', fontStyle: 'italic' },
  highlight: { backgroundColor: '#d4a76a', padding: '0 2px', borderRadius: '2px', color: '#1a0f08', fontWeight: 'bold' },
  sidebarToolbar: {
    padding: '8px 12px', backgroundColor: '#2c1810',
    display: 'flex', alignItems: 'center', gap: '6px',
    borderBottom: '2px solid #8b4513', flexShrink: 0,
  },
  sidebarSearchInput: {
    flex: 1, padding: '5px 8px', borderRadius: '3px', border: '1px solid #8b4513',
    fontSize: '12px', backgroundColor: '#4a3520', color: '#e8d5b0', fontFamily: 'Georgia, serif', minWidth: 0,
  },
  sidebarPlaceholder: {
    color: '#8b7355', fontSize: '13px', textAlign: 'center' as const, marginTop: '40px', fontStyle: 'italic', lineHeight: '1.6',
  },
  panelClose: {
    padding: '2px 8px', borderRadius: '3px', border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer',
    fontSize: '12px', fontFamily: 'Georgia, serif', lineHeight: '1.4',
  },
};

// ─── Helper Components ─────────────────────────────────────────────────────

function ParseResultCard({ result }: { result: ParseResult }) {
  return (
    <div style={S.resultCard}>
      <div style={S.lemma}>{result.lemma_form}</div>
      <div style={S.pos}>{result.part_of_speech} ({result.pos_code})</div>
      {result.translation && <div style={S.translation}>{result.translation}</div>}
      {result.morphology && <div style={S.morphology}>{result.morphology}</div>}
      <div style={{ fontSize: '10px', color: '#a09080', marginTop: '2px' }}>
        Model: {result.model} | Radical: {result.radical} | Ending: {result.ending}
      </div>
    </div>
  );
}

function DictEntryCard({ entry }: { entry: DictEntry }) {
  return (
    <div style={S.dictEntry}>
      <div style={{ fontWeight: 'bold', fontSize: '15px', color: '#2c1810' }}>{entry.key}</div>
      <div style={S.pos}>{entry.part_of_speech}</div>
      <div style={S.dictMeaning}>{entry.meaning}</div>
      <div style={S.dictMeta}>
        {entry.age && `Aetas: ${entry.age}`}{entry.frequency && ` | Frequentia: ${entry.frequency}`}{entry.source && ` | Fons: ${entry.source}`}
      </div>
    </div>
  );
}

function InflectionView({ table }: { table: InflectionTable }) {
  return (
    <div>
      {Object.entries(table).map(([section, rows]) => (
        <div key={section} style={S.tableSection}>
          <div style={S.tableTitle}>{section}</div>
          <table style={S.table}>
            <thead><tr>
              {rows[0]?.case ? <th style={S.th}>Casus</th> : null}
              {rows[0]?.person ? <th style={S.th}>Persona</th> : null}
              <th style={S.th}>Forma</th>
              <th style={S.th}>Terminatio</th>
            </tr></thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {row.case ? <td style={S.td}>{row.case}</td> : null}
                  {row.person ? <td style={S.td}>{row.person}</td> : null}
                  <td style={S.td}>{row.form}</td>
                  <td style={S.td}>{row.ending || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function tokenize(text: string): WordToken[] {
  const tokens: WordToken[] = [];
  const re = /([\w\u0101\u0113\u012b\u014d\u016b\u0233\u0103\u0115\u012d\u014f\u016d\u0102\u0114\u012c\u014e\u016c\u0100\u0112\u012a\u014c\u016a\u00c2\u00c0\u00ca\u00c8\u00ce\u00cc\u00d4\u00d2\u00db\u00d9]+)|([^]+?)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m[1]) tokens.push({ text: m[1], isWord: true });
    else if (m[2]) tokens.push({ text: m[2], isWord: false });
  }
  return tokens;
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const ql = query.toLowerCase();
  const tl = text.toLowerCase();
  const idx = tl.indexOf(ql);
  if (idx === -1) return text;
  return (<>{text.slice(0, idx)}<span style={S.highlight}>{text.slice(idx, idx + query.length)}</span>{text.slice(idx + query.length)}</>);
}

function SearchResultCard({ result, query, onClick }: { result: SearchResult; query: string; onClick: (r: SearchResult) => void }) {
  const ctx = 60;
  const start = Math.max(0, result.match_index - ctx);
  const end = Math.min(result.text.length, result.match_index + query.length + ctx);
  let snippet = result.text.slice(start, end);
  if (start > 0) snippet = '\u2026' + snippet;
  if (end < result.text.length) snippet = snippet + '\u2026';
  return (
    <div style={S.searchResultCard} onClick={() => onClick(result)}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = '#ede0c8'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = '#fdf5e6'; }}
    >
      <div style={S.searchResultMeta}>{result.book_title} — {result.chapter_title}</div>
      <div style={S.searchResultText}>{highlightText(snippet, query)}</div>
    </div>
  );
}

function renderWordToken(token: WordToken, idx: number, highlightedWord: string | null, onWordClick: (word: string) => void): React.ReactNode {
  if (!token.isWord) return <span key={idx}>{token.text}</span>;
  const clean = token.text.replace(/[.,;:!?()"']/g, '').trim().toLowerCase();
  const isHL = highlightedWord !== null && clean === highlightedWord.toLowerCase();
  return (
    <span key={idx} onClick={() => onWordClick(token.text)} style={{
      ...S.wordToken,
      backgroundColor: isHL ? '#d4a76a' : undefined,
      color: isHL ? '#1a0f08' : undefined,
      fontWeight: isHL ? 'bold' : undefined,
    }} title={clean}>{token.text}</span>
  );
}

const API = '';

export default function App() {
  const [books, setBooks] = useState<BookMeta[]>([]);
  const [selectedBookId, setSelectedBookId] = useState<string>('');
  const [bookContent, setBookContent] = useState<BookContent | null>(null);
  const [selectedWord, setSelectedWord] = useState('');
  const [highlightedWord, setHighlightedWord] = useState<string | null>(null);
  const [parseResults, setParseResults] = useState<ParseResult[]>([]);
  const [dictResults, setDictResults] = useState<DictEntry[]>([]);
  const [inflectionTable, setInflectionTable] = useState<InflectionTable | null>(null);
  const [activeTab, setActiveTab] = useState<'parse' | 'dict' | 'inflect'>('parse');
  const [manualInput, setManualInput] = useState('');
  const [loadingBooks, setLoadingBooks] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Panel visibility
  const [showBottomPanel, setShowBottomPanel] = useState(false);
  const [showSearchSidebar, setShowSearchSidebar] = useState(false);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchPage, setSearchPage] = useState(1);
  const [searchTotalPages, setSearchTotalPages] = useState(1);
  const [loadingSearch, setLoadingSearch] = useState(false);

  const textAreaRef = useRef<HTMLDivElement>(null);

  // ── Effects ──────────────────────────────────────────────────────────

  useEffect(() => {
    fetch(`${API}/api/books`).then(r => r.json()).then(data => {
      setBooks(data.books || []);
      if (data.books?.length > 0) setSelectedBookId(data.books[0].id);
    }).catch(err => setError(`Failed to load books: ${err.message}`)).finally(() => setLoadingBooks(false));
  }, []);

  useEffect(() => {
    if (!selectedBookId) return;
    setLoadingContent(true); setError(null); setBookContent(null);
    setHighlightedWord(null); setSelectedWord(''); setParseResults([]);
    setDictResults([]); setInflectionTable(null); setPage(1);
    setShowBottomPanel(false);
  }, [selectedBookId]);

  useEffect(() => {
    if (!selectedBookId) return;
    setLoadingContent(true);
    fetch(`${API}/api/books/${selectedBookId}?page=${page}&per_page=${PER_PAGE}`)
      .then(r => r.json()).then(data => {
        if (data.error) setError(data.error);
        else { setBookContent(data); setTotalPages(data.pagination?.total_pages ?? 1); }
      }).catch(err => setError(`Failed to load book: ${err.message}`)).finally(() => setLoadingContent(false));
  }, [selectedBookId, page]);

  // ── Word analysis ────────────────────────────────────────────────────

  const handleWordClick = useCallback(async (word: string) => {
    const clean = word.replace(/[.,;:!?()"']/g, '').trim();
    if (!clean) return;
    setSelectedWord(clean);
    setHighlightedWord(clean);
    setActiveTab('parse');
    setShowBottomPanel(true);
    setLoadingAnalyze(true);
    try {
      const res = await fetch(`${API}/api/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ word: clean }),
      });
      const result = await res.json();
      if (result.error) setError(result.error);
      else {
        setParseResults(result.parses || []);
        const allEntries: DictEntry[] = [];
        if (result.dictionary) for (const entries of Object.values(result.dictionary) as any) allEntries.push(...(entries as DictEntry[]));
        setDictResults(allEntries);
      }
    } catch (err: any) { setError(`API error: ${err.message}`); }
    finally { setLoadingAnalyze(false); }
  }, []);

  const handleInflect = useCallback(async (lemma: string) => {
    setActiveTab('inflect');
    try {
      const res = await fetch(`${API}/api/inflect`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lemma }),
      });
      const result = await res.json();
      if (result.table) setInflectionTable(result.table);
    } catch (err: any) { setError(`Inflection error: ${err.message}`); }
  }, []);

  const handleManualLookup = useCallback(async () => {
    if (!manualInput.trim()) return;
    await handleWordClick(manualInput.trim());
  }, [manualInput, handleWordClick]);

  const closeBottomPanel = useCallback(() => {
    setShowBottomPanel(false);
    setHighlightedWord(null);
    setSelectedWord('');
  }, []);

  // ── Search ───────────────────────────────────────────────────────────

  const handleSearch = useCallback(async (q: string, p: number) => {
    if (!q.trim()) return;
    setLoadingSearch(true);
    setSearchPage(p);
    setShowSearchSidebar(true);
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}&page=${p}&per_page=20`);
      const data: SearchResponse = await res.json();
      setSearchResults(data.results || []);
      setSearchTotal(data.total_results);
      setSearchTotalPages(data.pagination?.total_pages ?? 1);
    } catch (err: any) { setError(`Search error: ${err.message}`); }
    finally { setLoadingSearch(false); }
  }, []);

  const goSearchPage = useCallback((p: number) => {
    if (p < 1 || p > searchTotalPages) return;
    handleSearch(searchQuery, p);
  }, [searchQuery, searchTotalPages, handleSearch]);

  const openSearchResult = useCallback((r: SearchResult) => {
    if (r.book_id !== selectedBookId) setSelectedBookId(r.book_id);
    setPage(1); setHighlightedWord(null); setSelectedWord('');
    setParseResults([]); setDictResults([]); setInflectionTable(null);
  }, [selectedBookId]);

  const toggleSearchSidebar = useCallback(() => {
    setShowSearchSidebar(prev => !prev);
  }, []);

  const goToPage = useCallback((p: number) => {
    if (p < 1 || p > totalPages) return;
    setPage(p); setHighlightedWord(null); setSelectedWord('');
    setParseResults([]); setDictResults([]); setInflectionTable(null);
    setShowBottomPanel(false);
    textAreaRef.current?.scrollTo(0, 0);
  }, [totalPages]);

  // ── Render ──────────────────────────────────────────────────────────

  const readerPadding = showBottomPanel ? { paddingBottom: PANEL_HEIGHT } : {};

  return (
    <div style={S.container}>
      {/* ── Left Column ── */}
      <div style={{ ...S.leftColumn, ...readerPadding } as React.CSSProperties}>
        {/* Toolbar */}
        <div style={S.toolbar}>
          <span style={S.title}>{'\u2766'} Latin Reader</span>
          <span style={{ color: '#d4a76a', fontSize: '13px' }}>Choose:</span>
          <select style={S.bookSelect} value={selectedBookId}
            onChange={(e) => setSelectedBookId(e.target.value)} disabled={loadingBooks}>
            {loadingBooks && <option>Loading...</option>}
            {books.map(b => <option key={b.id} value={b.id}>{b.title}</option>)}
          </select>

          <input style={S.manualInput} placeholder="vel verbum inire..." value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleManualLookup()} />
          <button style={S.button} onClick={handleManualLookup}>Quaerere</button>

          <div style={{ flex: 1 }} />

          {/* Search toggle button */}
          <button style={{
            ...S.button, fontSize: '15px', padding: '4px 10px',
            backgroundColor: showSearchSidebar ? '#d4a76a' : '#5a3d2b',
            color: showSearchSidebar ? '#1a0f08' : '#e8d5b0',
          }} onClick={toggleSearchSidebar} title="Toggle search sidebar">
            {'\uD83D\uDD0D'}
          </button>

          {highlightedWord && (
            <span style={{ color: '#d4a76a', fontSize: '12px' }}>
              Lectio: <strong>{highlightedWord}</strong>
            </span>
          )}
        </div>

        {/* Reader */}
        <div style={S.textArea} ref={textAreaRef}>
          {loadingContent && <div style={S.loading}>Loading...</div>}
          {error && <div style={S.error}>{error}</div>}
          {!loadingContent && !error && bookContent && bookContent.chapters.length > 0 && (
            <div>
              {bookContent.chapters.map((ch, ci) => (
                <div key={ci}>
                  <div style={S.chapterTitle}>{'\u2766'} {ch.title} {'\u2766'}</div>
                  {ch.paragraphs.map((p, pi) => (
                    <p key={pi} style={ci === 0 && pi === 0 ? S.dropCap : S.paragraph}>
                      {pi === 0 && ci === 0 ? (() => {
                        const tokens = tokenize(p);
                        if (tokens.length > 0) {
                          const first = tokens[0], rest = tokens.slice(1);
                          return (<>
                            <span style={{ float: 'left', fontSize: '56px', lineHeight: '0.8', paddingRight: '6px', paddingTop: '4px', color: '#6b2300', fontFamily: "'Palatino Linotype', Georgia, serif", fontWeight: 'bold' }}>{first.text}</span>
                            {rest.map((tk, ti) => renderWordToken(tk, ti, highlightedWord, handleWordClick))}
                          </>);
                        } return null;
                      })() : tokenize(p).map((tk, ti) => renderWordToken(tk, ti, highlightedWord, handleWordClick))}
                    </p>
                  ))}
                  {ci < bookContent.chapters.length - 1 && (
                    <div style={{ textAlign: 'center', color: '#a09080', fontSize: '24px', margin: '32px 0', fontFamily: 'Georgia, serif' }}>{'\u2766'} {'\u2E19'} {'\u2766'}</div>
                  )}
                </div>
              ))}
            </div>
          )}
          {!loadingContent && !error && !bookContent && !loadingBooks && (
            <div style={{ color: '#8b7355', textAlign: 'center', marginTop: '60px', fontStyle: 'italic' }}>Selige librum ex indice supra.</div>
          )}
        </div>

        {/* Pagination */}
        {bookContent && totalPages > 1 && (
          <div style={S.paginationBar}>
            <button style={page <= 1 ? S.pageBtnDisabled : S.pageBtn} disabled={page <= 1} onClick={() => goToPage(page - 1)}>{'\u2190'} Prior</button>
            {Array.from({ length: Math.min(totalPages, 20) }, (_, i) => i + 1).map(p => (
              <button key={p} style={{ ...S.pageBtn, backgroundColor: p === page ? '#d4a76a' : '#5a3d2b', color: p === page ? '#1a0f08' : '#e8d5b0', fontWeight: p === page ? 'bold' : 'normal' }} onClick={() => goToPage(p)}>{p}</button>
            ))}
            <button style={page >= totalPages ? S.pageBtnDisabled : S.pageBtn} disabled={page >= totalPages} onClick={() => goToPage(page + 1)}>Sequens {'\u2192'}</button>
            <span style={S.pageInfo}>{page} / {totalPages}</span>
          </div>
        )}

        {/* ── Animated Bottom Panel ── */}
        <div style={{
          ...S.bottomPanel,
          transform: showBottomPanel ? 'translateY(0)' : 'translateY(100%)',
          opacity: showBottomPanel ? 1 : 0,
          pointerEvents: showBottomPanel ? 'auto' : 'none',
        }}>
          {/* Tab bar */}
          {selectedWord && (
            <div style={S.tabBar}>
              <div style={activeTab === 'parse' ? S.activeTab : S.tab} onClick={() => setActiveTab('parse')}>Analysis ({parseResults.length})</div>
              <div style={activeTab === 'dict' ? S.activeTab : S.tab} onClick={() => setActiveTab('dict')}>Dictionary ({dictResults.length})</div>
              <div style={activeTab === 'inflect' ? S.activeTab : S.tab} onClick={() => setActiveTab('inflect')}>Inflection</div>
              <div style={{ flex: 1 }} />
              <div style={{ fontSize: '12px', color: '#6b4c2a', display: 'flex', alignItems: 'center', gap: '8px', paddingRight: '8px' }}>
                <strong style={{ fontSize: '14px', color: '#2c1810' }}>{selectedWord}</strong>
                <button style={S.panelClose} onClick={closeBottomPanel}>{'\u2715'}</button>
              </div>
            </div>
          )}
          <div style={S.bottomPanelInner}>
            {loadingAnalyze && <div style={S.loading}>Analyzing...</div>}
            {!loadingAnalyze && activeTab === 'parse' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {parseResults.length === 0 && <div style={{ color: '#8b7355', fontSize: '13px', fontStyle: 'italic' }}>Non inventum.</div>}
                {parseResults.map((r, i) => (
                  <div key={i} style={{ flex: '1 1 280px', maxWidth: '400px' }}>
                    <ParseResultCard result={r} />
                    <button style={{ ...S.button, backgroundColor: '#6b4c2a', fontSize: '11px', padding: '3px 8px', marginTop: '-4px', marginBottom: '4px' }}
                      onClick={() => handleInflect(r.lemma)}>Declina {r.part_of_speech}</button>
                  </div>
                ))}
              </div>
            )}
            {!loadingAnalyze && activeTab === 'dict' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {dictResults.length === 0 && <div style={{ color: '#8b7355', fontSize: '13px', fontStyle: 'italic' }}>Non repertum.</div>}
                {dictResults.map((e, i) => <div key={i} style={{ flex: '1 1 280px', maxWidth: '400px' }}><DictEntryCard entry={e} /></div>)}
              </div>
            )}
            {!loadingAnalyze && activeTab === 'inflect' && (
              <div>{inflectionTable ? <InflectionView table={inflectionTable} /> : <div style={{ color: '#8b7355', fontSize: '13px', fontStyle: 'italic' }}>Preme "Declina" in analysi.</div>}</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Animated Right Sidebar (Search) ── */}
      <div style={{
        ...S.sidebar,
        width: showSearchSidebar ? SIDEBAR_WIDTH : 0,
        opacity: showSearchSidebar ? 1 : 0,
      }}>
        <div style={S.sidebarToolbar}>
          <span style={{ color: '#d4a76a', fontSize: '13px', whiteSpace: 'nowrap' }}>{'\uD83D\uDD0D'}</span>
          <input style={S.sidebarSearchInput} placeholder="Search in books..." value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && searchQuery.trim()) handleSearch(searchQuery.trim(), 1); }} />
          <button style={{ ...S.button, fontSize: '11px', padding: '4px 8px' }}
            onClick={() => searchQuery.trim() && handleSearch(searchQuery.trim(), 1)} disabled={loadingSearch}>
            {loadingSearch ? '...' : 'Go'}
          </button>
          <button style={{ ...S.button, fontSize: '10px', padding: '4px 6px', backgroundColor: '#4a3520' }}
            onClick={() => toggleSearchSidebar()}>{'\u2715'}</button>
        </div>
        <div style={S.sidebarInner}>
          {loadingSearch && <div style={S.loading}>Searching...</div>}
          {!loadingSearch && searchResults.length > 0 && (
            <>
              <div style={{ fontSize: '13px', color: '#6b4c2a', marginBottom: '8px' }}>
                <strong style={{ color: '#2c1810' }}>"{searchQuery}"</strong> ({searchTotal} results)
              </div>
              {searchResults.map((r, i) => <SearchResultCard key={i} result={r} query={searchQuery} onClick={openSearchResult} />)}
              {searchTotalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                  <button style={searchPage <= 1 ? S.pageBtnDisabled : S.pageBtn} disabled={searchPage <= 1} onClick={() => goSearchPage(searchPage - 1)}>Prev</button>
                  {Array.from({ length: Math.min(searchTotalPages, 10) }, (_, i) => i + 1).map(p => (
                    <button key={p} style={{ ...S.pageBtn, backgroundColor: p === searchPage ? '#d4a76a' : '#5a3d2b', color: p === searchPage ? '#1a0f08' : '#e8d5b0', padding: '3px 7px', fontSize: '11px' }} onClick={() => goSearchPage(p)}>{p}</button>
                  ))}
                  <button style={searchPage >= searchTotalPages ? S.pageBtnDisabled : S.pageBtn} disabled={searchPage >= searchTotalPages} onClick={() => goSearchPage(searchPage + 1)}>Next</button>
                </div>
              )}
            </>
          )}
          {!loadingSearch && searchResults.length === 0 && !searchQuery && (
            <div style={S.sidebarPlaceholder}>
              {'\uD83D\uDD0D'} Search for words or phrases<br />in the Latin texts.<br />
              <span style={{ fontSize: '11px' }}>Try "Gallia", "Caesar", "bellum"…</span>
            </div>
          )}
          {!loadingSearch && searchResults.length === 0 && searchQuery && (
            <div style={{ color: '#8b7355', fontSize: '13px', fontStyle: 'italic', textAlign: 'center', marginTop: '20px' }}>Non repertum.</div>
          )}
        </div>
      </div>
    </div>
  );
}
