import React from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default function CanvasPanel({ content }) {
  const html = DOMPurify.sanitize(marked(content || ''));

  return (
    <div className="canvas-panel">
      <div className="canvas-header">
        <h3>Live Specification</h3>
      </div>
      <div 
        className="canvas-content"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
