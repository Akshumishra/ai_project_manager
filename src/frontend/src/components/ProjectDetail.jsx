import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useSearchParams } from 'react-router-dom';
import InviteModal from './InviteModal';
import ProjectMembersModal from './ProjectMembersModal';
import AddTaskModal from './AddTaskModal';
import ProjectHeader from './ProjectHeader';
import ProjectDocuments from './ProjectDocuments';
import ProjectTasks from './ProjectTasks';
import ProjectStandups from './ProjectStandups';
import { useProjectData } from '../hooks/useProjectData';
import { getTaskGenerationStatusRequest } from '../api';

export default function ProjectDetail({ projectId, onSelectDocument, onBack }) {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'documents';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [taskGenStatus, setTaskGenStatus] = useState(null);

  const {
    project, setProject, documents, tasks, members, loading,
    setTasks,
    onTaskSaved,
    handleCreateDocument,
    handleDeleteDocument,
    handleRenameDocument,
    updateProjectStatus,
    refreshTasks,
  } = useProjectData(projectId);

  const handleProjectUpdated = (updatedProject) => {
    if (setProject) setProject(updatedProject);
  };

  useEffect(() => {
    if (!projectId) return;

    let pollInterval;
    const pollStatus = async () => {
      try {
        const data = await getTaskGenerationStatusRequest(projectId);
        const currentStatus = data.status;
        
        // Only show status when actively generating or recently completed
        if (currentStatus === 'generating' || currentStatus === 'started') {
          setTaskGenStatus(currentStatus);
        } else if (currentStatus === 'completed') {
          // If it just transitioned from generating to completed:
          setTaskGenStatus('completed');
          refreshTasks();
          clearInterval(pollInterval);
          setTimeout(() => {
            setTaskGenStatus(null);
          }, 4000);
        } else if (currentStatus === 'failed' || currentStatus === 'not_started' || currentStatus === 'failed_missing_docs') {
          setTaskGenStatus(null);
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    pollStatus();
    pollInterval = setInterval(pollStatus, 3000);

    return () => clearInterval(pollInterval);
  }, [projectId, refreshTasks]);

  const onHandleCreateDocument = async () => {
    const docId = await handleCreateDocument();
    if (docId) onSelectDocument(docId);
  };

  const handleCreateTask = () => {
    setEditingTask(null);
    setIsTaskModalOpen(true);
  };


  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="project-detail-container" style={{ padding: '40px', background: 'var(--gray-50)', minHeight: '100vh', display: 'flex', justifyContent: 'center' }}>
      <div className="document-container" style={{ width: '100%', maxWidth: '1000px', background: 'white', padding: '40px', borderRadius: '24px', boxShadow: 'var(--shadow-md)' }}>

        <ProjectHeader
          user={user}
          project={project}
          onBack={onBack}
          onUpdateStatus={updateProjectStatus}
          onAddMember={() => setIsInviteModalOpen(true)}
          onViewMembers={() => setIsMembersModalOpen(true)}
          onProjectUpdated={handleProjectUpdated}
        />

        <div className="document-inner-scroller" style={{ padding: '0 40px 40px 40px' }}>
          <div className="tabs" style={{ position: 'sticky', top: 0, background: 'white', zIndex: 10, paddingBottom: '16px', paddingTop: '8px' }}>
            <button
              className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveTab('documents')}
            >
              Documents
            </button>
            <button
              className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              Tasks
            </button>
            <button
              className={`tab ${activeTab === 'standups' ? 'active' : ''}`}
              onClick={() => setActiveTab('standups')}
            >
              Standups
            </button>
          </div>

          {activeTab === 'documents' && (
            <ProjectDocuments
              documents={documents}
              onSelectDocument={onSelectDocument}
              onCreateDocument={onHandleCreateDocument}
              onRenameDocument={handleRenameDocument}
              onDeleteDocument={handleDeleteDocument}
            />
          )}

          {activeTab === 'tasks' && (
            <ProjectTasks
              project={project}
              tasks={tasks}
              members={members}
              onCreateTask={handleCreateTask}
              refreshTasks={refreshTasks}
            />
          )}

          {activeTab === 'standups' && (
            <ProjectStandups projectId={projectId} />
          )}
        </div>

        <InviteModal
          projectId={projectId}
          isOpen={isInviteModalOpen}
          onClose={() => setIsInviteModalOpen(false)}
        />

        <ProjectMembersModal
          projectId={projectId}
          isOpen={isMembersModalOpen}
          onClose={() => setIsMembersModalOpen(false)}
        />

        <AddTaskModal
          isOpen={isTaskModalOpen}
          onClose={() => setIsTaskModalOpen(false)}
          projectId={projectId}
          onSuccess={onTaskSaved}
          members={members}
          task={editingTask}
        />
        
        {taskGenStatus && (
          <div style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: taskGenStatus === 'generating' || taskGenStatus === 'started' ? 'var(--brand-600)' : 'var(--success-600)',
            color: 'white',
            padding: '16px 24px',
            borderRadius: '12px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            animation: 'slideUp 0.3s ease-out',
            zIndex: 1000
          }}>
            {(taskGenStatus === 'generating' || taskGenStatus === 'started') && (
              <div className="spinner" style={{ width: '20px', height: '20px', border: '3px solid rgba(255,255,255,0.3)', borderTopColor: 'white', flexShrink: 0 }}></div>
            )}
            {taskGenStatus === 'completed' && (
              <span style={{ fontSize: '20px' }}>✅</span>
            )}
            <span style={{ fontWeight: '500' }}>
              {(taskGenStatus === 'generating' || taskGenStatus === 'started') 
                ? 'Tasks are generating in the background...' 
                : 'Tasks generated successfully!'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
