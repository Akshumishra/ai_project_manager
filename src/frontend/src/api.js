import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getAccessToken = () => localStorage.getItem('access_token');

// Auth endpoints
export const login = (email, password) => api.post('/api/users/login', { email, password });
export const register = (data) => api.post('/api/users/register', data);

// Project API Endpoints (matching backend prefix /api/projects)
export const createProjectRequest = async (payload) => {
  // Ensure payload has the expected fields and structure
  const { data } = await api.post('/api/projects/', payload);
  return data;
};

export const getProjectRequest = async (projectId) => {
  const { data } = await api.get(`/api/projects/${projectId}`);
  return data;
};

export const getProjectStatusRequest = async (projectId) => {
  const { data } = await api.get(`/api/projects/${projectId}/status`);
  return data;
};

export const getProjectTasksRequest = async (projectId) => {
  const { data } = await api.get(`/api/projects/${projectId}/tasks`);
  return data;
};

export const createProjectTaskRequest = async (projectId, payload) => {
  const { data } = await api.post(`/api/projects/${projectId}/tasks`, payload);
  return data;
};

export const updateProjectTaskRequest = async (projectId, taskId, payload) => {
  const { data } = await api.patch(`/api/projects/${projectId}/tasks/${taskId}`, payload);
  return data;
};

export const startRequirementAgentRequest = async (projectId, userId, background = null) => {
  let url = `/api/agent/projects/${projectId}/requirement-agent?user_id=${encodeURIComponent(userId)}`;
  if (background) url += `&background=${encodeURIComponent(background)}`;
  const { data } = await api.get(url);
  return data;
};

export const sendRequirementAgentMessage = async (projectId, message, userId) => {
  const { data } = await api.post(`/api/agent/projects/${projectId}/requirement-agent`, {
    user_id: userId,
    message,
  });
  return data;
};

export const saveRequirementDocRequest = async (projectId, payload) => {
  const { data } = await api.post(`/api/agent/projects/${projectId}/requirement-doc`, payload);
  return data;
};

export const completeRequirementStepRequest = async (projectId, userId = null) => {
  let url = `/api/agent/projects/${projectId}/requirement-complete`;
  if (userId) url += `?user_id=${encodeURIComponent(userId)}`;
  const { data } = await api.patch(url);
  return data;
};

export const startTechDocAgentRequest = async (projectId, userId) => {
  const { data } = await api.get(`/api/agent/projects/${projectId}/tech-doc-agent?user_id=${encodeURIComponent(userId)}`);
  return data;
};

export const sendTechDocAgentMessage = async (projectId, message, currentDocument, userId) => {
  const { data } = await api.post(`/api/agent/projects/${projectId}/tech-doc-agent`, {
    user_id: userId,
    message,
    current_document_markdown: currentDocument,
  });
  return data;
};

export const saveTechDocRequest = async (projectId, documentMarkdown, userId) => {
  const { data } = await api.post(`/api/agent/projects/${projectId}/tech-doc`, {
    user_id: userId,
    document_markdown: documentMarkdown,
  });
  return data;
};

export const generateTasksRequest = async (projectId) => {
  const { data } = await api.post(`/api/task-creator/projects/${projectId}/generate`);
  return data;
};

export const getTaskGenerationStatusRequest = async (projectId) => {
  const { data } = await api.get(`/api/task-creator/projects/${projectId}/status`);
  return data;
};

// Task Assigner API Endpoints
export const startTaskAssignerAgentRequest = async (projectId, userId) => {
  const { data } = await api.get(
    `/api/task-assigner/projects/${projectId}/agent?user_id=${encodeURIComponent(userId)}`
  );
  return data;
};

export const sendTaskAssignerMessageRequest = async (projectId, message, userId) => {
  const { data } = await api.post(`/api/task-assigner/projects/${projectId}/agent`, {
    user_id: userId,
    message,
  });
  return data;
};

export const autoAssignTasksRequest = async (projectId, userId) => {
  const { data } = await api.post(
    `/api/task-assigner/projects/${projectId}/auto-assign?user_id=${encodeURIComponent(userId)}`
  );
  return data;
};

export const updateProjectStatusRequest = async (projectId, status) => {
  const { data } = await api.patch(`/api/projects/${projectId}/status`, { status });
  return data;
};

export default api;
