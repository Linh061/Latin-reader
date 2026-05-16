/** Types for Latin Reader API */

export interface ParseResult {
  lemma: string;
  lemma_form: string;
  part_of_speech: string;
  pos_code: string;
  translation: string;
  morphology: string;
  morpho_code: number;
  model: string;
  radical: string;
  ending: string;
}

export interface DictEntry {
  key: string;
  part_of_speech: string;
  meaning: string;
  age: string;
  frequency: string;
  source: string;
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
    form: string;
    ending: string;
  }[];
}

export interface InflectResponse {
  lemma: string;
  table: InflectionTable | null;
  error?: string;
}
