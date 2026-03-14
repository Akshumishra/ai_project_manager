import { useCallback, useEffect, useState } from 'react'
import { useDocument } from './hooks/useDocument'
import Toolbar from './components/Toolbar'
import Editor from './components/Editor'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './components/Login'
import Register from './components/Register'
import Dashboard from './components/Dashboard'
import ProjectDetail from './components/ProjectDetail'
import ResumeUpload from './components/ResumeUpload'
import Sidebar from './components/Sidebar'
import { getAccessToken } from './api'

function AppContent() {
  const { user, isAuthenticated, loading, logout } = useAuth()
  const [showRegister, setShowRegister] = useState(false)
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard', 'project', 'editor'
  const [projectId, setProjectId] = useState(null)
  
  const {
    addBlockAfter,
    connectWebSocket,
    role,
    docId, setDocId,
    documentData, setDocumentData,
    lastSnapshotRef,
    status,
    syncStatus,
    isTypingRef,
    isSelectingRef,
    loadDocument,
    updateBlock,
    deleteBlock,
    disconnectWebSocket,
  } = useDocument()

  const isReadOnly = role === 'viewer'

  // ── Auto-load document if docId changes and we are in editor ────────────────
  useEffect(() => {
    let isMounted = true;
    if (isAuthenticated && docId && currentView === 'editor') {
      loadDocument(docId).then(() => {
        if (!isMounted) return;
        const token = getAccessToken()
        if (token) {
          connectWebSocket(docId, token)
        }
      })
    }
    
    return () => {
      isMounted = false;
      disconnectWebSocket();
    };
  }, [isAuthenticated, docId, currentView, loadDocument, connectWebSocket, disconnectWebSocket])

  const handleDelete = useCallback(async (id) => {
    if (isReadOnly) return
    
    // We get the latest blocks directly to avoid stale closure issues
    setDocumentData(prev => {
      const blocks = prev?.blocks || []
      if (blocks.length <= 1) {
        // If it's the last block, don't delete it - just clear it.
        updateBlock(id, '', 'paragraph')
        return prev
      }
      
      // Proceed with deletion
      deleteBlock(id)
      return prev
    })
  }, [deleteBlock, isReadOnly, updateBlock, setDocumentData])

  const handleSelectProject = (id) => {
    setProjectId(id);
    setCurrentView('project');
  };

  const handleSelectDocument = (id) => {
    setDocId(id);
    setCurrentView('editor');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
    setProjectId(null);
    setDocId(null);
    setDocumentData(null);
  };

  const handleBackToProject = () => {
    setCurrentView('project');
    setDocId(null);
    setDocumentData(null);
  };

  if (loading) return <div className="loading">Loading...</div>

  if (!isAuthenticated) {
    return showRegister ? (
      <Register onToggle={() => setShowRegister(false)} />
    ) : (
      <Login onToggle={() => setShowRegister(true)} />
    )
  }

  if (!user?.is_profile_complete) {
    return <ResumeUpload onComplete={() => setCurrentView('dashboard')} />
  }

  return (
    <div className="app-shell">
      <Toolbar
        status={status}
        syncStatus={syncStatus}
        documentData={documentData}
        onLogout={logout}
        onBack={
          currentView === 'editor' 
            ? handleBackToProject 
            : currentView === 'project' 
              ? handleBackToDashboard 
              : null
        }
      />

      <div className="app-main-layout">
        <Sidebar 
          activeProjectId={projectId || (documentData?.project_id)} 
          onSelectProject={(id) => {
            setProjectId(id);
            setCurrentView('project');
            setDocId(null);
            setDocumentData(null);
          }}
        />
        
        <main className="main-content">
          {currentView === 'dashboard' && (
            <Dashboard 
              onSelectProject={handleSelectProject} 
            />
          )}

          {currentView === 'project' && (
            <ProjectDetail 
              projectId={projectId}
              onSelectDocument={handleSelectDocument}
              onBack={handleBackToDashboard}
            />
          )}

          {currentView === 'editor' && (
            <>
              {isReadOnly && <div className="read-only-banner">View-only mode: Editor limit reached or no permissions.</div>}
              <div className="editor-wrapper">
                <div className="editor-page">
                  <Editor
                    docId={docId}
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
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
