/** Types for Latin Reader API */

export interface ParseResult {
  lemma: string;
  lemma_form: string;
  part_of_speech: string;
  translation: string;
  morphology: string;
}

export interface DictEntry {
  key: string;
  part_of_speech: string;
  meaning: string;
}

export interface ParseResponse {
  word: string;
  results: ParseResult[];
  count: number;
}

export interface DictResponse {
  key: string;
  results: DictEntry[];
  count: number;
}

export interface AnalyzeResponse {
  word: string;
  parses: ParseResult[];
  dictionary: Record<string, DictEntry[]>;
  parse_count: number;
}

export interface InflectionTable {
  [section: string]: {
    case?: string;
    person?: string;
    number?: string;
    gender?: string;
    form: string;
  }[];
}

export interface InflectResponse {
  lemma: string;
  table: InflectionTable | null;
  error?: string;
}

/** Book reader types */

export interface ChapterData {
  number: number;
  title: string;
  paragraphs: string[];
}

export interface BookData {
  id: string;
  title: string;
  author: string;
  language: string;
  total_chapters: number;
  chapters: ChapterData[];
  pagination: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

/** PDF Reader types */

export interface PdfMeta {
  pdf_id: string;
  title: string;
  total_pages: number;
}

export interface PdfListResponse {
  pdfs: PdfMeta[];
}

export interface PdfUploadResponse {
  pdf_id: string;
  total_pages: number;
  title: string;
}

export interface BookshelfBook {
  pdf_id: string;
  title: string;
  total_pages: number;
  cover_thumb: string | null;
}

export interface BookshelfResponse {
  books: BookshelfBook[];
}

export interface PdfPageResponse {
  page_img: string;
  ocr_text: string;
  lines: { text: string; bbox: number[] | null }[];
  page_num: number;
  total_pages: number;
  title: string;
  cached: boolean;
  ocr_pending?: boolean;
  user_edited?: boolean;
  error?: string;
}

export interface PdfStatusResponse {
  pdf_id: string;
  title: string;
  total_pages: number;
  cached_pages: number;
  error?: string;
}

/** Fuzzy search suggestion type */
export interface Suggestion {
  form: string;
  lemma: string;
  part_of_speech: string;
  highlight: { start: number; end: number }[];
}

/** Vocabulary (生词本) types */


export interface VocabEntry {
  lemma: string;
  lemma_form: string;
  pos: string;
  meaning: string;
  added_at: string;
}

export interface VocabListResponse {
  vocab: VocabEntry[];
  count: number;
}

export interface VocabAddResponse {
  message: string;
  vocab: VocabEntry[];
  count: number;
}
