import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const API = '';

// ─── Styles ─────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    fontFamily: "'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, 'Times New Roman', serif",
    color: '#2c1810',
    backgroundColor: '#3e2c1a',
    display: 'flex',
    flexDirection: 'column',
  },
  nav: {
    padding: '12px 24px',
    backgroundColor: '#2c1810',
    borderBottom: '2px solid #8b4513',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap' as const,
  },
  navTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#d4a76a',
    letterSpacing: '1px',
  },
  navLink: {
    padding: '6px 14px',
    borderRadius: '3px',
    border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: 'Georgia, serif',
  },
  navLinkActive: {
    padding: '6px 14px',
    borderRadius: '3px',
    border: '1px solid #d4a76a',
    backgroundColor: '#d4a76a',
    color: '#1a0f08',
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: 'Georgia, serif',
    fontWeight: 'bold',
  },
  mainContent: {
    flex: 1,
    padding: '24px',
    maxWidth: '800px',
    width: '100%',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  card: {
    backgroundColor: '#ede0c8',
    borderRadius: '8px',
    border: '2px solid #5a3d2b',
    overflow: 'hidden',
    boxShadow: '2px 2px 8px rgba(0,0,0,0.3)',
  },
  cardHeader: {
    padding: '12px 16px',
    backgroundColor: '#2c1810',
    color: '#d4a76a',
    fontSize: '15px',
    fontWeight: 'bold',
    letterSpacing: '0.5px',
    fontFamily: 'Georgia, serif',
  },
  cardBody: {
    padding: '16px',
  },
  // Upload zone
  uploadZone: {
    border: '2px dashed #8b4513',
    borderRadius: '8px',
    padding: '40px 20px',
    textAlign: 'center' as const,
    cursor: 'pointer',
    backgroundColor: '#faf0dc',
    transition: 'background 0.15s',
    marginBottom: '12px',
  },
  uploadText: {
    fontSize: '16px',
    color: '#6b4c2a',
    fontFamily: 'Georgia, serif',
  },
  uploadHint: {
    fontSize: '12px',
    color: '#8b7355',
    marginTop: '8px',
    fontStyle: 'italic',
  },
  preview: {
    maxWidth: '100%',
    maxHeight: '300px',
    borderRadius: '4px',
    border: '1px solid #c4a77d',
    display: 'block',
    margin: '0 auto',
  },
  button: {
    padding: '8px 20px',
    borderRadius: '4px',
    border: '1px solid #8b4513',
    backgroundColor: '#5a3d2b',
    color: '#e8d5b0',
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: 'Georgia, serif',
  },
  buttonRow: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'center',
    marginTop: '12px',
  },
  loading: {
    color: '#8b7355',
    fontSize: '14px',
    padding: '12px',
    fontStyle: 'italic',
    textAlign: 'center' as const,
  },
  error: {
    color: '#8b1a1a',
    fontSize: '14px',
    padding: '10px',
    borderLeft: '3px solid #8b1a1a',
    backgroundColor: '#fce8e6',
    margin: '8px 0',
    borderRadius: '3px',
  },
  resultTextArea: {
    width: '100%',
    minHeight: '120px',
    padding: '12px',
    fontSize: '15px',
    fontFamily: "'Palatino Linotype', Georgia, serif",
    border: '1px solid #c4a77d',
    borderRadius: '4px',
    backgroundColor: '#faf0dc',
    color: '#2c1810',
    resize: 'vertical' as const,
    lineHeight: '1.6',
    boxSizing: 'border-box' as const,
  },
  wordAnalysis: {
    backgroundColor: '#fdf5e6',
    borderRadius: '6px',
    padding: '8px 12px',
    marginBottom: '6px',
    border: '1px solid #c4a77d',
  },
  word: {
    fontWeight: 'bold',
    fontSize: '14px',
    color: '#3e2c1a',
  },
  pos: {
    fontSize: '12px',
    color: '#6b4c2a',
    fontStyle: 'italic',
  },
  translation: {
    fontSize: '13px',
    color: '#386e3a',
  },
};

