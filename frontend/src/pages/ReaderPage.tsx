import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type {
  BookData,
  ChapterData,
  ParseResult,
  DictEntry,
  AnalyzeResponse,
  InflectResponse,
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
  dictEntry: {
    borderBottom: '1px solid #5a3d2b',
    padding: '8px 0',
  },
  dictMeaning: {
    fontSize: '13px',
    color: '#c4a77d',
    fontStyle: 'italic',
  },
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

// ─── Helper: escape regex ──────────────────────────────────────────────────

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ─── Helper: highlight text (returns JSX) ──────────────────────────────────

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const escaped = escapeRegex(query);
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase()
      ? <mark key={i} style={{ backgroundColor: '#f7d44a', color: '#2c1810', padding: '0 2px', borderRadius: '2px' }}>{part}</mark>
      : part
  );
}

// ─── Helper: split text into clickable words, preserving HTML tags ────────

function renderText(text: string, onClick: (word: string, e: React.MouseEvent) => void) {
  const parts: React.ReactNode[] = [];
  // Split by HTML tags and text
  const regex = /(<[^>]+>)|([^<]+)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match[1]) {
      // It's an HTML tag — render it as-is
      parts.push(<span key={parts.length} dangerouslySetInnerHTML={{ __html: match[1] }} />);
    } else if (match[2]) {
      // It's plain text — process Markdown bold and URLs
      const plainText = match[2];
      // Process Markdown bold: **text** → <strong>text</strong>
      const boldRegex = /\*\*(.+?)\*\*/g;
      let lastIdx = 0;
      let boldMatch: RegExpExecArray | null;
      const boldSegments: { start: number; end: number; text: string }[] = [];
      while ((boldMatch = boldRegex.exec(plainText)) !== null) {
        boldSegments.push({ start: boldMatch.index, end: boldMatch.index + boldMatch[0].length, text: boldMatch[1] });
      }
      if (boldSegments.length > 0) {
        let pos = 0;
        for (const seg of boldSegments) {
          // Text before bold
          if (seg.start > pos) {
            parts.push(...renderPlainText(plainText.slice(pos, seg.start), onClick));
          }
          // Bold text — render as <strong>
          parts.push(<strong key={parts.length} style={{ color: '#2c1810' }}>{seg.text}</strong>);
          pos = seg.end;
        }
        // Text after last bold
        if (pos < plainText.length) {
          parts.push(...renderPlainText(plainText.slice(pos), onClick));
        }
      } else {
        parts.push(...renderPlainText(plainText, onClick));
      }
    }
  }
  return parts;
}

// Helper: render plain text with clickable words and URL detection
function renderPlainText(text: string, onClick: (word: string, e: React.MouseEvent) => void): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Detect URLs: www.example.com or http://example.com
  const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/g;
  let lastIdx = 0;
  let urlMatch: RegExpExecArray | null;
  while ((urlMatch = urlRegex.exec(text)) !== null) {
    // Text before URL
    if (urlMatch.index > lastIdx) {
      parts.push(...renderWords(text.slice(lastIdx, urlMatch.index), onClick));
    }
    // URL — render as clickable link
    const url = urlMatch[0];
    const href = url.startsWith('http') ? url : `https://${url}`;
    parts.push(
      <a key={parts.length} href={href} target="_blank" rel="noopener noreferrer"
        style={{ color: '#1a6dd4', textDecoration: 'underline', cursor: 'pointer' }}>
        {url}
      </a>
    );
    lastIdx = urlMatch.index + urlMatch[0].length;
  }
  // Text after last URL
  if (lastIdx < text.length) {
    parts.push(...renderWords(text.slice(lastIdx), onClick));
  }
  return parts;
}

