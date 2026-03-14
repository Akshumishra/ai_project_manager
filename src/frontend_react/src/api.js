const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const DEFAULT_USER_ID = "f07a6a99-ea63-4db6-9524-0cfc6aad00ba";

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

// GET /projects/{id}/requirement-agent  (backend uses GET for start/resume)
export async function startRequirementAgentRequest(projectId, userId = DEFAULT_USER_ID, background = null) {
  let url = `${API_BASE_URL}/projects/${projectId}/requirement-agent?user_id=${encodeURIComponent(userId)}`;
  if (background) url += `&background=${encodeURIComponent(background)}`;
  const response = await fetch(url);
  return parseJsonResponse(response);
}

// POST /projects/{id}/requirement-agent
export async function sendRequirementAgentMessage(projectId, message, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/requirement-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  return parseJsonResponse(response);
}

// GET /projects/{id}/tech-doc-agent/start
export async function startTechDocAgentRequest(projectId, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc-agent/start?user_id=${encodeURIComponent(userId)}`);
  return parseJsonResponse(response);
}

// POST /projects/{id}/tech-doc-agent  — sends current doc state so agent can do precise edits
export async function sendTechDocAgentMessage(projectId, message, currentDocument, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message, current_document_markdown: currentDocument }),
  });
  return parseJsonResponse(response);
}

// POST /projects/{id}/tech-doc  — explicit save (if needed separately)
export async function saveTechDocRequest(projectId, documentMarkdown, userId = DEFAULT_USER_ID) {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/tech-doc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, document_markdown: documentMarkdown }),
  });
  return parseJsonResponse(response);
}
