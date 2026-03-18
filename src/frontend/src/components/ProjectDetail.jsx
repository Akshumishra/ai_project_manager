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

export default function ProjectDetail({ projectId, onSelectDocument, onBack }) {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'documents';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);

  const {
    project, documents, tasks, members, loading,
    setTasks,
    onTaskSaved,
    handleCreateDocument,
    handleDeleteDocument,
    handleRenameDocument,
    updateProjectStatus,
    refreshTasks,
  } = useProjectData(projectId);

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
      </div>
    </div>
  );
}
