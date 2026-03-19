import React, { useCallback, useEffect, useState } from 'react'
import { Routes, Route, useNavigate, Navigate, useLocation, useParams } from 'react-router-dom'
import { useDocument } from './hooks/useDocument'
import Toolbar from './components/Toolbar'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './components/Login'
import Register from './components/Register'
import Dashboard from './components/Dashboard'
import ProjectDetail from './components/ProjectDetail'
import ResumeUpload from './components/ResumeUpload'
import Sidebar from './components/Sidebar'

// New Pages
import CreateProjectPage from './pages/CreateProjectPage'
import RequirementAgentPage from './pages/RequirementAgentPage'
import TechDocPage from './pages/TechDocPage'
import AddMember from './pages/AddMember'
import EditorPage from './pages/EditorPage'
import TaskDetailPage from './pages/TaskDetailPage'
import TaskGenerationLoading from './pages/TaskGenerationLoading'
import { getProjectStatusRequest } from './api'

function ProjectDetailRoute() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const checkWorkflow = async () => {
      try {
        const statusData = await getProjectStatusRequest(projectId)
        const workflows = statusData.workflows || []
        const reqStatus = workflows.find(w => w.workflow_name === 'requirement_gathering')?.status
        const techStatus = workflows.find(w => w.workflow_name === 'tech_doc_gathering')?.status

        if (reqStatus !== 'completed') {
          navigate(`/requirement-agent?project_id=${projectId}`, { replace: true })
        } else if (techStatus !== 'completed') {
          navigate(`/tech-doc?project_id=${projectId}`, { replace: true })
        } else {
          setChecking(false)
        }
      } catch (err) {
        console.error('Workflow check failed:', err)
        setChecking(false) // Fallback to allow entry if API fails, or could redirect to error
      }
    }
    if (projectId) checkWorkflow()
  }, [projectId, navigate])

  if (checking) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Verifying project status...</p>
      </div>
    )
  }

  return (
    <ProjectDetail
      projectId={projectId}
      onSelectDocument={(id) => navigate(`/editor/${id}`)}
      onBack={() => navigate('/')}
    />
  )
}

function AppContent() {
  const { user, isAuthenticated, loading, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showRegister, setShowRegister] = useState(false)
  
  const {
    addBlockAfter,
    connectWebSocket,
    role,
    docId, setDocId,
    documentData, setDocumentData,
    loading: docLoading,
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

  const shouldHideSidebar = () => {
    const path = location.pathname || ''
    if (path === '/') return true
    if (path.startsWith('/create-project')) return true
    if (path.startsWith('/requirement-agent')) return true
    if (path.startsWith('/tech-doc')) return true
    if (path.startsWith('/project')) return true
    if (path.startsWith('/editor')) return true
    return false
  }

  const handleSelectProject = useCallback(async (projectId) => {
    try {
      const statusData = await getProjectStatusRequest(projectId)
      const workflows = statusData.workflows || []
      
      const reqStatus = workflows.find(w => w.workflow_name === 'requirement_gathering')?.status
      const techStatus = workflows.find(w => w.workflow_name === 'tech_doc_gathering')?.status

      if (reqStatus !== 'completed') {
        navigate(`/requirement-agent?project_id=${projectId}`)
      } else if (techStatus !== 'completed') {
        navigate(`/tech-doc?project_id=${projectId}`)
      } else {
        navigate(`/project/${projectId}`)
      }
    } catch (err) {
      console.error('Failed to check project status:', err)
      navigate(`/project/${projectId}`)
    }
  }, [navigate])

  const handleDelete = useCallback(async (id) => {
    if (isReadOnly) return
    setDocumentData(prev => {
      const blocks = prev?.blocks || []
      if (blocks.length <= 1) {
        updateBlock(id, '', 'paragraph')
        return prev
      }
      deleteBlock(id)
      return prev
    })
  }, [deleteBlock, isReadOnly, updateBlock, setDocumentData])

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p className="loading-text">Authenticating...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return showRegister ? (
      <Register onToggle={() => setShowRegister(false)} />
    ) : (
      <Login onToggle={() => setShowRegister(true)} />
    )
  }

  if (!user?.is_profile_complete) {
    return <ResumeUpload onComplete={() => navigate('/')} />
  }

  return (
    <div className="app-shell">
      <Toolbar
        status={status}
        syncStatus={syncStatus}
        documentData={documentData}
        onLogout={logout}
        onBack={() => {
          if (location.pathname === '/') return;
          if (location.pathname.startsWith('/project/') || 
              location.pathname.startsWith('/requirement-agent') || 
              location.pathname.startsWith('/tech-doc')) {
            navigate('/');
          } else {
            navigate(-1);
          }
        }}
      />

      <div className="app-main-layout">
        {!shouldHideSidebar() && (
          <Sidebar 
            activeProjectId={documentData?.project_id} 
            onSelectProject={handleSelectProject}
          />
        )}
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard onSelectProject={handleSelectProject} />} />
            <Route path="/create-project" element={<CreateProjectPage />} />
            <Route
              path="/project/:projectId"
              element={<ProjectDetailRoute />}
            />
            <Route path="/requirement-agent" element={<RequirementAgentPage />} />
            <Route path="/tech-doc" element={<TechDocPage />} />
            <Route path="/project/:projectId/add-member" element={<AddMember />} />
            <Route path="/project/:projectId/task/:taskId" element={<TaskDetailPage />} />
            <Route path="/project/:projectId/generating-tasks" element={<TaskGenerationLoading />} />
            <Route path="/editor/:id" element={
              <EditorPage 
                docId={docId}
                setDocId={setDocId}
                loadDocument={loadDocument}
                connectWebSocket={connectWebSocket}
                disconnectWebSocket={disconnectWebSocket}
                documentData={documentData}
                setDocumentData={setDocumentData}
                loading={docLoading}
                lastSnapshotRef={lastSnapshotRef}
                isTypingRef={isTypingRef}
                isSelectingRef={isSelectingRef}
                updateBlock={updateBlock}
                handleDelete={handleDelete}
                addBlockAfter={addBlockAfter}
                isReadOnly={isReadOnly}
              />
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
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
