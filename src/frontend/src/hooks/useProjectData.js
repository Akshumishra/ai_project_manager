import { useState, useCallback, useEffect } from 'react';
import api, { getProjectTasksRequest } from '../api';

export function useProjectData(projectId) {
  const [documents, setDocuments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${projectId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    }
  }, [projectId]);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getProjectTasksRequest(projectId);
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }
  }, [projectId]);

  const fetchMembers = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${projectId}/members`);
      setMembers(res.data);
    } catch (err) {
      console.error('Failed to fetch members:', err);
    }
  }, [projectId]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      if (projectId) {
        await Promise.all([fetchDocuments(), fetchTasks(), fetchMembers()]);
      }
      setLoading(false);
    };
    load();
  }, [projectId, fetchDocuments, fetchTasks, fetchMembers]);

  const handleCreateDocument = async () => {
    const title = prompt('Document Title:', 'Untitled Document');
    if (!title) return null;
    try {
      const res = await api.post('/api/documents/', { title, project_id: projectId });
      await fetchDocuments();
      return res.data.document_id;
    } catch (err) {
      console.error('Create document failed:', err);
      return null;
    }
  };

  const handleDeleteDocument = async (docId, title) => {
    if (title.includes('Requirement') || title.includes('Technical')) {
      alert('This is a core project document and cannot be deleted.');
      return false;
    }

    if (!window.confirm('Are you sure you want to delete this document?')) return false;
    try {
      await api.delete(`/api/documents/${docId}`);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      return true;
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Failed to delete document');
      return false;
    }
  };

  const handleRenameDocument = async (docId, currentTitle) => {
    const newTitle = prompt('New Document Title:', currentTitle);
    if (!newTitle || newTitle === currentTitle) return false;
    
    try {
      await api.patch(`/api/documents/${docId}`, { title: newTitle });
      setDocuments(prev => prev.map(d => d.id === docId ? { ...d, title: newTitle } : d));
      return true;
    } catch (err) {
      console.error('Failed to rename document:', err);
      alert('Failed to rename document');
      return false;
    }
  };

  return {
    documents, tasks, members, loading,
    setTasks,
    handleCreateDocument,
    handleDeleteDocument,
    handleRenameDocument,
    refreshTasks: fetchTasks,
    refreshMembers: fetchMembers
  };
}
