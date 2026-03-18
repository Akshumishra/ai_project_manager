import React from 'react';

export default function ProjectDocuments({ documents, onSelectDocument, onCreateDocument, onRenameDocument, onDeleteDocument }) {
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
        <button className="btn btn-primary" onClick={onCreateDocument}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Document
        </button>
      </div>

      <div className="doc-grid">
        {documents.map(doc => (
          <div key={doc.id} className="doc-card" onClick={() => onSelectDocument(doc.id)}>
            <div className="doc-card-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <div className="doc-card-info" style={{ flex: 1 }}>
              <h3>{doc.title}</h3>
              <p>Created: {new Date(doc.created_at).toLocaleDateString()}</p>
            </div>
            <div className="doc-card-actions" onClick={(e) => e.stopPropagation()}>
              <button
                className="btn-action-doc btn-rename-doc"
                onClick={(e) => onRenameDocument(e, doc.id, doc.title)}
                title="Rename Document"
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
              {!(doc.title.includes('Requirement') || doc.title.includes('Technical')) && (
                <button
                  className="btn-action-doc btn-delete-doc"
                  onClick={(e) => onDeleteDocument(e, doc.id, doc.title)}
                  title="Delete Document"
                  style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}

        {documents.length === 0 && (
          <div className="no-docs">
            <p>No documents in this project yet. Click "New Document" to create one!</p>
          </div>
        )}
      </div>
    </>
  );
}
