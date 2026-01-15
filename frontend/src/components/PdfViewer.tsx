import { useState, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import "./PdfViewer.css";

// Configure the worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  /** URL or blob URL to the PDF file */
  file: string | null;
  /** Optional max height for the viewer container */
  maxHeight?: string;
  /** Optional callback when PDF fails to load */
  onError?: (error: Error) => void;
}

export function PdfViewer({ file, maxHeight = "400px", onError }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pageInputValue, setPageInputValue] = useState<string>("1");

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setCurrentPage(1);
    setPageInputValue("1");
    setIsLoading(false);
    setError(null);
  }, []);

  const onDocumentLoadError = useCallback((err: Error) => {
    setIsLoading(false);
    setError("Failed to load PDF");
    console.error("PDF load error:", err);
    onError?.(err);
  }, [onError]);

  const goToPrevPage = () => {
    setCurrentPage((prev) => {
      const newPage = Math.max(1, prev - 1);
      setPageInputValue(String(newPage));
      return newPage;
    });
  };

  const goToNextPage = () => {
    setCurrentPage((prev) => {
      const newPage = Math.min(numPages, prev + 1);
      setPageInputValue(String(newPage));
      return newPage;
    });
  };

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageInputValue(e.target.value);
  };

  const handlePageInputBlur = () => {
    const pageNum = parseInt(pageInputValue, 10);
    if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= numPages) {
      setCurrentPage(pageNum);
    } else {
      setPageInputValue(String(currentPage));
    }
  };

  const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handlePageInputBlur();
    }
  };

  if (!file) {
    return (
      <div className="pdf-viewer pdf-viewer-empty">
        <p>No PDF selected</p>
      </div>
    );
  }

  return (
    <div className="pdf-viewer">
      {/* Navigation controls */}
      <div className="pdf-viewer-controls">
        <button
          type="button"
          onClick={goToPrevPage}
          disabled={currentPage <= 1 || isLoading}
          className="pdf-nav-button"
          aria-label="Previous page"
        >
          &lt; Prev
        </button>
        <div className="pdf-page-info">
          <input
            type="text"
            value={pageInputValue}
            onChange={handlePageInputChange}
            onBlur={handlePageInputBlur}
            onKeyDown={handlePageInputKeyDown}
            className="pdf-page-input"
            disabled={isLoading || numPages === 0}
            aria-label="Page number"
          />
          <span className="pdf-page-total">/ {numPages || "?"}</span>
        </div>
        <button
          type="button"
          onClick={goToNextPage}
          disabled={currentPage >= numPages || isLoading}
          className="pdf-nav-button"
          aria-label="Next page"
        >
          Next &gt;
        </button>
      </div>

      {/* PDF Document */}
      <div className="pdf-viewer-container" style={{ maxHeight }}>
        {error ? (
          <div className="pdf-viewer-error">
            <p>{error}</p>
          </div>
        ) : (
          <Document
            file={file}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="pdf-viewer-loading">
                <span className="pdf-loading-spinner"></span>
                <p>Loading PDF...</p>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              loading={
                <div className="pdf-page-loading">
                  <span className="pdf-loading-spinner"></span>
                </div>
              }
            />
          </Document>
        )}
      </div>
    </div>
  );
}

