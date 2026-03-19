import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import Editor from '../components/Editor';
import { getAccessToken } from '../api';

export default function EditorPage({ 
  docId, setDocId, documentData, setDocumentData, loading,
  loadDocument, connectWebSocket, disconnectWebSocket,
  lastSnapshotRef, isTypingRef, isSelectingRef,
  updateBlock, handleDelete, addBlockAfter, isReadOnly
}) {
  const { id } = useParams();

  useEffect(() => {
    setDocId(id);
    let isMounted = true;
    
    if (id) {
      loadDocument(id).then(() => {
        if (!isMounted) return;
        const token = getAccessToken();
        if (token) {
          connectWebSocket(id, token);
        }
      });
    }

    return () => {
      isMounted = false;
      disconnectWebSocket();
    };
  }, [id, setDocId, loadDocument, connectWebSocket, disconnectWebSocket]);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <div className="loading-text">Loading document...</div>
      </div>
    );
  }

  return (
    <div className="document-panel">
      <div className="panel-content">
        <div className="document-container">
          <div className="document-inner-scroller">
            {isReadOnly && (
              <div className="read-only-banner">
                 View-only mode: Document is locked or limit reached
              </div>
            )}
            <Editor
              docId={id}
              documentData={documentData}
              lastSnapshotRef={lastSnapshotRef}
              isTypingRef={isTypingRef}
              isSelectingRef={isSelectingRef}
              setDocumentData={setDocumentData}
              onUpdate={updateBlock}
              onDelete={handleDelete}
              onAddAfter={addBlockAfter}
              isReadOnly={isReadOnly}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
