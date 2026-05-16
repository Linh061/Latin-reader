import { useState, useCallback } from 'react';
import type {
  ParseResponse,
  DictResponse,
  AnalyzeResponse,
  InflectResponse,
} from '../types/latin';

const API_BASE = '/api';

async function apiPost<T>(endpoint: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export function useLatinApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parse = useCallback(async (word: string, lang = 'en'): Promise<ParseResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiPost<ParseResponse>('/parse', { word, lang });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const dictLookup = useCallback(async (key: string): Promise<DictResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiPost<DictResponse>('/dict', { key });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const analyze = useCallback(async (word: string, lang = 'en'): Promise<AnalyzeResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiPost<AnalyzeResponse>('/analyze', { word, lang });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const inflect = useCallback(async (lemma: string): Promise<InflectResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiPost<InflectResponse>('/inflect', { lemma });
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { parse, dictLookup, analyze, inflect, loading, error };
}