// Helper: split text into clickable words and punctuation
function renderWords(text: string, onClick: (word: string, e: React.MouseEvent) => void): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const tokens = text.split(/(\s+|[.,;:!?()\[\]{}"\-])/);
  for (const token of tokens) {
    const isWord = /^[a-zA-Z\u0100-\u024F]+$/.test(token);
    if (isWord) {
      parts.push(
        <span
          key={parts.length}
          style={S.word}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e0b0')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          onClick={(e) => onClick(token.toLowerCase(), e)}
        >
          {token}
        </span>
      );
    } else {
      parts.push(<span key={parts.length}>{token}</span>);
    }
  }
  return parts;
}

// ─── Helper Components ─────────────────────────────────────────────────────

function ParseResultCard({ result, onInflect, highlight }: { result: ParseResult; onInflect?: (lemma: string) => void; highlight?: string }) {
  return (
    <div style={S.resultCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={S.lemma}>{highlightText(result.lemma_form, highlight || '')}</div>
        {onInflect && (
          <button
            onClick={(e) => { e.stopPropagation(); onInflect(result.lemma); }}
            title="Show inflection table"
            style={{
              padding: '1px 6px',
              fontSize: '10px',
              border: '1px solid #8b4513',
              borderRadius: '3px',
              backgroundColor: '#5a3d2b',
              color: '#e8d5b0',
              cursor: 'pointer',
              fontFamily: 'Georgia, serif',
            }}
          >
            {'\uD83D\uDCCA'} Inflect
          </button>
        )}
      </div>
      <div style={S.pos}>{result.part_of_speech}</div>
      {result.morphology && <div style={S.morphology}>{result.morphology}</div>}
      {result.translation && <div style={S.translation}>{result.translation}</div>}
    </div>
  );
}

function DictEntryCard({ entry, highlight }: { entry: DictEntry; highlight?: string }) {
  return (
    <div style={S.dictEntry}>
      <div style={{ fontWeight: 'bold', fontSize: '15px', color: '#e8d5b0' }}>{highlightText(entry.key, highlight || '')}</div>
      <div style={S.pos}>{entry.part_of_speech}</div>
      <div style={S.dictMeaning}>{entry.meaning}</div>
    </div>
  );
}

// ─── Render suggestion with highlight ─────────────────────────────────────

function renderSuggestionHtml(s: any): string {
  const form = s.form || '';
  const lemma = s.lemma || '';
  const pos = s.part_of_speech || '';
  const hl = s.highlight || [];

  let formHtml = '';
  if (hl.length > 0) {
    let last = 0;
    for (const r of hl) {
      formHtml += form.slice(last, r.start);
      formHtml += `<mark style="background-color:#f7d44a;color:#2c1810;padding:0 2px;border-radius:2px">${form.slice(r.start, r.end)}</mark>`;
      last = r.end;
    }
    formHtml += form.slice(last);
  } else {
    formHtml = form;
  }

  return `${formHtml} (${lemma}, ${pos})`;
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
    suggestions?: any[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);
  const [searchWord, setSearchWord] = useState('');
  const [searchingWord, setSearchingWord] = useState(false);
  const [reverseMode, setReverseMode] = useState(false);
  const [textSearchQ, setTextSearchQ] = useState('');
  const [textSearching, setTextSearching] = useState(false);
  const [textSearchResults, setTextSearchResults] = useState<{
    chapter_number: number;
    chapter_title: string;
    paragraph_index: number;
    text: string;
    match_index: number;
  }[] | null>(null);
  const [inflectTable, setInflectTable] = useState<{ lemma: string; table: InflectResponse['table'] } | null>(null);
  const [inflecting, setInflecting] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageInput, setPageInput] = useState('1');
  const [pagination, setPagination] = useState<{
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  } | null>(null);
  const PER_PAGE = 10;

  // ── Edit mode state ──────────────────────────────────────────────────────
  const [editMode, setEditMode] = useState(false);
  const [editFullText, setEditFullText] = useState('');
  const [savingText, setSavingText] = useState(false);
  const [tocOpen, setTocOpen] = useState(false);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [allChapters, setAllChapters] = useState<{ number: number; title: string }[]>([]);
  const [bookmarks, setBookmarks] = useState<{ chapter: number; label: string }[]>([]);
  const chapterRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Load full chapter list (for TOC) — separate from paginated content
  const loadChapterList = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API}/api/books/${id}?page=1&per_page=999999`);
      const data = await res.json();
      if (data.chapters) {
        setAllChapters(data.chapters.map((ch: any) => ({ number: ch.number, title: ch.title })));
      }
    } catch {
      // ignore
    }
  }, []);

  // Load bookmarks
  const loadBookmarks = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API}/api/books/${id}/bookmark`);
      const data = await res.json();
      if (data.bookmarks) {
        setBookmarks(data.bookmarks);
      }
    } catch {
      // ignore
    }
  }, []);

  // Add bookmark
  const addBookmark = useCallback(async (chapter: number) => {
    if (!bookId) return;
    try {
      const res = await fetch(`${API}/api/books/${bookId}/bookmark`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter, label: allChapters.find(c => c.number === chapter)?.title || `Chapter ${chapter}` }),
      });
      const data = await res.json();
      if (data.bookmarks) setBookmarks(data.bookmarks);
    } catch {
      // ignore
    }
  }, [bookId, allChapters]);

  // Remove bookmark
  const removeBookmark = useCallback(async (chapter: number) => {
    if (!bookId) return;
    try {
      const res = await fetch(`${API}/api/books/${bookId}/bookmark`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter }),
      });
      const data = await res.json();
      if (data.bookmarks) setBookmarks(data.bookmarks);
    } catch {
      // ignore
    }
  }, [bookId]);

  // Load book
  const loadBook = useCallback(async (id: string, p: number) => {
    setLoading(true);
    setError(null);
    setPopup(null);
    setPagination(null);
    setEditMode(false);
    setEditFullText('');
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

  // Restore last reading position from localStorage on mount
  useEffect(() => {
    if (bookId) {
      try {
        const saved = localStorage.getItem(`reading_progress_${bookId}`);
        if (saved) {
          const savedPage = parseInt(saved, 10);
          if (!isNaN(savedPage) && savedPage > 0) {
            setPage(savedPage);
            return; // loadBook will be triggered by page change
          }
        }
      } catch { /* ignore */ }
      loadBook(bookId, page);
      loadChapterList(bookId);
      loadBookmarks(bookId);
    }
  }, [bookId]); // only on mount/bookId change

  // Sync pageInput when page changes externally (Prev/Next, keyboard, bookmarks)
  useEffect(() => {
    setPageInput(String(page));
  }, [page]);

  // Save reading progress on every page change
  useEffect(() => {
    if (bookId && page > 0) {
      try {
        localStorage.setItem(`reading_progress_${bookId}`, String(page));
      } catch { /* ignore */ }
    }
  }, [bookId, page]);

  // Load book content when page changes (after initial restore)
  useEffect(() => {
    if (bookId) {
      loadBook(bookId, page);
      loadChapterList(bookId);
      loadBookmarks(bookId);
    }
  }, [bookId, page, loadBook, loadChapterList, loadBookmarks]);

  // Jump to a specific chapter: find the page that contains it
  const jumpToChapter = useCallback(async (chapterNumber: number) => {
    if (!bookId) return;
    setTocOpen(false);

    // Calculate which page this chapter is on by scanning all items
    try {
      const res = await fetch(`${API}/api/books/${bookId}?page=1&per_page=999999`);
      const data = await res.json();
      if (!data.chapters) return;

      // Find the paragraph index of the first paragraph in this chapter
      let paraIndex = 0;
      for (const ch of data.chapters) {
        if (ch.number === chapterNumber) {
          // Found it — calculate page
          const targetPage = Math.floor(paraIndex / PER_PAGE) + 1;
          setPage(targetPage);
          return;
        }
        paraIndex += (ch.paragraphs || []).length;
      }
    } catch {
      // fallback: just go to page 1
      setPage(1);
    }
  }, [bookId]);

  // Search word from header
  const handleSearchWord = useCallback(async () => {
    const word = searchWord.trim();
    if (!word) return;
    setSearchingWord(true);
    setPopup(null);
    try {
      if (reverseMode) {
        const res = await fetch(`${API}/api/reverse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ word }),
        });
        const data = await res.json();
        setPopup({
          word,
          x: 60,
          y: 120,
          parses: [],
          dict: (data.results || []).map((r: any) => ({
            key: r.key,
            part_of_speech: r.part_of_speech,
            meaning: r.meaning,
          })),
        });
      } else {
        const res = await fetch(`${API}/api/fuzzy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ word }),
        });
        const data = await res.json();

        if (data.exact && data.exact.length > 0) {
          setPopup({
            word,
            x: 60,
            y: 120,
            parses: data.exact,
            dict: data.exact.map((pr: any) => ({
              key: pr.lemma,
              part_of_speech: pr.part_of_speech,
              meaning: pr.meaning || '',
            })),
          });
        } else if (data.fuzzy && data.fuzzy.length > 0) {
          setPopup({
            word,
            x: 60,
            y: 120,
            parses: [],
            dict: [],
            suggestions: data.fuzzy,
          });
        } else if (data.prefix && data.prefix.length > 0) {
          setPopup({
            word,
            x: 60,
            y: 120,
            parses: [],
            dict: [],
            suggestions: data.prefix,
          });
        } else {
          setPopup({
            word,
            x: 60,
            y: 120,
            parses: [],
            dict: [],
            suggestions: [],
          });
        }
      }
    } catch (err: any) {
      setError(`Search failed: ${err.message}`);
    } finally {
      setSearchingWord(false);
    }
  }, [searchWord, reverseMode]);

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

  // Jump to a specific paragraph in a chapter: find the page that contains it, then scroll
  const jumpToParagraph = useCallback(async (chapterNumber: number, paragraphIndex: number) => {
    if (!bookId) return;
    setTextSearchResults(null);

    // First, jump to the chapter to find the right page
    try {
      const res = await fetch(`${API}/api/books/${bookId}?page=1&per_page=999999`);
      const data = await res.json();
      if (!data.chapters) return;

      // Find the global paragraph index of the target paragraph
      let globalParaIndex = 0;
      for (const ch of data.chapters) {
        if (ch.number === chapterNumber) {
          globalParaIndex += paragraphIndex;
          const targetPage = Math.floor(globalParaIndex / PER_PAGE) + 1;
          setPage(targetPage);
          // After page loads, scroll to the paragraph
          setTimeout(() => {
            const el = document.getElementById(`para-${chapterNumber}-${paragraphIndex}`);
            if (el) {
              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
              el.style.backgroundColor = '#f7e8c0';
              setTimeout(() => { el.style.backgroundColor = 'transparent'; }, 2000);
            }
          }, 300);
          return;
        }
        globalParaIndex += (ch.paragraphs || []).length;
      }
    } catch {
      // fallback
    }
  }, [bookId]);

  // Search text within current book
  const handleTextSearch = useCallback(async () => {
    const q = textSearchQ.trim();
    if (!q || !bookId) return;
    setTextSearching(true);
    setTextSearchResults(null);
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}&book_id=${bookId}`);
      const data = await res.json();
      setTextSearchResults(data.results || []);
    } catch {
      setTextSearchResults([]);
    } finally {
      setTextSearching(false);
    }
  }, [textSearchQ, bookId]);

  // Fetch inflection table
  const handleInflect = useCallback(async (lemma: string) => {
    setInflecting(lemma);
    setInflectTable(null);
    try {
      const res = await fetch(`${API}/api/inflect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lemma }),
      });
      const data: InflectResponse = await res.json();
      if (data.table) {
        setInflectTable({ lemma, table: data.table });
      } else {
        setInflectTable({ lemma, table: null });
      }
    } catch {
      setInflectTable({ lemma, table: null });
    } finally {
      setInflecting(null);
    }
  }, []);

  // Close popup only when clicking on the left panel's text area (not on interactive elements)
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        const target = e.target as HTMLElement;
        const tag = target.tagName.toLowerCase();
        // Never clear on interactive elements
        if (tag === 'input' || tag === 'button' || tag === 'textarea' || tag === 'select') {
          return;
        }
        // Never clear if clicking inside the right panel
        if (rightPanelRef.current && rightPanelRef.current.contains(target)) {
          return;
        }
        // Only clear if clicking on the left panel's text content (not header, not pagination)
        const leftPanel = target.closest('[class*="leftPanel"]');
        if (leftPanel) {
          setPopup(null);
        }
      }
    };
    if (popup) {
      document.addEventListener('mousedown', handler);
      return () => document.removeEventListener('mousedown', handler);
    }
  }, [popup]);

  // ── Keyboard shortcuts: ← → for page navigation ────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && pagination?.has_prev) {
        setPage(p => Math.max(1, p - 1));
      } else if (e.key === 'ArrowRight' && pagination?.has_next) {
        setPage(p => p + 1);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [pagination]);

  // ── Edit mode handlers ──────────────────────────────────────────────────

  const enterEditMode = useCallback(() => {
    setEditMode(true);
    // Merge all paragraphs from all chapters into one big text block
    let fullText = '';
    if (book) {
      book.chapters.forEach((ch, ci) => {
        if (ci > 0) fullText += '\n\n';
        fullText += `[${ch.title || `Chapter ${ch.number}`}]\n`;
        ch.paragraphs.forEach((para, pi) => {
          if (pi > 0) fullText += '\n\n';
          fullText += para;
        });
      });
    }
    setEditFullText(fullText);
  }, [book]);

  const cancelEdit = useCallback(() => {
    setEditMode(false);
    setEditFullText('');
  }, []);

  const saveEdits = useCallback(async () => {
    if (!bookId || !book) return;
    setSavingText(true);
    try {
      // Parse the edited text back into paragraphs.
      // Split by double newlines, then group into chapters.
      const lines = editFullText.split('\n');
      const paragraphs: string[] = [];
      let currentPara = '';
      for (const line of lines) {
        if (line.trim() === '' && currentPara) {
          paragraphs.push(currentPara.trim());
          currentPara = '';
        } else {
          currentPara += (currentPara ? ' ' : '') + line;
        }
      }
      if (currentPara.trim()) paragraphs.push(currentPara.trim());

      // Rebuild: skip chapter title lines (lines starting with '[')
      let paraIdx = 0;
      const promises: Promise<Response>[] = [];
      book.chapters.forEach((ch) => {
        ch.paragraphs.forEach((_para, pi) => {
          // Skip chapter title markers in the edited text
          while (paraIdx < paragraphs.length && paragraphs[paraIdx].startsWith('[') && paragraphs[paraIdx].endsWith(']')) {
            paraIdx++;
          }
          const newText = paraIdx < paragraphs.length ? paragraphs[paraIdx] : '';
          paraIdx++;
          if (newText && newText !== _para) {
            promises.push(
              fetch(`${API}/api/books/${bookId}/text`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  chapter_number: ch.number,
                  paragraph_index: pi,
                  text: newText,
                }),
              })
            );
          }
        });
      });
      await Promise.all(promises);
      if (bookId) loadBook(bookId, page);
      setEditMode(false);
      setEditFullText('');
    } catch (err: any) {
      setError(`Failed to save: ${err.message}`);
    } finally {
      setSavingText(false);
    }
  }, [bookId, book, editFullText, loadBook, page]);

  return (
    <div style={S.container}>
      {/* Header */}
      <header style={S.header}>
        <span style={S.title} onClick={() => navigate('/')}>
          {'\u2766'} {book?.title || 'Reader'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button onClick={() => navigate('/')} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
            {'\u2190'} Home
          </button>
          {/* Edit mode toggle */}
          {!editMode ? (
            <button onClick={enterEditMode} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#2d5a2e', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
              {'\u270F'} Edit
            </button>
          ) : (
            <>
              <button onClick={saveEdits} disabled={savingText} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#2d5a2e', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
                {savingText ? '\u2026' : '\u2714'} Done
              </button>
              <button onClick={cancelEdit} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
                {'\u2715'} Cancel
              </button>
            </>
          )}
          <input value={textSearchQ} onChange={e => setTextSearchQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleTextSearch(); }} placeholder="Search in this book\u2026" style={{ padding: '5px 10px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#faf0dc', color: '#2c1810', fontSize: '12px', fontFamily: 'Georgia, serif', outline: 'none', width: '160px' }} />
          <button onClick={handleTextSearch} disabled={textSearching} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
            {textSearching ? '\u2026' : '\uD83D\uDD0D'}
          </button>
          <button onClick={() => setReverseMode(m => !m)} title={reverseMode ? 'Switch to Latin\u2192English' : 'Switch to English\u2192Latin'} style={{ padding: '5px 8px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: reverseMode ? '#2d5a2e' : '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontSize: '11px', fontFamily: 'Georgia, serif', fontWeight: 'bold' }}>
            {reverseMode ? 'Eng\u2192Lat' : 'Lat\u2192Eng'}
          </button>
          <input value={searchWord} onChange={e => setSearchWord(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleSearchWord(); }} placeholder="Search any Latin word\u2026" style={{ padding: '5px 10px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#faf0dc', color: '#2c1810', fontSize: '12px', fontFamily: 'Georgia, serif', outline: 'none', width: '180px' }} />
          <button onClick={handleSearchWord} disabled={searchingWord} style={{ padding: '5px 12px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#5a3d2b', color: '#e8d5b0', cursor: 'pointer', fontSize: '12px', fontFamily: 'Georgia, serif' }}>
            {searchingWord ? '\u2026' : '\uD83D\uDD0D'}
          </button>
        </div>
      </header>

      {/* Main */}
      <div style={S.main}>
        {/* Left: book text */}
        <div style={S.leftPanel}>
          {error && <div style={S.error}>{error}</div>}
          {loading && <div style={S.loading}>Loading book...</div>}

          {editMode && (
            <div style={{ marginBottom: '12px', padding: '8px 12px', backgroundColor: '#f0e8d0', border: '1px solid #c4a77d', borderRadius: '4px', fontSize: '13px', color: '#6b4c2a' }}>
              {'\u270F'} Edit mode: edit all text on this page freely. Press <b>Done</b> to save permanently.
            </div>
          )}

          {textSearchResults !== null && (
            <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#faf0dc', border: '1px solid #c4a77d', borderRadius: '4px' }}>
              <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#8b4513', marginBottom: '6px' }}>
                Search results for "{textSearchQ}"
                <span style={{ marginLeft: '10px', cursor: 'pointer', color: '#8b7355', fontWeight: 'normal', fontSize: '12px' }} onClick={() => setTextSearchResults(null)}>
                  {'\u2715'} Clear
                </span>
              </div>
              {textSearchResults.length === 0 ? (
                <div style={{ color: '#8b7355', fontStyle: 'italic', fontSize: '13px' }}>No results found.</div>
              ) : (
                textSearchResults.slice(0, 20).map((r, i) => (
                  <div key={i}
                    onClick={() => jumpToParagraph(r.chapter_number, r.paragraph_index)}
                    style={{ padding: '6px 0', borderBottom: '1px solid #e0d0b0', cursor: 'pointer' }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e8d0')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div style={{ fontSize: '11px', color: '#6b4c2a', fontStyle: 'italic' }}>
                      {r.chapter_title || `Chapter ${r.chapter_number}`}
                    </div>
                    <div style={{ fontSize: '14px', color: '#2c1810', lineHeight: '1.5' }}
                      dangerouslySetInnerHTML={{
                        __html: r.text.substring(0, 200).replace(
                          new RegExp(`(${escapeRegex(textSearchQ)})`, 'gi'),
                          '<mark style="background-color:#f7d44a;color:#2c1810;padding:0 2px;border-radius:2px">$1</mark>'
                        )
                      }}
                    />
                  </div>
                ))
              )}
              {textSearchResults.length > 20 && (
                <div style={{ fontSize: '12px', color: '#8b7355', marginTop: '6px' }}>
                  Showing 20 of {textSearchResults.length} results.
                </div>
              )}
            </div>
          )}

          {/* Table of Contents — shows ALL chapters (not just current page) */}
          {allChapters.length > 1 && !editMode && (
            <div style={{ marginBottom: '8px', border: '1px solid #c4a77d', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                onClick={() => setTocOpen(o => !o)}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#f0e8d0',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  color: '#8b4513',
                  fontFamily: 'Georgia, serif',
                }}
              >
                <span>{'\uD83D\uDCD6'} Table of Contents ({allChapters.length})</span>
                <span style={{ fontSize: '12px', color: '#8b7355' }}>{tocOpen ? '\u25B2' : '\u25BC'}</span>
              </div>
              {tocOpen && (
                <div style={{ padding: '4px 0', backgroundColor: '#fffcf0', maxHeight: '300px', overflowY: 'auto' }}>
                  {allChapters.map((ch) => (
                    <div
                      key={ch.number}
                      onClick={() => jumpToChapter(ch.number)}
                      style={{
                        padding: '7px 12px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        color: '#6b4c2a',
                        borderBottom: '1px solid #f0e8d0',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e8d0')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {ch.title || `Chapter ${ch.number}`}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Bookmarks panel — separate from TOC */}
          {!editMode && (
            <div style={{ marginBottom: '16px', border: '1px solid #c4a77d', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                onClick={() => setBookmarkOpen(o => !o)}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#f0e8d0',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  color: '#8b4513',
                  fontFamily: 'Georgia, serif',
                }}
              >
                <span>{'\uD83D\uDCCD'} Bookmarks ({bookmarks.length})</span>
                <span style={{ fontSize: '12px', color: '#8b7355' }}>{bookmarkOpen ? '\u25B2' : '\u25BC'}</span>
              </div>
              {bookmarkOpen && (
                <div style={{ padding: '4px 0', backgroundColor: '#fffcf0', maxHeight: '300px', overflowY: 'auto' }}>
                  {bookmarks.length === 0 ? (
                    <div style={{ padding: '8px 12px', fontSize: '12px', color: '#8b7355', fontStyle: 'italic' }}>
                      No bookmarks yet. Click a chapter in TOC, then add bookmark.
                    </div>
                  ) : (
                    bookmarks.map((bm) => (
                      <div
                        key={bm.chapter}
                        style={{
                          padding: '7px 12px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: '#6b4c2a',
                          borderBottom: '1px solid #f0e8d0',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                        onClick={() => jumpToChapter(bm.chapter)}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e8d0')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <span>{'\uD83D\uDCCD'} {bm.label}</span>
                        <span
                          onClick={(e) => { e.stopPropagation(); removeBookmark(bm.chapter); }}
                          style={{ fontSize: '11px', color: '#c0392b', cursor: 'pointer', padding: '2px 6px' }}
                          title="Remove bookmark"
                        >
                          {'\u2715'}
                        </span>
                      </div>
                    ))
                  )}
                  {/* Add bookmark button */}
                  <div
                    onClick={() => {
                      // Find current chapter from the book data
                      if (book && book.chapters.length > 0) {
                        addBookmark(book.chapters[0].number);
                      }
                    }}
                    style={{
                      padding: '7px 12px',
                      cursor: 'pointer',
                      fontSize: '12px',
                      color: '#2d5a2e',
                      borderTop: '1px solid #e0d0b0',
                      textAlign: 'center',
                      fontWeight: 'bold',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0e8d0')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    {'\u2795'} Add Bookmark
                  </div>
                </div>
              )}
            </div>
          )}

          {editMode ? (
            <textarea
              value={editFullText}
              onChange={(e) => setEditFullText(e.target.value)}
              style={{
                width: '100%',
                minHeight: '400px',
                flex: 1,
                padding: '12px',
                fontSize: '16px',
                lineHeight: '1.8',
                fontFamily: "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif",
                border: '1px solid #c4a77d',
                borderRadius: '4px',
                backgroundColor: '#fffcf0',
                color: '#2c1810',
                resize: 'vertical',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          ) : (
            book?.chapters?.map((ch: ChapterData, ci: number) => (
              <div key={ci} ref={(el) => { if (el) chapterRefs.current.set(ch.number, el); }} style={S.chapter}>
                <div style={S.chapterTitle}>{ch.title || `Chapter ${ch.number}`}</div>
                {ch.paragraphs.map((para: string, pi: number) => (
                  <div key={pi} id={`para-${ch.number}-${pi}`} style={S.paragraph}>{renderText(para, handleWordClick)}</div>
                ))}
              </div>
            ))
          )}

          {!loading && !error && !book && (
            <div style={{ color: '#8b7355', fontStyle: 'italic', padding: '20px' }}>Book not found.</div>
          )}
        </div>

        {/* Right: analysis */}
        <div ref={rightPanelRef} style={S.rightPanel}>
          <div style={S.panelHeader}>Word Analysis</div>
          {popup && (
            <div ref={popupRef}>
              <div style={{ fontWeight: 'bold', fontSize: '18px', color: '#d4a76a', marginBottom: '8px' }}>
                {popup.word}
              </div>
              {popup.parses.length > 0 && (
                <>
                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b7355', marginBottom: '4px' }}>Analysis</div>
                  {popup.parses.map((p, i) => (
                    <ParseResultCard key={i} result={p} onInflect={handleInflect} highlight={popup.word} />
                  ))}
                </>
              )}
              {popup.dict.length > 0 && (
                <>
                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b7355', marginTop: '8px', marginBottom: '4px' }}>Dictionary</div>
                  {popup.dict.map((d, i) => (
                    <DictEntryCard key={i} entry={d} highlight={popup.word} />
                  ))}
                </>
              )}
              {popup.suggestions && popup.suggestions.length > 0 && (
                <>
                  <div style={{ fontWeight: 'bold', fontSize: '12px', color: '#8b7355', marginTop: '8px', marginBottom: '4px' }}>Did you mean?</div>
                  {popup.suggestions.map((s, i) => (
                    <div key={i} style={{ fontSize: '13px', color: '#c4a77d', padding: '2px 0', borderBottom: '1px solid #5a3d2b' }}
                      dangerouslySetInnerHTML={{ __html: renderSuggestionHtml(s) }}
                    />
                  ))}
                </>
              )}
              {popup.parses.length === 0 && popup.dict.length === 0 && (!popup.suggestions || popup.suggestions.length === 0) && (
                <div style={{ color: '#8b7355', fontStyle: 'italic', fontSize: '13px' }}>No analysis found.</div>
              )}
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

              {inflectTable && (
                <div style={{ marginTop: '12px', borderTop: '2px solid #8b4513', paddingTop: '8px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '13px', color: '#d4a76a', marginBottom: '6px' }}>
                    {'\uD83D\uDCCA'} Inflection: {inflectTable.lemma}
                    <span style={{ marginLeft: '8px', cursor: 'pointer', color: '#8b7355', fontSize: '11px', fontWeight: 'normal' }} onClick={() => setInflectTable(null)}>
                      {'\u2715'} Close
                    </span>
                  </div>
                  {inflectTable.table ? (
                    Object.entries(inflectTable.table).map(([section, rows]) => (
                      <div key={section} style={{ marginBottom: '8px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#8b7355', marginBottom: '2px' }}>{section}</div>
                        {rows.map((row, ri) => (
                          <div key={ri} style={{ fontSize: '12px', color: '#c4a77d', padding: '1px 0', display: 'flex', gap: '8px' }}>
                            <span style={{ color: '#8b7355', minWidth: '80px' }}>{row.case || row.person || ''} {row.number || ''}</span>
                            <span style={{ color: '#e8d5b0' }}>{row.form}</span>
                          </div>
                        ))}
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#8b7355', fontStyle: 'italic', fontSize: '12px' }}>
                      {inflecting === inflectTable.lemma ? 'Loading...' : 'No inflection table available.'}
                    </div>
                  )}
                </div>
              )}
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
          <button style={pagination.has_prev ? S.pageBtn : S.pageBtnDisabled} disabled={!pagination.has_prev} onClick={() => setPage(p => Math.max(1, p - 1))}>
            {'\u25C0'} Prev
          </button>
          <span style={S.pageInfo}>Page {page} of {pagination.total_pages}</span>
          <input type="number" min={1} max={pagination.total_pages} value={pageInput}
            onChange={(e) => {
              setPageInput(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const v = parseInt((e.target as HTMLInputElement).value, 10);
                if (!isNaN(v) && v >= 1 && v <= pagination.total_pages) {
                  setPage(v);
                  setPageInput(String(v));
                }
              } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                setPage(p => Math.max(1, p - 1));
              } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                setPage(p => Math.min(pagination.total_pages, p + 1));
              }
            }}
            style={{ width: '60px', padding: '4px 8px', borderRadius: '3px', border: '1px solid #8b4513', backgroundColor: '#faf0dc', color: '#2c1810', fontSize: '13px', fontFamily: 'Georgia, serif', textAlign: 'center' }}
          />
          <button style={pagination.has_next ? S.pageBtn : S.pageBtnDisabled} disabled={!pagination.has_next} onClick={() => setPage(p => p + 1)}>
            Next {'\u25B6'}
          </button>
        </div>
      )}
    </div>
  );
}
