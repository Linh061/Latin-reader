import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

const HomePage = lazy(() => import('./pages/HomePage'));
const ReaderPage = lazy(() => import('./pages/ReaderPage'));
const OCRPage = lazy(() => import('./pages/OCRPage'));
const PDFReaderPage = lazy(() => import('./pages/PDFReaderPage'));

export default function App() {
  return (
    <Suspense fallback={<div style={{display:'flex',justifyContent:'center',alignItems:'center',height:'100vh',backgroundColor:'#3e2c1a',color:'#d4a76a',fontFamily:'Georgia, serif',fontSize:'18px'}}>Loading…</div>}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/reader/:bookId" element={<ReaderPage />} />
        <Route path="/ocr" element={<OCRPage />} />
        <Route path="/pdf-reader" element={<PDFReaderPage />} />
        <Route path="/pdf-reader/:pdfId" element={<PDFReaderPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
