import React from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default function DocPreview({ content, onSave, loading }) {
  const html = DOMPurify.sanitize(marked(content || ''));

  return (
    <div className="canvas-panel">
      <div className="canvas-header">
        <h3>Generated Document</h3>
        <button className="btn btn-primary" onClick={onSave} disabled={loading}>
          {loading ? 'Saving...' : 'Confirm & Save'}
        </button>
      </div>
      <div 
        className="canvas-content"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
