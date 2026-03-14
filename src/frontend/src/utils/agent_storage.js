export const setProjectContext = (projectId, context) => {
  sessionStorage.setItem(`project_ctx_${projectId}`, JSON.stringify(context));
};

export const getProjectContext = (projectId) => {
  const data = sessionStorage.getItem(`project_ctx_${projectId}`);
  return data ? JSON.parse(data) : {};
};

export const setAgentState = (projectId, agentType, state) => {
  localStorage.setItem(`agent_${agentType}_${projectId}`, JSON.stringify(state));
};

export const getAgentState = (projectId, agentType) => {
  const data = localStorage.getItem(`agent_${agentType}_${projectId}`);
  return data ? JSON.parse(data) : null;
};

export const clearAgentState = (projectId, agentType) => {
  localStorage.removeItem(`agent_${agentType}_${projectId}`);
};