export default function OCRPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    full_text: string;
    lines: { text: string; bbox?: number[] }[];
    words?: { word: string; analyses: any[] }[];
    error?: string;
  } | null>(null);
  const [lang, setLang] = useState('en');
  const [modelType, setModelType] = useState<'print' | 'manuscript'>('print');

  const handleFileSelect = useCallback((file: File | null) => {
    if (!file) return;
    setImageFile(file);
    setError(null);
    setResult(null);

    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files?.[0] ?? null);
  }, [handleFileSelect]);

  const handleOCR = useCallback(async (analyze: boolean) => {
    if (!imageFile) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('model_type', modelType);
      if (analyze) formData.append('lang', lang);

      const endpoint = analyze ? '/api/ocr/analyze' : '/api/ocr';
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setError(`OCR error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [imageFile, lang]);

  return (
    <div style={S.container}>
      {/* Nav */}
      <nav style={S.nav}>
        <span style={S.navTitle}>{'\u2766'} Latin Reader</span>
        <span style={S.navLink} onClick={() => navigate('/')}>Home</span>
        <span style={S.navLink} onClick={() => navigate('/reader')}>Read</span>
        <span style={S.navLinkActive}>OCR</span>
      </nav>

      <div style={S.mainContent}>
        <div style={S.card}>
          <div style={S.cardHeader}>{'\uD83D\uDCF7'} Latin Text OCR</div>
          <div style={S.cardBody}>
            {/* Upload zone */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <div
              style={S.uploadZone}
              onClick={handleUploadClick}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = '#f5e6c8'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = '#faf0dc'; }}
            >
              {imagePreview ? (
                <img src={imagePreview} alt="Preview" style={S.preview} />
              ) : (
                <>
                  <div style={S.uploadText}>{'\uD83D\uDCC2'} Click or drop an image here</div>
                  <div style={S.uploadHint}>
                    Supports JPG, PNG, GIF — scans of Latin text pages
                  </div>
                </>
              )}
            </div>

            {/* Buttons */}
            {/* Model type toggle */}
            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginBottom: '10px' }}>
              <button
                style={{
                  padding: '4px 12px',
                  borderRadius: '3px',
                  border: '1px solid #8b4513',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontFamily: 'Georgia, serif',
                  backgroundColor: modelType === 'print' ? '#d4a76a' : '#faf0dc',
                  color: modelType === 'print' ? '#1a0f08' : '#6b4c2a',
                  fontWeight: modelType === 'print' ? 'bold' : 'normal',
                }}
                onClick={() => setModelType('print')}
              >
                Printed Text
              </button>
              <button
                style={{
                  padding: '4px 12px',
                  borderRadius: '3px',
                  border: '1px solid #8b4513',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontFamily: 'Georgia, serif',
                  backgroundColor: modelType === 'manuscript' ? '#d4a76a' : '#faf0dc',
                  color: modelType === 'manuscript' ? '#1a0f08' : '#6b4c2a',
                  fontWeight: modelType === 'manuscript' ? 'bold' : 'normal',
                }}
                onClick={() => setModelType('manuscript')}
              >
                Manuscript
              </button>
            </div>

            <div style={S.buttonRow}>
              <button style={S.button} onClick={() => handleOCR(false)} disabled={loading || !imageFile}>
                {loading ? 'Recognizing…' : 'Recognize Text'}
              </button>
              <button style={{ ...S.button, backgroundColor: '#6b4c2a' }}
                onClick={() => handleOCR(true)} disabled={loading || !imageFile}>
                {loading ? 'Analyzing…' : 'Recognize & Analyze'}
              </button>
              {imageFile && (
                <button style={{ ...S.button, backgroundColor: '#4a3520' }}
                  onClick={() => { setImageFile(null); setImagePreview(null); setResult(null); setError(null); }}>
                  Clear
                </button>
              )}
            </div>

            {error && <div style={S.error}>{error}</div>}
            {loading && <div style={S.loading}>Processing image with Kraken OCR…</div>}
          </div>
        </div>

        {/* Results */}
        {result && (
          <div style={S.card}>
            <div style={S.cardHeader}>{'\uD83D\uDCDD'} Recognition Result</div>
            <div style={S.cardBody}>
              <textarea style={S.resultTextArea} readOnly value={result.full_text} />

              {result.words && result.words.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#2c1810', marginBottom: '8px', borderBottom: '1px solid #c4a77d', paddingBottom: '4px' }}>
                    Word Analysis ({result.words.length} words)
                  </div>
                  {result.words.map((w, i) => (
                    <div key={i} style={S.wordAnalysis}>
                      <div style={S.word}>{w.word}</div>
                      {w.analyses.length > 0 ? w.analyses.map((a, j) => (
                        <div key={j} style={{ marginLeft: '12px', marginTop: '2px' }}>
                          <span style={S.pos}>{a.part_of_speech}</span>
                          {a.meaning && <span style={S.translation}> — {a.meaning}</span>}
                          {a.morphology && <span style={{ fontSize: '11px', color: '#7b3f9e' }}> [{a.morphology}]</span>}
                        </div>
                      )) : (
                        <div style={{ fontSize: '11px', color: '#8b7355', marginLeft: '12px' }}>Not found in dictionary</div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {result.lines && result.lines.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#2c1810', marginBottom: '4px', borderBottom: '1px solid #c4a77d', paddingBottom: '4px' }}>
                    Lines ({result.lines.length})
                  </div>
                  {result.lines.map((line, i) => (
                    <div key={i} style={{ fontSize: '13px', color: '#2c1810', padding: '2px 0', fontFamily: 'monospace' }}>
                      <span style={{ color: '#8b7355' }}>L{i + 1}:</span> {line.text}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
