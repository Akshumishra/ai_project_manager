const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const DEFAULT_USER_ID = "1690e959-d72b-40c4-91cc-db03ea809f71";

async function parseJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function createProjectRequest(payload) {
  const response = await fetch(`${API_BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function getProjectRequest(projectId) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}`);
  return parseJsonResponse(response);
}

export async function startRequirementAgentRequest(projectId, userId = DEFAULT_USER_ID, background = null) {
  let url = `${API_BASE_URL}/projects/${projectId}/requirement-agent/start?user_id=${userId}`;
  if (background) url += `&background=${encodeURIComponent(background)}`;
  const response = await fetch(url);
  return parseJsonResponse(response);
}

export async function sendRequirementAgentMessage(projectId, message, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/requirement-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  return parseJsonResponse(response);
}

export async function startTechDocAgentRequest(projectId, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc-agent/start?user_id=${userId}`);
  return parseJsonResponse(response);
}

export async function sendTechDocAgentMessage(projectId, message, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  return parseJsonResponse(response);
}

export async function saveTechDocRequest(projectId, documentMarkdown, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, document_markdown: documentMarkdown }),
  });
  return parseJsonResponse(response);
}
