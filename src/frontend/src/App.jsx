import { useCallback, useEffect, useState } from 'react';
import { useAuth } from './features/auth/context/AuthContext';
import Login from './features/auth/components/Login';
import Register from './features/auth/components/Register';
import Dashboard from './features/dashboard/components/Dashboard';
import ProjectDetail from './features/dashboard/components/ProjectDetail';
import Editor from './features/editor/components/Editor';
import Toolbar from './features/editor/components/Toolbar';
import { useDocument } from './features/editor/hooks/useDocument';
import ResumeUpload from './features/resume/components/ResumeUpload';
import Sidebar from './shared/components/Sidebar';
import { getAccessToken } from './shared/api/api';

function App() {
  const { user, logout, loading: authLoading } = useAuth();
  const [view, setView] = useState('dashboard'); // 'dashboard', 'project', 'editor', 'resume'
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);

  const {
    docId, setDocId,
    documentData, setDocumentData,
    lastSnapshotRef,
    status,
    syncStatus,
    role,
    isTypingRef,
    isSelectingRef,
    loadDocument,
    updateBlock,
    deleteBlock,
    addBlockAfter,
    connectWebSocket,
    disconnectWebSocket
  } = useDocument();

  // If user just logged in and profile is not complete, show resume upload
  useEffect(() => {
    if (user && !user.is_profile_complete) {
      setView('resume');
    } else if (user && view === 'resume') {
      setView('dashboard');
    }
  }, [user]);

  const handleSelectProject = (id) => {
    setSelectedProjectId(id);
    setView('project');
  };

  const handleSelectDocument = async (id) => {
    setDocId(id);
    const data = await loadDocument(id);
    if (data) {
      setView('editor');
      const token = getAccessToken();
      connectWebSocket(id, token);
    }
  };

  const handleBackToDashboard = () => {
    setSelectedProjectId(null);
    setView('dashboard');
  };

  const handleBackToProject = () => {
    disconnectWebSocket();
    setView('project');
  };

  const handleLogout = () => {
    disconnectWebSocket();
    logout();
    setView('dashboard');
  };

  const handleBlockDelete = useCallback(async (id) => {
    if (role === 'viewer') return;
    const blocks = documentData?.blocks || [];
    const idx = blocks.findIndex(b => b.block_id === id);
    if (idx === -1) return;

    let focusTargetId = null;
    let cursorAt = 'start';

    if (idx > 0) {
      focusTargetId = blocks[idx - 1].block_id;
      cursorAt = 'end';
    } else if (blocks.length > 1) {
      focusTargetId = blocks[idx + 1].block_id;
      cursorAt = 'start';
    }

    setDocumentData(prev => {
      if (!prev) return prev;
      if (prev.blocks.length <= 1) {
        updateBlock(id, '', 'paragraph', true);
        return prev;
      }

      const filtered = prev.blocks.filter(b => b.block_id !== id);
      const withFocus = filtered.map(b => 
        b.block_id === focusTargetId 
          ? { ...b, _focusOnMount: true, _cursorAt: cursorAt } 
          : b
      );
      
      const next = { ...prev, blocks: withFocus };
      lastSnapshotRef.current = JSON.stringify(next);
      return next;
    });

    await deleteBlock(id);
  }, [deleteBlock, role, updateBlock, setDocumentData, documentData, lastSnapshotRef]);

  if (authLoading) {
    return <div className="dashboard-loading">Initializing session...</div>;
  }

  if (!user) {
    return isRegistering ? (
      <Register onToggle={() => setIsRegistering(false)} />
    ) : (
      <Login onToggle={() => setIsRegistering(true)} />
    );
  }

  return (
    <div className="app-shell">
      <Toolbar 
        status={status}
        syncStatus={syncStatus}
        documentData={view === 'editor' ? documentData : null}
        onLogout={handleLogout}
        onBack={view === 'editor' ? handleBackToProject : (view === 'project' ? handleBackToDashboard : null)}
      />

      <div className="app-main-layout">
        {view !== 'resume' && (
          <Sidebar 
            activeProjectId={selectedProjectId}
            onSelectProject={handleSelectProject}
          />
        )}

        <main className="main-content">
          {view === 'resume' && (
            <ResumeUpload onComplete={() => setView('dashboard')} />
          )}

          {view === 'dashboard' && (
            <Dashboard onSelectProject={handleSelectProject} />
          )}

          {view === 'project' && (
            <ProjectDetail 
              projectId={selectedProjectId} 
              onSelectDocument={handleSelectDocument}
              onBack={handleBackToDashboard}
            />
          )}

          {view === 'editor' && (
            <div className="editor-wrapper">
              <div className="editor-page">
                {role === 'viewer' && (
                  <div className="read-only-banner">
                    You are in view-only mode. You cannot edit this document.
                  </div>
                )}
                <Editor 
                  docId={docId}
                  documentData={documentData}
                  lastSnapshotRef={lastSnapshotRef}
                  isTypingRef={isTypingRef}
                  isSelectingRef={isSelectingRef}
                  setDocumentData={setDocumentData}
                  onUpdate={updateBlock}
                  onDelete={handleBlockDelete}
                  onAddAfter={addBlockAfter}
                  isReadOnly={role === 'viewer'}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
